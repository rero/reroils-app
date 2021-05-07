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

"""Circulation Policy Record tests."""

from utils import get_mapping

from rero_ils.modules.circ_policies.api import CircPoliciesSearch, CircPolicy


def test_circ_policy_es_mapping(es_clear, db, org_martigny,
                                circ_policy_martigny_data_tmp):
    """Test circulation policy elasticsearch mapping."""
    search = CircPoliciesSearch()
    mapping = get_mapping(search.Meta.index)
    assert mapping
    CircPolicy.create(
        circ_policy_martigny_data_tmp,
        dbcommit=True,
        reindex=True,
        delete_pid=True
    )
    assert mapping == get_mapping(search.Meta.index)


def test_circ_policies_search_mapping(app, circulation_policies):
    """Test circulation policy search mapping."""
    search = CircPoliciesSearch()

    c = search.query('query_string', query='policy').count()
    assert c == 4
    c = search.query('match', name='default').count()
    assert c == 2
    es_query = search.query('match', name='temporary').source(['pid']).scan()
    pids = [hit.pid for hit in es_query]
    assert len(pids) == 1
    assert 'cipo3' in pids
