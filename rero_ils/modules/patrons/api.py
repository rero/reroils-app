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

"""API for manipulating patrons."""
from copy import deepcopy
from datetime import datetime
from functools import partial

from flask import current_app
from flask_babelex import gettext as _
from flask_login import current_user
from invenio_circulation.proxies import current_circulation
from werkzeug.local import LocalProxy

from .models import PatronIdentifier, PatronMetadata
from ..api import IlsRecord, IlsRecordsIndexer, IlsRecordsSearch
from ..errors import RecordValidationError
from ..fetchers import id_fetcher
from ..libraries.api import Library
from ..minters import id_minter
from ..organisations.api import Organisation
from ..patron_transactions.api import PatronTransaction
from ..providers import Provider
from ..users.api import User
from ..utils import extracted_data_from_ref, get_patron_from_arguments, \
    get_ref_for_pid, trim_patron_barcode_for_record
from ...utils import create_user_from_data

_datastore = LocalProxy(lambda: current_app.extensions['security'].datastore)

# current logged professionnal
current_librarian = LocalProxy(
    lambda: Patron.get_librarian_by_user(current_user))
# all patron role accounts releated to the current user
current_patrons = LocalProxy(
    lambda: [ptrn for ptrn in Patron.get_patrons_by_user(
        current_user) if 'patron' in ptrn.get('roles', [])])


def create_patron_from_data(data, delete_pid=False, dbcommit=False,
                            reindex=False):
    """Create a patron and a user from a data dict.

    :param data - dictionary representing a library user
    :param dbcommit - commit the changes in the db after the creation
    :param reindex - index the record after the creation
    :returns: - A `Patron` instance
    """
    data = create_user_from_data(data)
    return Patron.create(
        data=data,
        delete_pid=delete_pid,
        dbcommit=dbcommit,
        reindex=reindex)


# provider
PatronProvider = type(
    'PatronProvider',
    (Provider,),
    dict(identifier=PatronIdentifier, pid_type='ptrn')
)
# minter
patron_id_minter = partial(id_minter, provider=PatronProvider)
# fetcher
patron_id_fetcher = partial(id_fetcher, provider=PatronProvider)


class PatronsSearch(IlsRecordsSearch):
    """PatronsSearch."""

    class Meta:
        """Search only on patrons index."""

        index = 'patrons'
        doc_types = None
        fields = ('*', )
        facets = {}

        default_filter = None


