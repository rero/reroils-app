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

"""Template Record tests."""

from __future__ import absolute_import, print_function

import pytest
from jsonschema.exceptions import ValidationError
from utils import get_mapping

from rero_ils.modules.templates.api import Template, TemplatesSearch
from rero_ils.modules.templates.api import template_id_fetcher as fetcher


def test_template_es_mapping(es_clear, db,
                             templ_doc_public_martigny_data,
                             org_martigny, system_librarian_martigny):
    """Test template elasticsearch mapping."""
    search = TemplatesSearch()
    mapping = get_mapping(search.Meta.index)
    assert mapping
    Template.create(
        templ_doc_public_martigny_data,
        dbcommit=True,
        reindex=True,
        delete_pid=True
    )
    assert mapping == get_mapping(search.Meta.index)


def test_template_create(db, es_clear, templ_doc_public_martigny_data,
                         org_martigny, system_librarian_martigny):
    """Test template creation."""
    templ_doc_public_martigny_data['toto'] = 'toto'
    with pytest.raises(ValidationError):
        temp = Template.create(templ_doc_public_martigny_data, delete_pid=True)

    db.session.rollback()

    next_pid = Template.provider.identifier.next()
    del templ_doc_public_martigny_data['toto']
    temp = Template.create(templ_doc_public_martigny_data, delete_pid=True)
    next_pid += 1
    assert temp == templ_doc_public_martigny_data
    assert temp.get('pid') == str(next_pid)

    temp = Template.get_record_by_pid(str(next_pid))
    assert temp == templ_doc_public_martigny_data

    fetched_pid = fetcher(temp.id, temp)
    assert fetched_pid.pid_value == str(next_pid)
    assert fetched_pid.pid_type == 'tmpl'


def test_template_can_delete(templ_doc_public_martigny):
    """Test can delete."""
    assert templ_doc_public_martigny.get_links_to_me() == {}
    assert templ_doc_public_martigny.can_delete
