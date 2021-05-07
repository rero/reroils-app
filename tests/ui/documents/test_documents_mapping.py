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

"""Document mapping tests."""

from copy import deepcopy

import mock
from elasticsearch_dsl.query import MultiMatch
from utils import get_mapping, mock_response

from rero_ils.modules.documents.api import Document, DocumentsSearch


@mock.patch('requests.get')
def test_document_es_mapping(mock_contributions_mef_get, es, db, org_martigny,
                             document_data_ref, item_lib_martigny,
                             contribution_person_response_data):
    """Test document elasticsearch mapping."""
    search = DocumentsSearch()
    mapping = get_mapping(search.Meta.index)
    assert mapping
    data = deepcopy(document_data_ref)
    mock_contributions_mef_get.return_value = mock_response(
        json_data=contribution_person_response_data
    )
    Document.create(
        data,
        dbcommit=True,
        reindex=True,
        delete_pid=True
    )
    assert mapping == get_mapping(search.Meta.index)


def test_document_search_mapping(app, document_records):
    """Test document search mapping."""
    search = DocumentsSearch()

    count = search.query('query_string', query='reine Berthe').count()
    assert count == 2

    count = search.query('query_string', query='maison').count()
    assert count == 1

    count = search.query('query_string', query='Körper').count()
    assert count == 1

    count = search.query('query_string', query='Chamber Secrets').count()
    assert count == 1

    query = MultiMatch(query='Chamber of Secrets',
                       fields=['title._text.*'])
    count = search.query(query).count()
    assert count == 1

    count = search.query('query_string', query='9782823855890').count()
    assert count == 1

    count = search.query('query_string', query='2823855890').count()
    assert count == 1
