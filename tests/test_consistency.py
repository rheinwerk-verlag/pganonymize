"""Cross-table consistency tests for the anonymization registry."""

from collections import OrderedDict

import pytest
from mock.mock import patch

from pganonymize.providers import faker_initializer
from pganonymize.utils import (
    ANONYMIZED_BY_KEY,
    _assert_yaml_ordering,
    _consistent_group_for,
    _normalize_key,
    get_column_values,
)


@pytest.fixture(autouse=True)
def clear_registry():
    """Each test starts from an empty consistency registry."""
    ANONYMIZED_BY_KEY.clear()
    yield
    ANONYMIZED_BY_KEY.clear()


@pytest.fixture(autouse=True)
def faker_options():
    """FakerInitializer reads config.schema lazily; provide a minimal options stub."""
    with patch.object(faker_initializer, '_options', {'locales': ['it_IT'], 'default_locale': 'it_IT'}), \
         patch.object(faker_initializer, '_faker', None):
        yield


class TestConsistentGroupFor:
    """Routing of provider name + raw value to a registry group."""

    @pytest.mark.parametrize('provider_name, raw_value, expected', [
        ('fiscalcode', 'RSSMRA80A01H501X', 'fiscal_person'),
        ('fiscalcodevat', 'RSSMRA80A01H501X', 'fiscal_person'),
        ('fiscalcodevat', '12345678901', 'fiscal_business_or_vat'),
        ('fiscalcodebusiness', '12345678901', 'fiscal_business_or_vat'),
        ('vatnumber', 'IT12345678901', 'fiscal_business_or_vat'),
        ('fake.first_name', 'Mario', 'fake.first_name'),
        ('md5', 'foo@bar.it', 'md5'),
        ('uuid4', 'anything', None),
        ('apikey', 'token-xyz', None),
        ('clear', 'value', None),
    ])
    def test_routing(self, provider_name, raw_value, expected):
        assert _consistent_group_for(provider_name, raw_value) == expected


class TestNormalizeKey:
    """Normalization of raw values into registry keys."""

    @pytest.mark.parametrize('group_id, raw, expected', [
        ('fiscal_person', '  rssmra80a01h501x  ', 'RSSMRA80A01H501X'),
        ('fiscal_business_or_vat', 'IT12345678901', '12345678901'),
        ('fiscal_business_or_vat', 'it12345678901', '12345678901'),
        ('fiscal_business_or_vat', '12345678901', '12345678901'),
        ('fake.first_name', 'Mario', 'Mario'),
        ('fake.first_name', '  Mario  ', 'Mario'),
        ('any', None, None),
        ('any', '', None),
    ])
    def test_normalize(self, group_id, raw, expected):
        assert _normalize_key(group_id, raw) == expected


