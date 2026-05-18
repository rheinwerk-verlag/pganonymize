"""Helper methods"""


from __future__ import absolute_import
import typing
import json
import logging
import math
import re
import subprocess
import time
from datetime import datetime, date

from cachetools import cached
from cachetools.keys import hashkey

import parmap
import psycopg2
import psycopg2.extras
from pgcopy import CopyManager
from psycopg2.sql import SQL, Composed, Identifier
from tqdm import trange

from pganonymize.config import config
from pganonymize.constants import DEFAULT_CHUNK_SIZE, DEFAULT_PRIMARY_KEY
from pganonymize.providers import provider_registry

# Needed to work with UUID objects
psycopg2.extras.register_uuid()

global_cache = {}

# Maps (str(user_id), normalized_original_value) -> anonymized value.
# Composite key keeps distinct anonymizations when the same userId has multiple original
# fiscal/vat values across rows or tables. Populated by ``publish_anonymized_fiscal_user_id_field``
# and consumed by ``reuse_anonymized_fiscal_user_id_field``. Process publishing tables
# (e.g. ``user_profile``) before reusing ones (e.g. ``sim_account`` / ``cdt_account``).
ANONYMIZED_FISCAL_BY_USER_ID = {}


def _fiscal_publish_key(user_id, raw_value):
    """Composite key for the user→fiscal registry; ``None`` when either side is missing."""
    if user_id is None or raw_value is None:
        return None
    return (str(user_id), str(raw_value).strip())


# Maps normalized original VAT/business-fiscal string -> 9-digit "core" anonymized value.
# Indexed by the original value (across tables / providers) so that VAT-like identifiers stay
# consistent. The stored core is the 9-digit body shared by ``vatnumber``, ``fiscalcodebusiness``
# and the digit-leading branch of ``fiscalcodevat``; consumers rebuild the prefixed form when
# needed (e.g. ``vatnumber`` re-prepends ``IT``). Populated by ``publish_anonymized_vat`` and
# consumed by ``reuse_anonymized_vat``.
ANONYMIZED_VAT_BY_ORIGINAL = {}


def _vat_normalize_original(raw):
    """Drop leading ``IT`` and surrounding spaces, uppercase: registry key."""
    if raw is None:
        return None
    s = str(raw).strip().upper()
    if s.startswith('IT'):
        s = s[2:]
    return s or None


def _vat_extract_core(anonymized_value):
    """Strip ``IT`` prefix from an anonymized VAT-like output; keep only digit strings."""
    if anonymized_value is None:
        return None
    s = str(anonymized_value).strip().upper()
    if s.startswith('IT'):
        s = s[2:]
    return s if s.isdigit() else None


def _vat_format_for_provider(provider_name, core_digits):
    """Re-shape the 9-digit core to match the format expected by ``provider_name``."""
    if core_digits is None:
        return None
    return f'IT{core_digits}' if provider_name == 'vatnumber' else core_digits


def _merge_select_columns(primary_key, anonymized_column_names, context_columns):
    """Primary key first, then anonymized fields, then extra context columns (deduplicated)."""
    context_columns = context_columns or []
    seen = set()
    out = []
    for col in [primary_key] + list(anonymized_column_names) + list(context_columns):
        if col not in seen:
            seen.add(col)
            out.append(col)
    return out


