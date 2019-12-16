from __future__ import print_function

import argparse
import csv
import hashlib
import logging
import sys
import time
from cStringIO import StringIO

import faker
import psycopg2
import psycopg2.extras
import yaml
from progress.bar import IncrementalBar

from constants import DATABASE_ARGS, DEFAULT_PRIMARY_KEY


fake_data = faker.Faker()
logging.basicConfig(format='%(levelname)s: %(message)s')
log = logging.getLogger(__name__)


def data2csv(data):
    si = StringIO()
    cw = csv.writer(si, delimiter='\t', lineterminator='\n')
    [cw.writerow([(x is None and '\\N' or x) for x in row]) for row in data]
    si.seek(0)
    return si


def get_column_dict(columns):
    column_dict = {}
    for definition in columns:
        column_name = definition.keys()[0]
        column_dict[column_name] = None
    return column_dict


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
        elif provider == 'md5':
            value = hashlib.md5(orig_value).hexdigest()
        elif provider == 'clear':
            value = None
        elif provider == 'set':
            value = column_definition.get('value')
        else:
            log.warn('Unknown provider for field %s: %s', column_name, provider)
            continue

        append = column_definition.get('append')
        if append:
            value = value + append

        column_dict[column_name] = value
    return column_dict



def main():
    parser = argparse.ArgumentParser(description='Anonymize data of a PostgreSQL database')
    parser.add_argument('-v', '--verbose', action='count', help='Increase verbosity')
    parser.add_argument('--schema',  help='A YAML file that contains the anonymization rules', required=True,
                        default='./schema.yml')
    parser.add_argument('--dbname',  help='Name of the database')
    parser.add_argument('--user',  help='Name of the database user')
    parser.add_argument('--password',  default='', help='Password for the database user')
    parser.add_argument('--host', help='Database hostname', default='localhost')
    parser.add_argument('--port', help='Port of the database', default='5432')
    parser.add_argument('--dry-run', action='store_true', help='Dont commit changes made on the database', default=False)
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

    start_time = time.time()

    connection = psycopg2.connect(**pg_args)    

    cursor = connection.cursor()            
    for table_name in schema.get('truncate', []):
        log.info('Truncating table "%s"', table_name)
        cursor.execute('TRUNCATE TABLE {table}'.format(table=table_name))
    cursor.close()

    for definition in schema.get('tables', []):
        table_name = definition.keys()[0]
        table_defintion = definition[table_name]
        columns = table_defintion.get('fields', [])

        column_dict = get_column_dict(columns)

        primary_key = table_defintion.get('primary_key', DEFAULT_PRIMARY_KEY)

        sql = "SELECT COUNT(*) FROM {table};".format(table=table_name)
        cursor = connection.cursor()
        cursor.execute(sql)
        total_count = cursor.fetchone()[0]
        log.info('Found table defintion "%s"', table_name)
        cursor.close()

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
            
        cursor.close()

        new_data = data2csv(data)

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
        
        cursor.execute(sql)
        cursor.execute('DROP TABLE source;')
        cursor.close()

        if args.verbose:
            bar.finish()

    if not args.dry_run:
        connection.commit()
    connection.close()

    end_time = time.time()
    log.info('Anonymization took {:.2f}s.'.format(end_time - start_time))


if __name__ == '__main__':
    main()
