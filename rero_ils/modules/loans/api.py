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
from elasticsearch_dsl import A
from flask import current_app
from invenio_circulation.errors import MissingRequiredParameterError
from invenio_circulation.pidstore.fetchers import loan_pid_fetcher
from invenio_circulation.pidstore.minters import loan_pid_minter
from invenio_circulation.pidstore.providers import CirculationLoanIdProvider
from invenio_circulation.proxies import current_circulation
from invenio_circulation.search.api import search_by_patron_item_or_document
from invenio_circulation.utils import str2datetime
from invenio_jsonschemas import current_jsonschemas

from ..api import IlsRecord, IlsRecordError, IlsRecordsIndexer, \
    IlsRecordsSearch
from ..documents.api import Document
from ..errors import NoCirculationActionIsPermitted
from ..ill_requests.api import ILLRequest
from ..items.models import ItemCirculationAction, ItemStatus
from ..items.utils import item_pid_to_object
from ..libraries.api import Library
from ..locations.api import Location
from ..notifications.api import Notification, NotificationsSearch, \
    number_of_reminders_sent
from ..organisations.api import Organisation
from ..patron_transaction_events.api import PatronTransactionEvent
from ..patron_transactions.api import PatronTransaction, \
    PatronTransactionsSearch
from ..patrons.api import Patron
from ..utils import get_base_url, get_ref_for_pid
from ...filter import format_date_filter


class LoanState(object):
    """Class to handle different loan states."""

    CREATED = 'CREATED'
    PENDING = 'PENDING'
    ITEM_IN_TRANSIT_FOR_PICKUP = 'ITEM_IN_TRANSIT_FOR_PICKUP'
    ITEM_IN_TRANSIT_TO_HOUSE = 'ITEM_IN_TRANSIT_TO_HOUSE'
    ITEM_AT_DESK = 'ITEM_AT_DESK'
    ITEM_ON_LOAN = 'ITEM_ON_LOAN'
    ITEM_RETURNED = 'ITEM_RETURNED'
    CANCELLED = 'CANCELLED'


class LoanAction(object):
    """Class holding all available circulation loan actions."""

    REQUEST = 'request'
    CHECKOUT = 'checkout'
    CHECKIN = 'checkin'
    VALIDATE = 'validate'
    RECEIVE = 'receive'
    RETURN_MISSING = 'return_missing'
    EXTEND = 'extend_loan'
    CANCEL = 'cancel'
    NO = 'no'
    UPDATE = 'update'


