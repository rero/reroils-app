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

"""Signals connector for Item."""

from .api import Item, ItemsSearch
from ..documents.api import Document
from ..local_fields.api import LocalField
from ..utils import extracted_data_from_ref


def enrich_item_data(sender, json=None, record=None, index=None,
                     doc_type=None, arguments=None, **dummy_kwargs):
    """Signal sent before a record is indexed.

    :param json: The dumped record dictionary which can be modified.
    :param record: The record being indexed.
    :param index: The index in which the record will be indexed.
    :param doc_type: The doc_type for the record.
    """
    if index.split('-')[0] == ItemsSearch.Meta.index:
        item = record
        if not isinstance(record, Item):
            item = Item.get_record_by_pid(record.get('pid'))
        library = item.get_library()
        json['organisation'] = {
            'pid': extracted_data_from_ref(library.get('organisation'))
        }
        json['library'] = {
            'pid': library.pid
        }
        json['available'] = item.available
        # add vendor name
        if item.vendor_pid:
            json['vendor'] = {
                'pid': item.vendor_pid
            }
        # inherited_first_call_number to issue
        inherited_first_call_number = item.issue_inherited_first_call_number
        if inherited_first_call_number:
            json['issue']['inherited_first_call_number'] = \
                inherited_first_call_number
        # Local fields in JSON
        local_fields = LocalField.get_local_fields_by_resource(
            'item', item.pid)
        if local_fields:
            json['local_fields'] = local_fields

        # Document type
        document = Document.get_record_by_pid(json['document']['pid'])
        json['document']['document_type'] = document['type']
