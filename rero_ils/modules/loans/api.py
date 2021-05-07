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
import math
from bisect import bisect_right
from datetime import datetime, timedelta, timezone

import ciso8601
from elasticsearch_dsl import A
from flask import current_app
from flask_babelex import gettext as _
from invenio_circulation.errors import MissingRequiredParameterError
from invenio_circulation.pidstore.fetchers import loan_pid_fetcher
from invenio_circulation.pidstore.minters import loan_pid_minter
from invenio_circulation.pidstore.providers import CirculationLoanIdProvider
from invenio_circulation.proxies import current_circulation
from invenio_circulation.search.api import search_by_patron_item_or_document
from invenio_circulation.utils import str2datetime
from invenio_jsonschemas import current_jsonschemas

from rero_ils.modules.circ_policies.api import CircPolicy

from ..api import IlsRecord, IlsRecordError, IlsRecordsIndexer, \
    IlsRecordsSearch
from ..errors import NoCirculationActionIsPermitted
from ..items.models import ItemStatus
from ..items.utils import item_pid_to_object
from ..libraries.api import Library
from ..locations.api import Location
from ..notifications.api import Notification, NotificationsSearch, \
    number_of_reminders_sent
from ..patron_transactions.api import PatronTransactionsSearch
from ..patrons.api import Patron
from ..utils import date_string_to_utc, get_ref_for_pid
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

    class Meta:
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
        super().__init__(data, model)

    @classmethod
    def can_extend(cls, item, **kwargs):
        """Loan can extend."""
        from rero_ils.modules.loans.utils import extend_loan_data_is_valid
        if 'loan' not in kwargs:  # this method is not relevant
            return True, []
        loan = kwargs['loan']
        if loan.get('state') != LoanState.ITEM_ON_LOAN:
            return False, [_('The loan cannot be extended')]
        patron = Patron.get_record_by_pid(loan.get('patron_pid'))
        cipo = CircPolicy.provide_circ_policy(
            item.organisation_pid,
            item.library_pid,
            patron.patron_type_pid,
            item.item_type_circulation_category_pid
        )
        extension_count = loan.get('extension_count', 0)
        if not (cipo.get('number_renewals', 0) > 0 and
                extension_count < cipo.get('number_renewals', 0) and
                extend_loan_data_is_valid(
                    loan.get('end_date'),
                    cipo.get('renewal_duration'),
                    item.library_pid
               )):
            return False, [_('Circulation policies disallows the operation.')]
        if item.number_of_requests():
            return False, [_('A pending request exists on this item.')]
        return True, []

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
            message = f'Parameters {missing_params} are required'
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
        # default state assignment
        data.setdefault(
            'state',
            current_app.config['CIRCULATION_LOAN_INITIAL_STATE']
        )
        if delete_pid and data.get(cls.pid_field):
            del(data[cls.pid_field])
        cls._loan_build_org_ref(data)
        # set the field to_anonymize
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
        if self.state != LoanState.ITEM_ON_LOAN:
            return False

        circ_policy = get_circ_policy(self)
        now = datetime.now(timezone.utc)
        due_date = ciso8601.parse_datetime(self.end_date)
        days_after = circ_policy.initial_overdue_days
        if days_after and now > due_date + timedelta(days=days_after-1):
            return True
        return False

    def is_loan_due_soon(self, tstamp=None):
        """Check if a loan is due soon."""
        from .utils import get_circ_policy
        if self.state != LoanState.ITEM_ON_LOAN:
            return False

        circ_policy = get_circ_policy(self)
        date = tstamp or datetime.now(timezone.utc)
        due_date = ciso8601.parse_datetime(self.end_date).replace(
            tzinfo=timezone.utc)

        days_before = circ_policy.due_soon_interval_days
        if days_before:
            return due_date > date > due_date - timedelta(days=days_before)
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
    def state(self):
        """Shortcut for state."""
        return self.get('state')

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
    def overdue_date(self):
        """Get the date when the loan should be considerate as 'overdue'."""
        if self.end_date:
            d_after = date_string_to_utc(self.end_date) + timedelta(days=1)
            return datetime(
                year=d_after.year, month=d_after.month, day=d_after.day,
                tzinfo=timezone.utc
            )

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

    @property
    def get_overdue_fees(self):
        """Get all overdue fees based based on incremental fees setting.

        :return An array of tuple. Each tuple are composed with two values :
                the fee amount and a related timestamp.
                Ex: [
                  (0.1, datetime.date('2021-01-28')),
                  (0.1, datetime.date('2021-01-29')),
                  (0.5, datetime.date('2021-01-30')),
                  ...
                ]
        """
        from .utils import get_circ_policy
        fees = []
        # if the loan isn't overdue, no need to continue.
        if not self.is_loan_overdue():
            return fees

        # find the circulation policy corresponding to the loan and check if
        # some 'overdue_fees' settings exists. If not, no need to continue.
        cipo = get_circ_policy(self)
        overdue_settings = cipo.get('overdue_fees')
        if overdue_settings is None:
            return fees

        # At this point, we know that we need to compute an overdue amount.
        # Initialize some useful variables to perform the job.
        loan_lib = Library.get_record_by_pid(self.library_pid)
        # add 1 day to end_date because the first overdue_date is next day
        # after the due date
        end_date = date_string_to_utc(self.end_date) + timedelta(days=1)
        end_date = end_date
        total = 0
        max_overdue = overdue_settings.get('maximum_total_amount', math.inf)
        intervals = cipo.get_overdue_intervals()
        interval_lower_bounds = [inter['from'] for inter in intervals]

        # For each overdue day, we need to find the correct fee_amount to
        # charge. In the bellowed loop, `day_idx' is the day number from the
        # due date ; `day` is the datetime of this day

        for day_idx, day in enumerate(loan_lib.get_open_days(end_date), 1):
            # a) find the correct interval.
            # b) check the index found exist into intervals
            # c) check the upper limit of this interval is grower or equal
            #    to day index
            interval_idx = bisect_right(interval_lower_bounds, day_idx)-1
            if interval_idx == -1:
                continue
            if day_idx > intervals[interval_idx]['to']:
                continue
            # d) add the corresponding fee_amount to the fees array.
            # e) if maximum_overdue is reached, exit the loop
            fee_amount = intervals[interval_idx]['fee_amount']
            gap = round(max_overdue - total, 2)
            if fee_amount > gap:
                fee_amount = gap
            total = round(math.fsum([total, fee_amount]), 2)
            fees.append((fee_amount, day))
            if max_overdue <= total:
                break
        return fees

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

    def is_notified(self, notification_type=None, counter=0):
        """Check if a notification already exists for a loan by type."""
        return number_of_reminders_sent(
            self, notification_type=notification_type) > counter

    def create_notification(self, notification_type=None, counter=0):
        """Creates a notification from base on a loan.

        :param notification_type: the notification type to create.
        :param counter: the reminder counter to use (for OVERDUE notification)
        """
        if (self.get('state') == LoanState.ITEM_ON_LOAN or
            notification_type == Notification.AVAILABILITY_NOTIFICATION_TYPE) \
           and not self.is_notified(notification_type, counter):
            record = {
                'creation_date': datetime.now(timezone.utc).isoformat(),
                'notification_type': notification_type,
                'loan': {
                    '$ref': get_ref_for_pid('loans', self.pid)
                },
                'reminder_counter': counter
            }
            notification = Notification.create(
                data=record, dbcommit=True, reindex=True)
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
    def can_anonymize(cls, loan_data=None, patron=None):
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
        if not patron:
            patron = Patron.get_record_by_pid(loan_data.get('patron_pid'))
        keep_history = patron.user.profile.keep_history
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


