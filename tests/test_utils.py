import math
import os
from collections import OrderedDict, namedtuple
from unittest import mock

import pytest
from mock import ANY, Mock, call, patch

from tests.utils import quote_ident

from pganonymize.utils import (anonymize_tables, build_and_then_import_data, create_database_dump,
                               get_column_values, get_connection, import_data, load_config, truncate_tables)


class TestGetConnection:

    @patch('pganonymize.utils.psycopg2.connect')
    def test(self, mock_connect):
        connection_data = {
            'dbname': 'test',
            'user': 'user',
            'password': 'password',
            'host': 'localhost',
            'port': 5432
        }
        get_connection(connection_data)
        mock_connect.assert_called_once_with(**connection_data)


class TestTruncateTables:
    @patch('psycopg2.extensions.quote_ident', side_effect=quote_ident)
    @pytest.mark.parametrize('tables, expected', [
        [('table_a', 'table_b', 'CAPS_TABLe'), 'TRUNCATE TABLE "table_a", "table_b", "CAPS_TABLe"'],
        [(), None],
    ])
    def test(self, quote_ident, tables, expected):
        mock_cursor = Mock()
        connection = Mock()
        connection.cursor.return_value = mock_cursor
        truncate_tables(connection, tables)
        if tables:
            connection.cursor.assert_called_once()
            assert mock_cursor.execute.call_args_list == [call(expected)]
            mock_cursor.close.assert_called_once()
        else:
            connection.cursor.assert_not_called()
            mock_cursor.execute.assert_not_called()
            mock_cursor.close.assert_not_called()


class TestImportData:
    @patch('psycopg2.extensions.quote_ident', side_effect=quote_ident)
    @patch('pgcopy.copy.util')
    @patch('pgcopy.copy.inspect')
    @pytest.mark.parametrize('tmp_table, cols, data', [
        ['public.src_tbl', ('id', 'location'), [
            OrderedDict([("id", 0), ('location', 'Jerusalem')]),
            OrderedDict([("id", 1), ('location', 'New York')]),
            OrderedDict([("id", 2), ('location', 'Moscow')]),
        ]]
    ])
    def test(self, inspect, util, quote_ident, tmp_table, cols, data):
        mock_cursor = Mock()

        connection = Mock()
        connection.cursor.return_value = mock_cursor
        connection.encoding = 'UTF8'
        Record = namedtuple("Record", "attname,type_category,type_name,type_mod,not_null,typelem")

        inspect.get_types.return_value = {
            'id': Record(attname='id', type_category='N', type_name='int8', type_mod=-1, not_null=False, typelem=0),
            'location': Record(attname='location', type_category='S', type_name='varchar', type_mod=259,
                               not_null=False, typelem=0)
        }

        import_data(connection, tmp_table, cols, data)

        # assert connection.cursor.call_count == mock_cursor.close.call_count

        mock_cursor.copy_expert.assert_called_once()
        expected = [call('COPY "public"."src_tbl" ("id", "location") FROM STDIN WITH BINARY', ANY)]
        assert mock_cursor.copy_expert.call_args_list == expected

    @patch('pganonymize.utils.CopyManager')
    @patch('psycopg2.extensions.quote_ident', side_effect=quote_ident)
    def test_anonymize_tables(self, quote_ident, copy_manager):
        mock_cursor = Mock()
        mock_cursor.fetchone.return_value = [2]
        mock_cursor.fetchmany.side_effect = [
            [
                OrderedDict([("first_name", None),
                             ("json_column", None)
                             ]),
                OrderedDict([("first_name", "exclude me"),
                             ("json_column", {"field1": "foo"})
                             ]),
                OrderedDict([("first_name", "John Doe"),
                             ("json_column", {"field1": "foo"})
                             ]),
                OrderedDict([("first_name", "John Doe"),
                             ("json_column", {"field2": "bar"})
                             ])
            ]
        ]
        cmm = Mock()
        copy_manager.return_value = cmm
        copy_manager.copy.return_value = []

        connection = Mock()
        connection.cursor.return_value = mock_cursor
        definitions = []
        anonymize_tables(connection, definitions, verbose=True)

        assert connection.cursor.call_count == 0
        assert mock_cursor.close.call_count == 0
        assert copy_manager.copy.call_count == 0

        definitions = [
            {
                "auth_user": {
                    "primary_key": "id",
                    "chunk_size": 5000,
                    "excludes": [
                        {'first_name': ['exclude']}
                    ],
                    "fields": [
                        {
                            "first_name": {
                                "provider": {
                                    "name": "set",
                                    "value": "dummy name"
                                },
                                "append": "append-me"
                            }
                        },
                        {
                            "json_column.field1": {
                                "provider": {
                                    "name": "set",
                                    "value": "dummy json field1"
                                }
                            }
                        },
                        {
                            "json_column.field2": {
                                "provider": {
                                    "name": "set",
                                    "value": "dummy json field2"
                                }
                            }
                        },
                    ],
                    'search': 'first_name == "John"'
                }
            }
        ]

        anonymize_tables(connection, definitions, verbose=True)
        assert connection.cursor.call_count == mock_cursor.close.call_count
        assert copy_manager.call_args_list == [call(connection, 'tmp_auth_user', ['id', 'first_name', 'json_column'])]
        assert cmm.copy.call_count == 1
        assert cmm.copy.call_args_list == [call([['dummy nameappend-me', b'{"field1": "dummy json field1"}'],
                                                 ['dummy nameappend-me', b'{"field2": "dummy json field2"}']])]


