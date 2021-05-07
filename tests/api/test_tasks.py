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

"""Tasks tests."""

from datetime import datetime, timedelta, timezone

from freezegun import freeze_time
from invenio_accounts.testutils import login_user_via_session
from invenio_circulation.search.api import LoansSearch
from invenio_records.signals import after_record_update
from utils import flush_index, postdata

from rero_ils.modules.items.api import Item
from rero_ils.modules.items.tasks import clean_obsolete_temporary_item_types
from rero_ils.modules.loans.api import Loan, LoanAction, get_due_soon_loans, \
    get_overdue_loans
from rero_ils.modules.notifications.api import Notification, \
    NotificationsSearch, number_of_reminders_sent
from rero_ils.modules.notifications.tasks import create_notifications
from rero_ils.modules.patrons.api import Patron
from rero_ils.modules.patrons.listener import \
    create_subscription_patron_transaction
from rero_ils.modules.patrons.tasks import \
    check_patron_types_and_add_subscriptions as \
    check_patron_types_and_add_subscriptions
from rero_ils.modules.patrons.tasks import clean_obsolete_subscriptions, \
    task_clear_and_renew_subscriptions
from rero_ils.modules.utils import add_years, get_ref_for_pid


def test_notifications_task(
        client, librarian_martigny, patron_martigny,
        item_lib_martigny, circ_policy_short_martigny,
        loc_public_martigny, lib_martigny):
    """Test overdue and due_soon loans."""
    login_user_via_session(client, librarian_martigny.user)
    item = item_lib_martigny
    item_pid = item.pid
    patron_pid = patron_martigny.pid
    # First we need to create a checkout
    res, data = postdata(
        client,
        'api_item.checkout',
        dict(
            item_pid=item_pid,
            patron_pid=patron_pid,
            transaction_location_pid=loc_public_martigny.pid,
            transaction_user_pid=librarian_martigny.pid,
        )
    )
    assert res.status_code == 200
    loan_pid = data.get('action_applied')[LoanAction.CHECKOUT].get('pid')
    loan = Loan.get_record_by_pid(loan_pid)

    # test due_soon notification
    end_date = datetime.now(timezone.utc) + timedelta(days=3)
    loan['end_date'] = end_date.isoformat()
    loan.update(loan, dbcommit=True, reindex=True)
    due_soon_loans = get_due_soon_loans()
    assert due_soon_loans[0].get('pid') == loan_pid

    create_notifications(types=[
        Notification.DUE_SOON_NOTIFICATION_TYPE,
        Notification.OVERDUE_NOTIFICATION_TYPE
    ])
    flush_index(NotificationsSearch.Meta.index)
    flush_index(LoansSearch.Meta.index)
    assert loan.is_notified(Notification.DUE_SOON_NOTIFICATION_TYPE)

    # test overdue notification
    #   For this test, we will update the loan to simulate an overdue of 12
    #   days. With this delay, regarding the cipo configuration, only the first
    #   overdue reminder should be sent.
    #   NOTE : the cipo define the first overdue reminder after 5 days. But we
    #          use an overdue of 12 days because the overdue is based on
    #          loan->item->library open days. Using 12 (5 days + 1 week) we
    #          ensure than the overdue notification will be sent.
    end_date = datetime.now(timezone.utc) - timedelta(days=12)
    loan['end_date'] = end_date.isoformat()
    loan.update(loan, dbcommit=True, reindex=True)
    overdue_loans = list(get_overdue_loans())
    assert overdue_loans[0].get('pid') == loan_pid

    create_notifications(types=[
        Notification.DUE_SOON_NOTIFICATION_TYPE,
        Notification.OVERDUE_NOTIFICATION_TYPE
    ])
    flush_index(NotificationsSearch.Meta.index)
    flush_index(LoansSearch.Meta.index)
    assert loan.is_notified(Notification.OVERDUE_NOTIFICATION_TYPE, 0)
    assert number_of_reminders_sent(
        loan, notification_type=Notification.OVERDUE_NOTIFICATION_TYPE) == 1

    # test overdue notification#2
    #   Now simulate than the previous call crashed. So call the task with a
    #   fixed date. In our test, no new notifications should be sent
    create_notifications(types=[
        Notification.DUE_SOON_NOTIFICATION_TYPE,
        Notification.OVERDUE_NOTIFICATION_TYPE
    ], tstamp=datetime.now(timezone.utc))
    assert number_of_reminders_sent(
        loan, notification_type=Notification.OVERDUE_NOTIFICATION_TYPE) == 1

    # test overdue notification#3
    #   For this test, we will update the loan to simulate an overdue of 40
    #   days. With this delay, regarding the cipo configuration, the second
    #   (and last) overdue reminder should be sent.
    end_date = datetime.now(timezone.utc) - timedelta(days=40)
    loan['end_date'] = end_date.isoformat()
    loan.update(loan, dbcommit=True, reindex=True)
    overdue_loans = list(get_overdue_loans())
    assert overdue_loans[0].get('pid') == loan_pid

    create_notifications(types=[
        Notification.DUE_SOON_NOTIFICATION_TYPE,
        Notification.OVERDUE_NOTIFICATION_TYPE
    ])
    flush_index(NotificationsSearch.Meta.index)
    flush_index(LoansSearch.Meta.index)
    assert loan.is_notified(Notification.OVERDUE_NOTIFICATION_TYPE, 1)
    assert number_of_reminders_sent(
        loan, notification_type=Notification.OVERDUE_NOTIFICATION_TYPE) == 2

    # checkin the item to put it back to it's original state
    res, _ = postdata(
        client,
        'api_item.checkin',
        dict(
            item_pid=item_pid,
            pid=loan_pid,
            transaction_location_pid=loc_public_martigny.pid,
            transaction_user_pid=librarian_martigny.pid
        )
    )
    assert res.status_code == 200