class TestCrossTableConsistency:
    """Same raw value across distinct tables must yield the same anonymized output."""

    def test_same_raw_same_provider_same_output(self):
        cols = [{'firstName': {'provider': {'name': 'fake.first_name'}}}]
        row_a = OrderedDict([('firstName', 'Mario')])
        row_b = OrderedDict([('firstName', 'Mario')])
        out_a = get_column_values(row_a, cols)
        out_b = get_column_values(row_b, cols)
        assert out_a['firstName'] == out_b['firstName']

    def test_distinct_raw_have_independent_registry_slots(self):
        cols = [{'firstName': {'provider': {'name': 'fake.first_name'}}}]
        out_mario = get_column_values(OrderedDict([('firstName', 'Mario')]), cols)
        out_luca = get_column_values(OrderedDict([('firstName', 'Luca')]), cols)
        assert ('fake.first_name', 'Mario') in ANONYMIZED_BY_KEY
        assert ('fake.first_name', 'Luca') in ANONYMIZED_BY_KEY
        assert out_mario['firstName'] == ANONYMIZED_BY_KEY[('fake.first_name', 'Mario')]
        assert out_luca['firstName'] == ANONYMIZED_BY_KEY[('fake.first_name', 'Luca')]

    def test_vat_and_business_fiscal_share_core(self):
        """``vatnumber`` and ``fiscalcodebusiness`` share the 9-digit core for the same raw."""
        vat_cols = [{'vatNumber': {'provider': {'name': 'vatnumber'}}}]
        fcb_cols = [{'fiscalCode': {'provider': {'name': 'fiscalcodebusiness'}}}]

        vat_out = get_column_values(OrderedDict([('vatNumber', 'IT12345678901')]), vat_cols)['vatNumber']
        fcb_out = get_column_values(OrderedDict([('fiscalCode', '12345678901')]), fcb_cols)['fiscalCode']

        # ``vatnumber`` returns ``IT<core>``; ``fiscalcodebusiness`` returns ``<core>``.
        assert vat_out.startswith('IT')
        assert vat_out[2:] == fcb_out

    def test_fiscalcodevat_letter_reuses_fiscalcode_publisher(self):
        """user_profile.fiscalCode publishes; sim_account.fiscalId (letter-leading) reuses."""
        user_profile_cols = [
            {'firstName': {'provider': {'name': 'fake.first_name'}}},
            {'lastName': {'provider': {'name': 'fake.last_name'}}},
            {'birthDate': {'provider': {'name': 'set', 'value': '1980-01-01'}}},
            {'fiscalCode': {'provider': {
                'name': 'fiscalcode',
                'use_row': True,
                'surname_field': 'lastName',
                'name_field': 'firstName',
                'birth_date_field': 'birthDate',
                'gender_field': 'sex',
            }}},
        ]
        sim_cols = [{'fiscalId': {'provider': {'name': 'fiscalcodevat'}}}]

        user_row = OrderedDict([
            ('firstName', 'Mario'),
            ('lastName', 'Rossi'),
            ('birthDate', '1970-05-15'),
            ('sex', 'M'),
            ('fiscalCode', 'RSSMRA70E15H501Z'),
        ])
        user_out = get_column_values(user_row, user_profile_cols)
        published_cf = user_out['fiscalCode']

        sim_row = OrderedDict([('fiscalId', 'RSSMRA70E15H501Z')])
        sim_out = get_column_values(sim_row, sim_cols)
        assert sim_out['fiscalId'] == published_cf

    def test_fiscalcodevat_digit_reuses_vat_publisher(self):
        """business_profile.vatNumber publishes; sim_account.fiscalId (digit-leading) reuses."""
        bp_cols = [{'vatNumber': {'provider': {'name': 'vatnumber'}}}]
        sim_cols = [{'fiscalId': {'provider': {'name': 'fiscalcodevat'}}}]

        bp_out = get_column_values(OrderedDict([('vatNumber', 'IT12345678901')]), bp_cols)
        vat_core = bp_out['vatNumber'][2:]  # drop IT

        sim_out = get_column_values(OrderedDict([('fiscalId', '12345678901')]), sim_cols)
        # fiscalcodevat (digit-leading) outputs the bare 9-digit core
        assert sim_out['fiscalId'] == vat_core

    def test_non_consistent_provider_always_fresh(self):
        """``uuid4`` must produce a new value on every call (no registry caching)."""
        cols = [{'token': {'provider': {'name': 'uuid4'}}}]
        out_a = get_column_values(OrderedDict([('token', 'orig')]), cols)
        out_b = get_column_values(OrderedDict([('token', 'orig')]), cols)
        assert out_a['token'] != out_b['token']

    def test_null_input_skipped(self):
        cols = [{'firstName': {'provider': {'name': 'fake.first_name'}}}]
        out = get_column_values(OrderedDict([('firstName', None)]), cols)
        assert 'firstName' not in out

    def test_md5_consistent_across_calls(self):
        cols = [{'email': {'provider': {'name': 'md5'}}}]
        out_a = get_column_values(OrderedDict([('email', 'foo@bar.com')]), cols)
        out_b = get_column_values(OrderedDict([('email', 'foo@bar.com')]), cols)
        assert out_a['email'] == out_b['email']


class TestYamlOrdering:

    def test_valid_ordering_passes(self):
        definitions = [
            {'user_profile': {}},
            {'business_profile': {}},
            {'sim_account': {}},
            {'cdt_account': {}},
            {'anchor_investor': {}},
        ]
        _assert_yaml_ordering(definitions)  # no raise

    def test_sim_account_before_user_profile_raises(self):
        definitions = [
            {'sim_account': {}},
            {'user_profile': {}},
        ]
        with pytest.raises(ValueError, match="sim_account.*must come after.*user_profile"):
            _assert_yaml_ordering(definitions)

    def test_anchor_investor_before_business_profile_raises(self):
        definitions = [
            {'anchor_investor': {}},
            {'business_profile': {}},
        ]
        with pytest.raises(ValueError, match="anchor_investor.*must come after.*business_profile"):
            _assert_yaml_ordering(definitions)

    def test_missing_publisher_is_ignored(self):
        """If the publisher is absent, consumer ordering is irrelevant."""
        definitions = [
            {'sim_account': {}},
            {'cdt_account': {}},
        ]
        _assert_yaml_ordering(definitions)  # no raise

    def test_unrelated_tables_dont_matter(self):
        definitions = [
            {'investment_order': {}},
            {'system_log': {}},
        ]
        _assert_yaml_ordering(definitions)  # no raise