class LoansSearch(IlsRecordsSearch):
    """Libraries search."""

    class Meta():
        """Meta class."""

        index = 'loans'
        doc_types = None
        fields = ('*', )
        facets = {}

        default_filter = None


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
    DATE_FIELDS = []

    DATETIME_FIELDS = [
        "end_date",
        "request_expire_date",
        "request_start_date",
        "start_date",
        "transaction_date"
    ]

    def __init__(self, data, model=None):
        """Loan init."""
        self['state'] = current_app.config['CIRCULATION_LOAN_INITIAL_STATE']
        super().__init__(data, model)

    def action_required_params(self, action=None):
        """List of required parameters for circulation actions."""
        shared_params = [
            'transaction_location_pid',
            'transaction_user_pid',
        ]
        params = {
            'request': [
                'item_pid',
                'pickup_location_pid',
                'patron_pid',
            ],
            'cancel_loan': [
                'pid'
            ],
            'checkin': [
                'pid'
            ],
            'validate_request': [
                'pid'
            ],
            'checkout': [
                'item_pid',
                'patron_pid',
                'transaction_location_pid',
                'transaction_user_pid',
            ],
            'extend_loan': [
                'item_pid'
            ],
            'receive': []
        }

        return params.get(action) + shared_params

    def check_required_params(self, action, **kwargs):
        """Validate that all required parameters are given for an action."""
        # TODO: do we need to check also the parameter exist and its value?
        required_params = self.action_required_params(action=action)
        missing_params = set(required_params) - set(kwargs)
        if missing_params:
            message = 'Parameters {} are required'.format(missing_params)
            raise MissingRequiredParameterError(description=message)

    def update_pickup_location(self, pickup_location_pid):
        """Update the pickup location for a loan.

        Pickup location update is only possible for pending and in_transit
        to house loans.

        :param pickup_location_pid: The new pickup_location_pid.
        :return: the new updated loan.
        """
        if self['state'] not in [
                LoanState.PENDING, LoanState.ITEM_IN_TRANSIT_FOR_PICKUP]:
            raise NoCirculationActionIsPermitted(
                'No circulation action is permitted')

        self['pickup_location_pid'] = pickup_location_pid
        return self.update(self, dbcommit=True, reindex=True)

    @classmethod
    def create(cls, data, id_=None, delete_pid=True,
               dbcommit=False, reindex=False, **kwargs):
        """Create the loan record.

        :param cls - class object
        :param data - dictionary representing a loan record.
        :param id_ - UUID, it would be generated if it is not given.
        :param delete_pid - remove the pid present in the data if True,
        :param dbcommit - commit the changes in the db after the creation.
        :param reindex - index the record after the creation.
        """
        data['$schema'] = current_jsonschemas.path_to_url(cls._schema)
        if delete_pid and data.get(cls.pid_field):
            del(data[cls.pid_field])
        cls._loan_build_org_ref(data)
        # set the field to_anonymize
        to_anonymize = False
        data['to_anonymize'] = \
            cls.can_anonymize(loan_data=data) and not data.get('to_anonymize')

        if not data.get('state'):
            data['state'] = LoanState.CREATED
        record = super(Loan, cls).create(
            data=data, id_=id_, delete_pid=delete_pid, dbcommit=dbcommit,
            reindex=reindex, **kwargs)
        return record

    def update(self, data, dbcommit=False, reindex=False):
        """Update loan record."""
        self._loan_build_org_ref(data)
        # set the field to_anonymize
        if Loan.can_anonymize(loan_data=data) and not self.get('to_anonymize'):
            data['to_anonymize'] = True
        super(Loan, self).update(data, dbcommit, reindex)
        return self

    def anonymize(self, loan, dbcommit=False, reindex=False):
        """Anonymize a loan.

        :param loan: the loan to update.
        :param dbcommit - commit the changes in the db after the creation.
        :param reindex - index the record after the creation.
        """
        loan['to_anonymize'] = True
        super().update(loan, dbcommit, reindex)
        return self

    def date_fields2datetime(self):
        """Convert string datetime fields to Python datetime."""
        for field in self.DATE_FIELDS + self.DATETIME_FIELDS:
            if field in self:
                self[field] = str2datetime(self[field])

    def date_fields2str(self):
        """Convert Python datetime fields to string."""
        for field in self.DATE_FIELDS:
            if field in self:
                self[field] = self[field].date().isoformat()
        for field in self.DATETIME_FIELDS:
            if field in self:
                self[field] = self[field].isoformat()

    @classmethod
    def _loan_build_org_ref(cls, data):
        """Build $ref for the organisation of the Loan."""
        from ..items.api import Item
        item_pid = data.get('item_pid', {}).get('value')
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
    def request_creation_date(self):
        """Shortcut for request create date."""
        # TODO: remove this when the field request_creation_date is added.
        return self.created

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
        """Returns the item pid value."""
        return self.get('item_pid', {}).get('value', None)

    @property
    def item_pid_object(self):
        """Returns the loan item_pid object."""
        return self.get('item_pid', {})

    @property
    def patron_pid(self):
        """Shortcut for patron pid."""
        return self.get('patron_pid')

    @property
    def document_pid(self):
        """Shortcut for document pid."""
        return self.get('document_pid')

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
        item_pid = self.item_pid
        if item_pid:
            item = Item.get_record_by_pid(item_pid)
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
        item_pid = self.item_pid

        if not location_pid and item_pid:
            return Item.get_record_by_pid(item_pid).holding_location_pid
        elif location_pid:
            return location_pid
        return IlsRecordError.PidDoesNotExist(
            self.provider.pid_type,
            'library_pid'
        )

    def get_loan_end_date(self, format='short', time_format='medium',
                          language=None):
        """Get loan end date.

        :param format: The date format, ex: 'full', 'medium', 'short'
                        or custom
        :param time_format: The time format, ex: 'medium', 'short' or custom
        :param language: The language to fix the language format
        :return: original date or formatted date
        """
        end_date = self.end_date
        if format:
            return format_date_filter(
                end_date,
                date_format=format,
                time_format=time_format,
                locale=language,
            )
        return end_date

    def dumps_for_circulation(self):
        """Dumps for circulation."""
        from ..items.api import Item
        loan = self.replace_refs()
        data = loan.dumps()
        patron = Patron.get_record_by_pid(loan['patron_pid'])
        ptrn_data = patron.dumps()
        data['patron'] = {}
        data['patron']['barcode'] = ptrn_data['patron']['barcode']
        data['patron']['name'] = ', '.join((
            ptrn_data['last_name'], ptrn_data['first_name']))
        if loan.get('pickup_location_pid'):
            location = Location.get_record_by_pid(loan['pickup_location_pid'])
            data['pickup_location'] = {
                'name': location.get('name'),
                'library_name': location.get_library().get('name')
            }
        # Always add item destination readable informations if item state is
        # 'in transit' ; much more easier to know these informations for UI !
        item = Item.get_record_by_pid(self.item_pid)
        if item.status == ItemStatus.IN_TRANSIT:
            destination_loc_pid = item.location_pid
            if LoanState.ITEM_IN_TRANSIT_FOR_PICKUP:
                destination_loc_pid = self.get('pickup_location_pid')
            destination_loc = Location.get_record_by_pid(destination_loc_pid)
            destination_lib = destination_loc.get_library()
            data['item_destination'] = {
                'location_name': destination_loc.get('name'),
                'location_code': destination_loc.get('code'),
                'library_name': destination_lib.get('name'),
                'library_code': destination_lib.get('code')
            }

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
            if self.get('state') == LoanState.ITEM_ON_LOAN and \
                    not self.is_notified(notification_type=notification_type):
                notification_to_create = True
        elif notification_type == 'availability' and \
                not self.is_notified(notification_type=notification_type):
            notification_to_create = True
        elif notification_type == 'due_soon':
            if self.get('state') == LoanState.ITEM_ON_LOAN and \
                    not self.is_notified(notification_type=notification_type):
                notification_to_create = True
        elif notification_type == 'overdue':
            if self.get('state') == LoanState.ITEM_ON_LOAN and \
                    not number_of_reminders_sent(self):
                record['reminder_counter'] = 1
                notification_to_create = True
        if notification_to_create:
            notification = Notification.create(
                data=record, dbcommit=True, reindex=True)
            notification = notification.dispatch()
        return notification

    @classmethod
    def concluded(cls, loan):
        """Check if loan is concluded.

        Loan is considered concluded if it has either ITEM_RETURNED or
        CANCELLED states and has no open patron_transactions.

        :param loan: the loan to check.
        :return True|False
        """
        states = [LoanState.ITEM_RETURNED, LoanState.CANCELLED]
        return (
            loan.get('state') in states and
            not loan_has_open_events(loan_pid=loan.get('pid'))
        )

    @classmethod
    def age(cls, loan):
        """Return the age of a loan in days.

        The age of a loan is calculated based on the loan transaction date.

        :param loan: the loan to check.
        :return loan_age in number of days
        """
        transaction_date = ciso8601.parse_datetime(
            loan.get('transaction_date'))
        loan_age = (transaction_date.replace(tzinfo=None) - datetime.utcnow())
        return loan_age.days

    @classmethod
    def can_anonymize(cls, loan_data=None, patron_data=None):
        """Check if a loan can be anonymized and excluded from loan searches.

        Loan can be anonymized if:
        1. it is concluded and 6 months old
        2. patron has the keep_history set to False and the loan is concluded.

        This method is classmethod because it needs to check the loan record
        during the loan.update process. this way, you can have access to the
        old and new version of the loan.

        :param loan_data: the loan to check.
        :param patron_data: the patron to check.
        :return True|False.
        """
        if cls.concluded(loan_data) and cls.age(loan_data) > 6*365/12:
            return True
        if not patron_data:
            patron_data = Patron.get_record_by_pid(loan_data.get('patron_pid'))
        keep_history = patron_data.get('patron', {}).get('keep_history')
        return not keep_history and cls.concluded(loan_data)


