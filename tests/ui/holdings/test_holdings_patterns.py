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

import ciso8601
import jinja2
import pytest
from invenio_accounts.testutils import login_user_via_session
from jsonschema.exceptions import ValidationError

from rero_ils.modules.api import IlsRecordError
from rero_ils.modules.holdings.api import Holding
from rero_ils.modules.holdings.models import HoldingNoteTypes
from rero_ils.modules.items.api import Item
from rero_ils.modules.items.models import ItemIssueStatus, ItemStatus


def test_patterns_functions(holding_lib_martigny_w_patterns,
                            holding_lib_martigny):
    """Test holdings patterns functions."""
    # test no prediction for standard holdings record
    assert not holding_lib_martigny.increment_next_prediction()
    assert not holding_lib_martigny.next_issue_display_text
    assert not holding_lib_martigny.prediction_issues_preview(1)

    holding = holding_lib_martigny_w_patterns
    old_template = holding.get('patterns').get('template')
    # test invalid syntax for pattern templates
    template = 'no {{first_chronology.level_1}'
    holding['patterns']['template'] = template
    with pytest.raises(jinja2.exceptions.TemplateSyntaxError):
        assert holding.next_issue_display_text

    template = 'no {{unknown_chronology.level_1}}'
    holding['patterns']['template'] = template
    with pytest.raises(jinja2.exceptions.UndefinedError):
        assert holding.next_issue_display_text
    holding['patterns']['template'] = old_template


def test_patterns_quarterly_one_level(holding_lib_martigny_w_patterns):
    """Test holdings patterns annual two levels."""
    holding = holding_lib_martigny_w_patterns
    # test first issue
    assert holding.next_issue_display_text == 'no 61 mars 2020'
    holding.increment_next_prediction()
    assert holding.next_issue_display_text == 'no 62 juin 2020'
    for r in range(11):
        holding.increment_next_prediction()
    assert holding.next_issue_display_text == 'no 73 mars 2023'
    # test preview
    issues = holding.prediction_issues_preview(13)
    assert issues[-1]['issue'] == 'no 85 mars 2026'
    # test expected date
    new_holding = deepcopy(holding_lib_martigny_w_patterns)
    template = '{{expected_date.day}} {{expected_date.month}}'
    new_holding['patterns']['template'] = template
    assert new_holding.next_issue_display_text == '1 3'


def test_receive_regular_issue(holding_lib_martigny_w_patterns):
    """Test holdings receive regular issues."""
    holding = holding_lib_martigny_w_patterns
    assert holding.holding_is_serial
    issue = holding.receive_regular_issue(dbcommit=True, reindex=True)
    # test holdings call number inheriting
    assert issue.issue_inherited_first_call_number == \
        holding.get('call_number')
    assert list(holding.get_items)[0].get('pid') == issue.pid

    assert issue.location_pid == holding.location_pid
    assert issue.item_type_pid == holding.circulation_category_pid
    assert issue.document_pid == holding.document_pid
    assert issue.holding_pid == holding.pid
    assert issue.get('status') == ItemStatus.ON_SHELF
    assert issue.item_record_type == 'issue'
    assert issue.organisation_pid == holding.organisation_pid
    assert issue.get('issue', {}).get('regular')
    assert issue.issue_status == ItemIssueStatus.RECEIVED
    assert issue.expected_date == '2023-03-01'
    assert issue.get('enumerationAndChronology') == 'no 73 mars 2023'
    assert issue.received_date == datetime.now().strftime('%Y-%m-%d')
    issue_status_date = ciso8601.parse_datetime(issue.issue_status_date)
    assert issue_status_date.strftime('%Y-%m-%d') == \
        datetime.now().strftime('%Y-%m-%d')
    # test change status_date with status changes
    issue['issue']['status'] = ItemIssueStatus.CLAIMED
    new_issues = issue.update(issue, dbcommit=True, reindex=True)
    assert new_issues.issue_status == ItemIssueStatus.CLAIMED
    new_issue_status_date = ciso8601.parse_datetime(
        new_issues.issue_status_date)
    assert new_issue_status_date > issue_status_date

    holding = Holding.get_record_by_pid(holding.pid)
    issue = holding.receive_regular_issue(dbcommit=True, reindex=True)
    assert issue.get('issue', {}).get('regular')
    assert issue.issue_status == ItemIssueStatus.RECEIVED
    assert issue.expected_date == '2020-06-01'
    assert issue.get('enumerationAndChronology') == 'no 62 juin 2020'
    assert issue.received_date == datetime.now().strftime('%Y-%m-%d')
    # test create customized regular issue
    record = {
        'issue': {
            'regular': True,
            'status': ItemIssueStatus.RECEIVED,
            'expected_date': datetime.now().strftime('%Y-%m-%d'),
            'received_date': datetime.now().strftime('%Y-%m-%d')
        },
        'enumerationAndChronology': 'free_text'
    }
    holding = Holding.get_record_by_pid(holding.pid)
    issue = holding.receive_regular_issue(
        item=record, dbcommit=True, reindex=True)
    assert issue.get('issue', {}).get('regular')
    assert issue.issue_status == ItemIssueStatus.RECEIVED
    assert issue.expected_date == datetime.now().strftime('%Y-%m-%d')
    assert issue.get('enumerationAndChronology') == 'free_text'
    assert issue.received_date == datetime.now().strftime('%Y-%m-%d')


