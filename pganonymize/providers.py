import operator
import random
import re
from collections import OrderedDict
from hashlib import md5
from uuid import uuid4

from faker import Faker

from pganonymize.config import config
from pganonymize.exceptions import InvalidProvider, InvalidProviderArgument, ProviderAlreadyRegistered


class FakerInitializer(object):
    """A wrapper that allows to instantiate a faker instance with specific locales."""

    def __init__(self):
        self._faker = None
        self._options = None

    @property
    def options(self):
        if self._options is None:
            self._options = config.schema.get('options', {}).get('faker', {})
        return self._options

    @property
    def default_locale(self):
        return self.options.get('default_locale')

    @property
    def faker(self):
        """
        Return the actual :class:`faker.Faker` instance, with optional locales taken from the YAML schema.

        :return: A faker instance
        :rtype: faker.Faker
        """
        if self._faker is None:
            locales = self.options.get('locales')
            self._faker = Faker(locales)
        return self._faker

    def get_locale_generator(self, locale):
        """
        Get the internal generator for the given locale.

        :param str locale: A locale string
        :raises InvalidProviderArgument: If locale is unknown (not configured within the global locales option).
        :return: A Generator instance for the given locale
        :rtype: faker.Generator
        """
        try:
            generator = self.faker[locale]
        except KeyError:
            raise InvalidProviderArgument('Locale \'{}\' is unknown. Have you added it to the global option '
                                          '(options.faker.locales)?'.format(locale))
        return generator


faker_initializer = FakerInitializer()


class ProviderRegistry(object):
    """A registry for provider classes."""

    def __init__(self):
        self._registry = OrderedDict()

    def register(self, provider_class, provider_id):
        """
        Register a provider class.

        :param pganonymize.providers.Provider provider_class: Provider class that should be registered
        :param str provider_id: A string id to register the provider for
        :raises ProviderAlreadyRegistered: If another provider with the given id has been registered
        """
        if provider_id in self._registry:
            raise ProviderAlreadyRegistered('A provider with the id "{}" has already been registered'
                                            .format(provider_id))
        self._registry[provider_id] = provider_class

    def get_provider(self, provider_id):
        """
        Return a provider by its provider id.

        :param str provider_id: The string id of the desired provider.
        :raises InvalidProvider: If no provider can be found with the given id.
        :return: The provider class that matches the id.
        :rtype: type
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

    @classmethod
    def alter_value(cls, original_value, **kwargs):
        """
        Alter or replace the original value of the database column.

        :param original_value: The original value of the database column.
        """
        raise NotImplementedError()


@register('choice')
class ChoiceProvider(Provider):
    """Provider that returns a random value from a list of choices."""

    @classmethod
    def alter_value(cls, original_value, **kwargs):
        return random.choice(kwargs.get('values'))


@register('clear')
class ClearProvider(Provider):
    """Provider to set a field value to None."""

    @classmethod
    def alter_value(cls, original_value, **kwargs):
        return None


@register('fake.+')
class FakeProvider(Provider):
    """Provider to generate fake data."""

    regex_match = True

    @classmethod
    def alter_value(cls, original_value, **kwargs):
        func_name = kwargs['name'].split('.', 1)[1]
        func_kwargs = kwargs.get('kwargs', {})
        locale = kwargs.get('locale', faker_initializer.default_locale)
        # Use the generator for the locale if a locale is configured (per field definition or as global default locale)
        faker_generator = faker_initializer.get_locale_generator(locale) if locale else faker_initializer.faker
        try:
            func = operator.attrgetter(func_name)(faker_generator)
        except AttributeError as exc:
            raise InvalidProviderArgument(exc)
        return func(**func_kwargs)


@register('mask')
class MaskProvider(Provider):
    """Provider that masks the original value."""

    default_sign = 'X'
    """The default string used to replace each character."""

    @classmethod
    def alter_value(cls, original_value, **kwargs):
        sign = kwargs.get('sign', cls.default_sign) or cls.default_sign
        return sign * len(original_value)


@register('partial_mask')
class PartialMaskProvider(Provider):
    """Provider that masks some of the original value."""

    default_sign = 'X'
    default_unmasked_left = 1
    default_unmasked_right = 1
    """The default string used to replace each character."""

    @classmethod
    def alter_value(cls, original_value, **kwargs):
        sign = kwargs.get('sign', cls.default_sign) or cls.default_sign
        unmasked_left = kwargs.get('unmasked_left', cls.default_unmasked_left) or cls.default_unmasked_left
        unmasked_right = kwargs.get('unmasked_right', cls.default_unmasked_right) or cls.default_unmasked_right

        return (
            original_value[:unmasked_left] +
            (len(original_value) - (unmasked_left + unmasked_right)) * sign +
            original_value[-unmasked_right:]
        )


@register('md5')
class MD5Provider(Provider):
    """Provider to hash a value with the md5 algorithm."""

    default_max_length = 8
    """The default length used for the number representation."""

    @classmethod
    def alter_value(cls, original_value, **kwargs):
        as_number = kwargs.get('as_number', False)
        as_number_length = kwargs.get('as_number_length', cls.default_max_length)
        hashed = md5(original_value.encode('utf-8')).hexdigest()
        if as_number:
            return int(hashed, 16) % (10 ** as_number_length)
        else:
            return hashed


@register('set')
class SetProvider(Provider):
    """Provider to set a static value."""

    @classmethod
    def alter_value(cls, original_value, **kwargs):
        return kwargs.get('value')


@register('uuid4')
class UUID4Provider(Provider):
    """Provider to set a random uuid value."""

    @classmethod
    def alter_value(cls, original_value, **kwargs):
        return uuid4()
