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

"""Patron transaction Record tests."""

from __future__ import absolute_import, print_function

from copy import deepcopy

import pytest
from utils import get_mapping

from rero_ils.modules.patron_transactions.api import PatronTransaction, \
    PatronTransactionsSearch
from rero_ils.modules.patron_transactions.api import \
    patron_transaction_id_fetcher as fetcher


def test_patron_transaction_create(
        db, es_clear, patron_transaction_overdue_martigny):
    """Test patron transaction creation."""
    patron_transaction = deepcopy(patron_transaction_overdue_martigny)
    patron_transaction['status'] = 'no_status'
    import jsonschema
    with pytest.raises(jsonschema.exceptions.ValidationError):
        record = PatronTransaction.create(patron_transaction, delete_pid=True)

    db.session.rollback()

    next_pid = PatronTransaction.provider.identifier.next()
    patron_transaction['status'] = 'open'
    record = PatronTransaction.create(patron_transaction, delete_pid=True)
    next_pid += 1
    assert record == patron_transaction
    assert record.get('pid') == str(next_pid)

    pttr = PatronTransaction.get_record_by_pid(str(next_pid))
    assert pttr == patron_transaction

    fetched_pid = fetcher(pttr.id, pttr)
    assert fetched_pid.pid_value == str(next_pid)
    assert fetched_pid.pid_type == 'pttr'


def test_patron_transaction_es_mapping(
        es, db, patron_transaction_overdue_martigny):
    """Test patron_transaction elasticsearch mapping."""
    search = PatronTransactionsSearch()
    mapping = get_mapping(search.Meta.index)
    assert mapping
    PatronTransaction.create(
        patron_transaction_overdue_martigny,
        dbcommit=True,
        reindex=True,
        delete_pid=True
    )
    assert mapping == get_mapping(search.Meta.index)


def test_patron_transaction_can_delete(patron_transaction_overdue_martigny):
    """Test can delete."""
    assert patron_transaction_overdue_martigny.get_links_to_me() == \
        {'events': 1}
    assert not patron_transaction_overdue_martigny.can_delete


def test_patron_transaction_currency(
        patron_transaction_overdue_martigny, org_martigny):
    """Test patron transaction currency."""
    assert patron_transaction_overdue_martigny.currency == \
        org_martigny.get('default_currency')
