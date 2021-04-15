# -*- coding: utf-8 -*-
#
# RERO ILS
# Copyright (C) 2019 RERO
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, version 3 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

"""Pytest configuration."""

from __future__ import absolute_import, print_function

from copy import deepcopy

import pytest
from pkg_resources import resource_string
from utils import get_schema

from rero_ils.modules.patrons.api import Patron


@pytest.fixture(scope='module')
def create_app():
    """Create test app."""
    from invenio_app.factory import create_ui
    return create_ui


@pytest.fixture()
def circ_policy_schema(monkeypatch):
    """Circ policy Jsonschema for records."""
    schema_in_bytes = resource_string(
        'rero_ils.modules.circ_policies.jsonschemas',
        'circ_policies/circ_policy-v0.0.1.json',
    )
    return get_schema(monkeypatch, schema_in_bytes)


@pytest.fixture()
def template_schema(monkeypatch):
    """Template Jsonschema for records."""
    schema_in_bytes = resource_string(
        'rero_ils.modules.templates.jsonschemas',
        'templates/template-v0.0.1.json',
    )
    return get_schema(monkeypatch, schema_in_bytes)


@pytest.fixture()
def notification_schema(monkeypatch):
    """Notifications Jsonschema for records."""
    schema_in_bytes = resource_string(
        'rero_ils.modules.notifications.jsonschemas',
        '/notifications/notification-v0.0.1.json'
    )
    return get_schema(monkeypatch, schema_in_bytes)


@pytest.fixture()
def item_type_schema(monkeypatch):
    """Item type Jsonschema for records."""
    schema_in_bytes = resource_string(
        'rero_ils.modules.item_types.jsonschemas',
        '/item_types/item_type-v0.0.1.json'
    )
    return get_schema(monkeypatch, schema_in_bytes)


@pytest.fixture()
def acq_account_schema(monkeypatch):
    """Acq account Jsonschema for records."""
    schema_in_bytes = resource_string(
        'rero_ils.modules.acq_accounts.jsonschemas',
        '/acq_accounts/acq_account-v0.0.1.json'
    )
    return get_schema(monkeypatch, schema_in_bytes)


@pytest.fixture()
def budget_schema(monkeypatch):
    """Budget Jsonschema for records."""
    schema_in_bytes = resource_string(
        'rero_ils.modules.budgets.jsonschemas',
        '/budgets/budget-v0.0.1.json'
    )
    return get_schema(monkeypatch, schema_in_bytes)


@pytest.fixture()
def library_schema(monkeypatch):
    """Library Jsonschema for records."""
    schema_in_bytes = resource_string(
        'rero_ils.modules.libraries.jsonschemas',
        'libraries/library-v0.0.1.json'
    )
    return get_schema(monkeypatch, schema_in_bytes)


@pytest.fixture()
def local_fields_schema(monkeypatch):
    """Local fields Jsonschema for records."""
    schema_in_bytes = resource_string(
        'rero_ils.modules.local_fields.jsonschemas',
        'local_fields/local_field-v0.0.1.json')
    return get_schema(monkeypatch, schema_in_bytes)


@pytest.fixture()
def location_schema(monkeypatch):
    """Location Jsonschema for records."""
    schema_in_bytes = resource_string(
        'rero_ils.modules.locations.jsonschemas',
        'locations/location-v0.0.1.json')
    return get_schema(monkeypatch, schema_in_bytes)


@pytest.fixture()
def patron_transaction_schema(monkeypatch):
    """Patron transaction Jsonschema for records."""
    schema_in_bytes = resource_string(
        'rero_ils.modules.patron_transactions.jsonschemas',
        'patron_transactions/patron_transaction-v0.0.1.json')
    return get_schema(monkeypatch, schema_in_bytes)


@pytest.fixture()
def patron_transaction_event_schema(monkeypatch):
    """Patron transaction event Jsonschema for records."""
    schema_in_bytes = resource_string(
        'rero_ils.modules.patron_transaction_events.jsonschemas',
        'patron_transaction_events/patron_transaction_event-v0.0.1.json')
    return get_schema(monkeypatch, schema_in_bytes)


@pytest.fixture()
def organisation_schema(monkeypatch):
    """Organisation Jsonschema for records."""
    schema_in_bytes = resource_string(
        'rero_ils.modules.organisations.jsonschemas',
        'organisations/organisation-v0.0.1.json',
    )
    return get_schema(monkeypatch, schema_in_bytes)


@pytest.fixture()
def patron_type_schema(monkeypatch):
    """Patron type Jsonschema for records."""
    schema_in_bytes = resource_string(
        'rero_ils.modules.patron_types.jsonschemas',
        '/patron_types/patron_type-v0.0.1.json',
    )
    return get_schema(monkeypatch, schema_in_bytes)


@pytest.fixture()
def patron_schema(monkeypatch):
    """Patron Jsonschema for records."""
    schema_in_bytes = resource_string(
        'rero_ils.modules.patrons.jsonschemas',
        '/patrons/patron-v0.0.1.json'
    )
    return get_schema(monkeypatch, schema_in_bytes)


