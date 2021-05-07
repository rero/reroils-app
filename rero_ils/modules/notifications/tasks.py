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

"""Celery tasks for notification records."""

from __future__ import absolute_import, print_function

from datetime import datetime, timezone

from celery import shared_task
from flask import current_app

from .api import Notification, get_notifications
from .dispatcher import Dispatcher
from ..circ_policies.api import OVERDUE_REMINDER_TYPE
from ..libraries.api import Library
from ..loans.api import get_due_soon_loans, get_overdue_loans
from ..utils import set_timestamp


@shared_task()
def process_notifications(notification_type, verbose=True):
    """Dispatch notifications.

    :param notification_type: notification type to dispatch the notifications.
    :param verbose: is the task should be verbose.
    """
    notification_pids = get_notifications(notification_type=notification_type)
    result = Dispatcher.dispatch_notifications(
        notification_pids=notification_pids,
        verbose=verbose
    )
    set_timestamp(f'notification-dispatch-{notification_type}', **result)
    return result


@shared_task()
def create_notifications(types=None, tstamp=None, verbose=True):
    """Creates requested notifications.

    :param types: an array of notification types to create.
    :param tstamp: a timestamp to specify when the function is execute. By
                   default it will be `datetime.now()`.
    :param verbose: is the task should be verbose.
    """
    from ..loans.utils import get_circ_policy
    types = types or []
    tstamp = tstamp or datetime.now(timezone.utc)
    logger = current_app.logger
    notification_counter = {}

    # DUE SOON NOTIFICATIONS
    if Notification.DUE_SOON_NOTIFICATION_TYPE in types:
        due_soon_type = Notification.DUE_SOON_NOTIFICATION_TYPE
        notification_counter[due_soon_type] = 0
        logger.debug("DUE_SOON_NOTIFICATION_TYPE --------------")
        for loan in get_due_soon_loans(tstamp=tstamp):
            logger.debug(f'* Loan#{loan.pid} is considerate as \'due_soon\'')
            notification = loan.create_notification(
                notification_type=due_soon_type)
            notification_counter[due_soon_type] += 1

    # OVERDUE NOTIFICATIONS
    if Notification.OVERDUE_NOTIFICATION_TYPE in types:
        logger.debug("OVERDUE_NOTIFICATION_CREATION --------------")
        overdue_type = Notification.OVERDUE_NOTIFICATION_TYPE
        notification_counter[overdue_type] = 0
        for loan in get_overdue_loans(tstamp=tstamp):
            logger.debug(f'* Loan#{loan.pid} is considerate as \'overdue\'')
            # For each overdue loan, we need to get the 'overdue' reminders
            # to should be sent from the due_date and the current used date.
            loan_library = Library.get_record_by_pid(loan.library_pid)
            open_days = loan_library.count_open(
                start_date=loan.overdue_date,
                end_date=tstamp
            )
            circ_policy = get_circ_policy(loan)
            logger.debug(f'  - this loan use the cipo#{circ_policy.pid}')
            logger.debug(f'  - open days from loans due_date :: {open_days}')
            reminders = circ_policy.get_reminders(
                reminder_type=OVERDUE_REMINDER_TYPE,
                limit=open_days
            )
            # For each reminder, try to create it.
            #   the `create_notification` method will check if the notification
            #   is already sent. If the notification has already sent, it will
            #   not be created again
            for idx, reminder in enumerate(reminders):
                notification = loan.create_notification(
                    notification_type=overdue_type,
                    counter=idx
                )
                if notification:
                    logger.debug(f'  --> Overdue notification#{idx+1} created')
                    notification_counter[overdue_type] += 1

                else:
                    logger.debug(f'  --> Overdue notification#{idx+1} skipped '
                                 f':: already sent')
    notification_sum = sum(notification_counter.values())
    counters = {k: v for k, v in notification_counter.items() if v > 0}

    if verbose:
        logger = current_app.logger
        logger.info("NOTIFICATIONS CREATION TASK")
        logger.info(f'  * total of {notification_sum} notification(s) created')
        for notif_type, cpt in counters.items():
            logger.info(f'  +--> {cpt} `{notif_type}` notification(s) created')

    set_timestamp('notification-creation', **counters)
    return counters
