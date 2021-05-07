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

from rero_ils.modules.libraries.api import LibrariesSearch, Library


def test_library_es_mapping(es, db, lib_martigny_data, org_martigny):
    """Test library elasticsearch mapping."""
    search = LibrariesSearch()
    mapping = get_mapping(search.Meta.index)
    assert mapping
    lib = Library.create(
        lib_martigny_data, dbcommit=True, reindex=True, delete_pid=True)
    assert mapping == get_mapping(search.Meta.index)
    lib.delete(force=True, dbcommit=True, delindex=True)


def test_libraries_search_mapping(app, libraries_records):
    """Test library search mapping."""
    search = LibrariesSearch()

    assert search.query(
        'query_string', query='Fully Library Restricted Space'
    ).count() == 4
    assert search.query('query_string', query='bibliothèque').count() == 1
    assert search.query('query_string', query='library AND Martigny').count() \
           == 1
    assert search.query('match', name='Aproz').count() == 1

    es_query = search.query('match', name='Sion').source(['pid']).scan()
    pids = [hit.pid for hit in es_query]
    assert len(pids) == 1
    assert 'lib4' in pids
