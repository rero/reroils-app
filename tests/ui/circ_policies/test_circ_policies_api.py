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

"""Circulation policies tests."""

from __future__ import absolute_import, print_function

from copy import deepcopy

import mock
import pytest
from jsonschema.exceptions import ValidationError

from rero_ils.modules.circ_policies.api import CircPolicy, \
    circ_policy_id_fetcher


def test_no_default_policy(app):
    """Test when no default circulation policy configured."""
    cipo = CircPolicy.get_default_circ_policy('org1')
    assert not cipo


def test_circ_policy_create(circ_policy_martigny_data_tmp,
                            org_martigny,
                            lib_martigny, lib_saxon,
                            patron_type_children_martigny,
                            item_type_standard_martigny,
                            patron_type_adults_martigny,
                            item_type_specific_martigny,
                            item_type_regular_sion,
                            patron_type_youngsters_sion):
    """Test circulation policy creation."""
    cipo = CircPolicy.create(circ_policy_martigny_data_tmp, delete_pid=True)
    assert cipo == circ_policy_martigny_data_tmp
    assert cipo.get('pid') == '1'

    cipo = CircPolicy.get_record_by_pid('1')
    assert cipo == circ_policy_martigny_data_tmp

    fetched_pid = circ_policy_id_fetcher(cipo.id, cipo)
    assert fetched_pid.pid_value == '1'
    assert fetched_pid.pid_type == 'cipo'

    circ_policy = deepcopy(circ_policy_martigny_data_tmp)
    del circ_policy['$schema']
    cipo = CircPolicy.create(circ_policy, delete_pid=True)
    assert cipo.get('$schema')
    assert cipo.get('pid') == '2'

    cipo_data = {
        '$schema': 'https://ils.rero.ch/schemas/'
        'circ_policies/circ_policy-v0.0.1.json',
        'pid': 'cipo_test',
        'name': 'test',
        'organisation': {
            '$ref': 'https://ils.rero.ch/api/organisations/org1'
        },
        'is_default': False,
        'allow_requests': True,
        'policy_library_level': False,
        'settings': [{
            'patron_type': {
                '$ref': 'https://ils.rero.ch/api/patron_types/ptty3'
            },
            'item_type': {
                '$ref': 'https://ils.rero.ch/api/item_types/itty1'
            }
        }, {
            'patron_type': {
                '$ref': 'https://ils.rero.ch/api/patron_types/ptty2'
            },
            'item_type': {
                '$ref': 'https://ils.rero.ch/api/item_types/itty4'
            }
        }]
    }
    with pytest.raises(ValidationError):
        cipo = CircPolicy.create(cipo_data, delete_pid=False)


def test_circ_policy_exist_name_and_organisation_pid(
        circ_policy_default_martigny):
    """Test policy name existance."""
    circ_policy = circ_policy_default_martigny
    cipo = circ_policy.replace_refs()
    assert CircPolicy.exist_name_and_organisation_pid(
        cipo.get('name'), cipo.get('organisation', {}).get('pid'))
    assert not CircPolicy.exist_name_and_organisation_pid(
        'not exists yet', cipo.get('organisation', {}).get('pid'))


def test_circ_policy_can_not_delete(circ_policy_default_martigny,
                                    circ_policy_short_martigny):
    """Test can not delete a policy."""
    others = circ_policy_default_martigny.reasons_to_keep()
    assert others['is_default']
    assert not circ_policy_default_martigny.can_delete

    others = circ_policy_short_martigny.reasons_to_keep()
    assert 'is_default' not in others
    assert circ_policy_short_martigny.can_delete


def test_circ_policy_can_delete(app, circ_policy_martigny_data_tmp):
    """Test can delete a policy."""
    circ_policy_martigny_data_tmp['is_default'] = False
    cipo = CircPolicy.create(circ_policy_martigny_data_tmp, delete_pid=True)
    assert cipo.get_links_to_me() == {}
    assert cipo.can_delete

    reasons = cipo.reasons_not_to_delete()
    assert 'links' not in reasons

    with mock.patch(
            'rero_ils.modules.circ_policies.api.CircPolicy.get_links_to_me'
    ) as a:
        a.return_value = {'object': 1}
        reasons = cipo.reasons_not_to_delete()
        assert 'links' in reasons
