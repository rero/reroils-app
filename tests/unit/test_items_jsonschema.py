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

"""item JSON schema tests."""

from __future__ import absolute_import, print_function

import datetime

import pytest
from jsonschema import validate
from jsonschema.exceptions import ValidationError

from rero_ils.modules.items.models import ItemNoteTypes
from rero_ils.modules.utils import get_ref_for_pid


def test_required(item_schema, item_lib_martigny_data_tmp):
    """Test required for item jsonschemas."""
    validate(item_lib_martigny_data_tmp, item_schema)

    with pytest.raises(ValidationError):
        validate({}, item_schema)


def test_item_all_jsonschema_keys_values(
        item_schema, item_lib_martigny_data_tmp):
    """Test all keys and values for item jsonschema."""
    record = item_lib_martigny_data_tmp
    validate(record, item_schema)
    validator = [
        {'key': 'pid', 'value': 25},
        {'key': 'type', 'value': 25},
        {'key': 'barcode', 'value': 25},
        {'key': 'call_number', 'value': 25},
        {'key': 'second_call_number', 'value': 25},
        {'key': 'item_type', 'value': 25},
        {'key': 'location', 'value': 25},
        {'key': 'enumerationAndChronology', 'value': 25},
        {'key': 'document', 'value': 25},
        {'key': 'type', 'value': 25},
        {'key': 'issue', 'value': 25},
        {'key': 'status', 'value': 25},
        {'key': 'holding', 'value': 25},
        {'key': 'organisation', 'value': 25},
        {'key': 'ur', 'value': 25},
        {'key': 'pac_code', 'value': 25},
        {'key': 'price', 'value': '25'},
        {'key': '_masked', 'value': 25},
        {'key': 'legacy_checkout_count', 'value': '25'},
        {'key': 'legacy_circulation_rules', 'value': 25}
    ]
    for element in validator:
        with pytest.raises(ValidationError):
            record[element['key']] = element['value']
            validate(record, item_schema)


def test_item_notes(item_schema, item_lib_martigny_data_tmp):
    """Test notes for item jsonschemas."""
    validate(item_lib_martigny_data_tmp, item_schema)
    item_lib_martigny_data_tmp['notes'] = []

    public_note = dict(type=ItemNoteTypes.GENERAL, content='public note')
    staff_note = dict(type=ItemNoteTypes.STAFF, content='staff note')
    dummy_note = dict(type='dummy', content='dummy note')
    long_note = dict(type=ItemNoteTypes.CHECKIN, content='note' * 501)

    item_lib_martigny_data_tmp['notes'] = [public_note]
    validate(item_lib_martigny_data_tmp, item_schema)

    item_lib_martigny_data_tmp['notes'] = [public_note, staff_note]
    validate(item_lib_martigny_data_tmp, item_schema)

    # add a not-valid note type should raise a validation error
    with pytest.raises(ValidationError):
        item_lib_martigny_data_tmp['notes'] = [dummy_note]
        validate(item_lib_martigny_data_tmp, item_schema)

    # add a too long note content
    with pytest.raises(ValidationError):
        item_lib_martigny_data_tmp['notes'] = [long_note]
        validate(item_lib_martigny_data_tmp, item_schema)


def test_new_acquisition(item_schema, item_lib_martigny_data_tmp):
    """Test new acquisition for item jsonschemas."""
    validate(item_lib_martigny_data_tmp, item_schema)

    with pytest.raises(ValidationError):
        acq_date = datetime.date.today().strftime('%Y/%m/%d')
        item_lib_martigny_data_tmp['acquisition_date'] = acq_date
        validate(item_lib_martigny_data_tmp, item_schema)


def test_temporary_item_type(item_schema, item_lib_martigny):
    """Test temporary item type for item jsonschemas."""
    data = item_lib_martigny

    # tmp_itty cannot be the same than main_itty
    with pytest.raises(ValidationError):
        data['temporary_item_type'] = {
            '$ref': data['item_type']['$ref']
        }
        validate(data, item_schema)
        data.validate()  # check extented_validation

    # tmp_itty_enddate must be older than current date
    with pytest.raises(ValidationError):
        current_date = datetime.datetime.now().strftime('%Y-%m-%d')
        data['temporary_item_type'] = {
            '$ref': get_ref_for_pid('itty', 'sample'),
            'end_date': current_date
        }
        validate(data, item_schema)
        data.validate()  # check extented_validation
