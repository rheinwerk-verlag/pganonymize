import pytest
import six

from mock import patch

from pganonymizer import exceptions, providers


class TestClearProvider:

    def test_alter_value(self):
        provider = providers.ClearProvider()
        provider.alter_value('Foo') is None


class TestFakeProvider:

    @pytest.mark.parametrize('name, function_name', [
        ('fake.first_name', 'first_name'),
    ])
    @patch('pganonymizer.providers.fake_data')
    def test_alter_value(self, mock_fake_data, name, function_name):
        provider = providers.FakeProvider(name=name)
        provider.alter_value('Foo')
        assert getattr(mock_fake_data, function_name).call_count == 1

    @pytest.mark.parametrize('name', [
        'fake.foo_name'
    ])
    def test_invalid_names(self, name):
        provider = providers.FakeProvider(name=name)
        with pytest.raises(exceptions.InvalidProviderArgument):
            provider.alter_value('Foo')


class TestMD5Provider:

    def test_alter_value(self):
        provider = providers.MD5Provider()
        value = provider.alter_value('foo')
        assert isinstance(value, six.string_types)
        assert len(value) == 32


class TestSetProvider:

    @pytest.mark.parametrize('kwargs, expected', [
        ({'value': None}, None),
        ({'value': 'Bar'}, 'Bar')
    ])
    def test_alter_value(self, kwargs, expected):
        provider = providers.SetProvider(**kwargs)
        assert provider.alter_value('Foo') == expected
