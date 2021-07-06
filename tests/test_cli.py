from mock import call, patch, Mock
from pganonymizer.cli import get_arg_parser, main
import pytest
import shlex
from argparse import Namespace


class TestCli:
    @patch('pganonymizer.utils.psycopg2.connect')
    @pytest.mark.parametrize('cli_args, expected', [
                                                   ['--host localhost --port 5432 --user root --password my-cool-password --dbname db --schema ./tests/schemes/valid_schema.yml -v --init-sql "set work_mem=\'1GB\'"', # noqa
                                                    Namespace(verbose=1, list_providers=False, schema='./tests/schemes/valid_schema.yml', dbname='db', user='root', password='my-cool-password', host='localhost', port='5432', dry_run=False, dump_file=None, init_sql="set work_mem='1GB'") # noqa
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
        expected_execute_calls = [
            call("set work_mem='1GB'"),
            call('TRUNCATE TABLE django_session;'),
            call('SELECT COUNT(*) FROM auth_user;'),
            call('SELECT "id", "first_name", "last_name", "email" FROM "auth_user";'),
            call('CREATE TEMP TABLE "tmp_auth_user" AS SELECT "id", "first_name", "last_name", "email"\n                    FROM "auth_user" WITH NO DATA'), # noqa
            call('CREATE INDEX ON "tmp_auth_user" ("id")'),
            call('UPDATE "auth_user" t SET "first_name" = s."first_name", "last_name" = s."last_name", "email" = s."email" FROM "tmp_auth_user" s WHERE t."id" = s."id";') # noqa
        ]
        assert mock_cursor.execute.call_args_list == expected_execute_calls