def get_request_by_item_pid_by_patron_pid(item_pid, patron_pid):
    """Get pending, item_in_transit, item_at_desk loans for item, patron.

    :param item_pid: The item pid.
    :param patron_pid: The patron pid.
    :return: loans for given item and patron.
    """
    filter_states = [
        LoanState.PENDING,
        LoanState.ITEM_AT_DESK,
        LoanState.ITEM_IN_TRANSIT_FOR_PICKUP,
        LoanState.ITEM_IN_TRANSIT_TO_HOUSE
    ]
    return get_loans_by_item_pid_by_patron_pid(
        item_pid, patron_pid, filter_states)


def get_any_loans_by_item_pid_by_patron_pid(item_pid, patron_pid):
    """Get loans not ITEM_IN_TRANSIT_TO_HOUSE, CREATED for item, patron.

    :param item_pid: The item pid.
    :param patron_pid: The patron pid.
    :return: loans for given item and patron.
    """
    filter_states = [
        LoanState.PENDING,
        LoanState.ITEM_AT_DESK,
        LoanState.ITEM_IN_TRANSIT_FOR_PICKUP,
        LoanState.ITEM_ON_LOAN
    ]
    return get_loans_by_item_pid_by_patron_pid(
        item_pid, patron_pid, filter_states)