def get_due_soon_loans(tstamp=None):
    """Return all due_soon loans."""
    due_soon_loans = []
    results = current_circulation.loan_search_cls()\
        .filter('term', state=LoanState.ITEM_ON_LOAN)\
        .params(preserve_order=True)\
        .sort({'_created': {'order': 'asc'}})\
        .source(['pid']).scan()
    for record in results:
        loan = Loan.get_record_by_pid(record.pid)
        if loan.is_loan_due_soon(tstamp):
            due_soon_loans.append(loan)
    return due_soon_loans


def get_overdue_loan_pids(patron_pid=None, tstamp=None):
    """Return all overdue loan pids optionally filtered for a patron pid.

    :param patron_pid: the patron pid. If none, return all overdue loans.
    :param tstamp: a timestamp to define the execution time of the function.
                   Default to `datetime.now()`.
    :return a generator of loan pid
    """
    end_date = tstamp or datetime.now()
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


def get_overdue_loans(patron_pid=None, tstamp=None):
    """Return all overdue loans optionally filtered for a patron pid.

    :param patron_pid: the patron pid. If none, return all overdue loans.
    :param tstamp: a timestamp to define the execution time of the function
    :return a generator of Loan
    """
    for pid in get_overdue_loan_pids(patron_pid, tstamp):
        yield Loan.get_record_by_pid(pid)


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


def get_non_anonymized_loans(patron=None, org_pid=None):
    """Search all loans for non anonymized loans.

    :param patron_pid: optional parameter to filter by patron_pid.
    :param org_pid: optional parameter to filter by organisation.
    :return: loans.
    """
    search = current_circulation.loan_search_cls()\
        .filter('term', to_anonymize=False)\
        .filter('terms', state=[LoanState.CANCELLED, LoanState.ITEM_RETURNED])\
        .source(['pid'])
    if patron:
        search = search.filter('term', patron_pid=patron.pid)
    if org_pid:
        search = search.filter('term', organisation__pid=org_pid)
    for record in search.scan():
        yield Loan.get_record_by_pid(record.pid)


def anonymize_loans(
        patron=None, org_pid=None,
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
            patron=patron, org_pid=org_pid):
        if Loan.can_anonymize(loan_data=loan, patron=patron):
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
