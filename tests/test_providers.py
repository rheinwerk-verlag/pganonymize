import operator
import uuid
from collections import OrderedDict

import pytest
import six
from mock import MagicMock, Mock, call, patch

from pganonymize import exceptions, providers
from pganonymize.exceptions import InvalidProviderArgument


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


class TestProviderRegistry(object):

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


class TestProvider(object):

    def test_alter_value(self):
        provider = providers.Provider()
        with pytest.raises(NotImplementedError):
            provider.alter_value('Foo')


class TestChoiceProvider(object):

    def test_alter_value(self):
        choices = ['Foo', 'Bar', 'Baz']
        for choice in choices:
            assert providers.ChoiceProvider.alter_value(choice, values=choices) in choices


class TestClearProvider(object):

    def test_alter_value(self):
        provider = providers.ClearProvider()
        assert provider.alter_value('Foo') is None


@pytest.mark.usefixtures('valid_config')
class TestFakeProvider(object):

    @pytest.mark.parametrize('name, function_name', [
        ('fake.first_name', 'first_name'),
        ('fake.unique.first_name', 'unique.first_name'),
    ])
    @patch('pganonymize.providers.faker_initializer._faker')
    def test_alter_value(self, mock_faker, name, function_name):
        providers.FakeProvider.alter_value('Foo', name=name)
        assert operator.attrgetter(function_name)(mock_faker).call_count == 1

    @pytest.mark.parametrize('name', ['fake.foo_name'])
    def test_invalid_names(self, name):
        with pytest.raises(exceptions.InvalidProviderArgument):
            providers.FakeProvider.alter_value('Foo', name=name)

    @patch('pganonymize.providers.faker_initializer._faker')
    def test_alter_value_with_kwargs(self, mock_faker):
        providers.FakeProvider.alter_value('Foo', name='fake.date_of_birth', kwargs={'minimum_age': 18})
        assert mock_faker.date_of_birth.call_args == call(minimum_age=18)

    @patch('pganonymize.providers.faker_initializer._faker')
    def test_alter_value_with_locale(self, mock_faker):
        providers.FakeProvider.alter_value('Foo', name='fake.date_of_birth', locale='de_DE')
        assert mock_faker['de_DE'].date_of_birth.call_count == 1

    def test_alter_value_with_unkown_locale(self):
        with pytest.raises(InvalidProviderArgument):
            providers.FakeProvider.alter_value('Foo', name='fake.date_of_birth', locale='de_DE')

    def test_alter_value_use_default_locale(self, faker_initializer_with_localization):
        providers.FakeProvider.alter_value('Foo', name='fake.date_of_birth')
        faker = faker_initializer_with_localization._faker
        assert faker[faker_initializer_with_localization.default_locale].date_of_birth.call_count == 1

    def test_alter_value_ignore_default_locale(self, faker_initializer_with_localization):
        providers.FakeProvider.alter_value('Foo', name='fake.date_of_birth', locale=None)
        faker = faker_initializer_with_localization._faker
        assert faker.date_of_birth.call_count == 1


class TestMaskProvider(object):

    @pytest.mark.parametrize('value, sign, expected', [
        ('Foo', None, 'XXX'),
        ('Baaaar', '?', '??????'),
    ])
    def test_alter_value(self, value, sign, expected):
        assert providers.MaskProvider.alter_value(value, sign=sign) == expected


class TestPartialMaskProvider(object):

    @pytest.mark.parametrize('value, sign, unmasked_left, unmasked_right, expected', [
        ('Foo', None, 1, 1, 'FXo'),
        ('Foo', None, 0, 0, 'FXo'),
        ('Baaaar', '?', 2, 1, 'Ba???r'),
    ])
    def test_alter_value(self, value, sign, unmasked_left, unmasked_right, expected):
        assert providers.PartialMaskProvider.alter_value(value, sign=sign, unmasked_left=unmasked_left,
                                                         unmasked_right=unmasked_right) == expected


class TestMD5Provider(object):

    def test_alter_value(self):
        provider = providers.MD5Provider()
        value = provider.alter_value('foo')
        assert isinstance(value, six.string_types)
        assert len(value) == 32

    def test_as_number(self):
        value = providers.MD5Provider.alter_value('foo', as_number=True)
        assert isinstance(value, six.integer_types)
        assert value == 985560
        value = providers.MD5Provider.alter_value('foobarbazadasd', as_number=True, as_number_length=8)
        assert isinstance(value, six.integer_types)
        assert value == 45684001


class TestSetProvider(object):

    @pytest.mark.parametrize('kwargs, expected', [
        ({'value': None}, None),
        ({'value': 'Bar'}, 'Bar')
    ])
    def test_alter_value(self, kwargs, expected):
        assert providers.SetProvider.alter_value('Foo', **kwargs) == expected


class TestUUID4Provider(object):

    @pytest.mark.parametrize('value, expected', [(None, uuid.UUID), ('Foo', uuid.UUID)])
    def test_alter_value(self, value, expected):
        assert type(providers.UUID4Provider.alter_value(value)) == expected
