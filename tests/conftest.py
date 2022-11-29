# -*- coding: utf-8 -*-
import pytest
from mock.mock import patch

from pganonymize.config import config


@pytest.fixture
def valid_config():
    # Patch the config instance with a valid schema
    with patch.multiple('pganonymize.config.config', schema_file='./tests/schemes/valid_schema.yml', _schema=None):
        yield config
