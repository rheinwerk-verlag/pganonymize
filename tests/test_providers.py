import operator
import uuid
from collections import OrderedDict

import pytest
import six
from mock import MagicMock, Mock, patch

from pganonymizer import exceptions, providers


def test_register():
    registry = providers.ProviderRegistry()

    @providers.register('foo', registry=registry)
    class FooProvider(providers.Provider):

        def alter_value(self, value):
            return 'foo'

    @providers.register('bar', registry=registry)
    class BarProvider(providers.Provider):

        def alter_value(self, value):
            return 'bar'

    assert len(registry._registry) == 2
    assert 'foo' in registry._registry
    assert 'bar' in registry._registry


class TestProviderRegistry:

    def test_constructor(self):
        registry = providers.ProviderRegistry()
        assert registry._registry == {}

    @pytest.mark.parametrize('classes, expected', [
        (
            OrderedDict([
                ('foo', Mock(spec=providers.Provider)),
            ]),
            ['foo']
        ),
        (
            OrderedDict([
                ('foo', Mock(spec=providers.Provider)),
                ('bar', Mock(spec=providers.Provider)),
            ]),
            ['foo', 'bar']
        )
    ])
    def test_register(self, classes, expected):
        registry = providers.ProviderRegistry()
        for key, cls in classes.items():
            registry.register(cls, key)
        assert len(registry._registry) == len(classes)
        assert list(registry._registry.keys()) == expected

    def test_register_raises_exception(self):
        registry = providers.ProviderRegistry()
        registry.register(Mock(), 'foo1')
        registry.register(Mock(), 'foo2')
        with pytest.raises(exceptions.ProviderAlreadyRegistered):
            registry.register(Mock(), 'foo1')
            registry.register(Mock(), 'foo2')

    @pytest.mark.parametrize('provider_id, effect', [
        ('foooooo', pytest.raises(exceptions.InvalidProvider)),
        ('foobar', pytest.raises(exceptions.InvalidProvider)),
        ('barr', pytest.raises(exceptions.InvalidProvider)),
        ('foo', MagicMock()),
        ('bar', MagicMock()),
        ('baz', MagicMock()),
        ('baz.uuid', MagicMock()),
    ])
    def test_get_provider(self, provider_id, effect):
        provider = None
        registry = providers.ProviderRegistry()
        with patch.object(registry, '_registry', {
            'foo': Mock(spec=providers.Provider),
            'bar': Mock(spec=providers.Provider),
            'baz.*': Mock(spec=providers.Provider, regex_match=True)
        }):
            with effect:
                provider = registry.get_provider(provider_id)
        if provider is not None:
            assert isinstance(provider, providers.Provider)

    def test_providers(self):
        pass


class TestChoiceProvider:

    def test_alter_value(self):
        choices = ['Foo', 'Bar', 'Baz']
        provider = providers.ChoiceProvider(values=choices)
        for choice in choices:
            assert provider.alter_value(choice) in choices


class TestClearProvider:

    def test_alter_value(self):
        provider = providers.ClearProvider()
        assert provider.alter_value('Foo') is None


class TestFakeProvider:

    @pytest.mark.parametrize('name, function_name', [
        ('fake.first_name', 'first_name'),
        ('fake.unique.first_name', 'unique.first_name'),
    ])
    @patch('pganonymizer.providers.fake_data')
    def test_alter_value(self, mock_fake_data, name, function_name):
        provider = providers.FakeProvider(name=name)
        provider.alter_value('Foo')
        assert operator.attrgetter(function_name)(mock_fake_data).call_count == 1

    @pytest.mark.parametrize('name', [
        'fake.foo_name'
    ])
    def test_invalid_names(self, name):
        provider = providers.FakeProvider(name=name)
        with pytest.raises(exceptions.InvalidProviderArgument):
            provider.alter_value('Foo')


class TestMaskProvider:

    @pytest.mark.parametrize('value, sign, expected', [
        ('Foo', None, 'XXX'),
        ('Baaaar', '?', '??????'),
    ])
    def test_alter_value(self, value, sign, expected):
        provider = providers.MaskProvider(sign=sign)
        assert provider.alter_value(value) == expected


class TestMD5Provider:

    def test_alter_value(self):
        provider = providers.MD5Provider()
        value = provider.alter_value('foo')
        assert isinstance(value, six.string_types)
        assert len(value) == 32

    def test_as_number(self):
        provider = providers.MD5Provider(as_number=True)
        value = provider.alter_value('foo')
        assert isinstance(value, six.integer_types)
        assert value == 985560

        provider = providers.MD5Provider(as_number=True, as_number_length=8)
        value = provider.alter_value('foobarbazadasd')
        assert isinstance(value, six.integer_types)
        assert value == 45684001


class TestSetProvider:

    @pytest.mark.parametrize('kwargs, expected', [
        ({'value': None}, None),
        ({'value': 'Bar'}, 'Bar')
    ])
    def test_alter_value(self, kwargs, expected):
        provider = providers.SetProvider(**kwargs)
        assert provider.alter_value('Foo') == expected


class TestUUID4Provider:
    @pytest.mark.parametrize('kwargs, expected', [
        ({'value': None}, None),
        ({'value': 'Bar'}, 'Bar')
    ])
    def test_alter_value(self, kwargs, expected):
        provider = providers.UUID4Provider(**kwargs)
        assert type(provider.alter_value('Foo')) == uuid.UUID
