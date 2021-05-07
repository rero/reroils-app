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


"""Holding Record tests."""


from __future__ import absolute_import, print_function

import pytest
from utils import flush_index, get_mapping

from rero_ils.modules.errors import RecordValidationError
from rero_ils.modules.holdings.api import Holding, HoldingsSearch
from rero_ils.modules.holdings.api import holding_id_fetcher as fetcher


def test_holding_es_mapping(es, db, loc_public_martigny,
                            item_type_standard_martigny,
                            document, holding_lib_martigny_data):
    """Test holding elasticsearch mapping."""
    search = HoldingsSearch()
    mapping = get_mapping(search.Meta.index)
    assert mapping
    holding = Holding.create(
        holding_lib_martigny_data,
        dbcommit=True,
        reindex=True,
        delete_pid=True
    )
    assert mapping == get_mapping(search.Meta.index)
    # clean created data
    holding.delete(force=True, dbcommit=True, delindex=True)


def test_holding_create(db, es, document, org_martigny,
                        loc_public_martigny, item_type_standard_martigny,
                        holding_lib_martigny_data):
    """Test holding creation."""
    holding = Holding.create(holding_lib_martigny_data, dbcommit=True,
                             reindex=True, delete_pid=True)
    flush_index(HoldingsSearch.Meta.index)
    assert holding == holding_lib_martigny_data
    assert holding.get('pid') == '1'

    holding = Holding.get_record_by_pid('1')
    assert holding == holding_lib_martigny_data

    fetched_pid = fetcher(holding.id, holding)
    assert fetched_pid.pid_value == '1'
    assert fetched_pid.pid_type == 'hold'

    search = HoldingsSearch()
    es_hit = next(search.filter('term', pid=holding.pid).source('pid').scan())
    holding_record = Holding.get_record_by_pid(es_hit.pid)
    assert holding_record.organisation_pid == org_martigny.get('pid')
    # holdings does not exist
    assert not Holding.get_holdings_type_by_holding_pid('toto')

    # clean created data
    holding.delete(force=True, dbcommit=True, delindex=True)


def test_holding_holding_type(holding_lib_martigny_w_patterns,
                              holding_lib_martiny_electronic):
    """Test holdings type."""
    assert holding_lib_martigny_w_patterns.is_serial
    assert holding_lib_martiny_electronic.is_electronic


def test_holding_availability(holding_lib_martiny_electronic,
                              holding_lib_martigny, item_lib_martigny):
    """Test holding availability."""
    # An electronic holding is always available despite if no item are linked
    assert holding_lib_martiny_electronic.available
    # The availability of other holdings type depends of children availability
    assert holding_lib_martigny.available == item_lib_martigny.available


def test_holding_extended_validation(client,
                                     journal, ebook_5,
                                     item_type_standard_martigny,
                                     item_type_online_martigny,
                                     holding_lib_martigny_w_patterns_data,
                                     holding_lib_martiny_electronic_data):
    """Test holding extended validation."""
    # instantiate serial holding
    holding_tmp = Holding(holding_lib_martigny_w_patterns_data)
    # 1. holding type serial

    # 1.1. test correct holding
    holding_tmp.validate()  # validation with extented_validation rules

    # 1.1. test next expected date for regular frequencies
    expected_date = holding_tmp['patterns']['next_expected_date']
    del(holding_tmp['patterns']['next_expected_date'])
    with pytest.raises(RecordValidationError):
        holding_tmp.validate()

    # reset data with original value
    holding_tmp['patterns']['next_expected_date'] = expected_date

    # 1.2. test multiple note with same type
    holding_tmp.get('notes').append({
        'type': 'general_note',
        'content': 'other general_note...'
    })
    with pytest.raises(RecordValidationError):
        holding_tmp.validate()
    del holding_tmp['notes']

    # 2. holding type electronic
    # 2.1. test holding type electronic attached to wrong document type
    holding_tmp['holdings_type'] = 'electronic'
    with pytest.raises(RecordValidationError):
        holding_tmp.validate()

    # 2.2 test electronic holding
    # instantiate electronic holding
    holding_tmp = Holding(holding_lib_martiny_electronic_data)
    holding_tmp.validate()

    # 2.2 test electronic holding with enumeration and chronology
    holding_tmp['enumerationAndChronology'] = 'enumerationAndChronology'
    holding_tmp.validate()
