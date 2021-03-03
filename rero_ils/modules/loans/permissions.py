# -*- coding: utf-8 -*-
#
# RERO ILS
# Copyright (C) 2020 RERO
# Copyright (C) 2020 UCLouvain
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

"""Permissions for loans."""
from flask_babelex import gettext as _

from rero_ils.modules.loans.api import Loan, count_any_loans_by_patron_pid
from rero_ils.modules.organisations.api import current_organisation
from rero_ils.modules.patrons.api import current_patron
from rero_ils.modules.permissions import AbstractCondition, RecordPermission


class LoanPermission(RecordPermission):
    """Loan permissions."""

    @classmethod
    def list(cls, user, record=None):
        """List permission check.

        :param user: Logged user.
        :param record: Record to check.
        :return: True is action can be done.
        """
        # user must be authenticated
        return bool(current_patron)

    @classmethod
    def read(cls, user, record):
        """Read permission check.

        :param user: Logged user.
        :param record: Record to check.
        :return: True is action can be done.
        """
        # Read is denied for to_anonymize loans.
        if record.get('to_anonymize'):
            return False
        if current_patron \
           and current_organisation.pid == Loan(record).organisation_pid:
            # staff member (lib, sys_lib) can always read loans
            if current_patron.is_librarian:
                return True
            # patron can only read their own loans
            if current_patron.is_patron:
                return Loan(record).patron_pid == current_patron.pid
        return False

    @classmethod
    def create(cls, user, record=None):
        """Create permission check.

        :param user: Logged user.
        :param record: Record to check.
        :return: True is action can be done.
        """
        # deny all
        return False

    @classmethod
    def update(cls, user, record):
        """Update permission check.

        :param user: Logged user.
        :param record: Record to check.
        :return: True is action can be done.
        """
        # deny all
        return False

    @classmethod
    def delete(cls, user, record):
        """Delete permission check.

        :param user: Logged user.
        :param record: Record to check.
        :return: True if action can be done.
        """
        # deny all
        return False


# =============================================================================
# CONDITIONS
# =============================================================================

class PendingLoansCondition(AbstractCondition):
    """Condition class to check if a patron has some current pending loans."""

    message = _('Patron has open loans')

    def can(self, patron):
        """Check if the condition is validated.

        :return True if the condition is validate, False otherwise.
        """
        if patron:
            return count_any_loans_by_patron_pid(patron.pid) == 0
        return True
