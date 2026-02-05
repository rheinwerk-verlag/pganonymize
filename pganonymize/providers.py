import json
import operator
import random
import re
from collections import OrderedDict
from hashlib import md5
from uuid import uuid4

from faker import Faker
import string
import datetime
from calendar import isleap
import unicodedata

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
        except KeyError as e:
            raise InvalidProviderArgument(f"Locale \'{locale}\' is unknown. Have you added it to the global option "
                                          f"(" f"options.faker.locales)?") from e

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
            raise ProviderAlreadyRegistered(f'A provider with the id "{provider_id}" has already been registered')

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
        raise InvalidProvider(f'Could not find provider with id "{provider_id}"')

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
            raise InvalidProviderArgument(exc) from exc
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
        return int(hashed, 16) % (10 ** as_number_length) if as_number else hashed


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


FISCAL_CODE_MONTHS = ['A', 'B', 'C', 'D', 'E', 'H', 'L', 'M', 'P', 'R', 'S', 'T']
FISCAL_CODE_COMUNE_CODES = ['H501', 'F205', 'D612', 'L219', 'A794', 'G273']
FISCAL_CODE_ODD_MAP = {
    **{str(i): v for i, v in enumerate([1, 0, 5, 7, 9, 13, 15, 17, 19, 21])},
    **{k: v for k, v in zip('ABCDEFGHIJ', [1, 0, 5, 7, 9, 13, 15, 17, 19, 21])},
    **{k: v for k, v in zip('KLMNOPQRST', [2, 4, 18, 20, 11, 3, 6, 8, 12, 14])},
    **{k: v for k, v in zip('UVWXYZ', [16, 10, 22, 25, 24, 23])},
}
FISCAL_CODE_EVEN_MAP = {
    **{str(i): i for i in range(10)},
    **{k: v for k, v in zip(string.ascii_uppercase, range(26))},
}


def _fiscal_code_checksum(code_15):
    total = 0
    for index, char in enumerate(code_15, start=1):
        if index % 2 == 1:
            total += FISCAL_CODE_ODD_MAP[char]
        else:
            total += FISCAL_CODE_EVEN_MAP[char]
    return chr(ord('A') + (total % 26))


def _row_get(row, field_name):
    if not field_name:
        return None
    if '.' not in field_name:
        return row.get(field_name)
    current = row
    for part in field_name.split('.'):
        if not isinstance(current, dict):
            return None
        current = current.get(part)
    return current


def _normalize_letters(value):
    if value is None:
        return ''
    normalized = unicodedata.normalize('NFKD', str(value))
    normalized = normalized.encode('ascii', 'ignore').decode('ascii')
    normalized = normalized.upper()
    return re.sub(r'[^A-Z]', '', normalized)


def _normalize_comune_code(value):
    if value is None:
        return None
    value_str = str(value).strip().upper()
    letter = _normalize_letters(value_str)[:1]
    digits = re.sub(r'[^0-9]', '', value_str)[:3]
    if letter and len(digits) == 3:
        return f"{letter}{digits}"
    return None


def _fiscal_code_surname(surname):
    letters = _normalize_letters(surname)
    consonants = ''.join([ch for ch in letters if ch not in 'AEIOU'])
    vowels = ''.join([ch for ch in letters if ch in 'AEIOU'])
    code = (consonants + vowels + 'XXX')[:3]
    return code


def _fiscal_code_name(name):
    letters = _normalize_letters(name)
    consonants = ''.join([ch for ch in letters if ch not in 'AEIOU'])
    vowels = ''.join([ch for ch in letters if ch in 'AEIOU'])
    if len(consonants) >= 4:
        code = consonants[0] + consonants[2] + consonants[3]
    else:
        code = (consonants + vowels + 'XXX')[:3]
    return code


def _parse_birth_date(value, date_format=None):
    if isinstance(value, datetime.datetime):
        return value.date()
    if isinstance(value, datetime.date):
        return value
    if isinstance(value, str):
        if date_format:
            return datetime.datetime.strptime(value, date_format).date()
        try:
            return datetime.date.fromisoformat(value)
        except ValueError:
            return datetime.datetime.strptime(value, "%Y-%m-%d").date()
    return None


def _is_female(value, rng=None):
    if value is None:
        return rng.choice([True, False]) if rng else False
    if isinstance(value, bool):
        return value
    val = str(value).strip().lower()
    return val in {'f', 'female', 'femmina', 'donna'}


