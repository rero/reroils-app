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

"""Signals connector for Holding."""

from .api import HoldingsSearch
from ..local_fields.api import LocalField
from ..locations.api import LocationsSearch


def enrich_holding_data(sender, json=None, record=None, index=None,
                        doc_type=None, arguments=None, **dummy_kwargs):
    """Signal sent before a record is indexed.

    :param json: The dumped record dictionary which can be modified.
    :param record: The record being indexed.
    :param index: The index in which the record will be indexed.
    :param doc_type: The doc_type for the record.
    """
    if index.split('-')[0] == HoldingsSearch.Meta.index:
        # ES search reduces number of requests for organisation and library.
        es_loc = next(
            LocationsSearch()
            .filter('term', pid=json['location']['pid'])
            .scan()
        )
        json['organisation'] = {
            'pid': es_loc.organisation.pid
        }
        json['library'] = {
            'pid': es_loc.library.pid
        }

        # Local fields in JSON
        local_fields = LocalField.get_local_fields_by_resource(
            'hold', record['pid'])
        if local_fields:
            json['local_fields'] = local_fields