class Patron(IlsRecord):
    """Define API for patrons mixing."""

    ROLE_PATRON = 'patron'
    ROLE_LIBRARIAN = 'librarian'
    ROLE_SYSTEM_LIBRARIAN = 'system_librarian'

    ROLES_HIERARCHY = {
        ROLE_PATRON: [],
        ROLE_LIBRARIAN: [],
        ROLE_SYSTEM_LIBRARIAN: [ROLE_LIBRARIAN]
    }

    minter = patron_id_minter
    fetcher = patron_id_fetcher
    provider = PatronProvider
    model_cls = PatronMetadata

    available_roles = [ROLE_SYSTEM_LIBRARIAN, ROLE_LIBRARIAN, ROLE_PATRON]

    def _validate(self, **kwargs):
        """Validate record against schema.

        extended validation per record class
        and test of pid existence.
        """
        json = super()._validate(**kwargs)
        # We only like to run pids_exist_check if validation_message is True
        # and not a string with error from extended_validation
        validation_message = True
        if self.pid_check:
            from ..utils import pids_exists_in_data
            if self.is_patron:
                validation_message = pids_exists_in_data(
                    info=f'{self.provider.pid_type} ({self.pid})',
                    data=self.get('patron'),
                    required={'ptty': 'type'},
                    not_required={}
                ) or True
            if self.is_librarian:
                libraries = self.get('libraries')
                if not libraries:
                    validation_message = 'Missing libraries'
                for library_pid in self.library_pids:
                    library = Library.get_record_by_pid(library_pid)
                    if library is None:
                        validation_message =\
                            f'Library {library_pid} doesn\'t exist.'
                        break
        subscriptions = self.get('patron', {}).get('subscriptions')
        if subscriptions and validation_message:
            for subscription in subscriptions:
                subscription_validation_message = pids_exists_in_data(
                    info=f'{self.provider.pid_type} ({self.pid})',
                    data=subscription,
                    required={
                        'ptty': 'patron_type',
                        'pttr': 'patron_transaction'
                    },
                    not_required={}
                ) or True
                if subscription_validation_message is not True:
                    validation_message = subscription_validation_message
                    break
        self._validate_emails()
        if validation_message is not True:
            raise RecordValidationError(validation_message)
        return json

    def _validate_emails(self):
        """Check if emails are required.

        Check if the user has at least one email if the communication channel
        is email.
        """
        patron = self.get('patron')
        user = self._get_user_by_user_id(self.get('user_id'))
        if patron and patron.get('communication_channel') == 'email'\
           and user.email is None\
           and patron.get('additional_communication_email') is None:
            raise RecordValidationError('At least one email should be defined '
                                        'for an email communication channel.')

    @classmethod
    def create(cls, data, id_=None, delete_pid=False,
               dbcommit=False, reindex=False,
               **kwargs):
        """Patron record creation.

        :param cls - class object
        :param data - dictionary representing a library user
        :param id_ - UUID, it would be generated if it is not given
        :param delete_pid - remove the pid present in the data if True
        :param dbcommit - commit the changes in the db after the creation
        :param reindex - index the record after the creation
        :param email_notification - send a reset password link to the user
        """
        # remove spaces
        data = trim_patron_barcode_for_record(data=data)
        record = super().create(
                data, id_, delete_pid, dbcommit, reindex, **kwargs)
        record._update_roles()
        return record

    def update(self, data, dbcommit=False, reindex=False):
        """Update data for record."""
        # remove spaces
        data = trim_patron_barcode_for_record(data=data)
        super().update(data, dbcommit, reindex)
        self._update_roles()
        return self

    def delete(self, force=False, dbcommit=False, delindex=False):
        """Delete record and persistent identifier."""
        self._remove_roles()
        super().delete(force, dbcommit, delindex)
        return self

    @classmethod
    def load(cls, data):
        """Load the data and remove the user data."""
        return cls(cls.removeUserData(data))

    @classmethod
    def removeUserData(cls, data):
        """Remove the user data."""
        data = deepcopy(data)
        profile_fields = User.profile_fields + ['username', 'email']
        for field in profile_fields:
            try:
                del data[field]
            except KeyError:
                pass
        return data

    def dumps(self, **kwargs):
        """Return pure Python dictionary with record metadata."""
        user = User.get_by_id(self['user_id'])
        user_info = user.dumpsMetadata()
        dump = super().dumps(**kwargs)
        # role should comes from the patron
        user_info.update(dump)
        return user_info

    @classmethod
    def _get_user_by_user_id(cls, user_id):
        """Get the user using a dict representing a patron.

        Try to get an existing user by: user_id, email, username.
        :param cls: Class itself.
        :param data: dict representing a patron.
        :return: a patron object or None.
        """
        return _datastore.find_user(id=user_id)

    # TODO: use cached property one we found how to invalidate the cache when
    #       the user change
    @property
    def user(self):
        """Invenio user of a patron."""
        return self._get_user_by_user_id(self.get('user_id'))

    def get_patrons_roles(self, exclude_self=False):
        """Get the list of roles for all accounts of the related user."""
        patrons = self.get_patrons_by_user(self.user)
        roles = set()
        if not exclude_self:
            roles = set(self.get('roles'))
        for patron in patrons:
            # already there
            if patron == self:
                continue
            roles.update(patron.get('roles', []))
        return list(roles)

    def _update_roles(self):
        """Update user roles."""
        db_roles = self.user.roles
        # all the roles of all patron accounts related to the current user
        patron_roles = self.get_patrons_roles()
        for role in self.available_roles:
            in_db = role in db_roles
            in_record = role in patron_roles
            if in_record and not in_db:
                self.add_role(role)
            if not in_record and in_db:
                self.remove_role(role)

    def _remove_roles(self):
        """Remove roles."""
        # soft delete before hard delete
        if not self.user:
            return
        db_roles = self.user.roles
        # all the roles of all other patron accounts related to the
        # current user
        external_patron_roles = self.get_patrons_roles(exclude_self=True)
        # roles only on the current patron account
        for role in [r for r in self.get('roles')
                     if r not in external_patron_roles]:
            if role in db_roles:
                self.remove_role(role)

    @classmethod
    def get_all_pids_for_organisation(cls, organisation_pid):
        """Get all patron pids for a specific organisation."""
        query = PatronsSearch()\
            .filter('term', organisation__pid=organisation_pid)\
            .source(includes='pid')\
            .scan()
        for hit in query:
            yield hit['pid']

    @classmethod
    def get_librarian_by_user(cls, user):
        """Get patron with a role librarian or system_librarian by user."""
        patrons = cls.get_patrons_by_user(user)
        librarians = list(filter(lambda ptrn: ptrn.is_librarian, patrons))
        if len(librarians) > 1:
            raise Exception('more than one librarian account for a user')
        if len(librarians) == 0:
            return None
        return librarians[0]

    @classmethod
    def get_patrons_by_user(cls, user):
        """Get all patrons by user."""
        patrons = []
        if hasattr(user, 'id'):
            result = PatronsSearch()\
                .filter('term', user_id=user.id)\
                .source(includes='pid')\
                .scan()
            patrons = [cls.get_record_by_pid(hit.pid) for hit in result]
        return patrons

    @classmethod
    def get_patron_by_email(cls, email):
        """Get patron by email."""
        pid_value = cls.get_pid_by_email(email)
        if pid_value:
            return cls.get_record_by_pid(pid_value)

    @classmethod
    def get_pid_by_email(cls, email):
        """Get uuid pid by email."""
        result = PatronsSearch()\
            .filter('term', email=email)\
            .source(includes='pid').scan()
        try:
            return next(result).pid
        except StopIteration:
            return None

    @classmethod
    def get_patron_by_barcode(cls, barcode=None, filter_by_org_pid=None):
        """Get patron by barcode."""
        if not barcode:
            return None
        search = PatronsSearch()\
            .filter('term', patron__barcode=barcode)
        if filter_by_org_pid is not None:
            search = search.filter('term', organisation__pid=filter_by_org_pid)
        result = search.source(includes='pid').scan()
        try:
            patron_pid = next(result).pid
            return super().get_record_by_pid(patron_pid)
        except StopIteration:
            return None

    @classmethod
    def can_request(cls, item, **kwargs):
        """Check if a paton can request an item.

        :param item : the item to check
        :param kwargs : To be relevant, additional arguments should contains
                        'patron' argument.
        :return a tuple with True|False and reasons to disallow if False.
        """
        patron = get_patron_from_arguments(**kwargs)
        if not patron:
            # 'patron' argument are present into kwargs. This check can't
            # be relevant --> return True by default
            return True, []

        messages = []
        # 1) a blocked patron can't request any item
        # 2) a patron with obsolete expiration_date can't request any item
        if patron.is_blocked:
            messages.append(patron.get_blocked_message())
        if patron.is_expired:
            messages.append(_('Patron rights expired.'))

        return len(messages) == 0, messages

    @classmethod
    def can_checkout(cls, item, **kwargs):
        """Check if a patron can checkout an item."""
        # Same logic than can_request :: a blocked patron can't do a checkout
        return cls.can_request(item, **kwargs)

    @classmethod
    def can_extend(cls, item, **kwargs):
        """Check if a patron can extend a loan."""
        # Same logic than can_request :: a blocked patron can't extend a loan
        return cls.can_request(item, **kwargs)

    @classmethod
    def patrons_with_obsolete_subscription_pids(cls, end_date=None):
        """Search about patrons with obsolete subscription."""
        if end_date is None:
            end_date = datetime.now()
        end_date = end_date.strftime('%Y-%m-%d')
        results = PatronsSearch()\
            .filter('range', patron__subscriptions__end_date={'lt': end_date})\
            .source('pid')\
            .scan()
        for result in results:
            yield Patron.get_record_by_pid(result.pid)

    @classmethod
    def get_patrons_without_subscription(cls, patron_type_pid):
        """Get patrons linked to patron_type that haven't any subscription."""
        query = PatronsSearch() \
            .filter('term', patron__type__pid=patron_type_pid) \
            .exclude('exists', field='patron.subscriptions')
        for res in query.source('pid').scan():
            yield Patron.get_record_by_pid(res.pid)

    def add_role(self, role_name):
        """Add a given role to a user."""
        role = _datastore.find_role(role_name)
        _datastore.add_role_to_user(self.user, role)
        _datastore.commit()

    def remove_role(self, role_name):
        """Remove a given role from a user."""
        role = _datastore.find_role(role_name)
        _datastore.remove_role_from_user(self.user, role)
        _datastore.commit()

    @property
    def patron(self):
        """Patron property shortcut."""
        return self.get('patron', {})

    @property
    def expiration_date(self):
        """Shortcut to find the patron expiration date."""
        date_string = self.patron.get('expiration_date')
        if date_string:
            return datetime.strptime(date_string, '%Y-%m-%d')

    @property
    def is_expired(self):
        """Check if patron expiration date is obsolete."""
        expiration_date = self.expiration_date
        return expiration_date and datetime.now() > expiration_date

    @property
    def formatted_name(self):
        """Return the best possible human readable patron name."""
        profile = self.user.profile
        name_parts = [
            profile.last_name.strip(),
            profile.first_name.strip()
        ]
        name_parts = [part for part in name_parts if part]  # remove empty part
        return ', '.join(name_parts)

    @property
    def patron_type_pid(self):
        """Shortcut for patron type pid."""
        if self.get('patron', {}).get('type'):
            return extracted_data_from_ref(self.get('patron').get('type'))

    def get_number_of_loans(self):
        """Get number of loans."""
        from ..loans.api import LoanState
        exclude_states = [
            LoanState.CANCELLED, LoanState.ITEM_RETURNED]
        if self.pid:
            results = current_circulation.loan_search_cls()\
                .filter('term', patron_pid=self.pid)\
                .exclude('terms', state=exclude_states)\
                .source().count()
            return results
        return 0

    def get_links_to_me(self):
        """Get number of links."""
        links = {}
        loans = self.get_number_of_loans()
        if loans:
            links['loans'] = loans
        if self.pid:
            transactions = PatronTransaction.get_transactions_count_for_patron(
                self.pid, status='open')
            if transactions > 0:
                links['transactions'] = transactions
        return links

    def reasons_to_keep(self):
        """Reasons aside from record_links to keep a user.

        prevent users with role librarian to delete a system_librarian.
        """
        others = {}
        if current_librarian:
            if not current_librarian.is_system_librarian and \
               self.is_system_librarian:
                others['permission denied'] = True
        return others

    def reasons_not_to_delete(self):
        """Get reasons not to delete policy."""
        cannot_delete = {}
        others = self.reasons_to_keep()
        links = self.get_links_to_me()
        if others:
            cannot_delete['others'] = others
        if links:
            cannot_delete['links'] = links
        return cannot_delete

    def get_organisation(self):
        """Return organisation."""
        return Organisation.get_record_by_pid(self.organisation_pid)

    @property
    def library_pid(self):
        """Shortcut for patron library pid."""
        if self.library_pids:
            return self.library_pids[0]

    @property
    def library_pids(self):
        """Shortcut for patron libraries pid."""
        if self.is_librarian:
            pids = []
            for library in self.get('libraries', []):
                pids.append(extracted_data_from_ref(library))
            return pids

    @property
    def is_system_librarian(self):
        """Shortcut to check if user has system_librarian role."""
        return Patron.ROLE_SYSTEM_LIBRARIAN in self.get('roles', [])

    @property
    def is_librarian(self):
        """Shortcut to check if user has librarian role."""
        librarian_roles = [Patron.ROLE_SYSTEM_LIBRARIAN, Patron.ROLE_LIBRARIAN]
        return any(role in librarian_roles for role in self.get('roles', []))

    @property
    def is_patron(self):
        """Shortcut to check if user has patron role."""
        return Patron.ROLE_PATRON in self.get('roles', [])

    @property
    def is_blocked(self):
        """Shortcut to know if user is blocked."""
        return self.patron.get('blocked', False)

    def get_blocked_message(self, public=False):
        """Get the message in case of patron is blocked.

        :param public: Is the message is for public interface ?
        """
        main = _('Your account is currently blocked.') if public \
            else _('This patron is currently blocked.')
        if self.is_blocked:
            return '{main} {reason_str}: {reason}'.format(
                main=main,
                reason_str=_('Reason'),
                reason=self.patron.get('blocked_note')
            )

    @property
    def organisation_pid(self):
        """Get organisation pid for patron with first library."""
        if self.library_pid:
            library = Library.get_record_by_pid(self.library_pid)
            return library.organisation_pid
        patron_type_pid = self.patron_type_pid
        if patron_type_pid:
            from ..patron_types.api import PatronType
            patron_type = PatronType.get_record_by_pid(patron_type_pid)
            return patron_type.organisation_pid
        return None

    @property
    def has_valid_subscription(self):
        """Check if the patron has a valid subscription at current time.

        To know if the user has a valid subscription, we need to check the
        patron_type linked to it. If the patron type request a subscription,
        then we need to check the patron subscription attributes to find a
        subscription in a valid interval of time.
        """
        from ..patron_types.api import PatronType
        if self.patron_type_pid:
            patron_type = PatronType.get_record_by_pid(self.patron_type_pid)
            if patron_type.is_subscription_required:
                for sub in self.get('patron', {}).get('subscriptions', []):
                    # not need to check if the subscription is for the
                    # current patron.patron_type. If patron.patron_type
                    # change while a subscription is still pending, this
                    # subscription is still valid
                    start = datetime.strptime(sub['start_date'], '%Y-%m-%d')
                    end = datetime.strptime(sub['end_date'], '%Y-%m-%d')
                    if start < datetime.now() < end:
                        return True
                return False
        return True

    def get_valid_subscriptions(self):
        """Get valid subscriptions for a patron."""
        def is_subscription_valid(subscription):
            start = datetime.strptime(subscription['start_date'], '%Y-%m-%d')
            end = datetime.strptime(subscription['end_date'], '%Y-%m-%d')
            return start < datetime.now() < end
        subs = filter(
            is_subscription_valid,
            self.get('patron', {}).get('subscriptions', []))
        return list(subs)

    def add_subscription(self, patron_type, start_date, end_date,
                         dbcommit=True, reindex=True, delete_pids=False):
        """Add a subscription to a patron type.

        :param patron_type: the patron_type linked to the subscription
        :param start_date: As `datetime`, the subscription start date
        :param end_date: As `datetime`, the subscription end date (excluded)
        """
        transaction = PatronTransaction.create_subscription_for_patron(
            self, patron_type, start_date, end_date,
            dbcommit=dbcommit, reindex=reindex, delete_pid=delete_pids)
        if transaction:
            subscriptions = self.get('patron', {}).get('subscriptions', [])
            subscriptions.append({
                'patron_type': {
                    '$ref': get_ref_for_pid('ptty', patron_type.pid)
                },
                'patron_transaction': {
                    '$ref': get_ref_for_pid('pttr', transaction.pid)
                },
                'start_date': start_date.strftime('%Y-%m-%d'),
                'end_date': end_date.strftime('%Y-%m-%d'),
            })
            self['patron']['subscriptions'] = subscriptions
            self.update(self, dbcommit=dbcommit, reindex=reindex)

    def get_pending_subscriptions(self):
        """Get the pending subscriptions for a patron."""
        # Not need to use a generator to get pending subscriptions.
        # In a normal process, the maximum number of subscriptions for a patron
        # is two : current subscription and possibly next one.
        pending_subs = []
        for sub in self.get('patron', {}).get('subscriptions', []):
            trans_pid = extracted_data_from_ref(
                sub['patron_transaction'], data='pid')
            transaction = PatronTransaction.get_record_by_pid(trans_pid)
            if transaction.status == 'open':
                pending_subs.append(sub)
        return pending_subs

    def transaction_user_validator(self, user_pid):
        """Validate that the given transaction user PID is valid.

        Add additional validation later if needed.

        :param user_pid: user pid to validate.
        :returns: True if valid user otherwise false.
        """
        return Patron.record_pid_exists(user_pid)

    def get_circulation_messages(self, public=False):
        """Return messages useful for circulation.

        * check if the user is blocked ?
        * check if the user reaches the maximum loans limit ?
        * check if the user reaches the maximum fee amount limit ?

        :param public: is messages are for public interface ?
        :return an array of messages. Each message is a dictionary with a level
                and a content. The level could be used to filters messages if
                needed.
        """
        from ..patron_types.api import PatronType

        # if patron is blocked - error type message
        #   if patron is blocked, no need to return any other circulation
        #   messages !
        if self.is_blocked:
            return [{
                'type': 'error',
                'content': self.get_blocked_message(public)
            }]

        messages = []
        # if patron expiration_date has reached - error type message
        if self.is_expired:
            messages.append({
                'type': 'error',
                'content': _('Patron rights expired.')
            })

        # other messages must be only rendered for the professional interface
        if not public:
            # check the patron type define limit
            patron_type = PatronType.get_record_by_pid(self.patron_type_pid)
            valid, message = patron_type.check_checkout_count_limit(self)
            if not valid:
                messages.append({
                    'type': 'error',
                    'content': message
                })
            # check fee amount limit
            if not patron_type.check_fee_amount_limit(self):
                messages.append({
                    'type': 'error',
                    'content': _(
                        'Transactions denied: the maximal overdue fee amount '
                        'is reached.')
                })
            # check the patron type overdue limit
            if not patron_type.check_overdue_items_limit(self):
                messages.append({
                    'type': 'error',
                    'content': _('Checkout denied: the maximal number of '
                                 'overdue items is reached')
                })
        return messages


class PatronsIndexer(IlsRecordsIndexer):
    """Holdings indexing class."""

    record_cls = Patron

    def bulk_index(self, record_id_iterator):
        """Bulk index records.

        :param record_id_iterator: Iterator yielding record UUIDs.
        """
        super().bulk_index(record_id_iterator, doc_type='ptrn')
