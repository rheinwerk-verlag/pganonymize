import os

import pytest
from mock import patch

from pganonymize.config import load_schema


@pytest.mark.parametrize('file, envs, expected', [
    [
        './tests/schemes/valid_schema.yml',
        {},
        {
            'tables': [
                {
                    'auth_user': {
                        'primary_key': 'id',
                        'chunk_size': 5000,
                        'fields': [
                            {'first_name': {'provider': {'name': 'fake.first_name'}}},
                            {'last_name': {'provider': {'name': 'set', 'value': 'Bar'}}},
                            {'email': {'provider': {'name': 'md5'}, 'append': '@localhost'}},
                        ],
                        'excludes': [
                            {'email': ['\\S[^@]*@example\\.com']},
                        ]
                    }
                }
            ],
            'truncate': ['django_session']
        }
    ],
    [
        './tests/schemes/schema_with_env_variables.yml',
        {
            'TEST_CHUNK_SIZE': '123',
            'TEST_PRIMARY_KEY': 'foo-bar',
            'PRESENT_WORLD_NAME': 'beautiful world',
            'COMPANY_ID': '42',
            'USER_TO_BE_SEARCHED': 'i wanna be forgotten',
        },
        {
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
            'corrupted3': '$',
        }
    ]
])
def test_load_schema(file, envs, expected):
    with patch.dict(os.environ, envs):
        assert load_schema(file) == expected
