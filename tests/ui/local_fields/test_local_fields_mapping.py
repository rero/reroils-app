# -*- coding: utf-8 -*-
#
# RERO ILS
# Copyright (C) 2020 RERO
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

from rero_ils.modules.local_fields.api import LocalField, LocalFieldsSearch


def test_local_field_es_mapping(
        es, db, org_martigny, document, local_field_martigny_data):
    """Test local field elasticsearch mapping."""
    search = LocalFieldsSearch()
    mapping = get_mapping(search.Meta.index)
    assert mapping
    lf = LocalField.create(
        local_field_martigny_data,
        dbcommit=True,
        reindex=True,
        delete_pid=True)
    assert mapping == get_mapping(search.Meta.index)
    lf.delete(force=True, dbcommit=True, delindex=True)


def test_libraries_search_mapping(
        app, org_martigny, org_sion, document, local_fields_records):
    """Test local field search mapping."""
    search = LocalFieldsSearch()

    assert search.query('query_string', query='Auteur').count() == 2
    assert search.query('query_string', query='Bibliographie').count() == 1

    pids = [r.pid for r in search.query(
         'match', fields__field_2='students').source(['pid']).scan()]
    assert 'lofi2' in pids