def test_patterns_yearly_one_level(
        holding_lib_martigny_w_patterns,
        pattern_yearly_one_level_data):
    """Test pattern yearly one level."""
    holding = holding_lib_martigny_w_patterns
    holding = Holding.get_record_by_pid(holding.pid)
    holding['patterns'] = pattern_yearly_one_level_data['patterns']

    # test first issue
    assert holding.next_issue_display_text == '82 2020'
    holding.increment_next_prediction()
    assert holding.next_issue_display_text == '83 2021'
    for r in range(25):
        holding.increment_next_prediction()
    assert holding.next_issue_display_text == '108 2046'
    # test preview
    issues = holding.prediction_issues_preview(13)
    assert issues[-1]['issue'] == '120 2058'


def test_patterns_yearly_one_level_with_label(
        holding_lib_martigny_w_patterns,
        pattern_yearly_one_level_with_label_data):
    """Test pattern yearly one level with label."""
    holding = holding_lib_martigny_w_patterns
    holding = Holding.get_record_by_pid(holding.pid)
    holding['patterns'] = pattern_yearly_one_level_with_label_data['patterns']
    # test first issue
    assert holding.next_issue_display_text == '29 Edition 2020'
    holding.increment_next_prediction()
    assert holding.next_issue_display_text == '30 Edition 2021'
    for r in range(25):
        holding.increment_next_prediction()
    assert holding.next_issue_display_text == '55 Edition 2046'
    # test preview
    issues = holding.prediction_issues_preview(13)
    assert issues[-1]['issue'] == '67 Edition 2058'


def test_patterns_yearly_two_times(
        holding_lib_martigny_w_patterns,
        pattern_yearly_two_times_data):
    """Test pattern yearly two times."""
    holding = holding_lib_martigny_w_patterns
    holding = Holding.get_record_by_pid(holding.pid)
    holding['patterns'] = pattern_yearly_two_times_data['patterns']
    # test first issue
    assert holding.next_issue_display_text == 'Jg. 8 Nov. 2019'
    holding.increment_next_prediction()
    assert holding.next_issue_display_text == 'Jg. 9 März 2020'
    for r in range(25):
        holding.increment_next_prediction()
    assert holding.next_issue_display_text == 'Jg. 21 Nov. 2032'
    # test preview
    issues = holding.prediction_issues_preview(13)
    assert issues[-1]['issue'] == 'Jg. 27 Nov. 2038'


