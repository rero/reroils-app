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

"""Patron transaction event Record tests."""

from __future__ import absolute_import, print_function

from copy import deepcopy

import pytest
from utils import get_mapping

from rero_ils.modules.patron_transaction_events.api import \
    PatronTransactionEvent as PatronTransactionEvent
from rero_ils.modules.patron_transaction_events.api import \
    PatronTransactionEventsSearch
from rero_ils.modules.patron_transactions.api import \
    patron_transaction_id_fetcher as fetcher


def test_patron_transaction_event_es_mapping(
        es, db, patron_transaction_overdue_event_martigny):
    """Test patron_transaction event elasticsearch mapping."""
    search = PatronTransactionEventsSearch()
    mapping = get_mapping(search.Meta.index)
    assert mapping
    PatronTransactionEvent.create(
        patron_transaction_overdue_event_martigny,
        dbcommit=True,
        reindex=True,
        delete_pid=True
    )
    assert mapping == get_mapping(search.Meta.index)


def test_patron_transaction_event_create(
        db, es_clear, patron_transaction_overdue_event_martigny):
    """Test patron transaction event creation."""
    patron_event = deepcopy(patron_transaction_overdue_event_martigny)
    patron_event['type'] = 'no_type'
    import jsonschema
    with pytest.raises(jsonschema.exceptions.ValidationError):
        record = PatronTransactionEvent.create(
            patron_event, delete_pid=True)

    db.session.rollback()

    next_pid = PatronTransactionEvent.provider.identifier.next()
    patron_event['type'] = 'fee'
    record = PatronTransactionEvent.create(patron_event, delete_pid=True)
    next_pid += 1
    assert record == patron_event
    assert record.get('pid') == str(next_pid)

    pttr = PatronTransactionEvent.get_record_by_pid(str(next_pid))
    assert pttr == patron_event

    fetched_pid = fetcher(pttr.id, pttr)
    assert fetched_pid.pid_value == str(next_pid)
    assert fetched_pid.pid_type == 'pttr'


def test_patron_transaction_event_can_delete(
        patron_transaction_overdue_event_martigny):
    """Test can delete."""
    assert patron_transaction_overdue_event_martigny.get_links_to_me() == {}
    assert patron_transaction_overdue_event_martigny.can_delete
