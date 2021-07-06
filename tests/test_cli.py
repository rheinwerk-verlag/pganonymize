from mock import call, patch, Mock
from psycopg2.sql import Composed, Identifier, SQL
from pganonymizer.cli import get_arg_parser, main
import pytest
import shlex
from argparse import Namespace


class TestCli:
    @patch('pganonymizer.utils.psycopg2.connect')
    @pytest.mark.parametrize('cli_args, expected', [
                                                   ['--host localhost --port 5432 --user root --password my-cool-password --dbname db --schema ./tests/schemes/valid_schema.yml -v --init-sql "set work_mem=\'1GB\'"',  # noqa
                                                    Namespace(verbose=1, list_providers=False, schema='./tests/schemes/valid_schema.yml', dbname='db', user='root', password='my-cool-password', host='localhost', port='5432', dry_run=False, dump_file=None, init_sql="set work_mem='1GB'")  # noqa
                                                    ]
    ])
    def test_cli_args(self, patched_connect, cli_args, expected):
        arg_parser = get_arg_parser()
        parsed_args = arg_parser.parse_args(shlex.split(cli_args))
        assert parsed_args == expected
        mock_cursor = Mock()
        mock_cursor.fetchone.return_value = [0]
        mock_cursor.fetchmany.return_value = None

        connection = Mock()
        connection.cursor.return_value = mock_cursor
        patched_connect.return_value = connection
        main(parsed_args)
        expected_execute_calls = [call("set work_mem='1GB'"),
                                  call(Composed([SQL('TRUNCATE TABLE '), Composed([Identifier('django_session')])])),
                                  call(Composed([SQL('SELECT COUNT(*) FROM '), Identifier('auth_user')])),
                                  call(Composed([SQL('SELECT '), Composed([Identifier('id'), SQL(', '),
                                                                           Identifier('first_name'),
                                                                           SQL(', '), Identifier(
                                                                               'last_name'), SQL(', '),
                                                                           Identifier('email')]),
                                                 SQL(' FROM '), Identifier('auth_user')])),
                                  call(Composed([SQL('CREATE TEMP TABLE '), Identifier('tmp_auth_user'),
                                                 SQL(' AS SELECT '),
                                                 Composed([Identifier('id'), SQL(', '), Identifier('first_name'), SQL(
                                                     ', '), Identifier('last_name'), SQL(', '), Identifier('email')]),
                                                 SQL('\n                    FROM '), Identifier('auth_user'),
                                                 SQL(' WITH NO DATA')])),
                                  call(Composed([SQL('CREATE INDEX ON '), Identifier(
                                      'tmp_auth_user'), SQL(' ('), Identifier('id'), SQL(')')])),
                                  call(Composed([SQL('UPDATE '), Identifier('auth_user'), SQL(' t SET '),
                                                 Composed([
                                                     Composed([Identifier('first_name'), SQL(' = s.'),
                                                              Identifier('first_name')]), SQL(', '),
                                                     Composed([Identifier('last_name'), SQL(' = s.'),
                                                               Identifier('last_name')]), SQL(', '),
                                                     Composed([Identifier('email'), SQL(' = s.'),
                                                               Identifier('email')])]),
                                                 SQL(' FROM '), Identifier('tmp_auth_user'), SQL(' s WHERE t.'),
                                                 Identifier('id'), SQL(' = s.'), Identifier('id')]))]
        assert mock_cursor.execute.call_args_list == expected_execute_calls
