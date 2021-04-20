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

"""Blueprints for item."""

from __future__ import absolute_import

from .api_views import api_blueprint
from .rest import InventoryListResource

inventory_list = InventoryListResource.as_view(
    'inventory_search'
)
api_blueprint.add_url_rule(
    '/inventory',
    view_func=inventory_list
)

blueprints = [
    api_blueprint,
]

__all__ = 'api_blueprint'
