from __future__ import print_function

import argparse
import logging
import time

import psycopg2
import psycopg2.extras
import yaml
from progress.bar import IncrementalBar

from pganonymizer.constants import DEFAULT_PRIMARY_KEY
from pganonymizer.utils import (
    data2csv, get_column_dict, get_column_values, get_connection, get_table_count, truncate_tables)

logging.basicConfig(format='%(levelname)s: %(message)s')
log = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description='Anonymize data of a PostgreSQL database')
    parser.add_argument('-v', '--verbose', action='count', help='Increase verbosity')
    parser.add_argument('--schema', help='A YAML file that contains the anonymization rules', required=True,
                        default='./schema.yml')
    parser.add_argument('--dbname', help='Name of the database')
    parser.add_argument('--user', help='Name of the database user')
    parser.add_argument('--password', default='', help='Password for the database user')
    parser.add_argument('--host', help='Database hostname', default='localhost')
    parser.add_argument('--port', help='Port of the database', default='5432')
    parser.add_argument('--dry-run', action='store_true', help='Dont commit changes made on the database',
                        default=False)
    args = parser.parse_args()

    if args.verbose:
        log.setLevel(logging.DEBUG)

    schema = yaml.load(open(args.schema), Loader=yaml.FullLoader)
    connection = get_connection(args)

    start_time = time.time()
    truncate_tables(connection, schema.get('truncate', []))

    for definition in schema.get('tables', []):
        table_name = definition.keys()[0]
        table_defintion = definition[table_name]
        columns = table_defintion.get('fields', [])
        column_dict = get_column_dict(columns)
        primary_key = table_defintion.get('primary_key', DEFAULT_PRIMARY_KEY)

        total_count = get_table_count(connection, table_name)
        log.info('Found table defintion "%s"', table_name)

        sql = "SELECT * FROM {table};".format(table=table_name)
        cursor = connection.cursor(cursor_factory=psycopg2.extras.DictCursor, name='fetch_large_result')
        cursor.execute(sql)

        if args.verbose:
            bar = IncrementalBar('Anonymizing', max=total_count)

        data = []
        table_columns = None

        while True:
            records = cursor.fetchmany(size=2000)
            if not records:
                break
            for row in records:
                row_column_dict = get_column_values(row, columns)
                for key, value in row_column_dict.items():
                    row[key] = value
                if args.verbose:
                    bar.next()
                table_columns = row.keys()
                if not row_column_dict:
                    continue
                data.append(row.values())

        if args.verbose:
            bar.finish()
        cursor.close()

        log.info('Loading data')
        new_data = data2csv(data)

        log.info('Persisting temporary data')
        cursor = connection.cursor()
        cursor.execute('CREATE TEMP TABLE source(LIKE %s INCLUDING ALL) ON COMMIT DROP;' % table_name)
        cursor.copy_from(new_data, 'source', columns=table_columns)

        set_columns = ', '.join(['{column} = s.{column}'.format(column=key) for key in column_dict.keys()])
        sql = '''
            UPDATE {table} t
                SET {columns}
            FROM source s
            WHERE t.{primary_key} = s.{primary_key}
        '''.format(table=table_name, primary_key=primary_key, columns=set_columns)

        log.info('Writing data back')
        cursor.execute(sql)
        cursor.execute('DROP TABLE source;')
        cursor.close()

    if not args.dry_run:
        connection.commit()
    connection.close()

    end_time = time.time()
    log.info('Anonymization took {:.2f}s.'.format(end_time - start_time))


if __name__ == '__main__':
    main()
