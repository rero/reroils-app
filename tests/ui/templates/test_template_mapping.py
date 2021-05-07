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

from rero_ils.modules.templates.api import Template, TemplatesSearch


def test_template_es_mapping(es, db, templ_doc_public_martigny_data,
                             org_martigny, system_librarian_martigny,
                             librarian_martigny):
    """Test template elasticsearch mapping."""
    search = TemplatesSearch()
    mapping = get_mapping(search.Meta.index)
    assert mapping
    tmpl = Template.create(
        templ_doc_public_martigny_data,
        dbcommit=True, reindex=True, delete_pid=True
    )
    new_mapping = get_mapping(search.Meta.index)
    assert mapping == new_mapping
    tmpl.delete(force=True, dbcommit=True, delindex=True)


def test_template_search_mapping(
        app, templ_doc_public_martigny, templ_doc_private_martigny):
    """Test template search mapping."""
    search = TemplatesSearch()

    c = search.query('match', template_type='documents').count()
    assert c == 2
    c = search.query('match', organisation__pid='org1').count()
    assert c == 2
