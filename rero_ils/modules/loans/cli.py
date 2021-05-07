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

"""Click command-line interface for item record management."""

from __future__ import absolute_import, print_function

import json
import os
import random
import traceback
from datetime import datetime, timedelta, timezone

import click
from flask.cli import with_appcontext
from invenio_circulation.api import get_loan_for_item

from ..circ_policies.api import CircPolicy
from ..items.api import Item, ItemsSearch
from ..items.models import ItemStatus
from ..items.utils import item_pid_to_object
from ..libraries.api import Library
from ..loans.api import Loan
from ..locations.api import Location
from ..notifications.api import Notification
from ..notifications.dispatcher import Dispatcher
from ..notifications.tasks import create_notifications
from ..patron_transaction_events.api import PatronTransactionEvent
from ..patron_transactions.api import PatronTransaction
from ..patron_types.api import PatronType
from ..patrons.api import Patron, PatronsSearch
from ..utils import extracted_data_from_ref, get_ref_for_pid, \
    get_schema_for_resource, read_json_record


def check_missing_fields(transaction, transaction_type):
    """Return list of missing fields for a given transaction type.

    transaction: the json transaction record.
    transaction_type: type of transaction.
    """
    if transaction_type == 'checkout':
        fields = ['item_pid', 'patron_pid', 'end_date', 'transaction_date',
                  'transaction_location_pid', 'transaction_user_pid',
                  'organisation', 'start_date']
    elif transaction_type == 'request':
        fields = ['item_pid', 'patron_pid', 'organisation', 'transaction_date',
                  'pickup_location_pid', 'transaction_location_pid',
                  'transaction_user_pid', 'request_expire_date']
    elif transaction_type == 'fine':
        fields = ['note', 'type', 'patron', 'status', 'organisation',
                  'total_amount', 'creation_date']

    return [field for field in fields if field not in transaction]


def build_loan_record(transaction, transaction_type, item):
    """Build the loan record before inserting into db.

    transaction: the json transaction record.
    transaction_type: type of transaction.
    item: the item record.
    """
    if transaction_type == 'checkout':
        transaction['state'] = 'ITEM_ON_LOAN'
        transaction['trigger'] = 'checkout'
        transaction['document_pid'] = item.document_pid
        transaction['to_anonymize'] = False
        transaction['item_pid'] = {'value': transaction.get('item_pid'),
                                   'type': 'item'}
    elif transaction_type == 'request':
        transaction['state'] = 'PENDING'
        transaction['trigger'] = 'request'
        transaction['item_pid'] = {'value': transaction.get('item_pid'),
                                   'type': 'item'}
        transaction['document_pid'] = item.document_pid
        transaction['to_anonymize'] = False


@click.command('load_virtua_transactions')
@click.option('-l', '--lazy', 'lazy', is_flag=True, default=False)
@click.option('-e', '--save_errors', 'save_errors', type=click.File('w'))
@click.option('-t', '--transaction_type', 'transaction_type', is_flag=False,
              default='checkout')
