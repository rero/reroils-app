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

"""Items serializers."""
from invenio_records_rest.serializers.response import record_responsify, \
    search_responsify

from rero_ils.modules.items.serializers.response import search_responsify_csv
from rero_ils.modules.serializers import JSONSerializer, RecordSchemaJSONV1

from .csv import ItemCSVSerializer
from .json import ItemsJSONSerializer

csv_item = ItemCSVSerializer(
    JSONSerializer,
    csv_included_fields=[
        'pid',
        'document_pid',
        'document_title',
        'document_creator',
        'document_main_type',
        'document_sub_type',
        'library_name',
        'location_name',
        'barcode',
        'call_number',
        'second_call_number',
        'enumerationAndChronology',
        'item_type',
        'temporary_item_type',
        'temporary_item_type_end_date',
        'general_note',
        'staff_note',
        'checkin_note',
        'checkout_note',
        'loans_count',
        'last_transaction_date',
        'status',
        'created',
        'issue_status',
        'issue_status_date',
        'issue_claims_count',
        'issue_expected_date',
        'issue_regular'
    ]
)
csv_item_response = record_responsify(csv_item, "text/csv")
csv_item_search = search_responsify_csv(csv_item, "text/csv")
"""CSV serializer."""

json_item = ItemsJSONSerializer(RecordSchemaJSONV1)
"""JSON serializer."""

json_item_search = search_responsify(json_item, 'application/rero+json')
json_item_response = record_responsify(json_item, 'application/rero+json')
