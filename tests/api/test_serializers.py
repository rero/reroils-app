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

"""Tests Serializers."""

from flask import url_for
from utils import get_csv, get_json, item_record_to_a_specific_loan_state, \
    login_user

from rero_ils.modules.loans.api import LoanState


def test_patrons_serializers(
    client,
    json_header,
    librarian_martigny,
    librarian2_martigny
):
    """Test serializers for patrons."""
    login_user(client, librarian_martigny)

    list_url = url_for('invenio_records_rest.ptrn_list')
    response = client.get(list_url, headers=json_header)
    assert response.status_code == 200

    # Get the first result and check if it contains all desired keys.
    data = get_json(response)
    hit = data['hits']['hits'][0]
    for key in ['created', 'updated', 'id', 'links', 'metadata']:
        assert key in hit
        assert hit[key]


def test_holdings_serializers(
    client,
    rero_json_header,
    librarian_martigny,
    lib_martigny,
    holding_lib_martigny
):
    """Test serializers for holdings."""
    login_user(client, librarian_martigny)

    holding_url = url_for('invenio_records_rest.hold_list')
    response = client.get(holding_url, headers=rero_json_header)
    assert response.status_code == 200
    data = get_json(response)
    record = data['hits']['hits'][0]['metadata']
    assert record.get('location', {}).get('name')
    assert record.get('library', {}).get('name')
    assert record.get('circulation_category', {}).get('name')


def test_items_serializers(
    client,
    item_lib_martigny,  # on shelf
    item_lib_fully,  # on loan
    csv_header,
    json_header,
    rero_json_header,
    patron_martigny,
    librarian_martigny,
    librarian_sion,
    loan_pending_martigny
):
    """Test record retrieval."""
    login_user(client, librarian_martigny)

    item_url = url_for(
        'invenio_records_rest.item_item', pid_value=item_lib_fully.pid)
    response = client.get(item_url, headers=json_header)
    assert response.status_code == 200
    data = get_json(response)
    assert data['metadata'].get('item_type', {}).get('$ref')

    item_url = url_for(
        'invenio_records_rest.item_item', pid_value=item_lib_martigny.pid)
    response = client.get(item_url, headers=json_header)
    assert response.status_code == 200
    data = get_json(response)
    assert data['metadata'].get('item_type', {}).get('$ref')

    item_url = url_for(
        'invenio_records_rest.item_item',
        pid_value=item_lib_fully.pid, resolve=1)
    response = client.get(item_url, headers=json_header)
    data = get_json(response)
    assert data['metadata'].get('item_type', {}).get('pid')
    # test if all key exist into response with a value
    for key in ['created', 'updated', 'id', 'links', 'metadata']:
        assert key in data
        assert data[key]

    list_url = url_for('invenio_records_rest.item_list')
    response = client.get(list_url, headers=rero_json_header)
    assert response.status_code == 200

    list_url = url_for('api_item.inventory_search')
    response = client.get(list_url, headers=csv_header)
    assert response.status_code == 200
    data = get_csv(response)
    assert data
    assert '"pid","document_pid","document_title","document_creator",' \
           '"document_main_type","document_sub_type","library_name",' \
           '"location_name","barcode","call_number","second_call_number",' \
           '"enumerationAndChronology","item_type","temporary_item_type",' \
           '"temporary_item_type_end_date","general_note","staff_note",' \
           '"checkin_note","checkout_note","loans_count",' \
           '"last_transaction_date","status","created","issue_status",' \
           '"issue_status_date","issue_claims_count","issue_expected_date",' \
           '"issue_regular"' in data


def test_loans_serializers(
    client,
    rero_json_header,
    patron_martigny,
    loc_public_martigny,
    loc_public_fully,
    librarian_martigny,
    item_lib_martigny,
    item_lib_fully,
    circulation_policies
):
    """Test serializers for loans."""
    login_user(client, patron_martigny)
    # create somes loans on same item with different state
    params = {
        'patron_pid': patron_martigny.pid,
        'transaction_location_pid': loc_public_martigny.pid,
        'transaction_user_pid': librarian_martigny.pid,
        'pickup_location_pid': loc_public_martigny.pid,
    }
    item_record_to_a_specific_loan_state(
        item=item_lib_martigny, loan_state=LoanState.PENDING,
        params=params, copy_item=True)
    item_record_to_a_specific_loan_state(
        item=item_lib_martigny, loan_state=LoanState.ITEM_AT_DESK,
        params=params, copy_item=True)
    item_record_to_a_specific_loan_state(
        item=item_lib_martigny, loan_state=LoanState.ITEM_ON_LOAN,
        params=params, copy_item=True)
    params = {
        'patron_pid': patron_martigny.pid,
        'transaction_location_pid': loc_public_fully.pid,
        'transaction_user_pid': librarian_martigny.pid,
        'pickup_location_pid': loc_public_fully.pid,
        'checkin_transaction_location_pid': loc_public_martigny.pid
    }
    item_record_to_a_specific_loan_state(
        item=item_lib_fully,
        loan_state=LoanState.ITEM_IN_TRANSIT_TO_HOUSE,
        params=params, copy_item=True)

    list_url = url_for('invenio_records_rest.loanid_list')
    response = client.get(list_url, headers=rero_json_header)
    assert response.status_code == 200
    data = get_json(response)
    records = data.get('hits', {}).get('hits', [])
    for record in records:
        data = record.get('metadata', {})
        if data.get('state') == 'PENDING':
            assert data.get('pickup_name')
        elif data.get('state') == 'ITEM_AT_DESK':
            assert data.get('rank') == 0
        elif data.get('state') == 'ITEM_ON_LOAN':
            assert data.get('overdue') is False
        elif data.get('state') == 'ITEM_IN_TRANSIT_TO_HOUSE':
            assert data.get('pickup_library_name')
            assert data.get('transaction_library_name')


def test_patron_transactions_serializers(
    client,
    rero_json_header,
    librarian_saxon,
    patron_transaction_overdue_saxon
):
    """Test serializers for patron transactions."""
    login_user(client, librarian_saxon)
    list_url = url_for('invenio_records_rest.pttr_list')
    response = client.get(list_url, headers=rero_json_header)
    assert response.status_code == 200
    data = get_json(response)
    record = data.get('hits', {}).get('hits', [])[0]
    assert record.get('metadata', {}).get('document')
    assert record.get('metadata', {}).get('loan')
    assert record.get('metadata', {}).get('loan', {}).get('item')


def test_patron_transaction_events_serializers(
    client,
    rero_json_header,
    librarian_saxon,
    patron_transaction_overdue_event_saxon
):
    """Test serializers for patron transaction events."""
    login_user(client, librarian_saxon)
    list_url = url_for('invenio_records_rest.ptre_list')
    response = client.get(list_url, headers=rero_json_header)
    assert response.status_code == 200
    data = get_json(response)
    record = data.get('hits', {}).get('hits', [])[0]
    assert record.get('metadata', {}).get('library', {}).get('name')


def test_ill_requests_serializers(
    client,
    rero_json_header,
    patron_martigny,
    ill_request_martigny
):
    """Test serializers for ills requests."""
    login_user(client, patron_martigny)
    list_url = url_for('invenio_records_rest.illr_list')
    response = client.get(list_url, headers=rero_json_header)
    assert response.status_code == 200
    data = get_json(response)
    record = data.get('hits', {}).get('hits', [])[0]
    assert record.get('metadata', {}).get('pickup_location', {}).get('name')