class TestBuildAndThenImport:
    @patch('psycopg2.extensions.quote_ident', side_effect=quote_ident)
    @patch('pganonymize.utils.CopyManager')
    @pytest.mark.parametrize('table, primary_key, columns, total_count, chunk_size', [
        ['src_tbl', 'id', [{'col1': {'provider': {'name': 'md5'}}},
                           {'COL2': {'provider': {'name': 'md5'}}}], 10, 3]
    ])
    def test(self, quote_ident, copy_manager, table, primary_key, columns, total_count, chunk_size):
        fake_record = dict.fromkeys([list(definition.keys())[0] for definition in columns], "")
        records = [
            [fake_record for row in range(0, chunk_size)] for x in range(0, int(math.ceil(total_count / chunk_size)))
        ]

        mock_cursor = Mock()
        mock_cursor.fetchmany.side_effect = records
        mock_cursor.fetchone.return_value = [{}]

        connection = Mock()
        connection.cursor.return_value = mock_cursor

        build_and_then_import_data(connection, table, primary_key, columns, None, None, total_count, chunk_size)

        expected_execute_calls = [call('SELECT "id", "col1", "COL2" FROM "src_tbl"'),
                                  call(
                                      'CREATE TEMP TABLE "tmp_src_tbl" AS SELECT "id", "col1", "COL2"\n                    FROM "src_tbl" WITH NO DATA'),  # noqa
                                  call('CREATE INDEX ON "tmp_src_tbl" ("id")'),
                                  call('UPDATE "src_tbl" t SET "col1" = s."col1", "COL2" = s."COL2" FROM "tmp_src_tbl" s WHERE t."id" = s."id"')]  # noqa
        assert mock_cursor.execute.call_args_list == expected_execute_calls

    @patch('pganonymize.utils.CopyManager')
    def test_column_format(self, copy_manager):
        columns = [
            {
                "first_name": {
                    "format": "hello-{pga_value}-world",
                    "provider": {
                        "name": "set",
                        "value": "dummy name"
                    }
                }
            },
            {
                "phone": {
                    "format": "+65-{pga_value}",
                    "provider": {
                        "name": "md5",
                        "as_number": True
                    }
                }
            },
            {
                "templated": {
                    "format": "{pga_value}-{phone}-{first_name}",
                    "provider": {
                        "name": "set",
                        "value": "hello"
                    }
                }
            }
        ]
        row = OrderedDict([("first_name", "John Doe"), ("phone", "2354223432"), ("templated", "")])
        result = get_column_values(row, columns)
        expected = {'first_name': 'hello-dummy name-world',
                    'phone': '+65-91042872',
                    'templated': "hello-+65-91042872-hello-dummy name-world"}
        assert result == expected


class TestCreateDatabaseDump:

    @patch('pganonymize.utils.subprocess.call')
    def test(self, mock_call):
        create_database_dump('/tmp/dump.gz', {'dbname': 'database', 'user': 'foo', 'host': 'localhost', 'port': 5432})
        mock_call.assert_called_once_with('pg_dump -Fc -Z 9 -d database -U foo -h localhost -p 5432 -f /tmp/dump.gz',
                                          shell=True)


class TestConfigLoader:

    @pytest.mark.parametrize('file, envs, expected', [
        ['./tests/schemes/valid_schema.yml', {}, {
            'tables': [{'auth_user': {'primary_key': 'id', 'chunk_size': 5000, 'fields': [
                {'first_name': {'provider': {'name': 'fake.first_name'}}},
                {'last_name': {'provider': {'name': 'set', 'value': 'Bar'}}},
                {'email': {'provider': {'name': 'md5'}, 'append': '@localhost'}}
            ], 'excludes': [{'email': ['\\S[^@]*@example\\.com']}]}}], 'truncate': ['django_session']}],
        ['./tests/schemes/schema_with_env_variables.yml', {
            "TEST_CHUNK_SIZE": "123",
            "TEST_PRIMARY_KEY": "foo-bar",
            "PRESENT_WORLD_NAME": "beautiful world",
            "COMPANY_ID": "42",
            "USER_TO_BE_SEARCHED": "i wanna be forgotten",
        }, {
            'primary_key': 'foo-bar',
            'primary_key2': 'foo-bar',
            'chunk_size': '123',
            'concat_missing': 'Hello, MISSING_ENV_VAL',
            'concat_missing2': 'Hello, ${MISSING_ENV_VAL}',
            'concat_present': 'Hello, beautiful world',
            'concat_present2': 'beautiful world',
            'concat_present3': 'Hello, beautiful world',
            'search': 'id = 42',
            'search2': "username = 'i wanna be forgotten'",
            'corrupted': "username = '${CORRUPTED",
            'corrupted2': '',
            'corrupted3': '$'
        }
        ]
    ])
    def test(self, file, envs, expected):
        with mock.patch.dict(os.environ, envs):
            print(load_config(file))
            assert load_config(file) == expected