def test_patterns_quarterly_two_levels(
        holding_lib_martigny_w_patterns,
        pattern_quarterly_two_levels_data):
    """Test pattern quarterly_two_levels."""
    holding = holding_lib_martigny_w_patterns
    holding = Holding.get_record_by_pid(holding.pid)
    holding['patterns'] = pattern_quarterly_two_levels_data['patterns']
    # test first issue
    assert holding.next_issue_display_text == 'Jg. 20 Heft 1 2020'
    holding.increment_next_prediction()
    assert holding.next_issue_display_text == 'Jg. 20 Heft 2 2020'
    for r in range(25):
        holding.increment_next_prediction()
    assert holding.next_issue_display_text == 'Jg. 26 Heft 3 2026'
    # test preview
    issues = holding.prediction_issues_preview(13)
    assert issues[-1]['issue'] == 'Jg. 29 Heft 3 2029'


def test_patterns_quarterly_two_levels_with_season(
        holding_lib_martigny_w_patterns,
        pattern_quarterly_two_levels_with_season_data):
    """Test pattern quarterly_two_levels_with_season."""
    holding = holding_lib_martigny_w_patterns
    holding = Holding.get_record_by_pid(holding.pid)
    holding['patterns'] = \
        pattern_quarterly_two_levels_with_season_data['patterns']
    # test first issue
    assert holding.next_issue_display_text == \
        'année 2019 no 277 printemps 2018'
    holding.increment_next_prediction()
    assert holding.next_issue_display_text == 'année 2019 no 278 été 2018'
    for r in range(25):
        holding.increment_next_prediction()
    assert holding.next_issue_display_text == \
        'année 2025 no 303 automne 2024'
    # test preview
    issues = holding.prediction_issues_preview(13)
    assert issues[-1]['issue'] == 'année 2028 no 315 automne 2027'


def test_patterns_half_yearly_one_level(
        holding_lib_martigny_w_patterns,
        pattern_half_yearly_one_level_data):
    """Test pattern half_yearly_one_level."""
    holding = holding_lib_martigny_w_patterns
    holding = Holding.get_record_by_pid(holding.pid)

    holding['patterns'] = \
        pattern_half_yearly_one_level_data['patterns']

    # test first issue
    assert holding.next_issue_display_text == 'N˚ 48 printemps 2019'
    holding.increment_next_prediction()
    assert holding.next_issue_display_text == 'N˚ 49 automne 2019'
    for r in range(13):
        holding.increment_next_prediction()
    assert holding.next_issue_display_text == 'N˚ 62 printemps 2026'
    # test preview
    issues = holding.prediction_issues_preview(13)
    assert issues[-1]['issue'] == 'N˚ 74 printemps 2032'


def test_patterns_bimonthly_every_two_months_one_level(
        holding_lib_martigny_w_patterns,
        pattern_bimonthly_every_two_months_one_level_data):
    """Test pattern quarterly_two_levels."""
    holding = holding_lib_martigny_w_patterns
    holding = Holding.get_record_by_pid(holding.pid)
    holding['patterns'] = \
        pattern_bimonthly_every_two_months_one_level_data['patterns']
    # test first issue
    assert holding.next_issue_display_text == '47 jan./fév. 2020'
    holding.increment_next_prediction()
    assert holding.next_issue_display_text == '48 mars/avril 2020'
    for r in range(25):
        holding.increment_next_prediction()
    assert holding.next_issue_display_text == '73 mai/juin 2024'
    # test preview
    issues = holding.prediction_issues_preview(13)
    assert issues[-1]['issue'] == '85 mai/juin 2026'


def test_patterns_half_yearly_two_levels(
        holding_lib_martigny_w_patterns,
        pattern_half_yearly_two_levels_data):
    """Test pattern half_yearly_two_levels."""
    holding = holding_lib_martigny_w_patterns
    holding = Holding.get_record_by_pid(holding.pid)
    holding['patterns'] = \
        pattern_half_yearly_two_levels_data['patterns']
    # test first issue
    assert holding.next_issue_display_text == 'Année 30 no 84 June 2020'
    holding.increment_next_prediction()
    assert holding.next_issue_display_text == 'Année 30 no 85 Dec. 2020'
    for r in range(25):
        holding.increment_next_prediction()
    assert holding.next_issue_display_text == 'Année 43 no 110 June 2033'
    # test preview
    issues = holding.prediction_issues_preview(13)
    assert issues[-1]['issue'] == 'Année 49 no 122 June 2039'