@pytest.fixture(scope="function")
def patron_martigny_data_tmp_with_id(patron_martigny_data_tmp):
    """Load Martigny patron data scope function with a mocked user_id."""
    patron = Patron.removeUserData(deepcopy(patron_martigny_data_tmp))
    # mock the user_id which is add by the Patron API.
    patron['user_id'] = 100
    return patron


@pytest.fixture()
def contributions_schema(monkeypatch):
    """Patron Jsonschema for records."""
    schema_in_bytes = resource_string(
        'rero_ils.modules.contributions.jsonschemas',
        '/contributions/contribution-v0.0.1.json'
    )
    return get_schema(monkeypatch, schema_in_bytes)


@pytest.fixture()
def document_schema(monkeypatch):
    """Jsonschema for documents."""
    schema_in_bytes = resource_string(
        'rero_ils.modules.documents.jsonschemas',
        'documents/document-v0.0.1.json'
    )
    return get_schema(monkeypatch, schema_in_bytes)


@pytest.fixture()
def item_schema(monkeypatch):
    """Item Jsonschema for records."""
    schema_in_bytes = resource_string(
        'rero_ils.modules.items.jsonschemas',
        'items/item-v0.0.1.json'
    )
    return get_schema(monkeypatch, schema_in_bytes)


@pytest.fixture()
def user_schema(monkeypatch):
    """User Jsonschema for records."""
    schema_in_bytes = resource_string(
        'rero_ils.modules.users.jsonschemas',
        'users/user-v0.0.1.json'
    )
    return get_schema(monkeypatch, schema_in_bytes)


@pytest.fixture()
def holding_schema(monkeypatch):
    """Holdings Jsonschema for records."""
    schema_in_bytes = resource_string(
        'rero_ils.modules.holdings.jsonschemas',
        '/holdings/holding-v0.0.1.json')
    return get_schema(monkeypatch, schema_in_bytes)


@pytest.fixture()
def ill_request_schema(monkeypatch):
    """ILL requests JSONSchema for records."""
    schema_in_bytes = resource_string(
        'rero_ils.modules.ill_requests.jsonschemas',
        '/ill_requests/ill_request-v0.0.1.json')
    return get_schema(monkeypatch, schema_in_bytes)


@pytest.fixture()
def operation_log_schema(monkeypatch):
    """Operation log Jsonschema for records."""
    schema_in_bytes = resource_string(
        'rero_ils.modules.operation_logs.jsonschemas',
        'operation_logs/operation_log-v0.0.1.json'
    )
    return get_schema(monkeypatch, schema_in_bytes)


@pytest.fixture()
def marc21_record():
    """Marc21 record."""
    return {
        'leader': '00000cam a2200000zu 4500',
        '008': '000000|||||||||xx#|||||||||||||||||||||c',
    }


@pytest.fixture()
def mef_record_1():
    """Mef record 1."""
    return {
        '$schema': 'https://ils.rero.ch/schemas/'
                   'contributions/contribution-v0.0.1.json',
        'idref': {
            '$schema': 'https://mef.rero.ch/schemas/'
                       'agents_idref/idref-agent-v0.0.1.json',
            'authorized_access_point': 'Honnoré, Patrick',
            'bf:Agent': 'bf:Person',
            'biographical_information': ['Traduit du japonais en français'],
            'country_associated': 'fr',
            'identifier': 'http://www.idref.fr/072277742',
            'language': ['fre', 'jpn'],
            'md5': '8f1dda5f37239c65d3b3d0d2252ceffb',
            'pid': '072277742',
            'preferred_name': 'Honnoré, Patrick',
            'relation_pid': {'type': 'redirect_from', 'value': '193601680'}
        },
        'pid': '6627670',
        'rero': {
            '$schema': 'https://mef.rero.ch/schemas/'
                       'agents_rero/rero-agent-v0.0.1.json',
            'authorized_access_point': 'Honnoré, Patrick',
            'bf:Agent': 'bf:Person',
            'identifier': 'http://data.rero.ch/02-A009220673',
            'md5': 'c90fa0c93eac4346910734badb77bdce',
            'pid': 'A009220673',
            'preferred_name': 'Honnoré, Patrick'},
        'sources': ['rero', 'idref'],
        'type': 'bf:Person',
        'viaf_pid': '37141584'
    }