def anonymize_tables(connection, verbose=False, dry_run=False):
    """
    Anonymize a list of tables according to the schema definition.

    :param connection: A database connection instance.
    :param bool verbose: Display logging information and a progress bar.
    :param bool dry_run: Script is running in dry-run mode, no commit expected.
    """
    definitions = config.schema.get('tables', [])
    ANONYMIZED_FISCAL_BY_USER_ID.clear()
    ANONYMIZED_VAT_BY_ORIGINAL.clear()
    for definition in definitions:
        start_time = time.time()
        table_name = list(definition.keys())[0]
        logging.info('Found table definition "%s"', table_name)
        table_definition = definition[table_name]
        columns = table_definition.get('fields', [])
        excludes = table_definition.get('excludes', [])
        search = table_definition.get('search')
        primary_key = table_definition.get('primary_key', DEFAULT_PRIMARY_KEY)
        total_count = get_table_count(connection, table_name, dry_run)
        chunk_size = table_definition.get('chunk_size', DEFAULT_CHUNK_SIZE)
        context_columns = table_definition.get('context_columns') or []
        build_and_then_import_data(
            connection, table_name, primary_key, columns, excludes,
            search, total_count, chunk_size, context_columns=context_columns,
            verbose=verbose, dry_run=dry_run,
        )
        end_time = time.time()
        logging.info('{} anonymization took {:.2f}s'.format(table_name, end_time - start_time))

    # print("AAAAAAAAA", global_cache)
    # with open("/tmp/pp", 'wb') as f:
    #     pickle.dump(global_cache, f)


def process_row(row, columns, excludes):
    if row_matches_excludes(row, excludes):
        return None
    else:
        row_column_dict = get_column_values(row, columns)
        if row_column_dict:
            for key, value in row_column_dict.items():
                row[key] = value
        else:
            return None
        return row


def build_and_then_import_data(connection, table, primary_key, columns,
                               excludes, search, total_count, chunk_size,
                               context_columns=None, verbose=False, dry_run=False):
    """
    Select all data from a table and return it together with a list of table columns.

    :param connection: A database connection instance.
    :param str table: Name of the table to retrieve the data.
    :param str primary_key: Table primary key
    :param list columns: A list of table fields
    :param list[dict] excludes: A list of exclude definitions.
    :param str search: A SQL WHERE (search_condition) to filter and keep only the searched rows.
    :param int total_count: The amount of rows for the current table
    :param int chunk_size: Number of data rows to fetch with the cursor
    :param list context_columns: Extra source columns included in SELECT/COPY but not listed in
        ``fields`` (not anonymized). Use for linkage ids (e.g. ``userId``) with fiscal reuse options.
    :param bool verbose: Display logging information and a progress bar.
    :param bool dry_run: Script is running in dry-run mode, no commit expected.
    """
    column_names = get_column_names(columns)
    select_columns = _merge_select_columns(primary_key, column_names, context_columns)
    sql_columns = SQL(', ').join([Identifier(column_name) for column_name in select_columns])
    sql_select = SQL('SELECT {columns} FROM {table}').format(table=Identifier(table), columns=sql_columns)
    if search:
        sql_select = Composed([sql_select, SQL(" WHERE {search_condition}".format(search_condition=search))])
    if dry_run:
        sql_select = Composed([sql_select, SQL(" LIMIT 100")])
        logging.info(sql_select.as_string(connection))
    cursor = connection.cursor(cursor_factory=psycopg2.extras.DictCursor, name='fetch_large_result')
    cursor.execute(sql_select.as_string(connection))
    temp_table = 'tmp_{table}'.format(table=table)
    create_temporary_table(connection, columns, table, temp_table, primary_key, context_columns)
    batches = int(math.ceil((1.0 * total_count) / (1.0 * chunk_size)))
    for i in trange(batches, desc="Processing {} batches for {}".format(batches, table), disable=not verbose):
        records = cursor.fetchmany(size=chunk_size)
        if records:
            data = parmap.map(process_row, records, columns, excludes, pm_pbar=verbose, pm_parallel=False)
            import_data(connection, temp_table, select_columns, filter(None, data))
    apply_anonymized_data(connection, temp_table, table, primary_key, columns)

    cursor.close()


def apply_anonymized_data(connection, temp_table, source_table, primary_key, definitions):
    logging.info('Applying changes on table {}'.format(source_table))
    cursor = connection.cursor()
    create_index_sql = SQL('CREATE INDEX ON {temp_table} ({primary_key})')
    sql = create_index_sql.format(temp_table=Identifier(temp_table), primary_key=Identifier(primary_key))
    cursor.execute(sql.as_string(connection))

    column_names = get_column_names(definitions)
    columns_identifiers = [SQL('{column} = s.{column}').format(column=Identifier(column)) for column in column_names]
    set_columns = SQL(', ').join(columns_identifiers)
    sql_args = {
        'table': Identifier(source_table),
        'columns': set_columns,
        'source': Identifier(temp_table),
        'primary_key': Identifier(primary_key)
    }
    sql = SQL(
        'UPDATE {table} t '
        'SET {columns} '
        'FROM {source} s '
        'WHERE t.{primary_key} = s.{primary_key}'
    ).format(**sql_args)
    cursor.execute(sql.as_string(connection))
    cursor.close()


