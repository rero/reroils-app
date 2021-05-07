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

"""Notification Record tests."""

from __future__ import absolute_import, print_function

from copy import deepcopy

from utils import get_mapping

from rero_ils.modules.libraries.api import email_notification_type
from rero_ils.modules.notifications.api import Notification, \
    NotificationsSearch
from rero_ils.modules.notifications.dispatcher import Dispatcher


def test_notification_es_mapping(
        dummy_notification, loan_validated_martigny):
    """Test notification elasticsearch mapping."""

    search = NotificationsSearch()
    mapping = get_mapping(search.Meta.index)
    assert mapping

    notif = deepcopy(dummy_notification)
    validated_pid = loan_validated_martigny.get('pid')
    loan_ref = f'https://ils.rero.ch/api/loans/{validated_pid}'
    notif['loan'] = {"$ref": loan_ref}

    Notification.create(notif, dbcommit=True, delete_pid=True, reindex=True)

    assert mapping == get_mapping(search.Meta.index)


def test_notification_organisation_pid(
        app, org_martigny, notification_availability_martigny):
    """Test organisation pid has been added during the indexing."""
    assert notification_availability_martigny.organisation_pid == \
        org_martigny.pid

    # test notification can_delete
    assert notification_availability_martigny.get_links_to_me() == {}
    assert notification_availability_martigny.can_delete


def test_notification_mail(notification_late_martigny, lib_martigny, mailbox):
    """Test notification creation.
        Patron communication channel is mail.
    """
    mailbox.clear()
    Dispatcher.dispatch_notifications(notification_late_martigny['pid'])
    assert mailbox[0].recipients == [email_notification_type(
            lib_martigny, notification_late_martigny['notification_type'])]


def test_notification_email(notification_late_sion, patron_sion, mailbox):
    """Test overdue notification.
        Patron communication channel is email.
    """
    mailbox.clear()
    Dispatcher.dispatch_notifications(notification_late_sion['pid'])
    assert mailbox[0].recipients == [patron_sion.dumps()['email']]


def test_notification_email_availability(notification_availability_sion,
                                         lib_sion, patron_sion, mailbox):
    """Test availibility notification.
        Patron communication channel is email.
    """
    mailbox.clear()
    Dispatcher.dispatch_notifications(notification_availability_sion['pid'])
    assert mailbox[0].recipients == [patron_sion.dumps()['email']]


def test_notification_email_aggregated(notification_availability_martigny,
                                       notification2_availability_martigny,
                                       lib_martigny, patron_martigny, mailbox):
    """Test availibility notification.
        Patron communication channel is email.
    """
    mailbox.clear()
    Dispatcher.dispatch_notifications([
        notification_availability_martigny['pid'],
        notification2_availability_martigny['pid']
    ], verbose=True)
    assert len(mailbox) == 1
    from pprint import pprint
    pprint(mailbox[0])

    recipient = '???'
    for notification_setting in lib_martigny.get('notification_settings'):
        if notification_setting['type'] == \
                Notification.AVAILABILITY_NOTIFICATION_TYPE:
            recipient = notification_setting['email']
    assert mailbox[0].recipients == [recipient]