def test_bimonthly_every_two_months_two_levels(
        holding_lib_martigny_w_patterns,
        pattern_bimonthly_every_two_months_two_levels_data):
    """Test pattern bimonthly_every_two_months_two_levels."""
    holding = holding_lib_martigny_w_patterns
    holding = Holding.get_record_by_pid(holding.pid)
    holding['patterns'] = \
        pattern_bimonthly_every_two_months_two_levels_data['patterns']
    # test first issue
    assert holding.next_issue_display_text == 'Jg 51 Nr 1 Jan. 2020'
    holding.increment_next_prediction()
    assert holding.next_issue_display_text == 'Jg 51 Nr 2 März 2020'
    for r in range(25):
        holding.increment_next_prediction()
    assert holding.next_issue_display_text == 'Jg 55 Nr 3 Mai 2024'
    # test preview
    issues = holding.prediction_issues_preview(13)
    assert issues[-1]['issue'] == 'Jg 57 Nr 3 Mai 2026'


def test_holding_validate_next_expected_date(
        client, librarian_martigny,
        journal, loc_public_sion, item_type_internal_sion, document,
        pattern_yearly_two_times_data, json_header,
        holding_lib_sion_w_patterns_data):
    """Test create holding with regular frequency and missing

    the next_expected_date.
    """
    login_user_via_session(client, librarian_martigny.user)
    holding = holding_lib_sion_w_patterns_data
    holding['holdings_type'] = 'serial'
    holding['patterns'] = \
        pattern_yearly_two_times_data['patterns']
    del holding['pid']
    del holding['patterns']['next_expected_date']
    # test will fail when the serial holding has no field
    # next_expected_date for the regular frequency
    with pytest.raises(ValidationError):
        Holding.create(
            data=holding,
            delete_pid=False,
            dbcommit=True,
            reindex=True)