def row_matches_excludes(row, excludes=None):
    """
    Check whether a row matches a list of field exclusion patterns.

    :param list row: The data row
    :param list excludes: A list of field exclusion roles, e.g.:

    >>> [
    >>>     {'email': ['\\S.*@example.com', '\\S.*@foobar.com', ]}
    >>> ]

    :return: True or False
    :rtype: bool
    """
    excludes = excludes if excludes else []
    for definition in excludes:
        column = list(definition.keys())[0]
        for exclude in definition.get(column, []):
            pattern = re.compile(exclude, re.IGNORECASE)
            try:
                if row[column] is not None and pattern.match(row[column]):
                    return True
            except BaseException:
                pass
    return False


def create_temporary_table(connection, definitions, source_table, temp_table, primary_key,
                            context_columns=None):
    primary_key = primary_key if primary_key else DEFAULT_PRIMARY_KEY
    column_names = get_column_names(definitions)
    select_columns = _merge_select_columns(primary_key, column_names, context_columns)
    sql_columns = SQL(', ').join([Identifier(column_name) for column_name in select_columns])
    ctas_query = SQL("""CREATE TEMP TABLE {temp_table} AS SELECT {columns}
                    FROM {source_table} WITH NO DATA""")
    cursor = connection.cursor()
    cursor.execute(ctas_query.format(temp_table=Identifier(temp_table),
                                     source_table=Identifier(source_table), columns=sql_columns)
                   .as_string(connection)
                   )
    cursor.close()


def import_data(connection, table_name, column_names, data):
    """
    Import the temporary and anonymized data to a temporary table and write the changes back.

    :param connection: A database connection instance.
    :param str table_name: Name of the table to be populated with data.
    :param list column_names: A list of table fields
    :param list data: The table data.
    """
    mgr = CopyManager(connection, table_name, column_names)
    mgr.copy([[escape_str_replace(val) for col, val in row.items()] for row in data])


def get_connection(pg_args):
    """
    Return a connection to the database.

    :param pg_args:
    :return: A psycopg connection instance
    :rtype: psycopg2.connection
    """
    return psycopg2.connect(**pg_args)


def get_table_count(connection, table, dry_run):
    """
    Return the number of table entries.

    :param connection: A database connection instance
    :param str table: Name of the database table
    :param bool dry_run: Script is running in dry-run mode, no commit expected.
    :return: The number of table entries
    :rtype: int
    """
    if dry_run:
        return 100
    else:
        sql = SQL('SELECT COUNT(*) FROM {table}').format(table=Identifier(table))
        cursor = connection.cursor()
        cursor.execute(sql.as_string(connection))
        total_count = cursor.fetchone()[0]
        cursor.close()
        return total_count


def _normalize_provider_cache_name(raw_name):
    """Strip Faker-style ``fake.`` prefix for cache partitioning (matches YAML ``name: fake.*``)."""
    if not raw_name:
        return ''
    segment = raw_name.split('fake.')[-1]
    return segment.lstrip('.')


def _provider_cache_bucket(normalized_name, value):
    """
    Map a provider to a cache partition shared only with providers whose
    ``alter_value`` yields the same string for the same ``value``.

    ``@cached`` stores the return value of ``generate_value`` without re-calling
    ``alter_value``. If two providers shared a key but differed in logic, the
    first hit would poison the cache for the other (order-dependent bugs).
    """
    if normalized_name == 'fiscalcodebusiness':
        return 'fiscal_md5_9digits'
    if normalized_name == 'fiscalcodevat':
        s = str(value).strip() if value is not None else ''
        if s and s[0].isdigit():
            return 'fiscal_md5_9digits'
        return 'fiscalcodevat_natural'
    if normalized_name == 'fiscalcode':
        return 'fiscalcode'
    if normalized_name == 'vatnumber':
        return 'vatnumber'
    return normalized_name