def count_any_loans_by_patron_pid(patron_pid):
    """Count loans not ITEM_IN_TRANSIT_TO_HOUSE, CREATED for patron.

    :param patron_pid: the patron pid.
    :return the number of corresponding loans.
    """
    filter_states = [
        LoanState.PENDING,
        LoanState.ITEM_AT_DESK,
        LoanState.ITEM_IN_TRANSIT_FOR_PICKUP,
        LoanState.ITEM_ON_LOAN
    ]
    return search_by_patron_item_or_document(
        patron_pid=patron_pid,
        filter_states=filter_states,
    ).source().count()


def get_loans_by_item_pid_by_patron_pid(
        item_pid, patron_pid, filter_states=[]):
    """Get loans for item, patron according to the given filter_states.

    :param item_pid: The item pid.
    :param patron_pid: The patron pid.
    :param filter_states: states to use as a filter.
    :return: loans for given item and patron.
    """
    search = search_by_patron_item_or_document(
        item_pid=item_pid_to_object(item_pid),
        patron_pid=patron_pid,
        filter_states=filter_states,
    )
    search_result = search.execute()
    if search_result.hits:
        return search_result.hits.hits[0]['_source']
    return {}


def get_loans_stats_by_patron_pid(patron_pid):
    """Search loans for patron and aggregate result on loan state.

    :param patron_pid: The patron pid
    :return: a dict with loans state as key, number of loans as value
    """
    agg = A('terms', field='state')
    search = search_by_patron_item_or_document(patron_pid=patron_pid)
    search.aggs.bucket('state', agg)
    search = search[0:0]
    results = search.execute()
    stats = {}
    for result in results.aggregations.state.buckets:
        stats[result.key] = result.doc_count
    return stats


def get_loans_by_patron_pid(patron_pid, filter_states=[], to_anonymize=False):
    """Search all loans for patron to the given filter_states.

    :param to_anonymize: filter by field to_anonymize.
    :param patron_pid: The patron pid.
    :param filter_states: loan states to use as a filter.
    :return: loans for given patron.
    """
    search = search_by_patron_item_or_document(
        patron_pid=patron_pid,
        filter_states=filter_states)\
        .params(preserve_order=True)\
        .sort({'_created': {'order': 'asc'}})\
        .source(['pid'])
    search = search.filter('term', to_anonymize=to_anonymize)
    for loan in search.scan():
        yield Loan.get_record_by_pid(loan.pid)


