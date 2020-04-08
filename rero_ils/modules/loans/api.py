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

"""API for manipulating Loans."""

from datetime import datetime, timedelta, timezone
from operator import attrgetter

import ciso8601
from flask import current_app
from invenio_circulation.errors import MissingRequiredParameterError
from invenio_circulation.pidstore.fetchers import loan_pid_fetcher
from invenio_circulation.pidstore.minters import loan_pid_minter
from invenio_circulation.pidstore.providers import CirculationLoanIdProvider
from invenio_circulation.proxies import current_circulation
from invenio_circulation.search.api import search_by_patron_item_or_document
from invenio_jsonschemas import current_jsonschemas

from ..api import IlsRecord, IlsRecordError, IlsRecordsIndexer, \
    IlsRecordsSearch
from ..documents.api import Document
from ..items.models import ItemCirculationAction
from ..libraries.api import Library
from ..locations.api import Location
from ..notifications.api import Notification, NotificationsSearch, \
    number_of_reminders_sent
from ..organisations.api import Organisation
from ..patron_transaction_events.api import PatronTransactionEvent
from ..patron_transactions.api import PatronTransaction
from ..patrons.api import Patron
from ..utils import get_base_url, get_ref_for_pid


class LoanAction(object):
    """Class holding all availabe circulation loan actions."""

    REQUEST = 'request'
    CHECKOUT = 'checkout'
    CHECKIN = 'checkin'
    VALIDATE = 'validate'
    RECEIVE = 'receive'
    RETURN_MISSING = 'return_missing'
    EXTEND = 'extend'
    CANCEL = 'cancel'
    LOSE = 'lose'
    NO = 'no'


class LoansSearch(IlsRecordsSearch):
    """Libraries search."""

    class Meta():
        """Meta class."""

        index = 'loans'
        doc_types = None


