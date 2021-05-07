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

"""Item utils."""


def item_pid_to_object(item_pid):
    """Build an item_pid object from a given item pid.

    :param item_pid: the item pid value
    :return: the item_pid object
    :rtype: object
    """
    return {'value': item_pid, 'type': 'item'}


def item_location_retriever(item_pid):
    """Returns the item shelflocation pid for the given item_pid.

    :param item_pid: the item_pid object
    :type item_pid: object
    :return: the location pid of the item
    :rtype: str
    """
    from .api import Item

    # TODO: for requests we probably need the transation_location_pid
    #       to deal with multiple pickup locations for a library
    item = Item.get_record_by_pid(item_pid.get('value'))
    if item:
        # TODO: this will be useful for the very specific rero use cases

        # last_location = item.get_last_location()
        # if last_location:
        #     return last_location.pid
        return item.get_owning_pickup_location_pid()


def exists_available_item(items=[]):
    """Check if at least one item of the list are available.

    Caution: `items` param couldn't be a generator otherwise the
    :param items: the items to check. Either as a list of item pids, either as
                  a list of item resources.
    :return True if one item is available; false otherwise.
    """
    from rero_ils.modules.items.api import Item
    for item in items:
        if isinstance(item, str):  # `item` seems to be an item pid
            item = Item.get_record_by_pid(item)
        if not isinstance(item, Item):
            raise ValueError('All items should be Item resource.')
        if item.available:
            return True
    return False
