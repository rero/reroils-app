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

"""Tests REST API patrons."""

import json
from copy import deepcopy

from flask import url_for
from invenio_access import Permission
from invenio_accounts.testutils import login_user_via_session
from utils import get_json, postdata

from rero_ils.modules.loans.api import LoanAction
from rero_ils.modules.loans.permissions import PendingLoansCondition
from rero_ils.modules.patrons.api import Patron
from rero_ils.modules.permissions import ALLOW, DENY
from rero_ils.permissions import librarian_delete_permission_factory
from rero_ils.utils import create_user_from_data


def test_librarian_delete_permission_factory(
        client, librarian_fully, org_martigny, lib_martigny):
    """Test librarian_delete_permission_factory """
    login_user_via_session(client, librarian_fully.user)
    assert type(
        librarian_delete_permission_factory(None, credentials_only=True)
    ) == Permission
    assert librarian_delete_permission_factory(org_martigny) is not None


def test_librarian_permissions(
        client, system_librarian_martigny, json_header,
        patron_martigny,
        librarian_fully,
        patron_martigny_data_tmp,
        lib_saxon):
    """Test librarian permissions."""
    # Login as librarian
    login_user_via_session(client, librarian_fully.user)

    record = {
        "$schema": "https://ils.rero.ch/schemas/patrons/patron-v0.0.1.json",
        "first_name": "first_name",
        "last_name": "Last_name",
        "username": "username",
        "street": "Avenue Leopold-Robert, 132",
        "postal_code": "1920",
        "city": "Martigny",
        "birth_date": "1967-06-07",
        "patron": {
            "expiration_date": "2023-10-07",
            "type": {"$ref": "https://ils.rero.ch/api/patron_types/ptty1"},
            "communication_channel": "mail",
            "communication_language": "ita"
        },
        "libraries": [{"$ref": "https://ils.rero.ch/api/libraries/lib1"}],
        "home_phone": "+41324993111"
    }
    record = create_user_from_data(record)
    # can retrieve all type of users.
    list_url = url_for('invenio_records_rest.ptrn_list')
    res = client.get(list_url)
    assert res.status_code == 200
    data = get_json(res)
    assert data['hits']['total']['value'] == 3

    # can manage all types of patron roles
    role_url = url_for('api_patrons.get_roles_management_permissions')
    res = client.get(role_url)
    assert res.status_code == 200
    data = get_json(res)
    permissions = [role for role in data['roles'] if role['name'] ==
                   Patron.ROLE_LIBRARIAN][0]
    assert permissions['permissions']['add']['can'] == ALLOW
    assert permissions['permissions']['delete']['can'] == ALLOW
    permissions = [role for role in data['roles'] if role['name'] ==
                   Patron.ROLE_SYSTEM_LIBRARIAN][0]
    assert permissions['permissions']['add']['can'] == DENY
    assert permissions['permissions']['delete']['can'] == DENY

    # can create all type of users except system_librarians
    post_entrypoint = 'invenio_records_rest.ptrn_list'
    system_librarian = deepcopy(record)
    librarian = deepcopy(record)
    librarian_saxon = deepcopy(record)
    librarian_saxon['libraries'] = \
        [{"$ref": "https://ils.rero.ch/api/libraries/lib2"}]
    librarian['libraries'] = \
        [{"$ref": "https://ils.rero.ch/api/libraries/lib3"}]
    patron = deepcopy(record)
    patron['libraries'] = \
        [{"$ref": "https://ils.rero.ch/api/libraries/lib3"}]
    counter = 1
    for record in [
        {'data': patron, 'role': 'patron'},
        {'data': librarian, 'role': 'librarian'},
    ]:
        counter += 1
        data = record['data']
        data['roles'] = [record['role']]
        data['patron']['barcode'] = ['barcode' + str(counter)]

        res, _ = postdata(
            client,
            post_entrypoint,
            data
        )
        assert res.status_code == 201
        user = get_json(res)['metadata']
        user_pid = user.get('pid')
        record_url = url_for('invenio_records_rest.ptrn_item',
                             pid_value=user_pid)
        res = client.get(record_url)
        assert res.status_code == 200
        user = get_json(res)['metadata']

        # can update all type of user records except system_librarian.
        user['first_name'] = 'New Name' + str(counter)
        res = client.put(
            record_url,
            data=json.dumps(user),
            headers=json_header
        )
        assert res.status_code == 200

        # can not add the role system_librarian to user
        user['roles'] = ['system_librarian']
        res = client.put(
            record_url,
            data=json.dumps(user),
            headers=json_header
        )
        assert res.status_code == 403

        # can delete all type of user records except system_librarian.
        record_url = url_for('invenio_records_rest.ptrn_item',
                             pid_value=user_pid)

        res = client.delete(record_url)
        assert res.status_code == 204

    # can not create librarians of same libray.
    counter = 1
    for record in [
        {'data': librarian_saxon, 'role': 'librarian'},
    ]:
        counter += 1
        data = record['data']
        data['roles'] = [record['role']]
        data['patron']['barcode'] = ['barcode' + str(counter)]
        res, _ = postdata(
            client,
            post_entrypoint,
            data
        )
        assert res.status_code == 403

    system_librarian['roles'] = ['system_librarian']
    system_librarian['patron']['barcode'] = ['barcode']

    res, _ = postdata(
        client,
        post_entrypoint,
        system_librarian,
    )
    assert res.status_code == 403

    # can update all type of user records except system_librarian.
    record_url = url_for('invenio_records_rest.ptrn_item',
                         pid_value=system_librarian_martigny.pid)
    system_librarian_martigny['first_name'] = 'New Name'
    res = client.put(
        record_url,
        data=json.dumps(system_librarian_martigny),
        headers=json_header
    )
    assert res.status_code == 403

    # can delete all type of user records except system_librarian.
    sys_librarian_pid = system_librarian_martigny.get('pid')
    record_url = url_for('invenio_records_rest.ptrn_item',
                         pid_value=sys_librarian_pid)

    res = client.delete(record_url)
    assert res.status_code == 403


