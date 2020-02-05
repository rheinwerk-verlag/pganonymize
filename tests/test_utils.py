from mock import call, patch, Mock

from pganonymizer.utils import get_connection, truncate_tables


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
        mock_args = Mock()
        mock_args.configure_mock(**connection_data)
        get_connection(mock_args)
        mock_connect.assert_called_once_with(**connection_data)


class TestTruncateTables:

    def test(self):
        mock_cursor = Mock()
        connection = Mock()
        connection.cursor.return_value = mock_cursor
        truncate_tables(connection, ['table_a', 'table_b'])
        assert mock_cursor.execute.call_args_list == [
            call('TRUNCATE TABLE table_a, table_b;'),
        ]
        mock_cursor.close.assert_called_once()