@click.option('-v', '--verbose', 'verbose', is_flag=True, default=False)
@click.option('-d', '--debug', 'debug', is_flag=True, default=False)
@click.argument('infile', type=click.File('r'))
@with_appcontext
def load_virtua_transactions(
        infile, lazy, save_errors, transaction_type, verbose, debug):
    """Load Virtua circulation transactions.

    infile: Json Virtua transactions file.
    transaction_type: Transaction type either checkout, request or fine.
    :param lazy: lazy reads file.
    :param save_errors: save error records to file.
    """
    # TODO: move this method and other similar methods to a new project that
    # deals with loading data from other ILS into REROILS.
    if save_errors:
        name, ext = os.path.splitext(infile.name)
        err_file_name = f'{name}_errors{ext}'
        error_file = open(err_file_name, 'w')
        error_file.write('[\n')

    if lazy:
        records = read_json_record(infile)
    else:
        file_data = json.load(infile)
    text = 'Loading Virtua transactions of type {transaction_type}'.format(
            transaction_type=transaction_type
        )
    click.secho(text, fg='green')

    counter = 0
    for transaction in file_data:
        counter = counter + 1
        missing_fields = check_missing_fields(transaction, transaction_type)
        if missing_fields:
            text = '\ntransaction # {counter} missing fields: {fields}'.format(
                    fields=missing_fields,
                    counter=counter
                )
            click.secho(text, fg='red')
            if save_errors:
                error_file.write(json.dumps(transaction, indent=2))
            continue

        if transaction_type == 'fine':
            patron_pid = extracted_data_from_ref(transaction.get('patron'))
            patron = Patron.get_record_by_pid(patron_pid)
            if not patron:
                text = '\ntransaction # {counter} patron not in db'.format(
                        counter=counter)
                click.secho(text, fg='red')
                if save_errors:
                    error_file.write(json.dumps(transaction, indent=2))
                continue

            try:
                PatronTransaction.create(
                    transaction, dbcommit=True, reindex=True)
                click.secho(
                    '\ntransaction # {counter} created'.format(
                        counter=counter
                    ),
                    fg='green'
                )
            except Exception as error:
                text = 'transaction# {counter} failed creation {error}'.format(
                        counter=counter,
                        error=error
                    )
                click.secho(text, fg='red')
                if save_errors:
                    error_file.write(json.dumps(transaction, indent=2))

        elif transaction_type in ['checkout', 'request']:
            item = Item.get_record_by_pid(transaction.get('item_pid'))
            patron = Patron.get_record_by_pid(transaction.get('patron_pid'))
            if not (item and patron):
                text = '\ntransaction# {counter} item/patron not in db'.format(
                        counter=counter
                    )
                click.secho(text, fg='red')
                if save_errors:
                    error_file.write(json.dumps(transaction, indent=2))
                    continue
            else:
                build_loan_record(transaction, transaction_type, item)
            try:
                Loan.create(transaction, dbcommit=True, reindex=True)
                click.secho(
                    '\ntransaction # {counter} created'.format(
                        counter=counter
                    ),
                    fg='green'
                )
            except Exception as error:
                text = 'transaction# {counter} failed creation {error}'.format(
                        counter=counter,
                        error=error
                    )
                click.secho(text, fg='red')
                if save_errors:
                    error_file.write(json.dumps(transaction, indent=2))
    if save_errors:
        error_file.write(']')
        error_file.close()


