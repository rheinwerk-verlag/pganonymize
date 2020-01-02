from mock import patch, Mock

from pganonymizer.utils import get_connection


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