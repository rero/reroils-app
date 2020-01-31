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

"""Document serialization."""

from flask import current_app, request
from invenio_records_rest.serializers.response import record_responsify, \
    search_responsify

from ..documents.api import Document
from ..documents.utils import title_format_text_head
from ..documents.views import create_title_alternate_graphic, \
    create_title_responsibilites, create_title_variants
from ..libraries.api import Library
from ..organisations.api import Organisation
from ..persons.api import Person
from ..serializers import JSONSerializer, RecordSchemaJSONV1


class DocumentJSONSerializer(JSONSerializer):
    """Mixin serializing records as JSON."""

    def preprocess_record(self, pid, record, links_factory=None, **kwargs):
        """Prepare a record and persistent identifier for serialization."""
        rec = record
        titles = rec.get('title', [])
        responsibility_statement = rec.get('responsibilityStatement', [])
        responsibilities = \
            create_title_responsibilites(responsibility_statement)
        if responsibilities:
            rec['ui_responsibilities'] = responsibilities
        altgr_titles = create_title_alternate_graphic(titles)
        if altgr_titles:
            rec['ui_title_altgr'] = altgr_titles
        variant_titles = create_title_variants(titles)
        if variant_titles:
            rec['ui_title_variants'] = variant_titles
        if request and request.args.get('resolve') == '1':
            rec = record.replace_refs()
            authors = rec.get('authors', [])
            for idx, author in enumerate(authors):
                pid_value = author.get('pid')
                if pid_value:
                    person = Person.get_record_by_mef_pid(pid_value)
                    if person:
                        authors[idx] = person.dumps_for_document()
        data = super(JSONSerializer, self).preprocess_record(
            pid=pid, record=rec, links_factory=links_factory, kwargs=kwargs)

        return JSONSerializer.add_item_links_and_permissions(record, data, pid)

    def post_process_serialize_search(self, results, pid_fetcher):
        """Post process the search results."""
        # Item filters.
        viewcode = request.args.get('view',  current_app.config.get(
                'RERO_ILS_SEARCH_GLOBAL_VIEW_CODE'
        ))
        records = results.get('hits', {}).get('hits', {})
        for record in records:
            metadata = record.get('metadata', {})
            available = Document.get_record_by_pid(
                metadata.get('pid')).is_available(viewcode)
            metadata['available'] = available
            titles = metadata.get('title', [])
            text_title = title_format_text_head(titles, with_subtitle=False)
            if text_title:
                metadata['ui_title_text'] = text_title
        if viewcode != current_app.config.get(
                'RERO_ILS_SEARCH_GLOBAL_VIEW_CODE'
        ):
            view_id = Organisation.get_record_by_viewcode(viewcode)['pid']
            for record in records:
                metadata = record.get('metadata', {})
                items = metadata.get('items', [])
                if items:
                    output = []
                    for item in items:
                        if item.get('organisation')\
                                .get('organisation_pid') == view_id:
                            output.append(item)
                    record['metadata']['items'] = output

        # Add organisation name
        for org_term in results.get('aggregations', {}).get(
                'organisation', {}).get('buckets', []):
            pid = org_term.get('key')
            name = Organisation.get_record_by_pid(pid).get('name')
            org_term['name'] = name

        # Add library name
        for lib_term in results.get('aggregations', {}).get(
                'library', {}).get('buckets', []):
            pid = lib_term.get('key').split('-')[1]
            name = Library.get_record_by_pid(pid).get('name')
            lib_term['key'] = pid
            lib_term['name'] = name

        return super(
            DocumentJSONSerializer, self).post_process_serialize_search(
                results, pid_fetcher)


json_doc = DocumentJSONSerializer(RecordSchemaJSONV1)
"""JSON v1 serializer."""

json_doc_search = search_responsify(json_doc, 'application/rero+json')
json_doc_response = record_responsify(json_doc, 'application/rero+json')
