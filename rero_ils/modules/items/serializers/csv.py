# -*- coding: utf-8 -*-
#
# RERO ILS
# Copyright (C) 2019 RERO
# Copyright (C) 2020 UCLouvain
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

"""Item serializers."""

import csv

import ciso8601
from elasticsearch_dsl import A
from flask import current_app, request, stream_with_context
from invenio_i18n.ext import current_i18n
from invenio_records_rest.serializers.csv import CSVSerializer, Line

from rero_ils.modules.documents.api import DocumentsSearch
from rero_ils.modules.item_types.api import ItemTypesSearch
from rero_ils.modules.libraries.api import LibrariesSearch
from rero_ils.modules.loans.api import LoansSearch
from rero_ils.modules.locations.api import LocationsSearch
from rero_ils.utils import get_i18n_supported_languages

from ..models import ItemNoteTypes

role_filter = [
    'rsp',
    'cre',
    'enj',
    'dgs',
    'prg',
    'dsr',
    'ctg',
    'cmp',
    'inv',
    'com',
    'pht',
    'ivr',
    'art',
    'ive',
    'chr',
    'aut',
    'arc',
    'fmk',
    'pra',
    'csl'
]


class ItemCSVSerializer(CSVSerializer):
    """Serialize item search for csv."""

    def serialize_search(self, pid_fetcher, search_result, links=None,
                         item_links_factory=None):
        """Serialize a search result.

        :param pid_fetcher: Persistent identifier fetcher.
        :param search_result: Elasticsearch search result.
        :param links: Dictionary of links to add to response.
        :param item_links_factory: Factory function for record links.
        """
        # define chunk size
        chunk_size = 1000

        # language
        language = request.args.get("lang", current_i18n.language)
        if not language or language not in get_i18n_supported_languages():
            language = current_app.config.get('BABEL_DEFAULT_LANGUAGE', 'en')

        # prepare mapping dictionnaries
        item_types_map = {}
        for item_type in ItemTypesSearch().scan():
            item_types_map[item_type.pid] = item_type.name
        locations_map = {}
        for location in LocationsSearch().scan():
            locations_map[location.pid] = location.name
        libraries_map = {}
        for library in LibrariesSearch().scan():
            libraries_map[library.pid] = library.name

        def generate_csv():
            def batch(results):
                """Chunk search results.

                :param results: search results.
                :return list of chuncked item pids and search records
                """
                records = []
                pids = []
                for result in results:
                    pids.append(result.pid)
                    records.append(result)
                    if len(records) % chunk_size == 0:
                        yield pids, records
                        pids = []
                        records = []
                yield pids, records

            def get_documents_by_item_pids(item_pids):
                """Get documents for the given item pid list."""

                def _build_doc(data):
                    document_data = {
                        'document_title': next(
                            filter(lambda x: x.get('type') == 'bf:Title',
                                   data.get('title'))
                        ).get('_text')
                    }
                    # process contributions
                    creator = []
                    if 'contribution' in data:
                        for contribution in data.get('contribution'):
                            if any(role in contribution.get('role')
                                   for role in role_filter):
                                authorized_access_point = \
                                    f'authorized_access_point_{language}'
                                if authorized_access_point in contribution\
                                        .get('agent'):
                                    creator.append(
                                        contribution['agent'][
                                            authorized_access_point]
                                    )
                    document_data['document_creator'] = ' ; '.join(creator)
                    document_main_type = []
                    document_sub_type = []
                    for document_type in data.get('type'):
                        # data = document_type.to_dict()
                        document_main_type.append(
                            document_type.get('main_type'))
                        document_sub_type.append(
                            document_type.get('subtype', ''))
                    document_data['document_main_type'] = ', '.join(
                        document_main_type)
                    document_data['document_sub_type'] = ', '.join(
                        document_sub_type)
                    # TODO : build provision activity
                    return document_data

                doc_search = DocumentsSearch() \
                    .filter('terms', holdings__items__pid=list(item_pids)) \
                    .source(
                    ['pid', 'title', 'contribution', 'provisionActivity',
                     'type'])
                docs = {}
                for doc in doc_search.scan():
                    docs[doc.pid] = _build_doc(doc.to_dict())
                return docs

            def get_loans_by_item_pids(item_pids):
                """Get loans for the given item pid list."""
                states = ['PENDING'] + \
                    current_app.config['CIRCULATION_STATES_LOAN_ACTIVE']
                loan_search = LoansSearch() \
                    .filter('terms', state=states) \
                    .filter('terms', item_pid__value=item_pids) \
                    .source(['pid', 'item_pid.value', '_created'])
                agg = A('terms', field='item_pid.value', size=chunk_size)
                loan_search.aggs.bucket('loans_count', agg)

                loan_search = loan_search.extra(
                    collapse={
                        'field': 'item_pid.value',
                        "inner_hits": {
                            "name": "most_recent",
                            "size": 1,
                            "sort": [{"_created": "desc"}],
                        }
                    }
                )

                results = loan_search.execute()
                agg_buckets = {}
                for result in results.aggregations.loans_count.buckets:
                    agg_buckets[result.key] = result.doc_count
                loans = {}
                for loan_hit in results:
                    # get most recent loans
                    loan_data = loan_hit.meta.inner_hits.most_recent[0]\
                        .to_dict()
                    item_pid = loan_data['item_pid']['value']
                    loans[item_pid] = {
                        'loans_count': agg_buckets.get(item_pid, 0),
                        'last_transaction_date': ciso8601.parse_datetime(
                            loan_data['_created']).date()
                    }
                return loans

            headers = dict.fromkeys(self.csv_included_fields)

            # write the CSV output in memory
            line = Line()
            writer = csv.DictWriter(line,
                                    quoting=csv.QUOTE_ALL,
                                    fieldnames=headers)
            writer.writeheader()
            yield line.read()

            for pids, batch_results in batch(search_result):
                # get documents
                documents = get_documents_by_item_pids(pids)

                # get loans
                loans = get_loans_by_item_pids(pids)

                for hit in batch_results:
                    csv_data = hit.to_dict()
                    csv_data['library_name'] = libraries_map[
                        hit['library']['pid']]
                    csv_data['location_name'] = locations_map[
                        hit['location']['pid']]

                    try:
                        # update csv data with document
                        csv_data.update(documents.get(hit['document']['pid']))
                    except Exception as err:
                        current_app.logger.error(
                            'ERROR in csv serializer: '
                            '{message} on document: {pid}'.format(
                                message=err,
                                pid=hit['document']['pid'])
                        )

                    # update csv data with loan
                    csv_data.update(loans.get(hit['pid'], {'loans_count': 0}))

                    # process item type and temporary item type
                    csv_data['item_type'] = item_types_map[
                        hit['item_type']['pid']]
                    temporary_item_type = csv_data.get('temporary_item_type')
                    if temporary_item_type:
                        csv_data['temporary_item_type'] = item_types_map[
                            temporary_item_type['pid']]
                        csv_data['temporary_item_type_end_date'] = \
                            temporary_item_type.get('end_date')

                    # process note
                    for note in csv_data.get('notes', []):
                        if any(note_type in note.get('type')
                               for note_type in
                               ItemNoteTypes.INVENTORY_LIST_CATEGORY):
                            csv_data[note.get('type')] = note.get(
                                'content')

                    csv_data['created'] = ciso8601.parse_datetime(
                            hit['_created']).date()

                    # process item issue
                    if hit['type'] == 'issue':
                        issue = csv_data['issue']
                        if issue.get('inherited_first_call_number') \
                                and not csv_data.get('call_number'):
                            csv_data['call_number'] = \
                                issue.get('inherited_first_call_number')
                        csv_data['issue_status'] = issue.get('status')
                        if issue.get('status_date'):
                            csv_data['issue_status_date'] = \
                                ciso8601.parse_datetime(
                                    issue.get('status_date')).date()
                        csv_data['issue_claims_count'] = \
                            issue.get('claims_count', 0)
                        csv_data['issue_expected_date'] = \
                            issue.get('expected_date')
                        csv_data['issue_regular'] = issue.get('regular')

                    # prevent key error
                    del (csv_data['type'])

                    # write csv data
                    data = self.process_dict(csv_data)
                    writer.writerow(data)
                    yield line.read()

        # return streamed content
        return stream_with_context(generate_csv())