class Loan(IlsRecord):
    """Loan class."""

    minter = loan_pid_minter
    fetcher = loan_pid_fetcher
    provider = CirculationLoanIdProvider
    pid_field = 'pid'
    _schema = 'loans/loan-ils-v0.0.1.json'
    pids_exist_check = {
        'not_required': {
            'org': 'organisation',
            'item': 'item'
        }
    }
    DATE_FIELDS = [
        "start_date",
        "end_date",
        "request_expire_date",
        "request_start_date",
    ]
    DATETIME_FIELDS = ["transaction_date"]

    def __init__(self, data, model=None):
        """Loan init."""
        self['state'] = current_app.config['CIRCULATION_LOAN_INITIAL_STATE']
        super(Loan, self).__init__(data, model)

    @classmethod
    def create(cls, data, id_=None, delete_pid=True,
               dbcommit=False, reindex=False, **kwargs):
        """Create a new ils record."""
        data['$schema'] = current_jsonschemas.path_to_url(cls._schema)
        if delete_pid and data.get(cls.pid_field):
            del(data[cls.pid_field])
        cls._loan_build_org_ref(data)
        record = super(Loan, cls).create(
            data=data, id_=id_, delete_pid=delete_pid, dbcommit=dbcommit,
            reindex=reindex, **kwargs)
        return record

    def update(self, data, dbcommit=False, reindex=False):
        """Update loan record."""
        self._loan_build_org_ref(data)
        super(Loan, self).update(data, dbcommit, reindex)
        return self

    def attach_item_ref(self):
        """Attach item reference."""
        item_pid = self.get('item_pid')
        if not item_pid:
            raise MissingRequiredParameterError(
                description='item_pid missing from loan {0}'.format(
                    self.pid))
        self['item'] = self.loan_build_item_ref(item_pid, self)

    def loan_build_item_ref(self, item_pid, loan):
        """Build $ref for the Item attached to the Loan."""
        return {'$ref': '{base_url}/api/{doc_type}/{pid}'.format(
            base_url=get_base_url(),
            doc_type='items',
            pid=item_pid
        )}

    def loan_build_patron_ref(self, patron_pid, loan):
        """Build $ref for the Patron attached to the Loan."""
        base_url = current_app.config.get('RERO_ILS_APP_BASE_URL')
        url_api = '{base_url}/api/{doc_type}/{pid}'
        return {
            '$ref': url_api.format(
                base_url=base_url,
                doc_type='patrons',
                pid=patron_pid)
        }

    def loan_build_document_ref(self, document_pid, loan):
        """Build $ref for the Document attached to the Loan."""
        base_url = current_app.config.get('RERO_ILS_APP_BASE_URL')
        url_api = '{base_url}/api/{doc_type}/{pid}'
        return {
            '$ref': url_api.format(
                base_url=base_url,
                doc_type='documents',
                pid=document_pid)
        }

    @classmethod
    def _loan_build_org_ref(cls, data):
        """Build $ref for the organisation of the Loan."""
        from ..items.api import Item
        item_pid = data.get('item_pid')
        data['organisation'] = {'$ref': get_ref_for_pid(
            'org',
            Item.get_record_by_pid(item_pid).organisation_pid
        )}
        return data

    def is_loan_overdue(self):
        """Check if the loan is overdue."""
        from .utils import get_circ_policy
        circ_policy = get_circ_policy(self)
        now = datetime.now(timezone.utc)
        end_date = self.get('end_date')
        due_date = ciso8601.parse_datetime(end_date)

        days_after = circ_policy.get('number_of_days_after_due_date')
        if now > due_date + timedelta(days=days_after):
            return True
        return False

    @property
    def pid(self):
        """Shortcut for pid."""
        return self.get('pid')

    @property
    def rank(self):
        """Shortcut for rank.

        Used by the sorted function
        """
        return self.get('rank')

    @property
    def transaction_date(self):
        """Shortcut for transaction date.

        Used by the sorted function
        """
        return self.get('transaction_date')

    @property
    def end_date(self):
        """Shortcut for end date.

        Used by the sorted function
        """
        return self.get('end_date')

    @property
    def item_pid(self):
        """Shortcut for item pid."""
        return self.get('item_pid')

    @property
    def patron_pid(self):
        """Shortcut for patron pid."""
        return self.get('patron_pid')

    @property
    def is_active(self):
        """Shortcut to check of loan is active."""
        states = current_app.config['CIRCULATION_STATES_LOAN_ACTIVE']
        if self.get('state') in states:
            return True
        return False

    @property
    def organisation_pid(self):
        """Get organisation pid for loan."""
        from ..items.api import Item

        if self.get('item_pid'):
            item = Item.get_record_by_pid(self.get('item_pid'))
            return item.organisation_pid
        # return None
        raise IlsRecordError.PidDoesNotExist(
            self.provider.pid_type,
            'organisation_pid:item_pid'
        )

    @property
    def library_pid(self):
        """Get library PID regarding loan location."""
        return Location.get_record_by_pid(self.location_pid).library_pid

    @property
    def location_pid(self):
        """Get loan transaction_location PID or item owning location."""
        from ..items.api import Item
        location_pid = self.get('transaction_location_pid')
        item_pid = self.get('item_pid')

        if not location_pid and item_pid:
            return Item.get_record_by_pid(item_pid).holding_location_pid
        elif location_pid:
            return location_pid
        return IlsRecordError.PidDoesNotExist(
            self.provider.pid_type,
            'library_pid'
        )

    def dumps_for_circulation(self):
        """Dumps for circulation."""
        loan = self.replace_refs()
        data = loan.dumps()

        patron = Patron.get_record_by_pid(loan['patron_pid'])
        ptrn_data = patron.dumps()
        data['patron'] = {}
        data['patron']['barcode'] = ptrn_data['barcode']
        data['patron']['name'] = ', '.join((
            ptrn_data['first_name'], ptrn_data['last_name']))

        if loan.get('pickup_location_pid'):
            location = Location.get_record_by_pid(loan['pickup_location_pid'])
            library = location.get_library()
            loc_data = location.dumps()
            data['pickup_location'] = {}
            data['pickup_location']['name'] = loc_data['name']
            data['pickup_location']['library_name'] = library.get('name')
        return data

    def is_notified(self, notification_type=None):
        """Check if a notification exist already for a loan by type."""
        results = NotificationsSearch().filter(
            'term', loan__pid=self.pid
        ).filter('term', notification_type=notification_type).source().count()
        return results > 0

    def create_notification(self, notification_type=None):
        """Creates a recall notification from a checked-out loan."""
        notification = {}
        record = {}
        creation_date = datetime.now(timezone.utc).isoformat()
        record['creation_date'] = creation_date
        record['notification_type'] = notification_type
        url_api = '{base_url}/api/{doc_type}/{pid}'
        record['loan'] = {
            '$ref': url_api.format(
                base_url=get_base_url(),
                doc_type='loans',
                pid=self.pid)
        }
        notification_to_create = False
        if notification_type == 'recall':
            if self.get('state') == 'ITEM_ON_LOAN' and \
                    not self.is_notified(notification_type=notification_type):
                notification_to_create = True
        elif notification_type == 'availability' and \
                not self.is_notified(notification_type=notification_type):
            notification_to_create = True
        elif notification_type == 'due_soon':
            if self.get('state') == 'ITEM_ON_LOAN' and \
                    not self.is_notified(notification_type=notification_type):
                notification_to_create = True
        elif notification_type == 'overdue':
            if self.get('state') == 'ITEM_ON_LOAN' and \
                    not number_of_reminders_sent(self):
                record['reminder_counter'] = 1
                notification_to_create = True
        if notification_to_create:
            notification = Notification.create(
                data=record, dbcommit=True, reindex=True)
            notification = notification.dispatch()
        return notification


