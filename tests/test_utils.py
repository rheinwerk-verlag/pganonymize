from collections import OrderedDict
from io import StringIO
import math
from tests.utils import quote_ident
from mock import ANY, Mock, call, patch

import pytest

from pganonymizer.utils import anonymize_tables, build_and_then_import_data, data2csv, \
    get_connection, import_data, truncate_tables


class TestGetConnection:

    @patch('pganonymizer.utils.psycopg2.connect')
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
    @pytest.mark.parametrize('tmp_table', [
        ['src_tbl']
    ])
    def test(self, quote_ident, tmp_table):
        mock_cursor = Mock()

        connection = Mock()
        connection.cursor.return_value = mock_cursor

        import_data(connection, tmp_table, [])

        assert connection.cursor.call_count == 2
        assert mock_cursor.close.call_count == 2

        mock_cursor.copy_from.assert_called_once()
        expected = [call(ANY, tmp_table, null=ANY, sep=ANY)]
        assert mock_cursor.copy_from.call_args_list == expected

    @patch('pganonymizer.utils.StringIO')
    @patch('psycopg2.extensions.quote_ident', side_effect=quote_ident)
    def test_anonymize_tables(self, quote_ident, mock_stringid):
        siobuff = StringIO()
        sio_mock = Mock(wraps=siobuff)
        mock_stringid.return_value = sio_mock
        sio_mock.close.return_value = True

        mock_cursor = Mock()
        mock_cursor.fetchone.return_value = [2]
        mock_cursor.fetchmany.side_effect = [
            [
                OrderedDict([("first_name", "John Doe"),
                             ("json_column", {"field1": "foo"})
                             ]),
                OrderedDict([("first_name", "John Doe"),
                             ("json_column", {"field2": "bar"})
                             ])
            ]
        ]

        connection = Mock()
        connection.cursor.return_value = mock_cursor
        definitions = []
        anonymize_tables(connection, definitions, verbose=True)

        assert connection.cursor.call_count == 0
        assert mock_cursor.close.call_count == 0

        definitions = [
            {
                "auth_user": {
                    "primary_key": "id",
                    "chunk_size": 5000,
                    "fields": [
                        {
                            "first_name": {
                                "provider": {
                                    "name": "set",
                                    "value": "dummy name"
                                }
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
                    ]
                }
            }
        ]
        anonymize_tables(connection, definitions, verbose=True)
        assert connection.cursor.call_count == 6
        assert mock_cursor.close.call_count == 6

        assert mock_cursor.copy_from.call_args_list == [call(sio_mock, ANY, null=ANY, sep=ANY)]
        assert siobuff.getvalue(
        ) == """dummy name\x1f{"field1": "dummy json field1"}\ndummy name\x1f{"field2": "dummy json field2"}\n"""


class TestBuildAndThenImport:
    @patch('psycopg2.extensions.quote_ident', side_effect=quote_ident)
    @pytest.mark.parametrize('table, primary_key, columns, total_count, chunk_size, expected_callcount', [
        ['src_tbl', 'id', [{'col1': {'provider': None}}, {'COL2': {'provider': None}}], 10, 3, 4]
    ])
    def test(self, quote_ident, table, primary_key, columns, total_count, chunk_size, expected_callcount):
        fake_record = dict.fromkeys([list(definition.keys())[0] for definition in columns], "")
        records = [
            [fake_record for row in range(0, chunk_size)] for x in range(0, int(math.ceil(total_count / chunk_size)))
        ]

        def side_effect(size=None):
            if len(records) >= 1:
                return records.pop()
            else:
                return None

        mock_cursor = Mock()
        mock_cursor.fetchmany.side_effect = side_effect

        connection = Mock()
        connection.cursor.return_value = mock_cursor

        build_and_then_import_data(connection, table, primary_key, columns, None, None, total_count, chunk_size)

        assert connection.cursor.call_count == 11
        assert mock_cursor.close.call_count == 11
        assert mock_cursor.copy_from.call_count == expected_callcount

        expected_execute_calls = [call('SELECT "id", "col1", "COL2" FROM "src_tbl"'),
                                  call(
                                      'CREATE TEMP TABLE "tmp_src_tbl" AS SELECT "id", "col1", "COL2"\n                    FROM "src_tbl" WITH NO DATA'),# noqa
                                  call('CREATE INDEX ON "tmp_src_tbl" ("id")'),
                                  call('UPDATE "src_tbl" t SET "col1" = s."col1", "COL2" = s."COL2" FROM "tmp_src_tbl" s WHERE t."id" = s."id"')] # noqa
        assert mock_cursor.execute.call_args_list == expected_execute_calls


class TestCSVSerialization:
    @pytest.mark.parametrize('input, expected', [
        [
            [
                OrderedDict([("c1", "foo\nbar"), ("c2", None), ("c3", 123), ("c4", "tab \t tab"), ("c5", "cr\r cr")]),
                OrderedDict([("c1", None), ("c2", None), ("c3", None), ("c4", "\n"), ("c5", "")])
            ],
            "foo\\nbar\x1f\\N\x1f123\x1ftab \\t tab\x1fcr\\r cr\n\\N\x1f\\N\x1f\\N\x1f\x1f\n"]
    ])
    def test(self, input, expected):
        csv_data = data2csv(input)
        assert csv_data.getvalue() == expected
