from __future__ import print_function

import argparse
import logging
import psycopg2
import yaml

from constants import DATABASE_ARGS


log = logging.getLogger(__name__)


def truncate_table(cursor, name):
    log.info('Truncating table %s', name)
    cursor.execute('TRUNCATE TABLE {table}'.format(table=name))


def main():
    parser = argparse.ArgumentParser(description='Process some integers.')
    parser.add_argument('--schema',  help='A YAML file that contains the anonymization rules', required=True,
                        default='./schema.yml')
    parser.add_argument('--dbname',  help='Name of the database')
    parser.add_argument('--user',  help='')
    parser.add_argument('--password',  default='', help='')
    parser.add_argument('--host', help='', default='localhost')
    parser.add_argument('--port', help='', default='5432')
    args = parser.parse_args()
    print(args)

    schema = yaml.load(open(args.schema), Loader=yaml.FullLoader)
    truncate_tables = schema['truncate']

    pg_args = ({name: value for name, value in zip(DATABASE_ARGS, (args.dbname, args.user, args.password, args.host, args.port))})

    with psycopg2.connect(**pg_args) as connection:
        connection.autocommit = True
        with connection.cursor() as cursor:
            cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';")
            for table in cursor.fetchall():
                #print(table)
                #print('*' * 20)
                cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_schema = 'public' and table_name = %s", table)
                #for column in cursor.fetchall():
                #    print(column)

    
            for table in truncate_tables:
                truncate_table(cursor, table)


if __name__ == '__main__':
    main()