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

"""Item type elasticsearch mapping tests."""

from __future__ import absolute_import, print_function

from utils import get_mapping

from rero_ils.modules.item_types.api import ItemType, ItemTypesSearch


def test_item_type_es_mapping(es, db, org_martigny, item_type_data_tmp):
    """Test item type elasticsearch mapping."""
    search = ItemTypesSearch()
    mapping = get_mapping(search.Meta.index)
    assert mapping
    itty = ItemType.create(
        item_type_data_tmp,
        dbcommit=True,
        reindex=True,
        delete_pid=True
    )
    assert mapping == get_mapping(search.Meta.index)
    itty.delete(force=True, dbcommit=True, delindex=True)


def test_item_types_search_mapping(app, item_types_records):
    """Test item type search mapping."""
    search = ItemTypesSearch()

    assert search.query('query_string', query='checkout').count() == 2
    assert search.query('match', name='checkout').count() == 0

    eq_query = search.query('match', name='specific').source(['pid']).scan()
    pids = [hit.pid for hit in eq_query]
    assert len(pids) == 1
    assert 'itty3' in pids
