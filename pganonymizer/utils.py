"""Helper methods"""

from __future__ import absolute_import

import csv
import logging
import re
import subprocess

import psycopg2
import psycopg2.extras
from progress.bar import IncrementalBar
from psycopg2.errors import BadCopyFileFormat, InvalidTextRepresentation
from six import StringIO

from pganonymizer.constants import COPY_DB_DELIMITER, DEFAULT_PRIMARY_KEY
from pganonymizer.exceptions import BadDataFormat
from pganonymizer.providers import get_provider


def anonymize_tables(connection, definitions, verbose=False):
    """
    Anonymize a list of tables according to the schema definition.

    :param connection: A database connection instance.
    :param list definitions: A list of table definitions from the YAML schema.
    :param bool verbose: Display logging information and a progress bar.
    """
    for definition in definitions:
        table_name = list(definition.keys())[0]
        logging.info('Found table definition "%s"', table_name)
        table_definition = definition[table_name]
        columns = table_definition.get('fields', [])
        excludes = table_definition.get('excludes', [])
        column_dict = get_column_dict(columns)
        primary_key = table_definition.get('primary_key', DEFAULT_PRIMARY_KEY)
        total_count = get_table_count(connection, table_name)
        data, table_columns = build_data(connection, table_name, columns, excludes, total_count, verbose)
        import_data(connection, column_dict, table_name, table_columns, primary_key, data)


def build_data(connection, table, columns, excludes, total_count, verbose=False):
    """
    Select all data from a table and return it together with a list of table columns.

    :param connection: A database connection instance.
    :param str table: Name of the table to retrieve the data.
    :param list columns: A list of table fields
    :param list[dict] excludes: A list of exclude definitions.
    :param int total_count: The amount of rows for the current table
    :param bool verbose: Display logging information and a progress bar.
    :return: A tuple containing the data list and a complete list of all table columns.
    :rtype: (list, list)
    """
    if verbose:
        progress_bar = IncrementalBar('Anonymizing', max=total_count)
    sql = "SELECT * FROM {table};".format(table=table)
    cursor = connection.cursor(cursor_factory=psycopg2.extras.DictCursor, name='fetch_large_result')
    cursor.execute(sql)
    data = []
    table_columns = None
    while True:
        records = cursor.fetchmany(size=2000)
        if not records:
            break
        for row in records:
            row_column_dict = {}
            if not row_matches_excludes(row, excludes):
                row_column_dict = get_column_values(row, columns)
                for key, value in row_column_dict.items():
                    row[key] = value
            if verbose:
                progress_bar.next()
            table_columns = row.keys()
            if not row_column_dict:
                continue
            data.append(row.values())
    if verbose:
        progress_bar.finish()
    cursor.close()
    return data, table_columns


def row_matches_excludes(row, excludes=None):
    """
    Check whether a row matches a list of field exclusion patterns.

    :param list row: The data row
    :param list excludes: A list of field exclusion roles, e.g.:
        [
            {'email': ['\\S.*@example.com', '\\S.*@foobar.com', ]}
        ]
    :return: True or False
    :rtype: bool
    """
    excludes = excludes if excludes else []
    for definition in excludes:
        column = list(definition.keys())[0]
        for exclude in definition.get(column, []):
            pattern = re.compile(exclude, re.IGNORECASE)
            if row[column] is not None and pattern.match(row[column]):
                return True
    return False


def copy_from(connection, data, table, columns):
    """
    Copy the data from a table to a temporary table.

    :param connection: A database connection instance.
    :param list data: The data of a table.
    :param str table: Name of the temporary table used for copying the data.
    :param list columns: All columns of the current table.
    :raises BadDataFormat: If the data cannot be imported due to a invalid format.
    """
    new_data = data2csv(data)
    cursor = connection.cursor()
    try:
        cursor.copy_from(new_data, table, sep=COPY_DB_DELIMITER, null='\\N', columns=columns)
    except (BadCopyFileFormat, InvalidTextRepresentation) as exc:
        raise BadDataFormat(exc)
    cursor.close()


