from __future__ import print_function

import argparse
import psycopg2
import yaml

from constants import DATABASE_ARGS


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

    pg_args = ({name: value for name, value in zip(DATABASE_ARGS, (args.dbname, args.user, args.password, args.host, args.port))})

    with psycopg2.connect(**pg_args) as connection:
        print("TRUE")

    schema = yaml.load(open(args.schema), Loader=yaml.FullLoader)
    print(schema)


if __name__ == '__main__':
    main()