def patron_profile(patron):
    """Return formatted loans for patron profile display.

    :param patron: the patron resource
    :return: array of loans, requests, fees, history and ill_requests
    """
    from ..items.api import Item

    patron_pid = patron.get('pid')
    organisation = Organisation.get_record_by_pid(patron.organisation_pid)

    loans = []
    requests = []
    history = []

    for loan in get_loans_by_patron_pid(patron_pid, to_anonymize=False):
        item = Item.get_record_by_pid(loan.item_pid, with_deleted=True)
        if item == {}:
            # loans for deleted items are temporarily skipped.
            continue

        # inherit holdings call number when possible
        issue_call_number = item.issue_inherited_first_call_number
        if issue_call_number:
            item['call_number'] = issue_call_number

        document = Document.get_record_by_pid(
            item.replace_refs()['document']['pid'])
        loan['document'] = document.replace_refs().dumps()
        loan['item_call_number'] = item.get('call_number')
        loan['item_barcode'] = item['barcode']
        if loan['state'] == LoanState.ITEM_ON_LOAN:
            loan['overdue'] = loan.is_loan_overdue()
            loan['library_name'] = Library.get_record_by_pid(
                item.holding_library_pid).get('name')
        else:
            pickup_location = Location.get_record_by_pid(
                loan.get('pickup_location_pid'))
            if pickup_location:
                loan['pickup_name'] = pickup_location.get(
                    'pickup_name', pickup_location.get('name')
                )
        if loan['state'] == LoanState.ITEM_ON_LOAN:
            can, reasons = item.can(
                ItemCirculationAction.EXTEND,
                loan=loan
            )
            loan['can_renew'] = can
            if not can:
                loan['can_renew_reasons'] = reasons
            loans.append(loan)
        elif loan['state'] in [
                LoanState.PENDING,
                LoanState.ITEM_AT_DESK,
                LoanState.ITEM_IN_TRANSIT_FOR_PICKUP
        ]:
            pickup_loc = Location.get_record_by_pid(
                loan['pickup_location_pid'])
            loan['pickup_library_name'] = \
                pickup_loc.get_library().get('name')
            if loan['state'] == LoanState.ITEM_AT_DESK:
                loan['rank'] = 0
            if loan['state'] in [
                    LoanState.PENDING, LoanState.ITEM_IN_TRANSIT_FOR_PICKUP]:
                loan['rank'] = item.patron_request_rank(
                    patron.patron['barcode'][0])
            requests.append(loan)
        elif loan['state'] in [
                LoanState.ITEM_RETURNED,
                LoanState.ITEM_IN_TRANSIT_TO_HOUSE,
                LoanState.CANCELLED
        ]:
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
    # ILL request
    ill_requests = []
    for request in ILLRequest.get_requests_by_patron_pid(patron_pid):
        location_pid = request.replace_refs()['pickup_location']['pid']
        location = Location.get_record_by_pid(location_pid)
        loc_name = location.get('pickup_name', location.get('name'))
        request['pickup_location']['name'] = loc_name
        ill_requests.append(request)

    return \
        sorted(loans, key=attrgetter('end_date')),\
        sorted(requests, key=attrgetter('rank', 'request_creation_date')),\
        fees,\
        history,\
        ill_requests


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
            item = Item.get_record_by_pid(item_pid.get('value'))
            transaction['item_call_number'] = item.get('call_number')
        if transaction.status == 'closed':
            transaction.total_amount = PatronTransactionEvent\
                .get_initial_amount_transaction_event(transaction.pid)
        transaction['events'] = []
        if transaction.type == 'overdue':
            transaction['document'] = Document.get_record_by_pid(
                transaction.document.pid)
            transaction['loan'] = Loan.get_record_by_pid(transaction.loan.pid)
        for event in PatronTransactionEvent.get_events_by_transaction_id(
                transaction.pid):
            event['currency'] = Organisation\
                .get_record_by_pid(event.organisation.pid)\
                .get('default_currency')
            if 'library' in event:
                event.library = Library\
                    .get_record_by_pid(event.library.pid)
            transaction['events'].append(event)
        fees['lines'].append(transaction)
    return fees


def get_last_transaction_loc_for_item(item_pid):
    """Return last transaction location for an item."""
    results = current_circulation.loan_search_cls()\
        .filter('term', item_pid=item_pid)\
        .params(preserve_order=True)\
        .exclude('terms', state=[
            LoanState.PENDING, LoanState.CREATED])\
        .sort({'_created': {'order': 'desc'}})\
        .source(['pid']).scan()
    try:
        loan_pid = next(results).pid
        return Loan.get_record_by_pid(
            loan_pid).get('transaction_location_pid')
    except StopIteration:
        return None


def get_loans_count_by_library_for_patron_pid(patron_pid, filter_states=None):
    """Get loans count for patron and aggregate result on library_pid.

    :param patron_pid: The patron pid
    :param filter_states: loans type to filters
    :return: a dict with library_pid as key, number of loans as value
    """
    filter_states = filter_states or []  # prevent mutable argument warning
    agg = A('terms', field='library_pid')
    search = search_by_patron_item_or_document(
        patron_pid=patron_pid,
        filter_states=filter_states
    )
    search.aggs.bucket('library', agg)
    search = search[0:0]
    results = search.execute()
    stats = {}
    for result in results.aggregations.library.buckets:
        stats[result.key] = result.doc_count
    return stats


def get_due_soon_loans():
    """Return all due_soon loans."""
    due_soon_loans = []
    results = current_circulation.loan_search_cls()\
        .filter('term', state=LoanState.ITEM_ON_LOAN)\
        .params(preserve_order=True)\
        .sort({'_created': {'order': 'asc'}})\
        .source(['pid']).scan()
    for record in results:
        loan = Loan.get_record_by_pid(record.pid)
        if is_due_soon_loan(loan):
            due_soon_loans.append(loan)
    return due_soon_loans


