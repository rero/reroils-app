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

"""API for manipulating item records."""
from datetime import datetime, timezone

import pytz
from elasticsearch_dsl.query import Q
from flask_babelex import gettext as _

from ..utils import item_pid_to_object
from ...api import IlsRecord
from ...holdings.models import HoldingTypes
from ...item_types.api import ItemType
from ...libraries.api import Library
from ...locations.api import Location
from ...organisations.api import Organisation
from ...utils import date_string_to_utc, extracted_data_from_ref, \
    generate_item_barcode, get_base_url, get_ref_for_pid, \
    trim_item_barcode_for_record


class ItemRecord(IlsRecord):
    """Item record class."""

    def extended_validation(self, **kwargs):
        """Add additional record validation.

        Ensures that item of type issue is created only on
        holdings of type serials.

        Ensures that item of type issue has the issue field.
        Ensures that item of type issue has the enumAndChrono field required.

        Ensures that standard item has no issue field.

        Ensures that only one note of each type is present.

        :return: False if
            - holdings type is not journal and item type is issue.
            - item type is journal and field issue exists.
            - item type is standard and field issue does not exists.
            - if notes array has multiple notes with same type
            - `temporary_item_type` has same value than `item_type`
            - temporary_item_type isn't in the future (if specified)

        """
        from ...holdings.api import Holding
        holding_pid = extracted_data_from_ref(self.get('holding').get('$ref'))
        holding = Holding.get_record_by_pid(holding_pid)
        if not holding:
            return _('Holding does not exist: {pid}.'.format(pid=holding_pid))
        is_serial = holding.holdings_type == 'serial'
        issue = self.get('issue', {})
        if issue and self.get('type') == 'standard':
            return _('Standard item can not have a issue field.')
        if self.get('type') == 'issue':
            if not issue:
                return _('Issue item must have an issue field.')
            if not self.get('enumerationAndChronology'):
                return _('enumerationAndChronology field is required '
                         'for an issue item')
        note_types = [note.get('type') for note in self.get('notes', [])]
        if len(note_types) != len(set(note_types)):
            return _('Can not have multiple notes of same type.')

        # check temporary item type data
        tmp_itty = self.get('temporary_item_type')
        if tmp_itty:
            if tmp_itty['$ref'] == self['item_type']['$ref']:
                return _('Temporary circulation category cannot be the same '
                         'than default circulation category.')
            if tmp_itty.get('end_date'):
                end_date = date_string_to_utc(tmp_itty.get('end_date'))
                if end_date <= pytz.utc.localize(datetime.now()):
                    return _('Temporary circulation category end date must be '
                             'a date in the future.')

        return True

    @classmethod
    def create(cls, data, id_=None, delete_pid=False,
               dbcommit=False, reindex=False, **kwargs):
        """Create item record."""
        cls._item_build_org_ref(data)
        data = cls._prepare_item_record(data=data, mode='create')
        record = super().create(
            data, id_, delete_pid, dbcommit, reindex, **kwargs)
        holding = cls._increment_next_prediction_for_holding(
            record, dbcommit=dbcommit, reindex=reindex)
        # As we potentially update the parent holding when we create an issue
        # item, we need to commit this holding even if `dbcommit` iss set to
        # false. Without this commit, only the current (Item) resource will be
        # committed by `invenio-records` and the holding changes will be lost.
        #
        # If `dbcommit` is already set to True, this commit is already done by
        # the `IlsRecord.update()` function.
        #
        # /!\ if we write some other operation after _increement_next_predition
        #     we need to manage ourself the `rollback()`.
        #
        # TODO :: best solution will be to create an invenio `post_create`
        #         extension for the Item resource.
        # https://invenio-records.readthedocs.io/en/latest/api.html#module-invenio_records.extensions
        if not dbcommit and holding:
            holding.commit()
        return record

    def update(self, data, dbcommit=False, reindex=False):
        """Update an item record.

        :param data: The record to update.
        :param dbcommit: boolean to   the record to the database or not.
        :param reindex: boolean to reindex the record or not.
        :return: The updated item record.
        """
        data = self._set_issue_status_date(data)
        data = self._prepare_item_record(data=data, mode='update')
        super().update(data, dbcommit, reindex)
        # TODO: some item updates do not require holding re-linking
        return self

    def replace(self, data, dbcommit=False, reindex=False):
        """Replace an item record.

        :param data: The record to replace.
        :param dbcommit: boolean to commit the record to the database or not.
        :param reindex: boolean to reindex the record or not.
        :return: The replaced item record.
        """
        # update item record with a generated barcode if does not exist
        data = generate_item_barcode(data=data)
        super().replace(data, dbcommit, reindex)
        return self

    @classmethod
    def _set_issue_status_date(cls, data):
        """Set the status date to current timestamp for an issue.

        :param data: The record to update.
        :return: The updated record.
        """
        status = data.get('issue', {}).get('status')
        item = cls.get_record_by_pid(data.get('pid'))
        if status and item and status != item.issue_status:
            data['issue']['status_date'] = \
                datetime.now(timezone.utc).isoformat()
        return data

    @classmethod
    def _increment_next_prediction_for_holding(
            cls, item, dbcommit=False, reindex=False):
        """Increment next issue for items with regular frequencies."""
        from ...holdings.api import Holding
        holding = Holding.get_record_by_pid(item.holding_pid)
        if item.get('type') == 'issue' and \
                item.get('issue', {}).get('regular') and \
                holding.holdings_type == 'serial' and \
                holding.get('patterns') and \
                holding.get('patterns', {}).get('frequency') != 'rdafr:1016':
            updated_holding = holding.increment_next_prediction()
            return holding.update(
                data=updated_holding,
                dbcommit=dbcommit,
                reindex=reindex
            )

    @classmethod
    def _item_build_org_ref(cls, data):
        """Build $ref for the organisation of the item."""
        loc_pid = data.get('location', {}).get('pid')
        if not loc_pid:
            loc_pid = data.get('location').get('$ref').split('locations/')[1]
            org_pid = Location.get_record_by_pid(loc_pid).organisation_pid
        url_api = '{base_url}/api/{doc_type}/{pid}'
        org_ref = {
            '$ref': url_api.format(
                base_url=get_base_url(),
                doc_type='organisations',
                pid=org_pid or cls.organisation_pid)
        }
        data['organisation'] = org_ref

    @classmethod
    def link_item_to_holding(cls, record, mode):
        """Complete the item record.

        Link an item to a standard holding record.
        Only holdings check is made at the update mode.

        :param record: the item record.
        :param mode: update or create mode.
        :return: the updated record with matched holdings record
        """
        from ...holdings.api import Holding, create_holding, \
            get_holding_pid_by_doc_location_item_type

        old_holding_pid = None
        old_holding_type = None
        if record.get('holding'):
            old_holding_pid = extracted_data_from_ref(
                record['holding'], data='pid')
            old_holding_type = Holding.get_holdings_type_by_holding_pid(
                old_holding_pid)

        if (
            mode == 'create' and record.get('holding')) or (
            old_holding_type in [HoldingTypes.SERIAL, HoldingTypes.ELECTRONIC]
        ):
            return record

        # item type is important for linking to the correct holdings type.
        item_record_type = record.get('type', 'standard')

        # get pids from $ref
        document_pid = extracted_data_from_ref(record['document'], data='pid')
        location_pid = extracted_data_from_ref(record['location'], data='pid')
        item_type_pid = extracted_data_from_ref(
            record['item_type'], data='pid')

        holding_pid = get_holding_pid_by_doc_location_item_type(
            document_pid, location_pid, item_type_pid, item_record_type)

        # we will NOT create serial holdings for items
        if not holding_pid and item_record_type != 'serial':
            holdings_record = create_holding(
                document_pid=document_pid,
                location_pid=location_pid,
                item_type_pid=item_type_pid)
            holding_pid = holdings_record.pid

        # update item record with the parent holding record if different
        # from the old holding pid
        if not old_holding_pid or holding_pid != old_holding_pid:
            record['holding'] = {'$ref': get_ref_for_pid(
                'hold',
                holding_pid
            )}
        return record

    @classmethod
    def _prepare_item_record(cls, data, mode):
        """Prepare item data before the creation.

        Trims the barcode.
        Relinks to the correct holdings record.
        Generates a barcode if not given.

        :param data: the item record.
        :param mode: update or create mode.
        :return: the modified record.
        """
        data = trim_item_barcode_for_record(data=data)
        # Since the barcode is a mandatory field, we set it to current
        # timestamp if not given
        data = generate_item_barcode(data=data)
        data = cls.link_item_to_holding(data, mode)
        return data

    @classmethod
    def get_items_pid_by_holding_pid(cls, holding_pid):
        """Returns item pids from holding pid."""
        from . import ItemsSearch
        results = ItemsSearch() \
            .params(preserve_order=True)\
            .filter('term', holding__pid=holding_pid) \
            .sort({'pid': {"order": "asc"}}) \
            .source(['pid']).scan()
        for item in results:
            yield item.pid

    @property
    def holding_pid(self):
        """Shortcut for item holding pid."""
        if self.get('holding'):
            return extracted_data_from_ref(self.get('holding'))

    @property
    def document_pid(self):
        """Shortcut for item document pid."""
        if self.get('document'):
            return extracted_data_from_ref(self.get('document'))

    @classmethod
    def get_document_pid_by_item_pid(cls, item_pid):
        """Returns document pid from item pid."""
        item = cls.get_record_by_pid(item_pid)
        return extracted_data_from_ref(item.get('document'))

    @classmethod
    def get_document_pid_by_item_pid_object(cls, item_pid):
        """Returns document pid from item pid.

        :param item_pid: the item_pid object
        :type item_pid: object
        :return: the document pid
        :rtype: str
        """
        item = cls.get_record_by_pid(item_pid.get('value'))
        return extracted_data_from_ref(item.get('document'))

    @classmethod
    def get_items_pid_by_document_pid(cls, document_pid):
        """Returns item pisd from document pid."""
        from . import ItemsSearch
        results = ItemsSearch()\
            .filter('term', document__pid=document_pid)\
            .source(['pid']).scan()
        for item in results:
            yield item_pid_to_object(item.pid)

    @classmethod
    def get_item_by_barcode(cls, barcode, organisation_pid):
        """Get item by barcode.

        :param barcode: the item barcode.
        :param organisation_pid: the organisation pid. As barcode could be
                                 shared between items from multiple
                                 organisations we need to filter result by
                                 organisation.pid
        :return The item corresponding to the barcode if exists or None.
        """
        from . import ItemsSearch
        results = ItemsSearch()\
            .filter('term', barcode=barcode)\
            .filter('term', organisation__pid=organisation_pid)\
            .source(includes='pid')\
            .scan()
        try:
            return cls.get_record_by_pid(next(results).pid)
        except StopIteration:
            return None

    def get_organisation(self):
        """Shortcut to the organisation of the item location."""
        return self.get_library().get_organisation()

    def get_library(self):
        """Shortcut to the library of the item location."""
        return self.get_location().get_library()

    def get_location(self):
        """Shortcut to the location of the item."""
        location_pid = extracted_data_from_ref(self.get('location'))
        return Location.get_record_by_pid(location_pid)

    @property
    def status(self):
        """Shortcut for item status."""
        return self.get('status', '')

    @property
    def enumerationAndChronology(self):
        """Shortcut for item enumarationAndChronology."""
        return self.get('enumerationAndChronology', '')

    @property
    def item_type_pid(self):
        """Shortcut for item type pid."""
        if self.get('item_type'):
            return extracted_data_from_ref(self.get('item_type'))

    @property
    def temporary_item_type_pid(self):
        """Shortcut for temporary item type pid."""
        tmp_item_type = self.get('temporary_item_type', {})
        if tmp_item_type:
            end_date = tmp_item_type.get('end_date')
            # check if the temporary item_type.end_date is over. If yes, return
            # None
            if end_date:
                now_date = pytz.utc.localize(datetime.now())
                end_date = date_string_to_utc(end_date)
                if now_date > end_date:
                    return None
            return extracted_data_from_ref(tmp_item_type.get('$ref'))

    @property
    def item_type_circulation_category_pid(self):
        """Shortcut to find the best item_type to use for circulation."""
        return self.temporary_item_type_pid or self.item_type_pid

    @property
    def circulation_category(self):
        """Shortcut to find the used circulation category for this item.

        :return the in-used circulation category for this item.
        :rtype rero_ils.modules.item_types.api.ItemType
        """
        return ItemType.get_record_by_pid(
            self.item_type_circulation_category_pid
        )

    @property
    def item_record_type(self):
        """Shortcut for item type, whether a standard or an issue record."""
        return self.get('type')

    @property
    def holding_circulation_category_pid(self):
        """Shortcut for holding circulation category pid of an item."""
        from ...holdings.api import Holding
        circulation_category_pid = None
        if self.holding_pid:
            circulation_category_pid = \
                Holding.get_record_by_pid(
                    self.holding_pid).circulation_category_pid
        return circulation_category_pid

    @property
    def issue_inherited_first_call_number(self):
        """Get issue inherited first call number.

        For item of type issue, when the issue first call number is missing,
        it returns the parent holdings first call number if exists.
        """
        from ...holdings.api import Holding
        if self.get('type') == 'issue' and not self.get('call_number'):
            return Holding.get_record_by_pid(
                self.holding_pid).get('call_number')

    @property
    def location_pid(self):
        """Shortcut for item location pid."""
        if self.get('location'):
            return extracted_data_from_ref(self.get('location'))

    @property
    def holding_location_pid(self):
        """Shortcut for holding location pid of an item."""
        from ...holdings.api import Holding
        location_pid = None
        if self.holding_pid:
            location_pid = Holding.get_record_by_pid(
                self.holding_pid).location_pid
        return location_pid

    @property
    def library_pid(self):
        """Shortcut for item library pid."""
        location = Location.get_record_by_pid(self.location_pid)
        return extracted_data_from_ref(location.get('library'))

    @property
    def holding_library_pid(self):
        """Shortcut for holding library pid of an item."""
        if self.holding_location_pid:
            location = Location.get_record_by_pid(self.holding_location_pid)
            return extracted_data_from_ref(location.get('library'))

    @property
    def organisation_pid(self):
        """Get organisation pid for item."""
        library = Library.get_record_by_pid(self.library_pid)
        return library.organisation_pid

    @property
    def organisation_view(self):
        """Get Organisation view for item."""
        organisation = Organisation.get_record_by_pid(self.organisation_pid)
        return organisation['view_code']

    def get_owning_pickup_location_pid(self):
        """Returns the pickup location for the item owning location.

        :return the pid of the item owning item location.
        """
        library = self.get_library()
        return library.get_pickup_location_pid()

    @property
    def notes(self):
        """Return notes related to this item.

        :return an array of all notes related to the item. Each note should
                have two keys : `type` and `content`.
        """
        return self.get('notes', [])

    def get_note(self, note_type):
        """Return an item note by its type.

        :param note_type: the type of note (see ``ItemNoteTypes``)
        :return the content of the note, None if note type is not found
        """
        notes = [note.get('content') for note in self.notes
                 if note.get('type') == note_type]
        return next(iter(notes), None)

    @property
    def is_new_acquisition(self):
        """Is this item should be considered as a new acquisition.

        :return True if Item is a new acquisition, False otherwise
        """
        acquisition_date = self.get('acquisition_date')
        if acquisition_date:
            return datetime.strptime(
                acquisition_date, '%Y-%m-%d') < datetime.now()
        return False

    @classmethod
    def get_number_masked_items_by_holdings_pid(cls, holding_pid):
        """Returns the number of unmasked items and attached to a holding.

        :param holding_pid: the pid of the holdings.
        :return number of un masked items.
        """
        from . import ItemsSearch
        query = ItemsSearch().filter('term', holding__pid=holding_pid)
        results = query.filter('bool', must_not=[Q('term', _masked=True)]) \
            .source(['pid']).count()
        return results
