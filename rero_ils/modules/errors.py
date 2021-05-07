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

"""Errors for circulation policy module."""

from __future__ import absolute_import, print_function

from invenio_records.errors import RecordsError


class OrganisationDoesNotExist(RecordsError):
    """Error raised when organisation record doest not exist."""


class PolicyNameAlreadyExists(RecordsError):
    """Error raised when the name of the new policy record exists."""


class InvalidRecordID(RecordsError):
    """Error raised when the ID of record is invalid."""


class MissingRequiredParameterError(RecordsError):
    """Exception raised when required parameter is missing."""


class RegularReceiveNotAllowed(Exception):
    """Holdings of type serials and irregular frequency."""


class NoCirculationAction(RecordsError):
    """Exception raised when no circulation action is performed."""


class NoCirculationActionIsPermitted(RecordsError):
    """Exception raised when the circulation action is not forbidden."""
