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

"""Permissions for Patron transaction."""

from flask_babelex import gettext as _

from rero_ils.modules.organisations.api import current_organisation
from rero_ils.modules.patron_transactions.api import PatronTransaction
from rero_ils.modules.patrons.api import current_patron, current_user
from rero_ils.modules.permissions import AbstractCondition, RecordPermission


class PatronTransactionPermission(RecordPermission):
    """Patron transaction permissions."""

    @classmethod
    def list(cls, user, record=None):
        """List permission check.

        :param user: Logged user.
        :param record: Record to check
        :return: True is action can be done.
        """
        # user should be authenticated
        return current_user and current_user.is_authenticated

    @classmethod
    def read(cls, user, record):
        """Read permission check.

        :param user: Logged user.
        :param record: Record to check.
        :return: True is action can be done.
        """
        # user should be authenticated
        if not current_patron:
            return False
        #  For staff users (lib, sys_lib), they can read only their own
        #  organisation.
        if current_patron.is_librarian:
            return current_organisation['pid'] == record.organisation_pid
        # For other people (patron), they can read only their own transaction
        else:
            return current_patron.pid == record.patron_pid

    @classmethod
    def create(cls, user, record=None):
        """Create permission check.

        :param user: Logged user.
        :param record: Record to check.
        :return: True is action can be done.
        """
        # user should be authenticated
        if not current_patron:
            return False
        if not record:
            return True
        else:
            # Same as update
            return cls.update(user, record)

    @classmethod
    def update(cls, user, record):
        """Update permission check.

        :param user: Logged user.
        :param record: Record to check.
        :return: True is action can be done.
        """
        # only staff members (lib, sys_lib) can update acq_account
        # record cannot be null
        if not current_patron or not current_patron.is_librarian or not record:
            return False
        return current_organisation['pid'] == record.organisation_pid

    @classmethod
    def delete(cls, user, record):
        """Delete permission check.

        :param user: Logged user.
        :param record: Record to check.
        :return: True if action can be done.
        """
        # Same as update
        return cls.update(user, record)


# =============================================================================
# CONDITIONS
# =============================================================================

class OpenTransactionCondition(AbstractCondition):
    """Condition class to check if a patron has current open transactions."""

    message = _('Patron has open transactions')

    def can(self, patron):
        """Check if the condition is validated.

        :return True if the condition is validate, False otherwise.
        """
        if patron:
            return PatronTransaction.get_transactions_count_for_patron(
                   patron.pid, status='open') == 0
        return True
