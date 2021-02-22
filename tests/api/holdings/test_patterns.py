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


"""Holding Patterns Record tests."""

from __future__ import absolute_import, print_function

from copy import deepcopy
from datetime import datetime

import pytest
from flask import url_for
from invenio_accounts.testutils import login_user_via_session
from utils import get_json, postdata

from rero_ils.modules.documents.api import Document
from rero_ils.modules.errors import RecordValidationError
from rero_ils.modules.holdings.api import Holding
from rero_ils.modules.items.api import Item
from rero_ils.modules.items.models import ItemIssueStatus, ItemStatus
from rero_ils.modules.utils import get_ref_for_pid, get_schema_for_resource


def test_pattern_preview_api(
        client, holding_lib_martigny_w_patterns, librarian_martigny_no_email):
    """Test holdings patterns preview api."""
    login_user_via_session(client, librarian_martigny_no_email.user)
    holding = holding_lib_martigny_w_patterns
    # holding = Holding.get_record_by_pid(holding.pid)
    # test preview by default 10 issues returned
    res = client.get(
        url_for(
            'api_holding.patterns_preview',
            holding_pid=holding.pid
        )
    )
    assert res.status_code == 200
    issues = get_json(res).get('issues')
    assert issues[0]['issue'] == 'no 61 mars 2020'
    assert len(issues) == 10
    # test invalid size
    res = client.get(
        url_for(
            'api_holding.patterns_preview',
            holding_pid=holding.pid,
            size='no size'
        )
    )
    assert res.status_code == 200
    issues = get_json(res).get('issues')
    assert issues[0]['issue'] == 'no 61 mars 2020'
    assert len(issues) == 10
    # test preview for a given size
    res = client.get(
        url_for(
            'api_holding.patterns_preview',
            holding_pid=holding.pid,
            size=13
        )
    )
    assert res.status_code == 200
    issues = get_json(res).get('issues')
    assert issues[12]['issue'] == 'no 73 mars 2023'
    assert len(issues) == 13


def test_pattern_preview_api(
        client, holding_lib_martigny_w_patterns, librarian_martigny_no_email):
    """Test holdings patterns preview api."""
    login_user_via_session(client, librarian_martigny_no_email.user)
    holding = holding_lib_martigny_w_patterns
    # holding = Holding.get_record_by_pid(holding.pid)
    # test preview by default 10 issues returned
    res = client.get(
        url_for(
            'api_holding.patterns_preview',
            holding_pid=holding.pid
        )
    )
    assert res.status_code == 200
    issues = get_json(res).get('issues')
    assert issues[0]['issue'] == 'no 61 mars 2020'
    assert len(issues) == 10
    # test invalid size
    res = client.get(
        url_for(
            'api_holding.patterns_preview',
            holding_pid=holding.pid,
            size='no size'
        )
    )
    assert res.status_code == 200
    issues = get_json(res).get('issues')
    assert issues[0]['issue'] == 'no 61 mars 2020'
    assert len(issues) == 10
    # test preview for a given size
    res = client.get(
        url_for(
            'api_holding.patterns_preview',
            holding_pid=holding.pid,
            size=13
        )
    )
    assert res.status_code == 200
    issues = get_json(res).get('issues')
    assert issues[12]['issue'] == 'no 73 mars 2023'
    assert len(issues) == 13