def test_intervals_and_expected_dates(holding_lib_martigny_w_patterns):
    """Test expected dates and intervals for holdings patterns."""
    holding = holding_lib_martigny_w_patterns
    patterns = {
      'template': '{{first_chronology.level_1}}',
      'next_expected_date': '2020-01-05',
      'values': [
        {
          'name': 'first_chronology',
          'levels': [
            {
              'number_name': 'level_1',
              'starting_value': 1
            }
          ]
        }
      ]
    }
    holding['patterns'] = patterns

    def update_pattern(holding, frequency):
        """update holdings patterns with a new frequency."""
        holding['patterns']['frequency'] = frequency
        holding.update(holding, dbcommit=True, reindex=True)

    # test daily pattern
    update_pattern(holding, 'rdafr:1001')
    issues = holding.prediction_issues_preview(13)
    previous_expected_date = None
    for issue in issues:
        expected_date = datetime.strptime(
            issue.get('expected_date'), '%Y-%m-%d')
        if previous_expected_date:
            interval = expected_date - previous_expected_date
            assert divmod(interval.days, 1)[0] == 1
        previous_expected_date = expected_date

    # test three times a week pattern
    update_pattern(holding, 'rdafr:1002')
    issues = holding.prediction_issues_preview(13)
    previous_expected_date = None
    for issue in issues:
        expected_date = datetime.strptime(
            issue.get('expected_date'), '%Y-%m-%d')
        if previous_expected_date:
            interval = expected_date - previous_expected_date
            assert divmod(interval.days, 1)[0] == 2
        previous_expected_date = expected_date

    # test Biweekly pattern
    update_pattern(holding, 'rdafr:1003')
    issues = holding.prediction_issues_preview(13)
    previous_expected_date = None
    for issue in issues:
        expected_date = datetime.strptime(
            issue.get('expected_date'), '%Y-%m-%d')
        if previous_expected_date:
            interval = expected_date - previous_expected_date
            assert divmod(interval.days, 1)[0] == 14
        previous_expected_date = expected_date

    # test Weekly pattern
    update_pattern(holding, 'rdafr:1004')
    issues = holding.prediction_issues_preview(13)
    previous_expected_date = None
    for issue in issues:
        expected_date = datetime.strptime(
            issue.get('expected_date'), '%Y-%m-%d')
        if previous_expected_date:
            interval = expected_date - previous_expected_date
            assert divmod(interval.days, 1)[0] == 7
        previous_expected_date = expected_date

    # test Semiweekly pattern
    update_pattern(holding, 'rdafr:1005')
    issues = holding.prediction_issues_preview(13)
    previous_expected_date = None
    for issue in issues:
        expected_date = datetime.strptime(
            issue.get('expected_date'), '%Y-%m-%d')
        if previous_expected_date:
            interval = expected_date - previous_expected_date
            assert 3 <= divmod(interval.days, 1)[0] <= 4
        previous_expected_date = expected_date

    # test Three times a month pattern
    update_pattern(holding, 'rdafr:1006')
    issues = holding.prediction_issues_preview(13)
    previous_expected_date = None
    for issue in issues:
        expected_date = datetime.strptime(
            issue.get('expected_date'), '%Y-%m-%d')
        if previous_expected_date:
            interval = expected_date - previous_expected_date
            assert 11 > divmod(interval.days, 1)[0] > 7
        previous_expected_date = expected_date

    # test Bimonthly pattern
    update_pattern(holding, 'rdafr:1007')
    issues = holding.prediction_issues_preview(13)
    previous_expected_date = None
    for issue in issues:
        expected_date = datetime.strptime(
            issue.get('expected_date'), '%Y-%m-%d')
        if previous_expected_date:
            interval = expected_date - previous_expected_date
            assert 57 < divmod(interval.days, 1)[0] <= 62
        previous_expected_date = expected_date

    # test Monthly pattern
    update_pattern(holding, 'rdafr:1008')
    issues = holding.prediction_issues_preview(13)
    previous_expected_date = None
    for issue in issues:
        expected_date = datetime.strptime(
            issue.get('expected_date'), '%Y-%m-%d')
        if previous_expected_date:
            interval = expected_date - previous_expected_date
            assert 27 < divmod(interval.days, 1)[0] < 32
        previous_expected_date = expected_date

    # test Semimonthly pattern
    update_pattern(holding, 'rdafr:1009')
    issues = holding.prediction_issues_preview(13)
    previous_expected_date = None
    for issue in issues:
        expected_date = datetime.strptime(
            issue.get('expected_date'), '%Y-%m-%d')
        if previous_expected_date:
            interval = expected_date - previous_expected_date
            assert 13 < divmod(interval.days, 1)[0] < 16
        previous_expected_date = expected_date

    # test Quarterly pattern
    update_pattern(holding, 'rdafr:1010')
    issues = holding.prediction_issues_preview(13)
    previous_expected_date = None
    for issue in issues:
        expected_date = datetime.strptime(
            issue.get('expected_date'), '%Y-%m-%d')
        if previous_expected_date:
            interval = expected_date - previous_expected_date
            assert 84 < divmod(interval.days, 1)[0] < 94
        previous_expected_date = expected_date

    # test Three times a year pattern
    update_pattern(holding, 'rdafr:1011')
    issues = holding.prediction_issues_preview(13)
    previous_expected_date = None
    for issue in issues:
        expected_date = datetime.strptime(
            issue.get('expected_date'), '%Y-%m-%d')
        if previous_expected_date:
            interval = expected_date - previous_expected_date
            assert 112 < divmod(interval.days, 1)[0] < 125
        previous_expected_date = expected_date

    # test Semiannual pattern
    update_pattern(holding, 'rdafr:1012')
    issues = holding.prediction_issues_preview(13)
    previous_expected_date = None
    for issue in issues:
        expected_date = datetime.strptime(
            issue.get('expected_date'), '%Y-%m-%d')
        if previous_expected_date:
            interval = expected_date - previous_expected_date
            assert 177 < divmod(interval.days, 1)[0] < 207
        previous_expected_date = expected_date

    # test annual pattern
    update_pattern(holding, 'rdafr:1013')
    issues = holding.prediction_issues_preview(13)
    previous_expected_date = None
    for issue in issues:
        expected_date = datetime.strptime(
            issue.get('expected_date'), '%Y-%m-%d')
        if previous_expected_date:
            interval = expected_date - previous_expected_date
            assert 364 <= divmod(interval.days, 1)[0] <= 366
        previous_expected_date = expected_date

    # test Biennial pattern
    update_pattern(holding, 'rdafr:1014')
    issues = holding.prediction_issues_preview(13)
    previous_expected_date = None
    for issue in issues:
        expected_date = datetime.strptime(
            issue.get('expected_date'), '%Y-%m-%d')
        if previous_expected_date:
            interval = expected_date - previous_expected_date
            assert 725 < divmod(interval.days, 1)[0] < 733
        previous_expected_date = expected_date

    # test Triennial pattern
    update_pattern(holding, 'rdafr:1015')
    issues = holding.prediction_issues_preview(13)
    previous_expected_date = None
    for issue in issues:
        expected_date = datetime.strptime(
            issue.get('expected_date'), '%Y-%m-%d')
        if previous_expected_date:
            interval = expected_date - previous_expected_date
            assert 1092 < divmod(interval.days, 1)[0] < 1099
        previous_expected_date = expected_date


