import operator
import random
import re
from collections import OrderedDict
from hashlib import md5
from uuid import uuid4

from faker import Faker

from pganonymizer.exceptions import InvalidProvider, InvalidProviderArgument, ProviderAlreadyRegistered

fake_data = Faker()


class ProviderRegistry(object):
    """A registry for provider classes."""

    def __init__(self):
        self._registry = OrderedDict()

    def register(self, provider_class, provider_id):
        """
        Register a provider class.

        :param pganonymizer.providers.Provider provider_class: Provider class that should be registered
        :param str provider_id: A string id to register the provider for
        :raises ProviderAlreadyRegistered: If another provider with the given id has been registered
        """
        if provider_id in self._registry:
            raise ProviderAlreadyRegistered('A provider with the id "{}" has already been registered'
                                            .format(provider_id))
        self._registry[provider_id] = provider_class

    def get_provider(self, provider_id):
        """
        Return a provider by it's provider id.

        :param str provider_id: The string id of the desired provider.
        :raises InvalidProvider: If no provider can be found with the given id.
        """
        for key, cls in self._registry.items():
            if (cls.regex_match is True and re.match(re.compile(key), provider_id) is not None) or key == provider_id:
                return cls
        raise InvalidProvider('Could not find provider with id "{}"'.format(provider_id))

    @property
    def providers(self):
        """
        Return the registered providers.

        :rtype: OrderedDict
        """
        return self._registry


provider_registry = ProviderRegistry()


def register(provider_id, **kwargs):
    """
    A wrapper that registers a provider class to the provider registry.

    :param str provider_id: The string id to register the provider for.
    :keyword registry: The registry the provider class is registered at (default is the `provider_registry` instance).
    :return: The decorator function
    :rtype: function
    """
    def wrapper(provider_class):
        registry = kwargs.get('registry', provider_registry)
        registry.register(provider_class, provider_id)
        return provider_class
    return wrapper


class Provider(object):
    """Base class for all providers."""

    regex_match = False
    """Defines whether a provider matches it's id using regular expressions."""

    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def alter_value(self, value):
        """
        Alter or replace the original value of the database column.

        :param value: The original value of the database column.
        """
        raise NotImplementedError()


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


@register('fake.+')
class FakeProvider(Provider):
    """Provider to generate fake data."""

    regex_match = True

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
    """The default string used to replace each character."""

    def alter_value(self, value):
        sign = self.kwargs.get('sign', self.default_sign) or self.default_sign
        return sign * len(value)


@register('md5')
class MD5Provider(Provider):
    """Provider to hash a value with the md5 algorithm."""

    default_max_length = 8
    """The default length used for the number representation."""

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