def _generate_pseudo_fiscal_code(seed_source):
    rng_seed = int(md5(seed_source.encode('utf-8')).hexdigest(), 16)
    rng = random.Random(rng_seed)

    surname = ''.join(rng.choice(string.ascii_uppercase) for _ in range(3))
    name = ''.join(rng.choice(string.ascii_uppercase) for _ in range(3))
    year = rng.randint(0, 99)
    month = rng.choice(FISCAL_CODE_MONTHS)
    day = rng.randint(1, 28)
    female = rng.choice([True, False])
    day_code = day + (40 if female else 0)
    comune = rng.choice(FISCAL_CODE_COMUNE_CODES)

    code_15 = f"{surname}{name}{year:02d}{month}{day_code:02d}{comune}"
    return code_15 + _fiscal_code_checksum(code_15)


@register('fiscalcode')
class FiscalCodeProvider(Provider):
    """Provider to generate a syntactically valid Italian fiscal code."""

    @classmethod
    def alter_value(cls, original_value, **kwargs):
        if not original_value:
            return None
        if kwargs.get('use_row'):
            row = kwargs.get('row', {})
            surname = _row_get(row, kwargs.get('surname_field', 'surname'))
            name = _row_get(row, kwargs.get('name_field', 'name'))
            birth_date_raw = _row_get(row, kwargs.get('birth_date_field', 'birth_date'))
            gender = _row_get(row, kwargs.get('gender_field', 'gender'))
            comune_code = _row_get(row, kwargs.get('comune_code_field', 'comune_code'))
            comune_code = _normalize_comune_code(comune_code or kwargs.get('comune_code'))
            comune_codes = kwargs.get('comune_codes')
            if isinstance(comune_codes, str):
                comune_codes = [code.strip() for code in comune_codes.split(',') if code.strip()]
            comune_codes = comune_codes or FISCAL_CODE_COMUNE_CODES

            strict = kwargs.get('strict', False)
            birth_date = _parse_birth_date(birth_date_raw, kwargs.get('birth_date_format'))
            if not (surname and name and birth_date):
                if strict:
                    return None
                return _generate_pseudo_fiscal_code(str(original_value))
            if not comune_code:
                if strict and not comune_codes:
                    return None
                rng_seed = int(md5(str(original_value).encode('utf-8')).hexdigest(), 16)
                rng = random.Random(rng_seed)
                comune_code = _normalize_comune_code(rng.choice(comune_codes))
                if not comune_code:
                    if strict:
                        return None
                    return _generate_pseudo_fiscal_code(str(original_value))

            year = birth_date.year % 100
            month = FISCAL_CODE_MONTHS[birth_date.month - 1]
            rng_seed = int(md5(str(original_value).encode('utf-8')).hexdigest(), 16)
            rng = random.Random(rng_seed)
            day = birth_date.day + (40 if _is_female(gender, rng=rng) else 0)
            code_15 = (
                f"{_fiscal_code_surname(surname)}"
                f"{_fiscal_code_name(name)}"
                f"{year:02d}{month}{day:02d}{comune_code}"
            )
            return code_15 + _fiscal_code_checksum(code_15)

        return _generate_pseudo_fiscal_code(str(original_value))


@register('vatnumber')
class VatNumberProvider(Provider):
    """Provider to hash a vat number."""

    @classmethod
    def alter_value(cls, original_value, **kwargs):
        vatnumber = original_value[2:]
        crypt_vat_number = md5(vatnumber.encode('utf-8')).hexdigest()

        n = 2
        split_string = [crypt_vat_number[index: index + n] for index in range(0, len(crypt_vat_number), n)]

        numbers = [str(int(digit, 16) % 10) for digit in split_string]
        separator = ''
        return f'IT{separator.join(numbers[:9])}'


@register('fiscalcodebusiness')
class FiscalCodeBusinessProvider(Provider):
    """Provider to hash a vat number."""

    @classmethod
    def alter_value(cls, original_value, **kwargs):
        fiscalcode_business = original_value[:]
        crypt_fiscalcode_business = md5(fiscalcode_business.encode('utf-8')).hexdigest()

        n = 2
        split_string = [crypt_fiscalcode_business[index: index + n]
                        for index in range(0, len(crypt_fiscalcode_business), n)]

        numbers = [str(int(digit, 16) % 10) for digit in split_string]
        separator = ''
        return separator.join(numbers[:9])


