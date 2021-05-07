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

"""Patron elasticsearch mapping tests."""

from utils import get_mapping

from rero_ils.modules.patrons.api import PatronsSearch


def test_patron_es_mapping(
        roles, es, lib_martigny, librarian_martigny_data_tmp):
    """Test patron elasticsearch mapping."""
    search = PatronsSearch()
    mapping = get_mapping(search.Meta.index)
    # TODO: create of an patron
    assert mapping == get_mapping(search.Meta.index)


def test_patron_search_mapping(app, patrons_records, librarian_saxon):
    """Test patron search mapping."""
    search = PatronsSearch()

    assert search.query('query_string', query='Roduit').count() == 1
    assert search.query('match', first_name='Eric').count() == 1
    assert search.query('match', last_name='Moret').count() == 1
    assert search.query('match', first_name='Elena').count() == 1

    eq_query = search.query('match', first_name='Eléna').source(['pid']).scan()
    pids = [hit.pid for hit in eq_query]
    assert len(pids) == 1
    assert librarian_saxon.pid in pids
