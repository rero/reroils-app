# -*- coding: utf-8 -*-
#
# RERO ILS
# Copyright (C) 2021 RERO
# Copyright (C) 2021 UCLouvain
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

"""Inventory list REST API."""

from __future__ import absolute_import, print_function

from functools import partial

from invenio_rest import ContentNegotiatedMethodView

from rero_ils.modules.items.api import ItemsSearch
from rero_ils.modules.items.serializers import csv_item_search
from rero_ils.query import items_search_factory


class InventoryListResource(ContentNegotiatedMethodView):
    """Inventory List REST resource."""

    # TODO: is candidate for invenio-record-resource ?

    def __init__(self, **kwargs):
        """Init."""
        super().__init__(
            method_serializers={
                'GET': {
                    'text/csv': csv_item_search,
                }
            },
            serializers_query_aliases={
                'csv': 'text/csv',
            },
            default_method_media_type={
                'GET': 'text/csv'
            },
            default_media_type='text/csv',
            **kwargs
        )
        self.search_factory = partial(items_search_factory, self)

    def get(self, **kwargs):
        """Search records."""
        search_obj = ItemsSearch()
        search, qs_kwargs = self.search_factory(search_obj)

        return self.make_response(
            pid_fetcher=None,
            search_result=search.scan()
        )
