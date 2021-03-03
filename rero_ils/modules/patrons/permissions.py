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

"""Permissions for patrons."""
from flask import current_app, request

from rero_ils.modules.organisations.api import current_organisation
from rero_ils.modules.permissions import ALLOW, DENY, AbstractCondition, \
    RecordPermission

from .api import Patron, current_patron


class PatronPermission(RecordPermission):
    """Patrons permissions."""

    @classmethod
    def list(cls, user, record=None):
        """List permission check.

        :param user: Logged user.
        :param record: Record to check.
        :return: True is action can be done.
        """
        # All staff members (lib, sys_lib) can list patrons
        return current_patron and current_patron.is_librarian

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
        # only staff members (lib, sys_lib) are allowed to read an organisation
        if not current_patron.is_librarian:
            return False
        # For staff users, they can read only their own organisation.
        return current_organisation['pid'] == record.organisation_pid

    @classmethod
    def create(cls, user, record=None):
        """Create permission check.

        :param user: Logged user.
        :param record: pre-existing Record to check.
        :return: True is action can be done.
        """
        incoming_record = request.get_json(silent=True) or {}
        return cls.can_create(user, record, incoming_record)

    @classmethod
    def can_create(cls, user, record, incoming_record):
        """Create permission check.

        :param user: Logged user.
        :param record: pre-existing Record to check.
        :param record: new incoming Record data.
        :return: True is action can be done.
        """
        # only staff members (lib, sys_lib) can create patrons ...
        if not current_patron or not current_patron.is_librarian:
            return False
        # ... only for its own organisation
        if record:
            if current_organisation['pid'] == record.organisation_pid:
                # sys_lib can manage all kind of patron
                if current_patron.is_system_librarian:
                    return True
                # librarian user has some restrictions...
                if current_patron.is_librarian:
                    # a librarian cannot manage a system_librarian patron
                    if 'system_librarian' in incoming_record.get('roles', [])\
                       or 'system_librarian' in record.get('roles', []):
                        return False
                    # a librarian can only manage other librarian from its own
                    # library
                    if current_patron.library_pids and record.library_pid and\
                       record.library_pid not in current_patron.library_pids:
                        return False
                    return True
            return False
        return True

    @classmethod
    def update(cls, user, record):
        """Update permission check.

        :param user: Logged user.
        :param record: Record to check.
        :return: True is action can be done.
        """
        if not record:
            return False
        return cls.create(user, record)

    @classmethod
    def delete(cls, user, record):
        """Delete permission check.

        :param user: Logged user.
        :param record: Record to check.
        :return: True if action can be done.
        """
        if not record:
            return False
        # It should be not possible to remove itself
        if current_patron and record.pid == current_patron.pid:
            return False
        return cls.create(user, record)


def get_allowed_roles_management(patron_pid=None):
    """Get the roles that current logged user could manage.

    :param patron_pid: the patron pid to check
    :return An array of allowed role management.
    """
    allowed_roles = []
    patron = Patron.get_record_by_pid(patron_pid) if patron_pid else None
    restrictions = current_app.config.get('ROLES_MANAGEMENT_PERMISSIONS', {})
    for role in Patron.ALL_ROLES:
        # by default, all operations are allowed
        data = {
            'name': role,
            'permissions': {
                'add': {'can': ALLOW},
                'delete': {'can': ALLOW}
            }
        }
        # check about role management restrictions to know if one action should
        # be denied + reasons
        for name, conditions in restrictions.get(role, {}).items():
            reasons = [condition.message for condition in conditions
                       if not condition.can(patron)]
            # If reasons array isn't empty, the action is denied
            if reasons:
                data['permissions'][name]['can'] = DENY
                data['permissions'][name]['reasons'] = reasons
        allowed_roles.append(data)
    return allowed_roles


# =============================================================================
# CONDITIONS
# =============================================================================

class StaffMemberCondition(AbstractCondition):
    """Condition class to check if the current patron is a staff member.

    To be considerate as a staff member the patron should have one of the
    role defined into Patron.STAFF_MEMBERS_ROLE.
    """

    def can(self, *args, **kwargs):
        """Check if the condition is validated.

        :return True if the condition is validate, False otherwise.
        """
        if current_patron:
            return any(role in Patron.STAFF_MEMBER_ROLES
                       for role in current_patron.get('roles', []))
        return False


class SystemLibrarianCondition(AbstractCondition):
    """Condition class to check if the current patron is a system librarian."""

    def can(self, *args, **kwargs):
        """Check if the condition is validated.

        :return True if the condition is validate, False otherwise.
        """
        if current_patron:
            return Patron.ROLE_SYSTEM_LIBRARIAN in \
                   current_patron.get('roles', [])
        return False