@pytest.fixture()
def mef_record_2():
    """Mef record 2."""
    return {
        '$schema': 'https://mef.rero.ch/schemas/mef/mef-v0.0.1.json',
        'gnd': {
            '$schema': 'https://mef.rero.ch/schemas/'
                       'agents_gnd/gnd-agent-v0.0.1.json',
            'authorized_access_point': 'Université de Genève',
            'bf:Agent': 'bf:Organisation',
            'conference': False,
            'country_associated': 'sz',
            'date_of_establishment': '1873',
            'identifier': 'http://d-nb.info/gnd/1010450-1',
            'md5': '291d3a468f69af08fa4a0d352ce71ab4',
            'pid': '004058518',
            'preferred_name': 'Université de Genève',
            'variant_access_point': [
                'Schola Genevensis',
                'University of Geneva',
                'Ženevskij Universitet',
                'Universitet. Genf',
                'Universität Genf',
                'Università di Ginevra',
                'Universidad de Ginebra',
                'UNIGE. Abkuerzung'
            ],
            'variant_name': [
                'Schola Genevensis',
                'University of Geneva',
                'Ženevskij Universitet',
                'Universitet',
                'Universität Genf',
                'Università di Ginevra',
                'Universidad de Ginebra',
                'UNIGE'
            ]
        },
        'idref': {
            '$schema': 'https://mef.rero.ch/schemas/'
                       'agents_idref/idref-agent-v0.0.1.json',
            'authorized_access_point': 'Université de Genève',
            'bf:Agent': 'bf:Organisation',
            'biographical_information': [
                "Fondée en 1559, l'académie devint Université en 1872",
                "3 pl. de l'Université, Genève (Suisse)"
            ],
            'conference': False,
            'country_associated': 'sz',
            'date_of_establishment': '1559',
            'identifier': 'http://www.idref.fr/02643136X',
            'language': ['fre'],
            'md5': '96a27be2a6ee9741dab983c3f403c3ff',
            'pid': '02643136X',
            'preferred_name': 'Université de Genève',
            'relation_pid': {
                'type': 'redirect_from',
                'value': '126899959'
            },
            'variant_access_point': [
                'UNIGE',
                'Academia Genevensis',
                'Académie de Genève',
                'Académie théologique de Genève',
                'Académie de Calvin ( Genève )',
                'Schola Genevensis',
                'Università di Ginevra'
            ],
            'variant_name': [
                'UNIGE',
                'Academia Genevensis',
                'Académie de Genève',
                'Académie théologique de Genève',
                'Académie de Calvin ( Genève )',
                'Schola Genevensis',
                'Università di Ginevra'
            ]
        },
        'pid': '5890765',
        'viaf_pid': '143949988'
    }


@pytest.fixture()
def mef_record_3():
    """Mef record 3."""
    return {
        '$schema': 'https://mef.rero.ch/schemas/mef/mef-v0.0.1.json',
        'gnd': {
            '$schema': 'https://mef.rero.ch/schemas/'
                       'agents_gnd/gnd-agent-v0.0.1.json',
            'authorized_access_point': 'Congrès Ouvrier de France',
            'bf:Agent': 'bf:Organisation',
            'conference': True,
            'identifier': 'http://d-nb.info/gnd/5034321-X',
            'md5': '21ea03e240e10011305acac0cd731813',
            'pid': '050343211',
            'preferred_name': 'Congrès Ouvrier de France'
        },
        'idref': {
            '$schema': 'https://mef.rero.ch/schemas/'
                       'agents_idref/idref-agent-v0.0.1.json',
            'authorized_access_point': 'Congrès ouvrier français',
            'bf:Agent': 'bf:Organisation',
            'biographical_information': [
                'L\'ordre des formes exclues suit l\'ordre chronologique des '
                'publications et correspond à l\'évolution historique '
                '(Cf. la notice des congrès particuliers) On a gardé '
                'volontairement la forme \'Congrès ouvrier français\' '
                'pour toute la série'
            ],
            'conference': False,
            'country_associated': 'fr',
            'date_of_establishment': '1876',
            'identifier': 'http://www.idref.fr/03255608X',
            'language': ['fre'],
            'md5': '4f838b25c1281bc96aa14b9a4ee49572',
            'pid': '03255608X',
            'preferred_name': 'Congrès ouvrier français',
            'variant_access_point': [
                'Congrès ouvrier de France',
                'Congrès socialiste ouvrier de France',
                'Congrès national ouvrier socialiste',
                'Congrès socialiste national ouvrier'
            ],
            'variant_name': [
                'Congrès ouvrier de France',
                'Congrès socialiste ouvrier de France',
                'Congrès national ouvrier socialiste',
                'Congrès socialiste national ouvrier'
            ]
        },
        'pid': '5777972',
        'rero': {
            '$schema': 'https://mef.rero.ch/schemas/'
                       'agents_rero/rero-agent-v0.0.1.json',
            'authorized_access_point': 'Congrès ouvrier de France',
            'bf:Agent': 'bf:Organisation',
            'conference': True,
            'identifier': 'http://data.rero.ch/02-A005462931',
            'md5': 'e94636af02fbfabca711ec87a103f1b3',
            'pid': 'A005462931',
            'preferred_name': 'Congrès ouvrier de France',
            'variant_access_point': [
                'Congrès ouvrier socialiste de France',
                'Congrès national ouvrier socialiste (France)',
                'Congrès socialiste ouvrier de France',
                'Congrès national socialiste ouvrier (France)',
                'Congrès socialiste national ouvrier (France)',
                'Congrès ouvrier français'
            ],
            'variant_name': [
                'Congrès ouvrier socialiste de France',
                'Congrès national ouvrier socialiste (France)',
                'Congrès socialiste ouvrier de France',
                'Congrès national socialiste ouvrier (France)',
                'Congrès socialiste national ouvrier (France)',
                'Congrès ouvrier français'
            ]
        },
        'viaf_pid': '134406719'
    }