@click.command('create_loans')
@click.option('-v', '--verbose', 'verbose', is_flag=True, default=False)
@click.option('-d', '--debug', 'debug', is_flag=True, default=False)
@click.argument('infile', type=click.File('r'))
@with_appcontext
def create_loans(infile, verbose, debug):
    """Create circulation transactions.

    infile: Json transactions file
    """
    click.secho('Create circulation transactions:', fg='green')
    data = json.load(infile)
    errors_count = {}
    to_block = []
    for patron_data in data:
        barcode = patron_data.get('barcode')
        if barcode is None:
            click.secho('Patron barcode is missing!', fg='red')
        else:
            click.echo(f'Patron: {barcode}')
            loans = patron_data.get('loans', {})
            requests = patron_data.get('requests', {})
            blocked = patron_data.get('blocked', False)
            if blocked:
                to_block.append(patron_data)
            patron_type_pid = Patron.get_patron_by_barcode(
                barcode).patron_type_pid
            loanable_items = get_loanable_items(patron_type_pid)
            if verbose:
                loanable_items_count = len(
                    list(get_loanable_items(patron_type_pid))
                )
                msg = f'\t{patron_data} loanable_items: {loanable_items_count}'
                click.echo(msg)

            for transaction in range(loans.get('active', 0)):
                item_barcode = create_loan(
                    barcode, 'active',
                    loanable_items,
                    verbose,
                    debug
                )
                errors_count = print_message(item_barcode, 'active',
                                             errors_count)

            for transaction in range(loans.get('overdue_active', 0)):
                item_barcode = create_loan(
                    barcode, 'overdue_active',
                    loanable_items,
                    verbose,
                    debug
                )
                errors_count = print_message(item_barcode, 'overdue_active',
                                             errors_count)

            for transaction in range(loans.get('overdue_paid', 0)):
                item_barcode = create_loan(
                    barcode, 'overdue_paid',
                    loanable_items,
                    verbose,
                    debug
                )
                errors_count = print_message(item_barcode, 'overdue_paid',
                                             errors_count)

            for transaction in range(loans.get('extended', 0)):
                item_barcode = create_loan(
                    barcode, 'extended',
                    loanable_items,
                    verbose,
                    debug
                )
                errors_count = print_message(item_barcode, 'extended',
                                             errors_count)

            for transaction in range(loans.get('requested_by_others', 0)):
                item_barcode = create_loan(
                    barcode, 'requested_by_others',
                    loanable_items,
                    verbose,
                    debug
                )
                errors_count = print_message(item_barcode,
                                             'requested_by_others',
                                             errors_count)

            for transaction in range(requests.get('requests', 0)):
                item_barcode = create_request(barcode, 'requests',
                                              loanable_items, verbose, debug)
                errors_count = print_message(item_barcode, 'requests',
                                             errors_count)

            for transaction in range(requests.get('rank_1', 0)):
                item_barcode = create_request(barcode, 'rank_1',
                                              loanable_items, verbose, debug)
                errors_count = print_message(item_barcode, 'rank_1',
                                             errors_count)

            for transaction in range(requests.get('rank_2', 0)):
                item_barcode = create_request(barcode, 'rank_2',
                                              loanable_items, verbose, debug)
                errors_count = print_message(item_barcode, 'rank_2',
                                             errors_count)
    # create due soon notifications, overdue notifications are auto created.
    # block given patron
    for patron_data in to_block:
        barcode = patron_data.get('barcode')
        patron = Patron.get_patron_by_barcode(barcode)
        patron['patron']['blocked'] = True
        patron['patron']['blocked_note'] = patron_data.get('blocked', "")
        patron.update(
            patron,
            dbcommit=True,
            reindex=True
        )
    for transaction_type, count in errors_count.items():
        click.secho(f'Errors {transaction_type}: {count}', fg='red')
    result = create_notifications(
        types=[
            Notification.DUE_SOON_NOTIFICATION_TYPE,
            Notification.OVERDUE_NOTIFICATION_TYPE
        ],
        verbose=verbose
    )
    click.echo(result)


def print_message(item_barcode, transaction_type, errors_count):
    """Print confirmation message."""
    if item_barcode:
        click.echo(f'\titem {item_barcode}: {transaction_type}')
    else:
        click.secho(f'\tcreation error: {transaction_type}', fg='red')
        errors_count.setdefault(transaction_type, 0)
        errors_count[transaction_type] += 1
    return errors_count


