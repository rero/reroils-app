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

"""Item type record tests."""

from __future__ import absolute_import, print_function

import pytest
from jsonschema.exceptions import ValidationError

from rero_ils.modules.item_types.api import ItemType, item_type_id_fetcher


def test_item_type_create(db, item_type_data_tmp, org_martigny,
                          item_type_online_martigny):
    """Test item type record creation."""
    item_type_data_tmp['type'] = 'online'
    with pytest.raises(ValidationError):
        itty = ItemType.create(item_type_data_tmp, delete_pid=True)

    db.session.rollback()

    next_pid = ItemType.provider.identifier.next()
    item_type_data_tmp['type'] = 'standard'
    itty = ItemType.create(item_type_data_tmp, delete_pid=True)
    next_pid += 1

    assert itty == item_type_data_tmp
    assert itty.get('pid') == str(next_pid)

    itty = ItemType.get_record_by_pid(str(next_pid))
    assert itty == item_type_data_tmp

    fetched_pid = item_type_id_fetcher(itty.id, itty)
    assert fetched_pid.pid_value == str(next_pid)
    assert fetched_pid.pid_type == 'itty'
    assert not ItemType.get_pid_by_name('no exists')


def test_item_type_exist_name_and_organisation_pid(
        item_type_standard_martigny):
    """Test item type name uniqueness."""
    item_type = item_type_standard_martigny
    itty = item_type.replace_refs()
    assert ItemType.exist_name_and_organisation_pid(
        itty.get('name'), itty.get('organisation', {}).get('pid'))
    assert not ItemType.exist_name_and_organisation_pid(
        'not exists yet', itty.get('organisation', {}).get('pid'))


def test_item_type_get_pid_by_name(item_type_standard_martigny):
    """Test item type retrieval by name."""
    assert not ItemType.get_pid_by_name('no exists')
    assert ItemType.get_pid_by_name('standard') == 'itty1'


def test_item_type_can_not_delete(item_type_standard_martigny,
                                  item_lib_martigny):
    """Test item type can not delete"""
    links = item_type_standard_martigny.get_links_to_me()
    assert links['items'] == 1
    assert not item_type_standard_martigny.can_delete


def test_item_type_can_delete(app, item_type_data_tmp):
    """Test item type can delete"""
    itty = ItemType.create(item_type_data_tmp, delete_pid=True)
    assert itty.get_links_to_me() == {}
    assert itty.can_delete


def test_item_type_properties(item_type_standard_martigny):
    """Test item type properties."""
    itty = item_type_standard_martigny

    # test 'label'
    assert itty.get_label() == itty['name']
    label_strings = {
        'en': ('info_label_eng', 'disable_text_eng'),
        'fr': ('info_label_fre', 'disable_text_fre'),
        'es': (None, 'disable_text_spa')
    }
    for language, labels in label_strings.items():
        itty.setdefault('circulation_information', []).append({
            'language': language,
            'label': labels[0]
        })
        itty.setdefault('displayed_status', []).append({
            'language': language,
            'label': labels[1]
        })
    assert itty.get_label('en') == label_strings['en'][0]
    assert itty.get_label('fr') == label_strings['fr'][0]
    assert itty.get_label('es') == itty['name']
    assert itty.get_label('nl') == itty['name']
    itty['negative_availability'] = True
    assert itty.get_label('en') == label_strings['en'][1]
    assert itty.get_label('fr') == label_strings['fr'][1]
    assert itty.get_label('es') == label_strings['es'][1]
    assert itty.get_label('nl') == itty['name']
