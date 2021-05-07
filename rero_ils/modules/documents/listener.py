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

"""Signals connector for Document."""

from isbnlib import is_isbn10, is_isbn13, to_isbn10, to_isbn13

from .utils import create_contributions, title_format_text_head
from ..documents.api import Document, DocumentsSearch
from ..holdings.api import Holding, HoldingsSearch
from ..items.api import Item, ItemsSearch
from ..items.models import ItemNoteTypes
from ..local_fields.api import LocalField
from ..utils import extracted_data_from_ref


def enrich_document_data(sender, json=None, record=None, index=None,
                         doc_type=None, arguments=None, **dummy_kwargs):
    """Signal sent before a record is indexed.

    :param json: The dumped record dictionary which can be modified.
    :param record: The record being indexed.
    :param index: The index in which the record will be indexed.
    :param doc_type: The doc_type for the record.
    """
    if index.split('-')[0] == DocumentsSearch.Meta.index:
        # HOLDINGS
        holdings = []
        document_pid = record['pid']
        es_holdings = HoldingsSearch()\
            .filter('term', document__pid=document_pid)\
            .scan()
        for holding in es_holdings:
            holding = holding.to_dict()
            holding_obj = Holding.get_record_by_pid(holding['pid'])
            hold_data = {
                'pid': holding['pid'],
                'location': {
                    'pid': holding['location']['pid'],
                },
                'circulation_category': {
                    'pid': holding['circulation_category']['pid'],
                },
                'organisation': {
                    'organisation_pid': holding['organisation']['pid'],
                    'library_pid': holding['library']['pid']
                }
            }
            # Index additional holdings fields into the document record
            holdings_fields = [
                'call_number', 'second_call_number', 'index',
                'enumerationAndChronology', 'supplementaryContent',
                'local_fields'
            ]
            for field in holdings_fields:
                if field in holding:
                    hold_data[field] = holding.get(field)
            # Index holdings notes
            notes = [n['content'] for n in holding.get('notes', []) if n]
            if notes:
                hold_data['notes'] = notes

            # Index items attached to each holdings record
            es_items = ItemsSearch()\
                .filter('term', holding__pid=holding['pid'])\
                .scan()
            items = []
            for item in es_items:
                item = item.to_dict()

                item_obj = Item.get_record_by_pid(item['pid'])
                items.append(item_obj)

                item_data = {
                    'pid': item['pid'],
                    'barcode': item['barcode'],
                    'status': item['status'],
                    'available': item['available'],
                    'local_fields': item.get('local_fields'),
                    'call_number': item.get('call_number')
                }
                item_data = {k: v for k, v in item_data.items() if v}

                # item acquisition part.
                #   We need to store the acquisition data of the items into the
                #   document. As we need to link acquisition date and
                #   org/lib/loc, we need to store theses data together in a
                #   'nested' structure.
                acq_date = item.get('acquisition_date')
                if acq_date:
                    item_data['acquisition'] = {
                        'organisation_pid': holding['organisation']['pid'],
                        'library_pid': holding['library']['pid'],
                        'location_pid': holding['location']['pid'],
                        'date': acq_date
                    }
                # item notes content.
                #   index the content of the public notes into the document.
                public_notes_content = [
                    n['content']
                    for n in item.get('notes', [])
                    if n['type'] in ItemNoteTypes.PUBLIC
                ]
                if public_notes_content:
                    item_data['notes'] = public_notes_content

                # related collection
                #   index the collection title and description
                for collection in item_obj.in_collection():
                    coll_data = {
                        'title': collection.get('title'),
                        'description': collection.get('description')
                    }
                    coll_data = {k: v for k, v in coll_data.items() if v}
                    item_data.setdefault('collections', []).append(coll_data)
                hold_data.setdefault('items', []).append(item_data)
            hold_data['available'] = holding_obj.available
            holdings.append(hold_data)

        if holdings:
            json['holdings'] = holdings

        # MEF contribution ES index update
        contributions = create_contributions(json.get('contribution', []))
        if contributions:
            json.pop('contribution', None)
            json['contribution'] = contributions
        # TODO: compare record with those in DB to check which authors have
        # to be deleted from index
        # Index host document title in child document (part of)
        if 'partOf' in record:
            title = {'type': 'partOf'}
            for part_of in record['partOf']:
                doc_pid = extracted_data_from_ref(
                    part_of.get('document')
                )
                document = Document.get_record_by_pid(doc_pid)
                for part_of_title in document.get('title', []):
                    if 'mainTitle' in part_of_title:
                        title['partOfTitle'] = part_of_title.get(
                            'mainTitle'
                        )
            json['title'].append(title)

        json['sort_title'] = title_format_text_head(
            json.get('title', []),
            with_subtitle=True
        )
        # Local fields in JSON
        local_fields = LocalField.get_local_fields_by_resource(
            'doc', document_pid)
        if local_fields:
            json['local_fields'] = local_fields
        # index both ISBN 10 and 13 format

        def filter_isbn(identified_by):
            """Filter identified_by for type bf:Isbn."""
            return identified_by.get('type') == 'bf:Isbn'

        filtered_identified_by = filter(
            filter_isbn,
            json.get('identifiedBy', [])
        )
        isbns = set()
        for identified_by in filtered_identified_by:
            isbn = identified_by['value']
            isbns.add(isbn)
            if is_isbn10(isbn):
                isbns.add(to_isbn13(isbn))
            elif is_isbn13(isbn):
                isbns.add(to_isbn10(isbn))
        if isbns:
            json['isbn'] = list(isbns)
