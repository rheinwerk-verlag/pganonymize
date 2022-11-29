Localization
============

It's possible to use the localization feature of ``Faker`` to localize the generated data.

To localize the data, add the locales to use as a global option to the YAML schema:

.. code-block:: yaml

    tables:
      auth_user:
        fields:
          - name:
            provider:
              name: fake.name
          - street:
            provider:
              name: fake.street_address
          - city:
            provider:
              name: fake.city

    options:
      faker:
        locales:
          - de_DE
          - en_US

Now any field using the ``Faker`` provider will generate localized data. When multiple locales are configured, ``Faker``
will use its `Multiple Locale Mode <https://faker.readthedocs.io/en/master/fakerclass.html#multiple-locale-mode>`_.
In the example above, ``Faker`` selects the locale randomly for each field and row.

It's also possible to define the locale to use on field level and to define a default locale:

.. code-block:: yaml

    tables:
      - user:
          primary_key: id
          fields:
            - name:
                provider:
                  # No locale entry at all, use configured default_locale "de_DE"
                  name: fake.name
            - city:
                provider:
                  # Use "en_US"
                  name: fake.city
                  locale: en_US
            - street:
                provider:
                  # Use "cs_CZ"
                  name: fake.street_address
                  locale: cs_CZ
            - zipcode:
                provider:
                  # Use empty locale to ignore default_locale and to randomly select locale
                  name: fake.postcode
                  locale:

    options:
      faker:
        locales:
          - de_DE
          - en_US
          - cs_CZ
        default_locale: de_DE

.. ATTENTION::
    Make sure that the ``Faker`` provider (e.g. ``street_name``) is supported by the
    `Localized Provider <https://faker.readthedocs.io/en/master/locales.html>`_.
