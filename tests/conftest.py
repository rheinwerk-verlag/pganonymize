# -*- coding: utf-8 -*-
import pytest
from mock.mock import patch

from pganonymize.config import config
from pganonymize.providers import faker_initializer


@pytest.fixture
def valid_config():
    # Patch the config instance with a valid schema
    with patch.multiple('pganonymize.config.config', schema_file='./tests/schemes/valid_schema.yml', _schema=None):
        yield config


@pytest.fixture
def mocked_faker_initializer():
    # Patch the faker_initializer instance with a Faker mock
    with patch('pganonymize.providers.faker_initializer._faker'):
        yield faker_initializer


@pytest.fixture
def faker_initializer_with_localization(mocked_faker_initializer):
    # Patch the faker_initializer instance with localization options
    with patch.object(mocked_faker_initializer, '_options', {'locales': ('de_DE', 'en_US'), 'default_locale': 'en_US'}):
        yield mocked_faker_initializer
