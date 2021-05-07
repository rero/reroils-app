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

"""Location Record tests."""

from __future__ import absolute_import, print_function

import pytest
from jsonschema.exceptions import ValidationError
from utils import get_mapping

from rero_ils.modules.locations.api import Location, LocationsSearch
from rero_ils.modules.locations.api import location_id_fetcher as fetcher


def test_location_es_mapping(es_clear, db, lib_martigny,
                             loc_public_martigny_data):
    """Test location elasticsearch mapping."""
    search = LocationsSearch()
    mapping = get_mapping(search.Meta.index)
    assert mapping
    Location.create(
        loc_public_martigny_data,
        dbcommit=True,
        reindex=True,
        delete_pid=True
    )
    assert mapping == get_mapping(search.Meta.index)


def test_location_create(db, es_clear, loc_public_martigny_data, lib_martigny,
                         loc_online_martigny):
    """Test location creation."""
    loc_public_martigny_data['is_online'] = True
    with pytest.raises(ValidationError):
        loc = Location.create(loc_public_martigny_data, delete_pid=True)

    db.session.rollback()

    next_pid = Location.provider.identifier.next()
    del loc_public_martigny_data['is_online']
    loc = Location.create(loc_public_martigny_data, delete_pid=True)
    next_pid += 1
    assert loc == loc_public_martigny_data
    assert loc.get('pid') == str(next_pid)

    loc = Location.get_record_by_pid(str(next_pid))
    assert loc == loc_public_martigny_data

    fetched_pid = fetcher(loc.id, loc)
    assert fetched_pid.pid_value == str(next_pid)
    assert fetched_pid.pid_type == 'loc'


def test_location_organisation_pid(org_martigny, loc_public_martigny):
    """Test organisation pid has been added during the indexing."""
    search = LocationsSearch()
    location = next(search.filter('term', pid=loc_public_martigny.pid).scan())
    assert location.organisation.pid == org_martigny.pid


def test_location_can_delete(loc_public_martigny):
    """Test can delete."""
    assert loc_public_martigny.get_links_to_me() == {}
    assert loc_public_martigny.can_delete
