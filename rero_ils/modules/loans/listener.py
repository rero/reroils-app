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

"""Signals connector for Loan."""

from invenio_circulation.proxies import current_circulation

from ..items.api import Item
from ..items.models import ItemStatus
from ..loans.api import Loan, LoanState
from ..locations.api import Location
from ..notifications.utils import send_notification_to_location
from ..patron_transactions.api import PatronTransaction


def enrich_loan_data(sender, json=None, record=None, index=None,
                     doc_type=None, arguments=None, **dummy_kwargs):
    """Signal sent before a record is indexed.

    :param json: The dumped record dictionary which can be modified.
    :param record: The record being indexed.
    :param index: The index in which the record will be indexed.
    :param doc_type: The doc_type for the record.
    """
    if index.split('-')[0] == current_circulation.loan_search_cls.Meta.index:
        item = Item.get_record_by_pid(record.get('item_pid', {}).get('value'))
        json['library_pid'] = item.holding_library_pid


def listener_loan_state_changed(_, initial_loan, loan, trigger):
    """Create notification based on loan state changes."""
    if loan['state'] == LoanState.PENDING:
        item_pid = loan.get('item_pid', {}).get('value')
        checkedout_loan_pid = Item.get_loan_pid_with_item_on_loan(item_pid)
        if checkedout_loan_pid:
            checked_out_loan = Loan.get_record_by_pid(checkedout_loan_pid)
            checked_out_loan.create_notification(notification_type='recall')
        # send notification to location if needed
        #   Notification should be sent only if the item is on shelf without
        #   previous pending loan and item location assign 'send_notification'
        #   to true
        item = Item.get_record_by_pid(item_pid)
        item_location = Location.get_record_by_pid(item.location_pid)
        if item_location \
           and item_location.get('send_notification', False) \
           and item.status == ItemStatus.ON_SHELF \
           and item.number_of_requests() == 0:
            send_notification_to_location(loan, item, item_location)
    elif loan['state'] == LoanState.ITEM_AT_DESK:
        notification = loan.create_notification(
            notification_type='availability')

    # Create fees for checkin or extend operations
    if trigger in ['checkin', 'extend']:
        PatronTransaction.create_patron_transaction_from_overdue_loan(
            initial_loan
        )