def get_request_by_item_pid_by_patron_pid(item_pid, patron_pid):
    """Get pending, item_on_transit, item_at_desk loans for item, patron."""
    search = search_by_patron_item_or_document(
        item_pid=item_pid,
        patron_pid=patron_pid,
        filter_states=[
            'PENDING',
            'ITEM_AT_DESK',
            'ITEM_IN_TRANSIT_FOR_PICKUP',
            'ITEM_IN_TRANSIT_TO_HOUSE',
        ],
    )
    search_result = search.execute()
    if search_result.hits:
        return search_result.hits.hits[0]['_source']
    return {}


def get_loans_by_patron_pid(patron_pid):
    """Return all loans for patron."""
    results = current_circulation.loan_search_cls\
        .source(['pid'])\
        .params(preserve_order=True)\
        .filter('term', patron_pid=patron_pid)\
        .sort({'transaction_date': {'order': 'asc'}})\
        .scan()
    for loan in results:
        yield Loan.get_record_by_pid(loan.pid)


def patron_profile(patron):
    """Return formatted loans for patron profile display.

    :param patron: the patron resource
    :return: array of loans, requests, fees and history
    """
    from ..items.api import Item

    patron_pid = patron.get('pid')
    organisation = Organisation.get_record_by_pid(patron.organisation_pid)

    loans = []
    requests = []
    history = []

    for loan in get_loans_by_patron_pid(patron_pid):
        item = Item.get_record_by_pid(loan.item_pid, with_deleted=True)
        if item == {}:
            # loans for deleted items are temporarily skipped.
            continue
        document = Document.get_record_by_pid(
            item.replace_refs()['document']['pid'])
        loan['document'] = document.replace_refs().dumps()
        loan['item_call_number'] = item['call_number']
        if loan['state'] == 'ITEM_ON_LOAN':
            loan['overdue'] = loan.is_loan_overdue()
            loan['library_name'] = Library.get_record_by_pid(
                item.holding_library_pid).get('name')
        else:
            pickup_location = Location.get_record_by_pid(
                loan.get('pickup_location_pid'))
            if pickup_location.get('pickup_name'):
                loan['pickup_name'] = pickup_location.get('pickup_name')
            else:
                loan['pickup_name'] = pickup_location.get('name')
        if loan['state'] == 'ITEM_ON_LOAN':
            can, reasons = item.can(
                ItemCirculationAction.EXTEND,
                loan=loan
            )
            loan['can_renew'] = can
            loans.append(loan)
        elif loan['state'] in [
                'PENDING',
                'ITEM_AT_DESK',
                'ITEM_IN_TRANSIT_FOR_PICKUP'
        ]:
            pickup_loc = Location.get_record_by_pid(
                loan['pickup_location_pid'])
            loan['pickup_library_name'] = \
                pickup_loc.get_library().get('name')
            if loan['state'] == 'ITEM_AT_DESK':
                loan['rank'] = 0
            if loan['state'] in ['PENDING', 'ITEM_IN_TRANSIT_FOR_PICKUP']:
                loan['rank'] = item.patron_request_rank(patron['barcode'])
            requests.append(loan)
        elif loan['state'] in ['ITEM_RETURNED', 'CANCELLED']:
            end_date = loan.get('end_date')
            if end_date:
                end_date = ciso8601.parse_datetime(end_date)
                loan_age = (datetime.utcnow() - end_date.replace(tzinfo=None))
                # Only history of last six months is displayed
                if loan_age <= timedelta(6*365/12):
                    loan['pickup_library_name'] = Location\
                        .get_record_by_pid(loan['pickup_location_pid'])\
                        .get_library().get('name')
                    loan['transaction_library_name'] = Location\
                        .get_record_by_pid(loan['transaction_location_pid'])\
                        .get_library().get('name')
                    history.append(loan)
    # Fees
    fees = {
        'open': _process_patron_profile_fees(patron, organisation, 'open'),
        'closed': _process_patron_profile_fees(patron, organisation, 'closed')
    }
    return sorted(loans, key=attrgetter('end_date')),\
        sorted(requests, key=attrgetter('rank', 'transaction_date')),\
        fees,\
        history


