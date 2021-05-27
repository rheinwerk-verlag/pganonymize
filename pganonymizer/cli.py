"""Commandline implementation"""

from __future__ import absolute_import, print_function

import argparse
import logging
import sys
import time

import yaml

from pganonymizer.constants import DEFAULT_SCHEMA_FILE
from pganonymizer.providers import list_provider_classes
from pganonymizer.utils import anonymize_tables, create_database_dump, get_connection, truncate_tables


def main():
    """Main method"""
    parser = argparse.ArgumentParser(description='Anonymize data of a PostgreSQL database')
    parser.add_argument('-v', '--verbose', action='count', help='Increase verbosity')
    parser.add_argument('-l', '--list-providers', action='store_true', help='Show a list of all available providers',
                        default=False)
    parser.add_argument('--schema', help='A YAML schema file that contains the anonymization rules',
                        default=DEFAULT_SCHEMA_FILE)
    parser.add_argument('--dsn', help='Connection string (dsn) for the database, e.g. '
                                      'postgresql://localhost/dbname?user=username&password=secret')
    parser.add_argument('--dry-run', action='store_true', help='Don\'t commit changes made on the database',
                        default=False)
    parser.add_argument('--dump-file', help='Create a database dump file with the given name')

    args = parser.parse_args()

    loglevel = logging.WARNING
    if args.verbose:
        loglevel = logging.DEBUG
    logging.basicConfig(format='%(levelname)s: %(message)s', level=loglevel)

    if args.list_providers:
        list_provider_classes()
        sys.exit(0)

    schema = yaml.load(open(args.schema), Loader=yaml.FullLoader)

    connection = get_connection(args.dsn)

    start_time = time.time()
    truncate_tables(connection, schema.get('truncate', []))
    anonymize_tables(connection, schema.get('tables', []), verbose=args.verbose)

    if args.dump_file:
        create_database_dump(args.dump_file, connection)

    if not args.dry_run:
        connection.commit()
    connection.close()

    end_time = time.time()
    logging.info('Anonymization took {:.2f}s'.format(end_time - start_time))


if __name__ == '__main__':
    main()