def create_loan(barcode, transaction_type, loanable_items, verbose=False,
                debug=False):
    """Create loans transactions."""
    notification_pids = []
    try:
        item = next(loanable_items)
        patron = Patron.get_patron_by_barcode(barcode=barcode)
        transaction_date = datetime.now(timezone.utc).isoformat()
        user_pid, user_location = \
            get_random_librarian_and_transaction_location(patron)
        item.checkout(
            patron_pid=patron.pid,
            transaction_user_pid=user_pid,
            transaction_location_pid=user_location,
            transaction_date=transaction_date,
            document_pid=extracted_data_from_ref(item.get('document')),
            item_pid=item.pid,
        )
        loan = get_loan_for_item(item_pid_to_object(item.pid))
        loan_pid = loan.get('pid')
        loan = Loan.get_record_by_pid(loan_pid)
        if transaction_type == 'overdue_active':
            end_date = datetime.now(timezone.utc) - timedelta(days=2)
            loan['end_date'] = end_date.isoformat()
            loan.update(
                loan,
                dbcommit=True,
                reindex=True
            )
            notification = loan.create_notification(
                notification_type='due_soon')
            if notification:
                notification_pids.append(notification['pid'])

            end_date = datetime.now(timezone.utc) - timedelta(days=70)
            loan['end_date'] = end_date.isoformat()
            loan.update(
                loan,
                dbcommit=True,
                reindex=True
            )
            notification = loan.create_notification(
                notification_type='overdue')
            if notification:
                notification_pids.append(notification['pid'])

        elif transaction_type == 'overdue_paid':
            end_date = datetime.now(timezone.utc) - timedelta(days=2)
            loan['end_date'] = end_date.isoformat()
            loan.update(
                loan,
                dbcommit=True,
                reindex=True
            )
            notification = loan.create_notification(
                notification_type='due_soon')
            if notification:
                notification_pids.append(notification['pid'])

            end_date = datetime.now(timezone.utc) - timedelta(days=70)
            loan['end_date'] = end_date.isoformat()
            loan.update(
                loan,
                dbcommit=True,
                reindex=True
            )
            notification = notif = loan.create_notification(
                notification_type='overdue')
            if notification:
                notification_pids.append(notification['pid'])
            patron_transaction = next(notif.patron_transactions)
            user = get_random_librarian(patron).replace_refs()
            payment = create_payment_record(
                patron_transaction,
                user_pid,
                random.choice(user['libraries'])['pid']
            )
            PatronTransactionEvent.create(
                payment,
                dbcommit=True,
                reindex=True,
                update_parent=True
            )
        elif transaction_type == 'extended':
            user_pid, user_location = \
                get_random_librarian_and_transaction_location(patron)
            item.extend_loan(
                pid=loan_pid,
                patron_pid=patron.pid,
                transaction_location_pid=user_location,
                transaction_user_pid=user_pid,
                transaction_date=transaction_date,
                document_pid=extracted_data_from_ref(item.get('document')),
                item_pid=item.pid,
            )
        elif transaction_type == 'requested_by_others':
            requested_patron = get_random_patron(barcode)
            user_pid, user_location = \
                get_random_librarian_and_transaction_location(patron)
            circ_policy = CircPolicy.provide_circ_policy(
                item.organisation_pid,
                item.library_pid,
                requested_patron.patron_type_pid,
                item.item_type_circulation_category_pid
            )
            if circ_policy.get('allow_requests'):
                item.request(
                    patron_pid=requested_patron.pid,
                    transaction_location_pid=user_location,
                    transaction_user_pid=user_pid,
                    transaction_date=transaction_date,
                    pickup_location_pid=get_random_pickup_location(
                        requested_patron.pid, item),
                    document_pid=extracted_data_from_ref(item.get('document')),
                )
                notification = loan.create_notification(
                    notification_type='recall')
                if notification:
                    notification_pids.append(notification['pid'])
        Dispatcher.dispatch_notifications(notification_pids, verbose=verbose)
        return item['barcode']
    except Exception as err:
        if verbose:
            click.secho(f'\tException loan {transaction_type}:{err}', fg='red')
        if debug:
            traceback.print_exc()
        return None, []


def create_request(barcode, transaction_type, loanable_items, verbose=False,
                   debug=False):
    """Create request transactions."""
    try:
        item = next(loanable_items)
        rank_1_patron = get_random_patron(barcode)
        patron = Patron.get_patron_by_barcode(barcode)
        if transaction_type == 'rank_2':
            transaction_date = \
                (datetime.now(timezone.utc) - timedelta(2)).isoformat()
            user_pid, user_location = \
                get_random_librarian_and_transaction_location(patron)

            circ_policy = CircPolicy.provide_circ_policy(
                item.organisation_pid,
                item.holding_library_pid,
                rank_1_patron.patron_type_pid,
                item.holding_circulation_category_pid
            )
            if circ_policy.get('allow_requests'):
                item.request(
                    patron_pid=rank_1_patron.pid,
                    transaction_location_pid=user_location,
                    transaction_user_pid=user_pid,
                    transaction_date=transaction_date,
                    pickup_location_pid=get_random_pickup_location(
                        rank_1_patron.pid, item),
                    document_pid=extracted_data_from_ref(item.get('document')),
                )
        transaction_date = datetime.now(timezone.utc).isoformat()
        user_pid, user_location = \
            get_random_librarian_and_transaction_location(patron)
        item.request(
            patron_pid=patron.pid,
            transaction_location_pid=user_location,
            transaction_user_pid=user_pid,
            transaction_date=transaction_date,
            pickup_location_pid=get_random_pickup_location(patron.pid, item),
            document_pid=extracted_data_from_ref(item.get('document')),
        )
        return item['barcode']
    except Exception as err:
        if verbose:
            click.secho(
                f'\tException request {transaction_type}: {err}',
                fg='red'
            )
        if debug:
            traceback.print_exc()
        return None


