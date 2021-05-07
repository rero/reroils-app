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

"""Libraries elasticsearch mapping tests."""

from utils import get_mapping

from rero_ils.modules.locations.api import Location, LocationsSearch


def test_location_es_mapping(es, db, loc_public_martigny_data,
                             lib_martigny, org_martigny):
    """Test library elasticsearch mapping."""
    search = LocationsSearch()
    mapping = get_mapping(search.Meta.index)
    assert mapping
    loc = Location.create(
        loc_public_martigny_data, dbcommit=True, reindex=True, delete_pid=True)
    new_mapping = get_mapping(search.Meta.index)
    assert mapping == new_mapping
    loc.delete(force=True, dbcommit=True, delindex=True)


def test_location_search_mapping(app, locations_records):
    """Test library search mapping."""
    search = LocationsSearch()

    c = search.query('match', code='MARTIGNY-PUBLIC').count()
    assert c == 1
    c = search.query('match', code='SAXON-PUBLIC').count()
    assert c == 1
