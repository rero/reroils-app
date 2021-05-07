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

"""Circulation policies JSON schema tests."""

from __future__ import absolute_import, print_function

from copy import deepcopy

import pytest
from jsonschema import validate
from jsonschema.exceptions import ValidationError

from rero_ils.modules.circ_policies.api import DUE_SOON_REMINDER_TYPE, \
    OVERDUE_REMINDER_TYPE


def test_required(circ_policy_schema, circ_policy_martigny_data_tmp):
    """Test required for circulation policy jsonschema."""
    validate(circ_policy_martigny_data_tmp, circ_policy_schema)

    with pytest.raises(ValidationError):
        validate({}, circ_policy_schema)
        validate(circ_policy_martigny_data_tmp, circ_policy_schema)


def test_pid(circ_policy_schema, circ_policy_martigny_data_tmp):
    """Test pid for circulation policy jsonschema."""
    validate(circ_policy_martigny_data_tmp, circ_policy_schema)

    with pytest.raises(ValidationError):
        circ_policy_martigny_data_tmp['pid'] = 25
        validate(circ_policy_martigny_data_tmp, circ_policy_schema)


def test_circ_policy_name(circ_policy_schema, circ_policy_martigny_data_tmp):
    """Test name for circulation policy jsonschema."""
    validate(circ_policy_martigny_data_tmp, circ_policy_schema)

    with pytest.raises(ValidationError):
        circ_policy_martigny_data_tmp['name'] = 25
        validate(circ_policy_martigny_data_tmp, circ_policy_schema)


def test_circ_policy_desc(circ_policy_schema, circ_policy_martigny_data_tmp):
    """Test description for circulation policy jsonschema."""
    validate(circ_policy_martigny_data_tmp, circ_policy_schema)

    with pytest.raises(ValidationError):
        circ_policy_martigny_data_tmp['description'] = 25
        validate(circ_policy_martigny_data_tmp, circ_policy_schema)


def test_circ_policy_org(circ_policy_schema, circ_policy_martigny_data_tmp):
    """Test organisation pid for circulation policy jsonschema."""
    validate(circ_policy_martigny_data_tmp, circ_policy_schema)

    with pytest.raises(ValidationError):
        circ_policy_martigny_data_tmp['organisation_pid'] = 25
        validate(circ_policy_martigny_data_tmp, circ_policy_schema)


def test_circ_policy_renewal_duration(
    circ_policy_schema, circ_policy_martigny_data_tmp
):
    """Test renewal_duration for circulation policy jsonschema."""
    validate(circ_policy_martigny_data_tmp, circ_policy_schema)

    with pytest.raises(ValidationError):
        circ_policy_martigny_data_tmp['renewal_duration'] = '25'
        validate(circ_policy_martigny_data_tmp, circ_policy_schema)


def test_circ_policy_checkout_duration(
    circ_policy_schema, circ_policy_martigny_data_tmp
):
    """Test checkout_duration for circulation policy jsonschema."""
    validate(circ_policy_martigny_data_tmp, circ_policy_schema)

    with pytest.raises(ValidationError):
        circ_policy_martigny_data_tmp['checkout_duration'] = '25'
        validate(circ_policy_martigny_data_tmp, circ_policy_schema)


def test_circ_policy_allow_requests(
    circ_policy_schema, circ_policy_martigny_data_tmp
):
    """Test allow_requests for circcirculation policy jsonschema."""
    validate(circ_policy_martigny_data_tmp, circ_policy_schema)

    with pytest.raises(ValidationError):
        circ_policy_martigny_data_tmp['allow_requests'] = 25
        validate(circ_policy_martigny_data_tmp, circ_policy_schema)


def test_circ_policy_number_renewals(
    circ_policy_schema, circ_policy_martigny_data_tmp
):
    """Test number_renewals for circulation policy jsonschema."""
    validate(circ_policy_martigny_data_tmp, circ_policy_schema)

    with pytest.raises(ValidationError):
        circ_policy_martigny_data_tmp['number_renewals'] = '25'
        validate(circ_policy_martigny_data_tmp, circ_policy_schema)


