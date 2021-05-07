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

"""Organisation Record tests."""

from __future__ import absolute_import, print_function

from rero_ils.modules.organisations.api import Organisation
from rero_ils.modules.organisations.api import \
    organisation_id_fetcher as fetcher
from rero_ils.modules.providers import append_fixtures_new_identifiers


def test_organisation_libararies(org_martigny, lib_martigny):
    """Test libraries retrival."""
    assert list(org_martigny.get_libraries()) == [lib_martigny]


def test_organisation_libararies(org_martigny, vendor_martigny):
    """Test vendors retrival."""
    assert list(org_martigny.get_vendors()) == [vendor_martigny]


def test_organisation_organisation_pid(org_martigny):
    """Test organisation_pid property."""
    assert org_martigny.organisation_pid == 'org1'


def test_organisation_create(app, db, org_martigny_data, org_sion_data):
    """Test organisation creation."""
    org_martigny_data['pid'] = '1'
    org = Organisation.create(org_martigny_data, dbcommit=True, reindex=True)
    assert org == org_martigny_data
    assert org.get('pid') == '1'

    assert org.get_links_to_me() == {}
    assert org.can_delete

    org = Organisation.get_record_by_pid('1')
    assert org == org_martigny_data

    fetched_pid = fetcher(org.id, org)
    assert fetched_pid.pid_value == '1'
    assert fetched_pid.pid_type == 'org'

    org_sion_data['pid'] = '2'
    org = Organisation.create(
        org_sion_data, dbcommit=True, reindex=True)
    assert org.get('pid') == '2'

    identifier = Organisation.provider.identifier
    append_fixtures_new_identifiers(identifier, ['1', '2'], 'org', limit=1)
    assert identifier.next() == identifier.max() == 3