@register('fiscalcodevat')
class FiscalCodeVatNumberProvider(Provider):
    """Provider to hash a vat number."""

    @classmethod
    def alter_value(cls, original_value, **kwargs):

        if original_value[0].isdigit():
            # code for fiscalcode legal entity
            fiscalcode_business = original_value[:]
            crypt_fiscalcode_business = md5(fiscalcode_business.encode('utf-8')).hexdigest()

            split_string = []
            n = 2
            for index in range(0, len(crypt_fiscalcode_business), n):
                split_string.append(crypt_fiscalcode_business[index: index + n])

            numbers = []
            for digit in split_string:
                digit_hex = int(digit, 16)
                digit_char = digit_hex % 10
                numbers.append(str(digit_char))

            separator = ''
            generate_fiscalcode_business = separator.join(numbers[:9])
            return generate_fiscalcode_business
        else:
            # code for fiscalcode natural person
            crypt_fiscal_code = md5(original_value.encode('utf-8')).hexdigest()

            def check_day(num):
                if int(num[3]) > 7:
                    num[3] = str(1)
                return num[3:5]

            def check_month(char):
                char_month = ['A', 'B', 'C', 'D', 'E', 'H', 'L', 'M', 'P', 'R', 'S', 'T']
                if char in char_month:
                    return char
                index = 4
                return char_month[index]

            def generate_fiscal_code(characters, numbers):
                sep = ''
                fiscal_code = f"{sep.join(characters[:6])}" \
                              f"{sep.join(numbers[:2])}" \
                              f"{check_month(characters[8])}" \
                              f"{sep.join(check_day(numbers))}" \
                              f"{characters[11]}" \
                              f"{sep.join(numbers[6:9])}" \
                              f"{characters[12]}"
                return fiscal_code

            split_string = []
            n = 2
            for index in range(0, len(crypt_fiscal_code), n):
                split_string.append(crypt_fiscal_code[index: index + n])

            characters = []

            for digit in split_string:
                digit_hex = int(digit, 16)
                digit_char = digit_hex % 26
                character = chr(ord('A') + digit_char)
                characters.append(character)

            numbers = []
            for digit in split_string[6:]:
                digit_hex = int(digit, 16)
                digit_char = digit_hex % 10
                numbers.append(str(digit_char))

            generate_fiscal_code = generate_fiscal_code(characters, numbers)
            return generate_fiscal_code


@register('phonenumberita')
class PhoneNumberItaProvider(Provider):
    """Provider to set a random value for phone number."""

    @classmethod
    def alter_value(cls, original_value, **kwargs):
        prefix = '+003'
        return prefix + ''.join([str(random.randint(0, 9)) for _ in range(9)])


@register('randomidcard')
class RandomIDCardProvider(Provider):
    """Provider to set a random value for id card."""

    @classmethod
    def alter_value(cls, original_value, **kwargs):
        chars = ''.join(random.choice(string.ascii_letters).upper() for _ in range(2))
        numbers = ''.join([str(random.randint(0, 9)) for _ in range(7)])
        return chars + numbers


@register('apikey')
class ApiKeyProvider(Provider):
    """Provider to set a random uuid"""

    @classmethod
    def alter_value(cls, original_value, **kwargs):
        return uuid4()


@register('jsonstring')
class JsonStringProvider(Provider):
    """Provider to generate jsonstring"""

    @classmethod
    def alter_value(cls, original_value, **kwargs):
        return json.dumps(kwargs.get('object'))


@register('sameyear')
class SameYearProvider(Provider):
    """Provider to generate a random date but with same year of original value."""

    @classmethod
    def alter_value(cls, original_value, **kwargs):
        if not original_value:
            return None
        birth_date = faker_initializer.faker.date_of_birth()
        # birth_date = datetime.datetime.strptime('1968-02-29', "%Y-%m-%d").date()
        if isleap(birth_date.year):
            birth_date = birth_date.replace(day=random.randint(1, 25))
        year = (
            original_value.year if isinstance(original_value, datetime.date) else
            datetime.datetime.strptime(original_value, "%Y-%m-%d").year
        )
        # print(f"{type(original_value)}, {original_value}, {type(birth_date)}, {birth_date}")
        return birth_date.replace(year=year)
