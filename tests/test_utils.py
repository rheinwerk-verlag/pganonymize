import math
from mock import ANY, Mock, call, patch
from psycopg2.sql import Composed, Identifier, SQL
import pytest

from pganonymizer.utils import build_and_then_import_data, data2csv, get_connection, import_data, truncate_tables


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

    @pytest.mark.parametrize('tables, expected', [
        [('table_a', 'table_b', 'CAPS_TABLe'), Composed([SQL('TRUNCATE TABLE '), Composed(
            [Identifier('table_a'), SQL(', '), Identifier('table_b'), SQL(', '), Identifier('CAPS_TABLe')])])],
        [(), None],
    ])
    def test(self, tables, expected):
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

    @pytest.mark.parametrize('tmp_table', [
        ['src_tbl']
    ])
    def test(self, tmp_table):
        mock_cursor = Mock()

        connection = Mock()
        connection.cursor.return_value = mock_cursor

        import_data(connection, tmp_table, [])

        assert connection.cursor.call_count == 2
        assert mock_cursor.close.call_count == 2

        mock_cursor.copy_from.assert_called_once()
        expected = [call(ANY, tmp_table, null=ANY, sep=ANY)]
        assert mock_cursor.copy_from.call_args_list == expected


class TestBuildAndThenImport:
    @pytest.mark.parametrize('table, primary_key, columns, total_count, chunk_size, expected_callcount', [
        ['src_tbl', 'id', [{'col1': {'provider': None}}, {'COL2': {'provider': None}}], 10, 3, 4]
    ])
    def test(self, table, primary_key, columns, total_count, chunk_size, expected_callcount):
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
        expected_execute_calls = [
            call(Composed([SQL('SELECT '), Composed([Identifier('id'), SQL(', '), Identifier(
                'col1'), SQL(', '), Identifier('COL2')]), SQL(' FROM '), Identifier('src_tbl')])),
            call(Composed([SQL('CREATE TEMP TABLE '), Identifier('tmp_src_tbl'),
                           SQL(' AS SELECT '),
                           Composed([Identifier('id'), SQL(', '), Identifier(
                               'col1'), SQL(', '), Identifier('COL2')]), SQL('\n                    FROM '),
                           Identifier('src_tbl'), SQL(' WITH NO DATA')])),
            call(Composed([SQL('CREATE INDEX ON '), Identifier('tmp_src_tbl'), SQL(' ('), Identifier('id'), SQL(')')])),
            call(Composed([SQL('UPDATE '), Identifier('src_tbl'), SQL(' t SET '),
                           Composed([Composed([Identifier('col1'), SQL(' = s.'), Identifier('col1')]), SQL(', '),
                                     Composed([Identifier('COL2'), SQL(' = s.'), Identifier('COL2')])]),
                           SQL(' FROM '), Identifier('tmp_src_tbl'),
                           SQL(' s WHERE t.'), Identifier('id'), SQL(' = s.'), Identifier('id')]))]
        assert mock_cursor.execute.call_args_list == expected_execute_calls


class TestCSVSerialization:
    @pytest.mark.parametrize('input, expected', [
        [
            [
                ["foo\nbar", None, 123, "tab \t tab", "cr\r cr"],
                [None, None, None, "\n", ""]
            ],
            "foo\\nbar\x1f\\N\x1f123\x1ftab \\t tab\x1fcr\\r cr\n\\N\x1f\\N\x1f\\N\x1f\x1f\n"]
    ])
    def test(self, input, expected):
        csv_data = data2csv(input)
        assert csv_data.getvalue() == expected