def cache_key_generator(provider_name, value):
    """
    Build a stable cache key for :func:`generate_value`.

    ``value`` is normalized for ``hashkey``; the provider branch for
    ``fiscalcodevat`` uses the raw value shape (before ``json.dumps``) so
    numeric-vs-natural detection stays correct.
    """
    normalized = _normalize_provider_cache_name(provider_name)
    bucket = _provider_cache_bucket(normalized, value)
    if isinstance(value, (datetime, date)):
        value = value.isoformat()
    if not isinstance(value, typing.Hashable):
        value = json.dumps(value)
    return hashkey(bucket, value)


@cached(
    cache=global_cache,
    key=lambda provider_class, orig_value, **provider_config: cache_key_generator(
        provider_config.get('name'), orig_value)
)
def generate_value(provider_class, orig_value, **provider_config):
    return provider_class.alter_value(orig_value, **provider_config)


def get_column_values(row, columns):
    """
    Return a dictionary for a single data row, with altered data.

    :param psycopg2.extras.DictRow row: A data row from the current table to be altered
    :param list columns: A list of table columns with their provider rules, e.g.:

    >>> [
    >>>     {'guest_email': {'append': '@localhost', 'provider': 'md5'}}
    >>> ]

    :return: A dictionary with all fields that have to be altered and their value for a single data row, e.g.:
        {'guest_email': '12faf5a9bb6f6f067608dca3027c8fcb@localhost'}
    :rtype: dict
    """
    column_dict = {}
    for definition in columns:
        full_column_name = get_column_name(definition, True)
        column_name = get_column_name(definition, False)
        column_definition = definition[full_column_name]
        provider_config = column_definition.get('provider')
        if not provider_config:
            continue
        orig_value = nested_get(row, full_column_name)

        reuse_field = provider_config.get('reuse_anonymized_fiscal_user_id_field')
        if reuse_field:
            link_uid = nested_get(row, reuse_field)
            lookup_key = _fiscal_publish_key(link_uid, orig_value)
            if lookup_key is not None:
                cached_fc = ANONYMIZED_FISCAL_BY_USER_ID.get(lookup_key)
                # Safety net: business-shaped originals (digit-leading) stay on fiscalcodevat,
                # even if a stale match existed in the registry.
                if cached_fc is not None and not lookup_key[1][:1].isdigit():
                    value = cached_fc
                    if append := column_definition.get('append'):
                        value = value + append
                    if _format := column_definition.get('format'):
                        value = _format.format(pga_value=value, **row)
                    nested_set(row, full_column_name, value)
                    column_dict[column_name] = nested_get(row, column_name)
                    continue

        if provider_config.get('reuse_anonymized_vat'):
            vat_key = _vat_normalize_original(orig_value)
            cached_core = ANONYMIZED_VAT_BY_ORIGINAL.get(vat_key) if vat_key else None
            if cached_core is not None:
                value = _vat_format_for_provider(provider_config.get('name'), cached_core)
                if value is not None:
                    if append := column_definition.get('append'):
                        value = value + append
                    if _format := column_definition.get('format'):
                        value = _format.format(pga_value=value, **row)
                    nested_set(row, full_column_name, value)
                    column_dict[column_name] = nested_get(row, column_name)
                    continue

        # Skip the current column if there is no value to be altered
        if orig_value is not None:
            provider_class = provider_registry.get_provider(provider_config['name'])
            if provider_config.get('use_row'):
                value = provider_class.alter_value(orig_value, row=row, **provider_config)
            else:
                value = generate_value(provider_class, orig_value, **provider_config)
            if append := column_definition.get('append'):
                value = value + append
            if _format := column_definition.get('format'):
                value = _format.format(pga_value=value, **row)
            nested_set(row, full_column_name, value)
            column_dict[column_name] = nested_get(row, column_name)

            publish_field = provider_config.get('publish_anonymized_fiscal_user_id_field')
            if publish_field:
                link_uid = nested_get(row, publish_field)
                pub_key = _fiscal_publish_key(link_uid, orig_value)
                if pub_key is not None and value is not None:
                    existing = ANONYMIZED_FISCAL_BY_USER_ID.get(pub_key)
                    if existing is not None and existing != value:
                        logging.warning(
                            'Duplicate fiscal publish for userId=%s original=%s: '
                            'overwriting previous anonymized value.',
                            pub_key[0], pub_key[1],
                        )
                    ANONYMIZED_FISCAL_BY_USER_ID[pub_key] = value

            if provider_config.get('publish_anonymized_vat'):
                vat_key = _vat_normalize_original(orig_value)
                core = _vat_extract_core(value)
                if vat_key and core:
                    existing_core = ANONYMIZED_VAT_BY_ORIGINAL.get(vat_key)
                    if existing_core is not None and existing_core != core:
                        logging.warning(
                            'Duplicate VAT publish for original=%s: '
                            'overwriting previous anonymized core.', vat_key,
                        )
                    ANONYMIZED_VAT_BY_ORIGINAL[vat_key] = core
    return column_dict