def _process_patron_profile_fees(patron, organisation, status='open'):
    """Process fees by status.

    :param patron: the patron resource
    :param organsation: the organisation resource
    :param status: the status of fee transaction
    :return: array of fees
    """
    from ..items.api import Item
    from ..loans.api import Loan

    fees = {
        'currency': organisation.get('default_currency'),
        'total_amount': 0,
        'lines': []
    }
    for transaction in PatronTransaction.get_transactions_by_patron_pid(
            patron.get('pid'), status):
        fees['total_amount'] += transaction.total_amount
        transaction['currency'] = Organisation\
            .get_record_by_pid(transaction.organisation.pid)\
            .get('default_currency')
        if 'loan' in transaction:
            item_pid = Loan.get_record_by_pid(transaction.loan.pid)\
                .get('item_pid')
            item = Item.get_record_by_pid(item_pid)
            transaction['item_call_number'] = item['call_number']
        if (transaction.status == 'closed'):
            transaction.total_amount = PatronTransactionEvent\
                .get_initial_amount_transaction_event(transaction.pid)
        transaction['events'] = []
        if (transaction.type == 'overdue'):
            transaction['document'] = Document.get_record_by_pid(
                transaction.document.pid)
            transaction['loan'] = Loan.get_record_by_pid(transaction.loan.pid)
        for event in PatronTransactionEvent.get_events_by_transaction_id(
                transaction.pid):
            event['currency'] = Organisation\
                .get_record_by_pid(event.organisation.pid)\
                .get('default_currency')
            if ('library' in event):
                event.library = Library\
                    .get_record_by_pid(event.library.pid)
            transaction['events'].append(event)
        fees['lines'].append(transaction)
    return fees


def get_last_transaction_loc_for_item(item_pid):
    """Return last transaction location for an item."""
    results = current_circulation.loan_search_cls\
        .source(['pid'])\
        .params(preserve_order=True)\
        .filter('term', item_pid=item_pid)\
        .exclude('terms', state=['PENDING', 'CREATED'])\
        .sort({'transaction_date': {'order': 'desc'}})\
        .scan()
    try:
        loan_pid = next(results).pid
        return Loan.get_record_by_pid(
            loan_pid).get('transaction_location_pid')
    except StopIteration:
        return None


def get_due_soon_loans():
    """Return all due_soon loans."""
    from .utils import get_circ_policy
    due_soon_loans = []
    results = current_circulation.loan_search_cls\
        .source(['pid'])\
        .params(preserve_order=True)\
        .filter('term', state='ITEM_ON_LOAN')\
        .sort({'transaction_date': {'order': 'asc'}})\
        .scan()
    for record in results:
        loan = Loan.get_record_by_pid(record.pid)
        circ_policy = get_circ_policy(loan)
        now = datetime.now(timezone.utc)
        end_date = loan.get('end_date')
        due_date = ciso8601.parse_datetime(end_date)

        days_before = circ_policy.get('number_of_days_before_due_date')
        if due_date > now > due_date - timedelta(days=days_before):
            due_soon_loans.append(loan)
    return due_soon_loans


def get_overdue_loans():
    """Return all overdue loans."""
    from .utils import get_circ_policy
    overdue_loans = []
    results = current_circulation.loan_search_cls\
        .source(['pid'])\
        .params(preserve_order=True)\
        .filter('term', state='ITEM_ON_LOAN')\
        .sort({'transaction_date': {'order': 'asc'}})\
        .scan()
    for record in results:
        loan = Loan.get_record_by_pid(record.pid)
        circ_policy = get_circ_policy(loan)
        now = datetime.now(timezone.utc)
        end_date = loan.get('end_date')
        due_date = ciso8601.parse_datetime(end_date)

        days_after = circ_policy.get('number_of_days_after_due_date')
        if now > due_date + timedelta(days=days_after):
            overdue_loans.append(loan)
    return overdue_loans


class LoansIndexer(IlsRecordsIndexer):
    """Holdings indexing class."""

    record_cls = Loan

    def bulk_index(self, record_id_iterator):
        """Bulk index records.

        :param record_id_iterator: Iterator yielding record UUIDs.
        """
        super(LoansIndexer, self).bulk_index(record_id_iterator,
                                             doc_type='loan')