def get_loanable_items(patron_type_pid):
    """Get the list of loanable items."""
    patron_type = PatronType.get_record_by_pid(patron_type_pid)
    org_pid = extracted_data_from_ref(patron_type.get('organisation'))
    loanable_items = ItemsSearch()\
        .filter('term', organisation__pid=org_pid)\
        .filter('term', status=ItemStatus.ON_SHELF).source(['pid']).scan()
    for loanable_item in loanable_items:
        item = Item.get_record_by_pid(loanable_item.pid)
        if item:
            circ_policy = CircPolicy.provide_circ_policy(
                item.organisation_pid,
                item.holding_library_pid,
                patron_type_pid,
                item.holding_circulation_category_pid
            )
            if (circ_policy.allow_checkout and
               circ_policy.get('allow_requests')):
                if not item.number_of_requests():
                    # exclude the first 16 items of the 3rd organisation
                    barcode = item.get('barcode')
                    if not (
                        barcode.startswith('fictive') and
                        int(barcode.split('fictive')[1]) < 17
                    ):
                        yield item


def get_random_pickup_location(patron_pid, item):
    """Find a qualified pickup location."""
    pickup_locations_pids = list(Location.get_pickup_location_pids(
        patron_pid=patron_pid,
        item_pid=item.pid
    ))
    return random.choice(pickup_locations_pids)


def get_random_patron(exclude_this_barcode):
    """Find a qualified patron other than exclude_this_barcode."""
    ptrn_to_exclude = Patron.get_patron_by_barcode(exclude_this_barcode)
    ptty_pid = extracted_data_from_ref(
        ptrn_to_exclude.get('patron').get('type')
    )
    org_pid = extracted_data_from_ref(
        PatronType.get_record_by_pid(ptty_pid).get('organisation')
    )
    patrons = PatronsSearch()\
        .filter('term', roles='patron')\
        .filter('term', organisation__pid=org_pid)\
        .source(['patron']).scan()
    for patron in patrons:
        if exclude_this_barcode not in patron.patron.barcode:
            return Patron.get_patron_by_barcode(
                barcode=patron.patron.barcode[0])


def get_random_librarian(patron):
    """Find a qualified staff user."""
    ptty_pid = extracted_data_from_ref(patron.get('patron').get('type'))
    org_pid = extracted_data_from_ref(
        PatronType.get_record_by_pid(ptty_pid).get('organisation')
    )
    patrons = PatronsSearch()\
        .filter('term', roles='librarian')\
        .filter('term', organisation__pid=org_pid)\
        .source(['pid']).scan()
    for patron in patrons:
        return Patron.get_record_by_pid(patron.pid)
    return None


def get_random_librarian_and_transaction_location(patron):
    """Find a qualified user data."""
    user = get_random_librarian(patron).replace_refs()
    library = Library.get_record_by_pid(
        random.choice(user['libraries'])['pid'])
    return user.pid, library.get_pickup_location_pid()


def create_payment_record(patron_transaction, user_pid, user_library):
    """Create payment record from patron_transaction."""
    data = {
        '$schema': get_schema_for_resource('ptre')
    }
    for record in [
        {
            'resource': 'parent',
            'doc_type': 'patron_transactions',
            'pid': patron_transaction.pid
        },
        {
            'resource': 'operator',
            'doc_type': 'patrons',
            'pid': user_pid
        },
        {
            'resource': 'library',
            'doc_type': 'libraries',
            'pid': user_library
        },
    ]:
        data[record['resource']] = {
            '$ref': get_ref_for_pid(record['doc_type'], record['pid'])
        }
    data['type'] = 'payment'
    data['subtype'] = 'cash'
    data['amount'] = patron_transaction.get('total_amount')
    data['creation_date'] = datetime.now(timezone.utc).isoformat()
    return data
