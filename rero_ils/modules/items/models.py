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

"""Define relation between records and buckets."""

from __future__ import absolute_import

from invenio_db import db
from invenio_pidstore.models import RecordIdentifier
from invenio_records.models import RecordMetadataBase


class ItemIdentifier(RecordIdentifier):
    """Sequence generator for Item identifiers."""

    __tablename__ = 'item_id'
    __mapper_args__ = {'concrete': True}

    recid = db.Column(
        db.BigInteger().with_variant(db.Integer, 'sqlite'),
        primary_key=True,
        autoincrement=True,
    )


class ItemMetadata(db.Model, RecordMetadataBase):
    """Item record metadata."""

    __tablename__ = 'item_metadata'


class ItemStatus:
    """Class holding all availabe circulation item statuses."""

    ON_SHELF = 'on_shelf'
    AT_DESK = 'at_desk'
    ON_LOAN = 'on_loan'
    IN_TRANSIT = 'in_transit'
    EXCLUDED = 'excluded'
    MISSING = 'missing'


class ItemIssueStatus:
    """Enum class to list all possible status of an issue item."""

    RECEIVED = 'received'
    CLAIMED = 'claimed'
    DELETED = 'deleted'
    LATE = 'late'


class ItemCirculationAction:
    """Enum class to list all possible action about an item."""

    CHECKOUT = 'checkout'
    CHECKIN = 'checkin'
    REQUEST = 'request'
    EXTEND = 'extend'


class ItemNoteTypes:
    """Class to list all possible note types."""

    ACQUISITION = 'acquisition_note'
    BINDING = 'binding_note'
    CHECKIN = 'checkin_note'
    CHECKOUT = 'checkout_note'
    CONDITION = 'condition_note'
    GENERAL = 'general_note'
    PATRIMONIAL = 'patrimonial_note'
    PROVENANCE = 'provenance_note'
    STAFF = 'staff_note'

    PUBLIC = [
        GENERAL,
        BINDING,
        PROVENANCE,
        CONDITION,
        PATRIMONIAL
    ]

    INVENTORY_LIST_CATEGORY = [
        GENERAL,
        STAFF,
        CHECKIN,
        CHECKOUT
    ]