def import_data(connection, column_dict, source_table, table_columns, primary_key, data):
    """
    Import the temporary and anonymized data to a temporary table and write the changes back.

    :param connection: A database connection instance.
    :param dict column_dict: A dictionary with all columns (specified by the schema definition) and a default value of
      None.
    :param str source_table: Name of the table to be anonymized.
    :param list table_columns: A list of all table columns.
    :param str primary_key: Name of the tables primary key.
    :param list data: The table data.
    """
    primary_key = primary_key if primary_key else DEFAULT_PRIMARY_KEY
    cursor = connection.cursor()
    cursor.execute('CREATE TEMP TABLE source(LIKE %s INCLUDING ALL) ON COMMIT DROP;' % source_table)
    copy_from(connection, data, 'source', table_columns)
    set_columns = ', '.join(['{column} = s.{column}'.format(column=key) for key in column_dict.keys()])
    sql = (
        'UPDATE {table} t '
        'SET {columns} '
        'FROM source s '
        'WHERE t.{primary_key} = s.{primary_key};'
    ).format(table=source_table, primary_key=primary_key, columns=set_columns)
    cursor.execute(sql)
    cursor.execute('DROP TABLE source;')
    cursor.close()


def get_connection(pg_args):
    """
    Return a connection to the database.

    :param pg_args:
    :return: A psycopg connection instance
    :rtype: psycopg2.connection
    """
    return psycopg2.connect(**pg_args)


def get_table_count(connection, table):
    """
    Return the number of table entries.

    :param connection: A database connection instance
    :param str table: Name of the database table
    :return: The number of table entries
    :rtype: int
    """
    sql = 'SELECT COUNT(*) FROM {table};'.format(table=table)
    cursor = connection.cursor()
    cursor.execute(sql)
    total_count = cursor.fetchone()[0]
    cursor.close()
    return total_count


def data2csv(data):
    """
    Return a string buffer, that contains delimited data.

    :param list data: A list of values
    :return: A stream that contains tab delimited csv data
    :rtype: StringIO
    """
    buf = StringIO()
    writer = csv.writer(buf, delimiter=COPY_DB_DELIMITER, lineterminator='\n', quotechar='~')
    [writer.writerow([(x is None and '\\N' or (x.strip() if type(x) == str else x)) for x in row]) for row in data]
    buf.seek(0)
    return buf


def get_column_dict(columns):
    """
    Return a dictionary with all fields from the table definition and None as value.

    :param list columns: A list of field definitions from the YAML schema, e.g.:
        [
            {'first_name': {'provider': 'set', 'value': 'Foo'}},
            {'guest_email': {'append': '@localhost', 'provider': 'md5'}},
        ]
    :return: A dictionary containing all fields to be altered with a default value of None, e.g.::
        {'guest_email': None}
    :rtype: dict
    """
    column_dict = {}
    for definition in columns:
        column_name = list(definition.keys())[0]
        column_dict[column_name] = None
    return column_dict


def get_column_values(row, columns):
    """
    Return a dictionary for a single data row, with altered data.

    :param psycopg2.extras.DictRow row: A data row from the current table to be altered
    :param list columns: A list of table columns with their provider rules, e.g.:
        [
            {'guest_email': {'append': '@localhost', 'provider': 'md5'}}
        ]
    :return: A dictionary with all fields that have to be altered and their value for a single data row, e.g.:
        {'guest_email': '12faf5a9bb6f6f067608dca3027c8fcb@localhost'}
    :rtype: dict
    """
    column_dict = {}
    for definition in columns:
        column_name = list(definition.keys())[0]
        column_definition = definition[column_name]
        provider_config = column_definition.get('provider')
        orig_value = row.get(column_name)
        if not orig_value:
            # Skip the current column if there is no value to be altered
            continue
        provider = get_provider(provider_config)
        value = provider.alter_value(orig_value)
        append = column_definition.get('append')
        if append:
            value = value + append
        column_dict[column_name] = value
    return column_dict


def truncate_tables(connection, tables):
    """
    Truncate a list of tables.

    :param connection: A database connection instance
    :param list[str] tables: A list of table names
    """
    if not tables:
        return
    cursor = connection.cursor()
    table_names = ', '.join(tables)
    logging.info('Truncating tables "%s"', table_names)
    cursor.execute('TRUNCATE TABLE {tables};'.format(tables=table_names))
    cursor.close()


def create_database_dump(filename, db_args):
    """
    Create a dump file from the current database.

    :param str filename: Path to the dumpfile that should be created
    :param dict db_args: A dictionary with database related information
    """
    arguments = '-d {dbname} -U {user} -h {host} -p {port}'.format(**db_args)
    cmd = 'pg_dump -p -Fc -Z 9 {args} -f {filename}'.format(
        args=arguments,
        filename=filename
    )
    logging.info('Creating database dump file "%s"', filename)
    subprocess.run(cmd, shell=True)