def test_regular_issue_creation_update_delete_api(
        client, holding_lib_martigny_w_patterns, loc_public_martigny,
        lib_martigny):
    """Test create, update and delete of a regular issue API."""
    holding = holding_lib_martigny_w_patterns
    issue_display, expected_date = holding._get_next_issue_display_text(
                        holding.get('patterns'))
    issue = holding.receive_regular_issue(dbcommit=True, reindex=True)
    item = deepcopy(issue)
    item['issue']['status'] = ItemIssueStatus.DELETED
    issue.update(data=item, dbcommit=True, reindex=True)
    created_issue = Item.get_record_by_pid(issue.pid)
    assert created_issue.get('issue').get('status') == ItemIssueStatus.DELETED
    # Unable to delete a regular issue
    with pytest.raises(IlsRecordError.NotDeleted):
        created_issue.delete(dbcommit=True, delindex=True)

    # no errors when deleting an irregular issue
    pid = created_issue.pid
    created_issue.get('issue')['regular'] = False
    created_issue.delete(dbcommit=True, delindex=True)
    assert not Item.get_record_by_pid(pid)


def test_holding_notes(client, librarian_martigny,
                       holding_lib_martigny_w_patterns, json_header):
    """Test holdings notes."""

    holding = holding_lib_martigny_w_patterns
    login_user_via_session(client, librarian_martigny.user)

    # holdings has only on general note
    assert len(holding.notes) == 1

    # add other note types
    holding['notes'] = [
        {'type': HoldingNoteTypes.STAFF, 'content': 'Staff note'},
        {'type': HoldingNoteTypes.CLAIM, 'content': 'Claim note'}
    ]
    holding.update(holding, dbcommit=True, reindex=True)
    assert len(holding.notes) == 2

    # will receive a validation error if tries to add a note type already exist
    holding['notes'].append(
        {'type': HoldingNoteTypes.CLAIM, 'content': 'new cliam note'}
    )
    with pytest.raises(ValidationError):
        holding.update(holding, dbcommit=True, reindex=True)
    holding['notes'] = holding.notes[:-1]

    # get a specific type of notes
    #  --> staff : should return a note
    #  --> routing : should return nothing
    #  --> dummy : should never return something !
    assert holding.get_note(HoldingNoteTypes.STAFF)
    assert holding.get_note(HoldingNoteTypes.ROUTING) is None
    assert holding.get_note('dummy') is None
