import operator
import random
import re
from hashlib import md5
from uuid import uuid4

from faker import Faker

from pganonymizer.exceptions import InvalidProvider, InvalidProviderArgument

fake_data = Faker()


class ProviderRegistry(object):
    """A registry for provider classes."""

    def __init__(self):
        self._registry = {}

    def register(self, provider_class, provider_id):
        """
        Register a provider.

        :param provider_class:
        :param provider_id:
        """
        self._registry[provider_id] = provider_class

    def get_provider(self, provider_id):
        """
        Return a provider by it's provider id.

        :param str provider_id:
        :raises InvalidProvider: If no provider can be found with the given id.
        """
        provider = None
        for key, cls in self._registry.items():
            if re.compile(key).match(provider_id) is not None:
                provider = cls
                break
        if provider is None:
            raise InvalidProvider('Could not find provider with id "{}"'.format(provider_id))
        return provider

    @property
    def providers(self):
        """
        Return the registered providers.

        :rtype: dict
        """
        return self._registry


provider_registry = ProviderRegistry()


def register(provider_id, **kwargs):
    """
    A wrapper that registers a provider class to the provider registry.

    :param str provider_id:
    """
    def wrapper(provider_class):
        registry = kwargs.get('registry', provider_registry)
        registry.register(provider_class, provider_id)
        return provider_class
    return wrapper


class Provider(object):
    """Base class for all providers."""

    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def alter_value(self, value):
        raise NotImplementedError


@register('choice')
class ChoiceProvider(Provider):
    """Provider that returns a random value from a list of choices."""

    def alter_value(self, value):
        return random.choice(self.kwargs.get('values'))


@register('clear')
class ClearProvider(Provider):
    """Provider to set a field value to None."""

    def alter_value(self, value):
        return None


@register('fake')
class FakeProvider(Provider):
    """Provider to generate fake data."""

    def alter_value(self, value):
        func_name = self.kwargs['name'].split('.', 1)[1]
        try:
            func = operator.attrgetter(func_name)(fake_data)
        except AttributeError as exc:
            raise InvalidProviderArgument(exc)
        return func()


@register('mask')
class MaskProvider(Provider):
    """Provider that masks the original value."""

    default_sign = 'X'

    def alter_value(self, value):
        sign = self.kwargs.get('sign', self.default_sign) or self.default_sign
        return sign * len(value)


@register('md5')
class MD5Provider(Provider):
    """Provider to hash a value with the md5 algorithm."""

    default_max_length = 8

    def alter_value(self, value):
        as_number = self.kwargs.get('as_number', False)
        as_number_length = self.kwargs.get('as_number_length', self.default_max_length)
        hashed = md5(value.encode('utf-8')).hexdigest()
        if as_number:
            return int(hashed, 16) % (10 ** as_number_length)
        else:
            return hashed


@register('set')
class SetProvider(Provider):
    """Provider to set a static value."""

    def alter_value(self, value):
        return self.kwargs.get('value')


@register('uuid4')
class UUID4Provider(Provider):
    """Provider to set a random uuid value."""

    def alter_value(self, value):
        return uuid4()