def truncate_tables(connection):
    """
    Truncate a list of tables.

    :param connection: A database connection instance
    """
    tables = config.schema.get('truncate', [])
    if not tables:
        return
    cursor = connection.cursor()
    table_names = SQL(', ').join([Identifier(table_name) for table_name in tables])
    logging.info('Truncating tables "%s"', table_names)
    cursor.execute(SQL('TRUNCATE TABLE {tables}').format(tables=table_names).as_string(connection))
    cursor.close()


def create_database_dump(filename, db_args):
    """
    Create a dump file from the current database.

    :param str filename: Path to the dumpfile that should be created
    :param dict db_args: A dictionary with database related information
    """
    arguments = '-d {dbname} -U {user} -h {host} -p {port}'.format(**db_args)
    cmd = 'pg_dump -Fc -Z 9 {args} -f {filename}'.format(
        args=arguments,
        filename=filename
    )
    logging.info('Creating database dump file "%s"', filename)
    subprocess.call(cmd, shell=True)


def get_column_name(definition, fully_qualified=False):
    """
    Get column name by definition.

    :param dict definition: Column definition
    :param bool fully_qualified: Get complete column name with path (json objects)
    :return: A string, containing column name. ex:
        id
        name
        metadata.col1
    :rtype: string
    """
    col_name = list(definition.keys())[0]
    if fully_qualified:
        return col_name
    else:
        return col_name.split('.', 2)[0]


def get_column_names(definitions):
    """
    Get distinct column names from definitions

    :param list definitions: A list of table definitions from the YAML schema.
    :return: A list of column names
    :rtype: list
    """
    names = []
    for definition in definitions:
        name = get_column_name(definition)
        if name not in names:
            names.append(name)
    return names


def escape_str_replace(value):
    """
    Get escaped value.

    :param value: The value to be encoded.
    :return: Escaped value
    """
    if isinstance(value, dict):
        return json.dumps(value).encode()
    if isinstance(value, str):
        return str.encode(value)
    return value


def nested_get(dic, path, delimiter='.'):
    """
    Get from dictionary by path.

    :param dict dic: The source dictionary.
    :param str path: The path within the dictionary.
    :param str delimiter: The path delimiter
    :return: Value at path
    """
    try:
        keys = path.split(delimiter)
        for key in keys[:-1]:
            dic = dic.get(key, {})
        return dic[keys[-1]]
    except (AttributeError, KeyError, TypeError):
        return None


def nested_set(dic, path, value, delimiter='.'):
    """
    Set dictionary value by path.

    :param dict dic: The source dictionary
    :param str path: The path withing dictionary
    :param value: The value to be set
    :param str delimiter: The path delimiter
    """
    keys = path.split(delimiter)
    for key in keys[:-1]:
        dic = dic.get(key, {})
    dic[keys[-1]] = value