def get_overdue_loan_pids(patron_pid=None):
    """Return all overdue loan pids optionally filtered for a patron pid.

    :param patron_pid: the patron pid. If none, return all overdue loans.
    :return a generator of loan pid
    """
    end_date = datetime.now()
    end_date = end_date.strftime('%Y-%m-%d')
    query = current_circulation.loan_search_cls() \
        .filter('term', state=LoanState.ITEM_ON_LOAN) \
        .filter('range', end_date={'lte': end_date})
    if patron_pid:
        query = query.filter('term', patron_pid=patron_pid)
    results = query\
        .params(preserve_order=True) \
        .sort({'_created': {'order': 'asc'}}) \
        .source(['pid']).scan()
    for hit in results:
        yield hit.pid


def get_overdue_loans(patron_pid=None):
    """Return all overdue loans optionally filtered for a patron pid.

    :param patron_pid: the patron pid. If none, return all overdue loans.
    :return a generator of Loan
    """
    for pid in get_overdue_loan_pids(patron_pid):
        yield Loan.get_record_by_pid(pid)


def is_due_soon_loan(loan):
    """Check if loan is due soon.

    :param loan: loan object to check
    :returns True if loan is due Soon.
    """
    from .utils import get_circ_policy
    circ_policy = get_circ_policy(loan)
    now = datetime.now(timezone.utc)
    end_date = loan.get('end_date')
    due_date = ciso8601.parse_datetime(end_date).replace(
        tzinfo=timezone.utc)

    days_before = circ_policy.get('number_of_days_before_due_date')
    return due_date > now > due_date - timedelta(days=days_before)


def is_overdue_loan(loan):
    """Check if loan is in overdue.

    :param loan: loan object to check
    :returns True if loan is in overdue.
    """
    from .utils import get_circ_policy
    circ_policy = get_circ_policy(loan)
    now = datetime.now(timezone.utc)
    end_date = loan.get('end_date')
    due_date = ciso8601.parse_datetime(end_date).replace(
        tzinfo=timezone.utc)

    days_after = circ_policy.get('number_of_days_after_due_date')
    return now > due_date + timedelta(days=days_after)


def loan_has_open_events(loan_pid=None):
    """Check if a loan has open patron transactions.

    Loan has no open_events if the he has no related patron transaction with
    the status open.

    :return True|False.
    """
    search = NotificationsSearch().filter(
        'term', loan__pid=loan_pid).source(['pid']).scan()
    for record in search:
        transactions_count = PatronTransactionsSearch().filter(
            'term', notification__pid=record.pid).filter(
                'term', status='open').source().count()
        if transactions_count:
            return True
    return False


def get_non_anonymized_loans(patron_pid=None, org_pid=None):
    """Search all loans for non anonymized loans.

    :param patron_pid: optional parameter to filter by patron_pid.
    :param org_pid: optional parameter to filter by organisation.
    :return: loans.
    """
    search = current_circulation.loan_search_cls()\
        .filter('term', to_anonymize=False)\
        .filter('terms', state=[LoanState.CANCELLED, LoanState.ITEM_RETURNED])\
        .source(['pid'])
    if patron_pid:
        search = search.filter('term', patron_pid=patron_pid)
    if org_pid:
        search = search.filter('term', organisation__pid=org_pid)
    for record in search.scan():
        yield Loan.get_record_by_pid(record.pid)


def anonymize_loans(
        patron_pid=None, patron_data=None, org_pid=None,
        dbcommit=False, reindex=False):
    """Anonymise loans.

    :param dbcommit - commit the changes in the db after the creation.
    :param reindex - index the record after the creation.
    :param patron_pid: optional parameter to filter by patron_pid.
    :param org_pid: optional parameter to filter by organisation.
    :param patron_data: patron data to check.
    :return: loans.
    """
    counter = 0
    for loan in get_non_anonymized_loans(
            patron_pid=patron_pid, org_pid=org_pid):
        if Loan.can_anonymize(loan_data=loan, patron_data=patron_data):
            loan.anonymize(loan, dbcommit=dbcommit, reindex=reindex)
            counter += 1
    return counter


class LoansIndexer(IlsRecordsIndexer):
    """Holdings indexing class."""

    record_cls = Loan

    def bulk_index(self, record_id_iterator):
        """Bulk index records.

        :param record_id_iterator: Iterator yielding record UUIDs.
        """
        super().bulk_index(record_id_iterator, doc_type='loan')
