import random
from hashlib import md5

from faker import Faker
from six import with_metaclass

from pganonymizer.exceptions import InvalidProvider, InvalidProviderArgument

PROVIDERS = []

fake_data = Faker()


def get_provider(provider_config):
    """
    Return a provider instance, according to the schema definition of a field.

    :param dict provider_config: A provider configuration for a single field, e.g.:

        {'name': 'set', 'value': 'Foo'}

    :return: A provider instance
    :rtype: Provider
    """
    def get_provider_class(cid):
        for klass in PROVIDERS:
            if klass.matches(cid):
                return klass
    name = provider_config['name']
    cls = get_provider_class(name)
    if cls is None:
        raise InvalidProvider('Could not find provider with id %s' % name)
    return cls(**provider_config)


class ProviderMeta(type):
    """Metaclass to register all provider classes."""

    def __new__(cls, clsname, bases, attrs):
        newclass = super(ProviderMeta, cls).__new__(cls, clsname, bases, attrs)
        if clsname != 'Provider':
            PROVIDERS.append(newclass)
        return newclass


class Provider(object):
    """Base class for all providers."""

    id = None

    def __init__(self, **kwargs):
        self.kwargs = kwargs

    @classmethod
    def matches(cls, name):
        return cls.id.lower() == name.lower()

    def alter_value(self, value):
        raise NotImplementedError


class ChoiceProvider(with_metaclass(ProviderMeta, Provider)):
    """Provider that returns a random value from a list of choices."""

    id = 'choice'

    def alter_value(self, value):
        return random.choice(self.kwargs.get('values'))


class ClearProvider(with_metaclass(ProviderMeta, Provider)):
    """Provider to set a field value to None."""

    id = 'clear'

    def alter_value(self, value):
        return None


class FakeProvider(with_metaclass(ProviderMeta, Provider)):
    """Provider to generate fake data."""

    id = 'fake'

    @classmethod
    def matches(cls, name):
        return cls.id.lower() == name.split('.')[0].lower()

    def alter_value(self, value):
        func_name = self.kwargs['name'].split('.')[1]
        try:
            func = getattr(fake_data, func_name)
        except AttributeError as exc:
            raise InvalidProviderArgument(exc)
        return func()


class MaskProvider(with_metaclass(ProviderMeta, Provider)):
    """Provider that masks the original value."""

    id = 'mask'
    default_sign = 'X'

    def alter_value(self, value):
        sign = self.kwargs.get('sign', self.default_sign) or self.default_sign
        return sign * len(value)


class MD5Provider(with_metaclass(ProviderMeta, Provider)):
    """Provider to hash a value with the md5 algorithm."""

    id = 'md5'

    def alter_value(self, value):
        return md5(value.encode('utf-8')).hexdigest()


class SetProvider(with_metaclass(ProviderMeta, Provider)):
    """Provider to set a static value."""

    id = 'set'

    def alter_value(self, value):
        return self.kwargs.get('value')
