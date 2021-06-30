import pytest
from mock import ANY, Mock, call, patch

from pganonymizer.utils import get_connection, import_data, truncate_tables


class TestGetConnection:

    @patch('pganonymizer.utils.psycopg2.connect')
    def test(self, mock_connect):
        dsn = 'postgresql://localhost/anon_test?user=postgres&password=postgres'
        get_connection(dsn)
        mock_connect.assert_called_once_with(dsn)


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

    @pytest.mark.parametrize('source_table, table_columns, primary_key, expected_tbl_name, expected_columns', [
        ['src_tbl', ['id', 'COL_1'], 'id', 'tmp_src_tbl', ['"id"', '"COL_1"']]
    ])
    def test(self, source_table, table_columns, primary_key, expected_tbl_name, expected_columns):
        mock_cursor = Mock()

        connection = Mock()
        connection.cursor.return_value = mock_cursor

        import_data(connection, {}, source_table, table_columns, primary_key, [])

        assert connection.cursor.call_count == 2
        assert mock_cursor.close.call_count == 2

        mock_cursor.copy_from.assert_called_once()
        expected = [call(ANY, expected_tbl_name, columns=expected_columns, null=ANY, sep=ANY)]
        assert mock_cursor.copy_from.call_args_list == expected