def test_receive_regular_issue_api(
        client, holding_lib_martigny_w_patterns,
        librarian_fully_no_email, librarian_martigny_no_email,
        system_librarian_sion_no_email):
    """Test holdings receive regular issues API."""
    holding = holding_lib_martigny_w_patterns
    holding = Holding.get_record_by_pid(holding.pid)
    issue_display, expected_date, gaps = holding._get_next_issue_display_text(
                        holding.get('patterns'))
    # not logged users are not authorized
    res, data = postdata(
        client,
        'api_holding.receive_regular_issue',
        url_data=dict(holding_pid=holding.pid)
    )
    assert res.status_code == 401

    # librarian of another library are not authoritzed to receive issues
    # for another library.
    login_user_via_session(client, librarian_fully_no_email.user)
    res, data = postdata(
        client,
        'api_holding.receive_regular_issue',
        url_data=dict(holding_pid=holding.pid)
    )
    assert res.status_code == 401
    # only users of same organisation may receive issues.
    login_user_via_session(client, system_librarian_sion_no_email.user)
    res, data = postdata(
        client,
        'api_holding.receive_regular_issue',
        url_data=dict(holding_pid=holding.pid)
    )
    assert res.status_code == 401

    login_user_via_session(client, librarian_martigny_no_email.user)
    res, data = postdata(
        client,
        'api_holding.receive_regular_issue',
        url_data=dict(holding_pid=holding.pid)
    )
    assert res.status_code == 200
    issue = get_json(res).get('issue')
    assert issue.get('enumerationAndChronology') == issue_display
    assert issue.get('issue').get('expected_date') == expected_date
    item = {
        'issue': {
            'regular': True,
            'status': ItemIssueStatus.RECEIVED,
            'expected_date': datetime.now().strftime('%Y-%m-%d'),
            'received_date': datetime.now().strftime('%Y-%m-%d')
        },
        'enumerationAndChronology': 'free_text'
    }
    res, data = postdata(
        client,
        'api_holding.receive_regular_issue',
        data=dict(item=item),
        url_data=dict(holding_pid=holding.pid)
    )
    assert res.status_code == 200
    issue = get_json(res).get('issue')
    assert issue.get('enumerationAndChronology') == 'free_text'
    assert issue.get('issue').get('expected_date') == \
        datetime.now().strftime('%Y-%m-%d')


def test_create_holdings_with_pattern(
        client, librarian_martigny_no_email, loc_public_martigny,
        journal, item_type_standard_martigny, document,
        json_header, holding_lib_martigny_data, pattern_yearly_one_level_data,
        holding_lib_martigny_w_patterns_data):
    """Test create holding type serial with patterns."""
    login_user_via_session(client, librarian_martigny_no_email.user)
    post_entrypoint = 'invenio_records_rest.hold_list'

    del holding_lib_martigny_data['pid']
    holding_lib_martigny_data['holdings_type'] = 'serial'
    res, _ = postdata(
        client,
        post_entrypoint,
        holding_lib_martigny_data
    )
    assert res.status_code == 201

    holding_lib_martigny_data['patterns'] = \
        pattern_yearly_one_level_data['patterns']

    # test will fail when creating a serial holding for a standard document.
    res, _ = postdata(
        client,
        post_entrypoint,
        holding_lib_martigny_data
    )
    assert res.status_code == 201

    # test will not fail when creating a standard holding for a journal doc.
    holding_lib_martigny_w_patterns_data['holdings_type'] = 'standard'
    # delete serials fields
    fields = [
                'enumerationAndChronology', 'notes', 'index', 'missing_issues',
                'supplementaryContent', 'acquisition_status',
                'acquisition_method', 'acquisition_expected_end_date',
                'general_retention_policy', 'completeness',
                'composite_copy_report', 'issue_binding'
    ]
    for field in fields:
        del holding_lib_martigny_w_patterns_data[field]
    Holding.create(
        data=holding_lib_martigny_w_patterns_data,
        delete_pid=True,
        dbcommit=True,
        reindex=True)

    journal_pids = list(Document.get_all_serial_pids())
    assert journal_pids == [journal.pid]


def test_holding_pattern_preview_api(
        client, pattern_yearly_one_level_data,
        librarian_martigny_no_email):
    """Test holdings patterns preview api."""
    login_user_via_session(client, librarian_martigny_no_email.user)
    patterns = pattern_yearly_one_level_data.get('patterns')
    # test preview by default 10 issues returned
    res, data = postdata(
        client,
        'api_holding.pattern_preview',
        dict(data=patterns, size=15)
    )
    assert res.status_code == 200

    issues = get_json(res).get('issues')
    assert issues[0]['issue'] == '82 2020'
    assert len(issues) == 15

    # test invalid patterns
    del(patterns['values'])
    res, data = postdata(
        client,
        'api_holding.pattern_preview',
        dict(data=patterns)
    )
    assert res.status_code == 200

    issues = get_json(res).get('issues')
    assert issues == []
    assert len(issues) == 0


