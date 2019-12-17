import csv
import logging
from cStringIO import StringIO
from hashlib import md5

import psycopg2
from faker import Faker

from pganonymizer.constants import DATABASE_ARGS
from pganonymizer.exceptions import InvalidFieldProvider


fake_data = Faker()
log = logging.getLogger(__name__)


def get_connection(args):
    """
    Return a connection to the database.

    :param args:
    :return: Connection instance
    :rtype: psycopg2.connection
    """
    pg_args = ({name: value for name, value in
                zip(DATABASE_ARGS, (args.dbname, args.user, args.password, args.host, args.port))})
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
    stream = StringIO()
    writer = csv.writer(stream, delimiter='\t', lineterminator='\n', quotechar='|')
    [writer.writerow([(x is None and '\\N' or x) for x in row]) for row in data]
    stream.seek(0)
    return stream


def get_column_dict(columns):
    """
    Return a dictionary with all fields from the table defintion and None as value.

    :param list columns: A list of field definitions from the YAML schema, e.g.:

        [
            {'first_name': {'provider': 'set', 'value': 'Foo'}},
            {'guest_email': {'append': '@localhost', 'provider': 'md5'}},
        ]
    :return: A dictionary containing all fields to be altered with a default value of None, e.g.:

        {'guest_email': None}

    :rtype: dict
    """
    column_dict = {}
    for definition in columns:
        column_name = definition.keys()[0]
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
        column_name = definition.keys()[0]
        column_definition = definition[column_name]
        provider = column_definition.get('provider')
        orig_value = row.get(column_name)
        if not orig_value:
            # Skip the current column if there is no value to be altered
            continue
        if provider.startswith('fake'):
            func_name = provider.split('.')[1]
            func = getattr(fake_data, func_name)
            value = func()
        elif provider == 'md5':
            value = md5(orig_value).hexdigest()
        elif provider == 'clear':
            value = None
        elif provider == 'set':
            value = column_definition.get('value')
        else:
            raise InvalidFieldProvider('Unknown provider for field {}: {}'.format(column_name, provider))
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
    cursor = connection.cursor()
    for table_name in tables:
        log.info('Truncating table "%s"', table_name)
        cursor.execute('TRUNCATE TABLE {table}'.format(table=table_name))
    cursor.close()
