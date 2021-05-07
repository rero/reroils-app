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

"""API for manipulating the item issue."""

from datetime import datetime, timezone

import ciso8601
from flask import current_app

from .record import ItemRecord
from ..models import ItemIssueStatus, TypeOfItem


class ItemIssue(ItemRecord):
    """Item issue class."""

    @property
    def is_issue(self):
        """Is this item is an issue or not."""
        return self.get('type') == TypeOfItem.ISSUE

    @property
    def expected_date(self):
        """Shortcut for issue expected date."""
        return self.get('issue', {}).get('expected_date')

    @property
    def received_date(self):
        """Shortcut for issue received date."""
        return self.get('issue', {}).get('received_date')

    @property
    def issue_status(self):
        """Shortcut for issue status."""
        return self.get('issue', {}).get('status')

    @property
    def issue_is_regular(self):
        """Shortcut for issue is regular."""
        return self.get('issue', {}).get('regular', True)

    @property
    def issue_status_date(self):
        """Shortcut for issue status date."""
        return self.get('issue', {}).get('status_date')

    @property
    def claims_count(self):
        """Shortcut for the issue claims_count."""
        return self.get('issue', {}).get('claims_count', 0)

    @claims_count.setter
    def claims_count(self, claims_count):
        self.setdefault('issue', {}).setdefault('claims_count', 0)
        self['issue']['claims_count'] = claims_count

    @property
    def vendor_pid(self):
        """Shortcut for vendor pid if exists."""
        from ...holdings.api import Holding
        if self.holding_pid:
            holding = Holding.get_record_by_pid(self.holding_pid)
            vendor = holding.vendor
            if vendor:
                return vendor.pid

    @classmethod
    def get_issues_pids_by_status(cls, issue_status, holdings_pid=None):
        """Return issues pids by status optionally filtered by holdings_pid.

        :param holdings_pid: the holdings pid. If none, return all late issues.
        :param issue_status: the issue status.
        :return a generator of issues pid.
        """
        from . import ItemsSearch
        query = ItemsSearch() \
            .filter('term', issue__status=issue_status) \
            .filter('term', type='issue')
        if holdings_pid:
            query = query.filter('term', holding__pid=holdings_pid)
        results = query\
            .params(preserve_order=True) \
            .sort({'_created': {'order': 'asc'}}) \
            .source(['pid']).scan()
        for hit in results:
            yield hit.pid

    @classmethod
    def get_issues_by_status(cls, issue_status, holdings_pid=None):
        """Return all issues by status optionally filtered for a holdings pid.

        :param holdings_pid: the holdings pid. If none, return all late issues.
        :return a generator of Item.
        """
        from . import Item
        for pid in cls.get_issues_pids_by_status(
                issue_status, holdings_pid=holdings_pid):
            yield Item.get_record_by_pid(pid)

    @classmethod
    def get_late_serial_holdings_pids(cls):
        """Return pids for all late holdings.

        The holdings is considered late if :
          * it is of type serial
          * it is considerate as alive (acq_status='currently_received')
          * next expected date has passed (greater than current datetime).

        :return a generator of holdings pid.
        """
        from ...holdings.api import HoldingsSearch
        today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
        results = HoldingsSearch() \
            .filter('term', holdings_type='serial') \
            .filter('term', acquisition_status='currently_received') \
            .filter('range', patterns__next_expected_date={'lte': today}) \
            .params(preserve_order=True) \
            .sort({'_created': {'order': 'asc'}}) \
            .source(['pid']).scan()
        for hit in results:
            yield hit.pid

    @classmethod
    def receive_next_late_expected_issues(cls, dbcommit=False, reindex=False):
        """Receive the next late expected issue for all holdings.

        :param reindex: reindex record by record.
        :param dbcommit: commit record to database.

        :return a count of created issues.
        """
        from ...holdings.api import Holding
        created_issues = 0
        pids = cls.get_late_serial_holdings_pids()
        for pid in pids:
            try:
                holding = Holding.get_record_by_pid(pid)
                issue = holding.receive_regular_issue(
                    dbcommit=dbcommit, reindex=reindex)
                issue['issue']['status'] = ItemIssueStatus.LATE
                issue.update(issue, dbcommit=dbcommit, reindex=reindex)
                created_issues += 1
            except Exception:
                current_app.logger.error(
                    'Can not receive next late expected issue for serial '
                    f'holding: {pid}'
                )
        return created_issues

    @classmethod
    def _process_issue_claim(
            cls, issue, claims_count, claims_days, modified_issues,
            dbcommit=False, reindex=False):
        """Process issue for a new claim.

        :param issue: the issue item record.
        :param claims_days: claims days parameter to compare with issue age.
        :param modified_issues: counter to count modified issues.
        :param reindex: reindex the records.
        :param dbcommit: commit record to database.
        :param claims_count: current claim count for this issue.

        :return a count of modified issues.
        """
        days = cls._get_issue_status_age(issue)
        if days >= claims_days:
            cls._update_issue_status_claims_count(
                issue, claims_count,
                dbcommit=dbcommit, reindex=reindex)
            modified_issues += 1
        return modified_issues

    @classmethod
    def _get_issue_status_age(cls, issue):
        """Return the age of an issue.

        It compares the issue status date with the current timestamp

        :param issue: the issue item record.
        :return the issue status age in days.
        """
        issue_status_date = ciso8601.parse_datetime(
            issue.issue_status_date)
        return (datetime.now(timezone.utc) - issue_status_date).days

    @classmethod
    def _update_issue_status_claims_count(
            cls, issue, claims_count, dbcommit=False,
            reindex=False):
        """Update issue status and claims count.

        It compares the issue status date with the current timestamp

        :param issue: the issue item record.
        :param claims_count: the current claims_count from the issue.
        :param reindex: reindex the records.
        :param dbcommit: commit record to database.
        """
        issue['issue']['status'] = ItemIssueStatus.CLAIMED
        issue.claims_count += 1
        issue = issue.update(
            issue, dbcommit=dbcommit, reindex=reindex)

    @classmethod
    def create_first_and_next_claims(
            cls, claim_type=None, dbcommit=False, reindex=False):
        """Claim the late and claimed issues for all holdings.

        :param claim_type: if first, it creates the first claim for the late
        issues. if value is next, it creates the next claim for the claimed
        issues.
        :param reindex: reindex the records.
        :param dbcommit: commit record to database.

        :return a count of modified issues.
        """
        from ...holdings.api import Holding

        modified_issues = 0
        issues = []

        if claim_type == 'first':
            issue_status = ItemIssueStatus.LATE
        elif claim_type == 'next':
            issue_status = ItemIssueStatus.CLAIMED
        if issue_status:
            issues = cls.get_issues_by_status(issue_status=issue_status)

        for issue in issues:
            try:
                email = None
                holding = Holding.get_record_by_pid(issue.holding_pid)
                vendor = holding.vendor
                if vendor:
                    email = vendor.order_email
                max_number_of_claims = holding.max_number_of_claims
                if email and max_number_of_claims and \
                        max_number_of_claims > issue.claims_count:
                    if issue.claims_count == 0 and \
                            holding.days_before_first_claim:
                        claims_days = holding.days_before_first_claim
                    elif issue.claims_count and holding.days_before_next_claim:
                        claims_days = holding.days_before_next_claim
                    modified_issues = cls._process_issue_claim(
                        issue=issue,
                        claims_count=issue.claims_count,
                        claims_days=claims_days,
                        modified_issues=modified_issues,
                        dbcommit=dbcommit,
                        reindex=reindex
                    )
            except Exception:
                current_app.logger.error(
                    f'Can not create {claim_type} claim for issue: {issue.pid}'
                )
        return modified_issues
