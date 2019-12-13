from __future__ import print_function

import argparse


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


if __name__ == '__main__':
    main()