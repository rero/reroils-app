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


class HoldingIdentifier(RecordIdentifier):
    """Sequence generator for holdings identifiers."""

    __tablename__ = 'holding_id'
    __mapper_args__ = {'concrete': True}

    recid = db.Column(
        db.BigInteger().with_variant(db.Integer, 'sqlite'),
        primary_key=True, autoincrement=True,
    )


class HoldingMetadata(db.Model, RecordMetadataBase):
    """Holding record metadata."""

    __tablename__ = 'holding_metadata'


class HoldingTypes:
    """Class to list all possible holding types."""

    ELECTRONIC = 'electronic'
    SERIAL = 'serial'
    STANDARD = 'standard'


class HoldingNoteTypes:
    """Class to list all holdings possible note types."""

    GENERAL = 'general_note'
    STAFF = 'staff_note'
    CONSERVATION = 'conservation_note'
    RECEPTION = 'reception_note'
    CLAIM = 'claim_note'
    ROUTING = 'routing_note'
    BINDING = 'binding_note'
    ACQUISITION = 'acquisition_note'

    # TODO: Add any of the above items to the array
    # to display them on the interface
    PUBLIC = [
    ]
