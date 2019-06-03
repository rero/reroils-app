# -*- coding: utf-8 -*-
#
# This file is part of RERO ILS.
# Copyright (C) 2017 RERO.
#
# RERO ILS is free software; you can redistribute it
# and/or modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 2 of the
# License, or (at your option) any later version.
#
# RERO ILS is distributed in the hope that it will be
# useful, but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with RERO ILS; if not, write to the
# Free Software Foundation, Inc., 59 Temple Place, Suite 330, Boston,
# MA 02111-1307, USA.
#
# In applying this license, RERO does not
# waive the privileges and immunities granted to it by virtue of its status
# as an Intergovernmental Organization or submit itself to any jurisdiction.

"""Pytest configuration."""

from __future__ import absolute_import, print_function

from json import loads

import pytest
from pkg_resources import resource_string


@pytest.fixture()
def circ_policy_schema():
    """Patron Jsonschema for records."""
    schema_in_bytes = resource_string(
        'rero_ils.modules.circ_policies.jsonschemas',
        'circ_policies/circ_policy-v0.0.1.json',
    )
    schema = loads(schema_in_bytes.decode('utf8'))
    return schema


@pytest.fixture()
def notification_schema():
    """Notifications Jsonschema for records."""
    schema_in_bytes = resource_string(
        'rero_ils.modules.notifications.jsonschemas',
        '/notifications/notification-v0.0.1.json'
    )
    schema = loads(schema_in_bytes.decode('utf8'))
    return schema


@pytest.fixture()
def item_type_schema():
    """Item type Jsonschema for records."""
    schema_in_bytes = resource_string(
        'rero_ils.modules.item_types.jsonschemas',
        '/item_types/item_type-v0.0.1.json'
    )
    schema = loads(schema_in_bytes.decode('utf8'))
    return schema


@pytest.fixture()
def library_schema():
    """Library Jsonschema for records."""
    schema_in_bytes = resource_string(
        'rero_ils.modules.libraries.jsonschemas',
        'libraries/library-v0.0.1.json'
    )
    schema = loads(schema_in_bytes.decode('utf8'))
    return schema


@pytest.fixture()
def location_schema():
    """Location Jsonschema for records."""
    schema_in_bytes = resource_string(
        'rero_ils.modules.locations.jsonschemas',
        'locations/location-v0.0.1.json')
    schema = loads(schema_in_bytes.decode('utf8'))
    return schema


@pytest.fixture()
def organisation_schema():
    """Organisation Jsonschema for records."""
    schema_in_bytes = resource_string(
        'rero_ils.modules.organisations.jsonschemas',
        'organisations/organisation-v0.0.1.json',
    )
    schema = loads(schema_in_bytes.decode('utf8'))
    return schema


@pytest.fixture()
def patron_type_schema():
    """Patron type Jsonschema for records."""
    schema_in_bytes = resource_string(
        'rero_ils.modules.patron_types.jsonschemas',
        '/patron_types/patron_type-v0.0.1.json',
    )
    schema = loads(schema_in_bytes.decode('utf8'))
    return schema


@pytest.fixture()
def patron_schema():
    """Patron Jsonschema for records."""
    schema_in_bytes = resource_string(
        'rero_ils.modules.patrons.jsonschemas', '/patrons/patron-v0.0.1.json'
    )
    schema = loads(schema_in_bytes.decode('utf8'))
    return schema


@pytest.fixture()
def mef_persons_schema():
    """Patron Jsonschema for records."""
    schema_in_bytes = resource_string(
        'rero_ils.modules.mef_persons.jsonschemas',
        '/persons/mef_person-v0.0.1.json'
    )
    schema = loads(schema_in_bytes.decode('utf8'))
    return schema


@pytest.fixture()
def document_schema():
    """Jsonschema for documents."""
    schema_in_bytes = resource_string(
        'rero_ils.modules.documents.jsonschemas',
        'documents/document-v0.0.1.json'
    )
    schema = loads(schema_in_bytes.decode('utf8'))
    return schema


@pytest.fixture()
def item_schema():
    """Item Jsonschema for records."""
    schema_in_bytes = resource_string(
        'rero_ils.modules.items.jsonschemas', 'items/item-v0.0.1.json'
    )
    schema = loads(schema_in_bytes.decode('utf8'))
    return schema