def test_role_management_api(client, patron_martigny_no_email,
                             librarian_martigny_no_email, item_lib_martigny,
                             loc_public_martigny, lib_martigny,
                             circ_policy_short_martigny):
    """Test the role management permissions API."""
    # Login as librarian
    login_user_via_session(client, librarian_martigny_no_email.user)

    # First checkout - All should be fine.
    res, data = postdata(client, 'api_item.checkout', dict(
        item_pid=item_lib_martigny.pid,
        patron_pid=patron_martigny_no_email.pid,
        transaction_location_pid=loc_public_martigny.pid,
        transaction_user_pid=librarian_martigny_no_email.pid,
    ))
    assert res.status_code == 200
    loan_pid = data.get('action_applied')[LoanAction.CHECKOUT].get('pid')

    # Check the role management API
    role_url = url_for('api_patrons.get_roles_management_permissions',
                       patron_pid=patron_martigny_no_email.pid)
    res = client.get(role_url)
    assert res.status_code == 200
    data = get_json(res)
    permissions = [role for role in data['roles'] if role['name'] ==
                   Patron.ROLE_PATRON][0]
    assert permissions['permissions']['add']['can'] == ALLOW
    assert permissions['permissions']['delete']['can'] == DENY
    assert PendingLoansCondition.message in \
        permissions['permissions']['delete']['reasons']

    # Reset fixtures - Do checkin
    res, _ = postdata(client, 'api_item.checkin', dict(
        item_pid=item_lib_martigny.pid,
        pid=loan_pid,
        transaction_location_pid=loc_public_martigny.pid,
        transaction_user_pid=librarian_martigny_no_email.pid,
    ))
    assert res.status_code == 200