def test_clear_and_renew_subscription(patron_type_grown_sion,
                                      patron_sion):
    """Test the `task patrons.tasks.clear_and_renew_subscription`."""
    patron_sion = patron_sion

    # To test correctly all the code we need to disconnect the listener
    # `create_subscription_patron_transaction` method. Otherwise, the
    # first part of the task (clean_obsolete_subscriptions) will automatically
    # create new subscriptions because the last instruction is a
    # `patron.update()` call.
    after_record_update.disconnect(create_subscription_patron_transaction)

    # first step : clear all subscription for the patron and crate an new
    # obsolete subscription.
    if 'subscriptions' in patron_sion.get('patron', {}):
        del patron_sion['patron']['subscriptions']
    start = datetime.now() - timedelta(days=200)
    end = start + timedelta(days=100)
    patron_sion.add_subscription(patron_type_grown_sion, start, end)
    assert len(patron_sion.get('patron', {}).get('subscriptions', [])) == 1
    assert patron_sion.get('patron', {})['subscriptions'][0]['end_date'] == \
        end.strftime('%Y-%m-%d')

    # clean old subscription - Reload the patron and check they are no more
    # subscriptions
    clean_obsolete_subscriptions()
    patron_sion = Patron.get_record_by_pid(patron_sion.pid)
    assert len(patron_sion.get('patron', {}).get('subscriptions', [])) == 0

    # check for patron needed subscriptions and create new subscription if
    # needed. As our patron has no subscription and is still connected to
    # a patron type requiring subscription, this task should create a
    # new subscription for this patron
    check_patron_types_and_add_subscriptions()
    patron_sion = Patron.get_record_by_pid(patron_sion.pid)
    assert len(patron_sion.get('patron', {}).get('subscriptions', [])) == 1
    assert patron_sion.get('patron', {})['subscriptions'][0]['end_date'] == \
        add_years(datetime.now(), 1).strftime('%Y-%m-%d')

    # run both operation using task_clear_and_renew_subscriptions` and check
    # the result. The patron should still have one subscription but end_date
    # must be today.
    del patron_sion['patron']['subscriptions']
    start = datetime.now() - timedelta(days=200)
    end = start + timedelta(days=100)
    patron_sion.add_subscription(patron_type_grown_sion, start, end)
    task_clear_and_renew_subscriptions()
    patron_sion = Patron.get_record_by_pid(patron_sion.pid)
    assert len(patron_sion.get('patron', {}).get('subscriptions', [])) == 1
    assert patron_sion.get('patron', {})['subscriptions'][0]['end_date'] != \
        end.strftime('%Y-%m-%d')

    # as we disconnect the `create_subscription_patron_transaction` listener
    # at the beginning, we need to connect it now.
    after_record_update.connect(create_subscription_patron_transaction)


def test_clear_obsolete_temporary_item_type(item_lib_martigny,
                                            item_type_on_site_martigny):
    """test task clear_obsolete_temporary_item_type"""
    item = item_lib_martigny
    end_date = datetime.now() + timedelta(days=2)
    item['temporary_item_type'] = {
        '$ref': get_ref_for_pid('itty', item_type_on_site_martigny.pid),
        'end_date': end_date.strftime('%Y-%m-%d')
    }
    item.update(item, dbcommit=True, reindex=True)
    assert item.item_type_circulation_category_pid == \
        item_type_on_site_martigny.pid

    over_4_days = datetime.now() + timedelta(days=4)
    with freeze_time(over_4_days.strftime('%Y-%m-%d')):
        items = Item.get_items_with_obsolete_temporary_item_type()
        assert len(list(items)) == 1
        # run the tasks
        clean_obsolete_temporary_item_types()
        # check after task was ran
        items = Item.get_items_with_obsolete_temporary_item_type()
        assert len(list(items)) == 0
        assert item.item_type_circulation_category_pid == item.item_type_pid
