# -*- coding: utf-8 -*-
#
# RERO ILS
# Copyright (C) 2019 RERO
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

"""API for manipulating items."""
from datetime import datetime
from functools import partial

from elasticsearch.exceptions import NotFoundError
from invenio_search import current_search

from .circulation import ItemCirculation
from .issue import ItemIssue
from ..models import ItemIdentifier, ItemMetadata
from ...api import IlsRecordError, IlsRecordsIndexer, IlsRecordsSearch
from ...documents.api import Document, DocumentsSearch
from ...fetchers import id_fetcher
from ...minters import id_minter
from ...organisations.api import Organisation
from ...patrons.api import current_librarian
from ...providers import Provider
from ...utils import extracted_data_from_ref

# provider
ItemProvider = type(
    'ItemProvider',
    (Provider,),
    dict(identifier=ItemIdentifier, pid_type='item')
)
# minter
item_id_minter = partial(id_minter, provider=ItemProvider)
# fetcher
item_id_fetcher = partial(id_fetcher, provider=ItemProvider)


class ItemsSearch(IlsRecordsSearch):
    """ItemsSearch."""

    class Meta:
        """Search only on item index."""

        index = 'items'
        doc_types = None
        fields = ('*', )
        facets = {}

        default_filter = None

    @classmethod
    def flush(cls):
        """Flush indexes."""
        from rero_ils.modules.holdings.api import HoldingsSearch
        current_search.flush_and_refresh(DocumentsSearch.Meta.index)
        current_search.flush_and_refresh(HoldingsSearch.Meta.index)
        current_search.flush_and_refresh(cls.Meta.index)


class Item(ItemCirculation, ItemIssue):
    """Item class."""

    minter = item_id_minter
    fetcher = item_id_fetcher
    provider = ItemProvider
    model_cls = ItemMetadata
    pids_exist_check = {
        'required': {
            'loc': 'location',
            'doc': 'document',
            'itty': 'item_type'
        },
        'not_required': {
            'org': 'organisation',
            # We can not make the holding required because it is created later
            'hold': 'holding'
        }
    }

    def delete_from_index(self):
        """Delete record from index."""
        try:
            ItemsIndexer().delete(self)
        except NotFoundError:
            pass

    def get_links_to_me(self):
        """Get number of links."""
        links = {}
        loans = self.get_number_of_loans()
        if loans:
            links['loans'] = loans
        return links

    def reasons_not_to_delete(self):
        """Get reasons not to delete record."""
        cannot_delete = {}
        links = self.get_links_to_me()
        if links:
            cannot_delete['links'] = links
        if self.item_record_type == 'issue' and self.issue_is_regular:
            cannot_delete['others'] = dict(
                regular_issue_cannot_be_deleted=True
            )
        return cannot_delete

    def in_collection(self, **kwargs):
        """Get published collection pids for current item."""
        from ...collections.api import CollectionsSearch
        output = []
        search = CollectionsSearch() \
            .filter('term', items__pid=self.get('pid')) \
            .filter('term', published=True) \
            .sort({'title_sort': {'order': 'asc'}}) \
            .params(preserve_order=True) \
            .source(['pid', 'organisation', 'title', 'description'])
        orgs = {}
        for record in search.scan():
            if record.organisation.pid not in orgs:
                orgs[record.organisation.pid] = Organisation \
                    .get_record_by_pid(record.organisation.pid)
            output.append({
                'pid': record.pid,
                'title': record.title,
                'description': record.description,
                'viewcode': orgs[record.organisation.pid].get('code')
            })
        return output

    def replace_refs(self):
        """Replace $ref with real data."""
        tmp_itty_end_date = self.get('temporary_item_type', {}).get('end_date')
        data = super().replace_refs()
        if tmp_itty_end_date:
            data['temporary_item_type']['end_date'] = tmp_itty_end_date
        return data

    @classmethod
    def get_item_record_for_ui(cls, **kwargs):
        """Return the item record for ui calls.

        retrieving the item record is possible from an item pid, barcode or
        from a loan.

        :param kwargs: contains at least one of item_pid, item_barcode, or pid.
        :return: the item record.
        """
        from ...loans.api import Loan
        item = None
        item_pid = kwargs.get('item_pid')
        item_barcode = kwargs.pop('item_barcode', None)
        loan_pid = kwargs.get('pid')
        if item_pid:
            item = Item.get_record_by_pid(item_pid)
        elif item_barcode:
            org_pid = kwargs.get(
                'organisation_pid', current_librarian.organisation_pid)
            item = Item.get_item_by_barcode(item_barcode, org_pid)
        elif loan_pid:
            item_pid = Loan.get_record_by_pid(loan_pid).item_pid
            item = Item.get_record_by_pid(item_pid)
        return item

    @classmethod
    def get_items_with_obsolete_temporary_item_type(cls, end_date=None):
        """Get all items with an obsolete temporary item_type.

        An end_date could be attached to the item temporary item_type. If this
        date is less or equal to sysdate, then the temporary_item_type must be
        considered as obsolete.

        :param end_date: the end_date to check (`datetime.now()` by default)
        :return A generator of `ItemRecord` object.
        """
        if end_date is None:
            end_date = datetime.utcnow()
        end_date = end_date.strftime('%Y-%m-%d')
        results = ItemsSearch() \
            .filter('range', temporary_item_type__end_date={'lte': end_date}) \
            .source('pid') \
            .scan()
        for result in results:
            yield Item.get_record_by_pid(result.pid)


