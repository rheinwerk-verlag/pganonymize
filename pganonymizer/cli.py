from __future__ import print_function

import argparse
import logging
import psycopg2
import psycopg2.extras
import sys
import yaml

import faker
from progress.bar import IncrementalBar

from constants import DATABASE_ARGS, DEFAULT_PRIMARY_KEY


logging.basicConfig(format='%(levelname)s: %(message)s')
log = logging.getLogger(__name__)

fake_data = faker.Faker()


def get_column_values(row, columns):
    column_dict = {}
    for definition in columns:
        column_name = definition.keys()[0]
        column_definition = definition[column_name]
        provider = column_definition.get('provider')
        orig_value = row.get(column_name)
        if not orig_value:
            continue
        if provider.startswith('fake'):
            func_name = provider.split('.')[1]
            func = getattr(fake_data, func_name)
            value = func()
        elif provider == 'clear':
            value = None
        elif provider == 'set':
            value = column_definition.get('value')
        else:
            log.warn('Unknown provider for field %s: %s', column_name, provider)
            continue
        column_dict[column_name] = value
    columns = ', '.join(['{column} = %s'.format(column=key, value=value) for key, value in column_dict.items()])
    values = column_dict.values()
    return columns, values


def main():
    parser = argparse.ArgumentParser(description='Anonymize data of a PostgreSQL database')
    parser.add_argument('-v', '--verbose', action='count', help='Increase verbosity')
    parser.add_argument('--schema',  help='A YAML file that contains the anonymization rules', required=True,
                        default='./schema.yml')
    parser.add_argument('--dbname',  help='Name of the database')
    parser.add_argument('--dbschema', default='public', help='Name of the database schema')
    parser.add_argument('--user',  help='Name of the database user')
    parser.add_argument('--password',  default='', help='Password for the database user')
    parser.add_argument('--host', help='Database hostname', default='localhost')
    parser.add_argument('--port', help='Port of the database', default='5432')
    args = parser.parse_args()

    if args.verbose:
        log.setLevel(logging.DEBUG)

    schema = yaml.load(open(args.schema), Loader=yaml.FullLoader)

    pg_args = ({name: value for name, value in zip(DATABASE_ARGS, (
        args.dbname, 
        args.user, 
        args.password, 
        args.host, 
        args.port))})
    pg_schema = args.dbschema

    with psycopg2.connect(**pg_args) as connection:
        connection.autocommit = True
        with connection.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
            
            for table_name in schema.get('truncate', []):
                log.info('Truncating table "%s"', table_name)
                cursor.execute('TRUNCATE TABLE {table}'.format(table=table_name))

            for definition in schema.get('tables', []):
                table_name = definition.keys()[0]
                table_defintion = definition[table_name]
                columns = table_defintion.get('fields', [])
                primary_key = table_defintion.get('primary_key', DEFAULT_PRIMARY_KEY)

                sql = "SELECT COUNT(*) FROM {table};".format(table=table_name)
                cursor.execute(sql)
                total_count = cursor.fetchone()[0]
                log.info('Found table defintion "%s"', table_name)
                sql = "SELECT * FROM {table};".format(table=table_name)
                cursor.execute(sql)
                bar = IncrementalBar('Anonymizing', max=total_count)

                for row in cursor.fetchall():
                    columns_to_update, values = get_column_values(row, columns)
                    sql = "UPDATE {table} SET {columns} WHERE {primary_key} = {id};".format(
                        table=table_name,
                        columns=columns_to_update,
                        primary_key=primary_key,
                        id=row['id']
                    )
                    bar.next()
                    cursor.execute(sql, values)
                bar.finish()


if __name__ == '__main__':
    main()
