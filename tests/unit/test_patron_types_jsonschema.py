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

"""patron JSON schema tests."""

from __future__ import absolute_import, print_function

import pytest
from jsonschema import validate
from jsonschema.exceptions import ValidationError

from rero_ils.modules.utils import get_ref_for_pid


def test_required(patron_type_schema, patron_type_data_tmp):
    """Test required for patron jsonschemas."""
    validate(patron_type_data_tmp, patron_type_schema)

    with pytest.raises(ValidationError):
        validate({}, patron_type_schema)
        validate(patron_type_data_tmp, patron_type_schema)


def test_pid(patron_type_schema, patron_type_data_tmp):
    """Test pid for patron type jsonschemas."""
    validate(patron_type_data_tmp, patron_type_schema)

    with pytest.raises(ValidationError):
        patron_type_data_tmp['pid'] = 25
        validate(patron_type_data_tmp, patron_type_schema)


def test_name(patron_type_schema, patron_type_data_tmp):
    """Test name for patron type jsonschemas."""
    validate(patron_type_data_tmp, patron_type_schema)

    with pytest.raises(ValidationError):
        patron_type_data_tmp['name'] = 25
        validate(patron_type_data_tmp, patron_type_schema)


def test_description(patron_type_schema, patron_type_data_tmp):
    """Test description for patron type jsonschemas."""
    validate(patron_type_data_tmp, patron_type_schema)

    with pytest.raises(ValidationError):
        patron_type_data_tmp['description'] = 25
        validate(patron_type_data_tmp, patron_type_schema)


def test_organisation_pid(
        patron_type_schema, patron_type_data_tmp):
    """Test organisation_pid for patron type jsonschemas."""
    validate(patron_type_data_tmp, patron_type_schema)

    with pytest.raises(ValidationError):
        patron_type_data_tmp['organisation_pid'] = 25
        validate(patron_type_data_tmp, patron_type_schema)


def test_subscription_amount(
        patron_type_schema, patron_type_data_tmp):
    """Test subscription amount for patron type jsonschemas."""
    patron_type_data_tmp['subscription_amount'] = 25
    validate(patron_type_data_tmp, patron_type_schema)

    with pytest.raises(ValidationError):
        patron_type_data_tmp['organisation_pid'] = -25
        validate(patron_type_data_tmp, patron_type_schema)

    with pytest.raises(ValidationError):
        patron_type_data_tmp['organisation_pid'] = '35'
        validate(patron_type_data_tmp, patron_type_schema)


def test_limits(patron_type_schema, patron_type_tmp):
    """Test limits fr patron type JSON schema."""
    data = patron_type_tmp

    # checkout limits :: library limit > general limit
    data['limits'] = {
        'checkout_limits': {
            'global_limit': 20,
            'library_limit': 15
        }
    }
    validate(data, patron_type_schema)
    with pytest.raises(ValidationError):
        data['limits']['checkout_limits']['library_limit'] = 40
        validate(data, patron_type_schema)  # valid for JSON schema
        data.validate()  # invalid against extented_validation rules

    data['limits']['checkout_limits']['library_limit'] = 15
    with pytest.raises(ValidationError):
        lib_ref = get_ref_for_pid('lib', 'dummy')
        data['limits']['checkout_limits']['library_exceptions'] = [
            {'library': {'$ref': lib_ref}, 'value': 15}
        ]
        validate(data, patron_type_schema)  # valid for JSON schema
        data.validate()  # invalid against extented_validation rules

    with pytest.raises(ValidationError):
        data['limits']['checkout_limits']['library_exceptions'] = [
            {'library': {'$ref': lib_ref}, 'value': 5},
            {'library': {'$ref': lib_ref}, 'value': 7}
        ]
        validate(data, patron_type_schema)  # valid for JSON schema
        data.validate()  # invalid against extented_validation rules