class ItemsIndexer(IlsRecordsIndexer):
    """Indexing items in Elasticsearch."""

    record_cls = Item

    def index(self, record):
        """Index an item."""
        from ...documents.api import DocumentsIndexer
        from ...holdings.api import Holding, HoldingsSearch

        # get the old holding record if exists
        items_search = ItemsSearch(). \
            filter('term', pid=record.get('pid')). \
            source('holding').execute().hits

        old_holdings_pid = None
        if items_search.total.value:
            old_holdings_pid = items_search[0].holding.pid

        return_value = super().index(record)

        # reindex document in background
        document_pid = extracted_data_from_ref(record.get('document'))
        uid = Document.get_id_by_pid(document_pid)
        DocumentsIndexer().index_by_id(uid)
        current_search.flush_and_refresh(HoldingsSearch.Meta.index)
        current_search.flush_and_refresh(DocumentsSearch.Meta.index)
        # set holding masking for standard holdings
        new_holdings_pid = extracted_data_from_ref(record['holding']['$ref'])
        holding = Holding.get_record_by_pid(new_holdings_pid)
        if holding.get('holdings_type') == 'standard':
            number_of_unmasked_items = \
                Item.get_number_masked_items_by_holdings_pid(new_holdings_pid)
            update_holdings = False
            # masking holding if all items are masked
            if not number_of_unmasked_items and not holding.get('_masked'):
                holding['_masked'] = True
                holding.update(
                    data=holding, dbcommit=True, reindex=True)
            # unmask holding if at least one of its items is unmasked
            elif number_of_unmasked_items and holding.get('_masked'):
                holding['_masked'] = False
                holding.update(
                    data=holding, dbcommit=True, reindex=True)
            # check if old holding can be deleted
            if old_holdings_pid and new_holdings_pid != old_holdings_pid:
                old_holding_rec = Holding.get_record_by_pid(old_holdings_pid)
                try:
                    # TODO: Need to split DB and elasticsearch deletion.
                    old_holding_rec.delete(
                        force=False, dbcommit=True, delindex=True)
                except IlsRecordError.NotDeleted:
                    pass

        return return_value

    def delete(self, record):
        """Delete a record.

        :param record: Record instance.
        """
        from ...holdings.api import Holding

        return_value = super().delete(record)
        rec_with_refs = record.replace_refs()
        document_pid = rec_with_refs['document']['pid']
        document = Document.get_record_by_pid(document_pid)
        document.reindex()
        current_search.flush_and_refresh(DocumentsSearch.Meta.index)

        holding = rec_with_refs.get('holding', '')
        if holding:
            holding_rec = Holding.get_record_by_pid(holding.get('pid'))
            try:
                # TODO: Need to split DB and elasticsearch deletion.
                holding_rec.delete(force=False, dbcommit=True, delindex=True)
            except IlsRecordError.NotDeleted:
                pass

        return return_value

    def bulk_index(self, record_id_iterator):
        """Bulk index records.

        :param record_id_iterator: Iterator yielding record UUIDs.
        """
        super().bulk_index(record_id_iterator, doc_type='item')
