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

"""Acquisition invoice serialization."""

from invenio_records_rest.serializers.response import search_responsify

from ..libraries.api import Library
from ..serializers import JSONSerializer, RecordSchemaJSONV1


class AcquisitionInvoiceJSONSerializer(JSONSerializer):
    """Mixin serializing records as JSON."""

    def post_process_serialize_search(self, results, pid_fetcher):
        """Post process the search results."""
        # Add library name
        for lib_term in results.get('aggregations', {}).get(
                'library', {}).get('buckets', []):
            pid = lib_term.get('key')
            name = Library.get_record_by_pid(pid).get('name')
            lib_term['key'] = pid
            lib_term['name'] = name

        return super(
            AcquisitionInvoiceJSONSerializer,
            self).post_process_serialize_search(results, pid_fetcher)


json_acquisition_invoice = AcquisitionInvoiceJSONSerializer(RecordSchemaJSONV1)
"""JSON v1 serializer."""

json_acquisition_invoice_search = search_responsify(
    json_acquisition_invoice, 'application/rero+json')