def test_automatic_item_creation_no_serials(
        client, json_header, holding_lib_martigny_w_patterns,
        item_lib_martigny_data, librarian_martigny_no_email):
    """Test automatically created items are not attached to serials."""
    login_user_via_session(client, librarian_martigny_no_email.user)
    post_url = 'invenio_records_rest.item_list'
    res, _ = postdata(
        client,
        post_url,
        item_lib_martigny_data
    )
    assert res.status_code == 201
    item = Item.get_record_by_pid(item_lib_martigny_data.get('pid'))
    holding = Holding.get_record_by_pid(item.holding_pid)
    assert holding.pid != holding_lib_martigny_w_patterns.pid
    assert holding.location_pid == holding_lib_martigny_w_patterns.location_pid
    assert holding.get('circulation_category') == \
        holding_lib_martigny_w_patterns.get('circulation_category')


def test_pattern_validate_next_expected_date(
        client, librarian_martigny_no_email,
        journal, loc_public_sion, item_type_regular_sion, document,
        pattern_yearly_two_times_data, json_header,
        holding_lib_sion_w_patterns_data):
    """Test create holding with regular frequency and missing

    the next_expected_date.
    """
    login_user_via_session(client, librarian_martigny_no_email.user)
    holding = holding_lib_sion_w_patterns_data
    holding['holdings_type'] = 'serial'
    holding['patterns'] = \
        pattern_yearly_two_times_data['patterns']
    del holding['pid']
    del holding['patterns']['next_expected_date']
    # test will fail when the serial holding has no field
    # next_expected_date for the regular frequency
    with pytest.raises(RecordValidationError):
        Holding.create(
            data=holding,
            delete_pid=False,
            dbcommit=True,
            reindex=True)


def test_irregular_issue_creation_update_delete_api(
        client, holding_lib_martigny_w_patterns,
        librarian_martigny_no_email):
    """Test create, update and delete of an irregular issue API."""
    holding = holding_lib_martigny_w_patterns
    issue_display, expected_date, gaps = holding._get_next_issue_display_text(
                        holding.get('patterns'))

    login_user_via_session(client, librarian_martigny_no_email.user)
    item = {
        'issue': {
            'status': ItemIssueStatus.RECEIVED,
            'received_date': datetime.now().strftime('%Y-%m-%d'),
            'expected_date': datetime.now().strftime('%Y-%m-%d'),
            'regular': False
        },
        'enumerationAndChronology': 'irregular_issue',
        'status': ItemStatus.ON_SHELF,
        'holding': {'$ref': get_ref_for_pid('hold', holding.pid)},
        '$schema': get_schema_for_resource(Item),
        'location': holding.get('location'),
        'document': holding.get('document'),
        'item_type': holding.get('circulation_category'),
        'type': 'issue',
        'organisation':
            {'$ref': get_ref_for_pid('org', holding.organisation_pid)}
    }
    res, data = postdata(
        client,
        'invenio_records_rest.item_list',
        item
    )
    assert res.status_code == 201
    created_item = Item.get_record_by_pid(data['metadata'].get('pid'))
    assert created_item.get('barcode').startswith('f-')
    assert created_item.get('type') == 'issue'
    assert not created_item.get('issue').get('regular')
    assert created_item.get('enumerationAndChronology') == 'irregular_issue'
    new_issue_display, new_expected_date, gaps = \
        holding._get_next_issue_display_text(holding.get('patterns'))
    assert new_issue_display == issue_display
    assert new_expected_date == expected_date

    # No Validation error if you try to create an issue with no holdings links
    item = {
        'issue': {
            'status': ItemIssueStatus.RECEIVED,
            'received_date': datetime.now().strftime('%Y-%m-%d'),
            'expected_date': datetime.now().strftime('%Y-%m-%d'),
            'regular': False
        },
        'enumerationAndChronology': 'irregular_issue',
        'status': ItemStatus.ON_SHELF,
        'location': holding.get('location'),
        'document': holding.get('document'),
        'item_type': holding.get('circulation_category'),
        'type': 'issue'
    }
    res, data = postdata(
        client,
        'invenio_records_rest.item_list',
        item
    )
    # NO validation error if you try to update an issue with a holdings link
    item = deepcopy(created_item)
    created_item.update(data=item, dbcommit=True, reindex=True)
    # Validation error if you try to update an issue with no holdings links
    item.pop('holding')
    # with pytest.raises(RecordValidationError):
    created_item.update(data=item, dbcommit=True, reindex=True)
    # no errors when deleting an irregular issue
    pid = created_item.pid
    created_item.delete(dbcommit=True, delindex=True)
    assert not Item.get_record_by_pid(pid)
