import math
from mock import ANY, Mock, call, patch
import pytest

from pganonymizer.utils import build_and_then_import_data, get_connection, import_data, truncate_tables


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

    @pytest.mark.parametrize('tables, expected_sql', [
        [('table_a', 'table_b'), 'TRUNCATE TABLE table_a, table_b;'],
        [(), None],
    ])
    def test(self, tables, expected_sql):
        mock_cursor = Mock()
        connection = Mock()
        connection.cursor.return_value = mock_cursor
        truncate_tables(connection, tables)
        if tables:
            connection.cursor.assert_called_once()
            assert mock_cursor.execute.call_args_list == [call(expected_sql)]
            mock_cursor.close.assert_called_once()
        else:
            connection.cursor.assert_not_called()
            mock_cursor.execute.assert_not_called()
            mock_cursor.close.assert_not_called()


class TestImportData:

    @pytest.mark.parametrize('source_table, primary_key, expected_tbl_name', [
        ['src_tbl', 'id', 'tmp_src_tbl']
    ])
    def test(self, source_table, primary_key, expected_tbl_name):
        mock_cursor = Mock()

        connection = Mock()
        connection.cursor.return_value = mock_cursor

        import_data(connection, {}, source_table, primary_key, [])

        assert connection.cursor.call_count == 2
        assert mock_cursor.close.call_count == 2

        mock_cursor.copy_from.assert_called_once()
        expected = [call(ANY, expected_tbl_name, null=ANY, sep=ANY)]
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

        assert connection.cursor.call_count == 9
        assert mock_cursor.close.call_count == 9
        assert mock_cursor.copy_from.call_count == expected_callcount