def test_circ_policy_is_default(
    circ_policy_schema, circ_policy_martigny_data_tmp
):
    """Test is_default for circulation policy jsonschema."""
    validate(circ_policy_martigny_data_tmp, circ_policy_schema)
    with pytest.raises(ValidationError):
        circ_policy_martigny_data_tmp['is_default'] = 25
        validate(circ_policy_martigny_data_tmp, circ_policy_schema)


def test_circ_policy_reminders(circ_policy_schema,
                               circ_policy_short_martigny):
    """Test reminders section for circulation policy jsonschemas."""
    cipo = deepcopy(circ_policy_short_martigny)
    validate(cipo, circ_policy_schema)

    # Empty reminders array is invalid
    with pytest.raises(ValidationError):
        cipo['reminders'] = []
        validate(cipo, circ_policy_schema)

    due_soon_reminder = {
        'type': DUE_SOON_REMINDER_TYPE,
        'days_delay': 3,
        'communication_channel': 'patron_setting',
        'template': 'email/due_soon/'
    }
    cipo['reminders'].append(due_soon_reminder)
    validate(cipo, circ_policy_schema)
    # Tow "DUE_SOON" reminder is disallow
    with pytest.raises(ValidationError):
        due_soon_reminder_2 = deepcopy(due_soon_reminder)
        due_soon_reminder_2['days_delay'] = 5
        cipo['reminders'].append(due_soon_reminder_2)
        validate(cipo, circ_policy_schema)  # valid for JSON schema
        cipo.validate()  # invalid against extented_validation rules
    del cipo['reminders'][1]

    # Tow "OVERDUE" reminders with same delay are disallow
    overdue_reminder = {
        'type': OVERDUE_REMINDER_TYPE,
        'days_delay': 2,
        'communication_channel': 'mail',
        'template': 'email/overdue'
    }
    with pytest.raises(ValidationError):
        overdue_reminder1 = deepcopy(overdue_reminder)
        overdue_reminder2 = deepcopy(overdue_reminder)
        overdue_reminder2['template'] = 'email/overdue2'
        cipo['reminders'].extend([overdue_reminder1, overdue_reminder2])
        validate(cipo, circ_policy_schema)  # valid for JSON schema
        cipo.validate()  # invalid against extented_validation rules
    del cipo['reminders']


def test_circ_policy_overdue_fees(circ_policy_schema,
                                  circ_policy_short_martigny):
    """Test overdue fees section for circulation policy jsonschemas."""
    cipo = deepcopy(circ_policy_short_martigny)
    validate(cipo, circ_policy_schema)

    overdue_data = {
        'maximum_total_amount': 100,
        'intervals': [
            {'from': 1, 'to': 5, 'fee_amount': 0.1},
            {'from': 11, 'fee_amount': 0.5},
            {'from': 6, 'to': 10, 'fee_amount': 0.1}
        ]
    }
    cipo['overdue_fees'] = overdue_data
    validate(cipo, circ_policy_schema)
    cipo.validate()

    # two intervals with no upper limit
    with pytest.raises(ValidationError):
        invalid_overdue_data = deepcopy(overdue_data)
        del invalid_overdue_data['intervals'][2]['to']
        cipo['overdue_fees'] = invalid_overdue_data
        cipo.validate()

    # two intervals with conflict on lower interval limit
    with pytest.raises(ValidationError):
        invalid_overdue_data = deepcopy(overdue_data)
        invalid_overdue_data['intervals'][2]['from'] = 4
        cipo['overdue_fees'] = invalid_overdue_data
        cipo.validate()

    # two intervals with conflict on upper interval limit
    with pytest.raises(ValidationError):
        invalid_overdue_data = deepcopy(overdue_data)
        invalid_overdue_data['intervals'][0]['to'] = 7
        cipo['overdue_fees'] = invalid_overdue_data
        cipo.validate()
