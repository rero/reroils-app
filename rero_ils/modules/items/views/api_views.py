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

"""Blueprint used for loading templates."""

from __future__ import absolute_import, print_function

from functools import wraps

from elasticsearch import exceptions
from flask import Blueprint, abort, current_app, jsonify
from flask import request as flask_request
from flask_login import current_user
from invenio_circulation.api import get_loan_for_item
from invenio_circulation.errors import CirculationException, \
    MissingRequiredParameterError
from werkzeug.exceptions import NotFound

from rero_ils.modules.circ_policies.api import CircPolicy
from rero_ils.modules.documents.views import item_library_pickup_locations
from rero_ils.modules.errors import NoCirculationActionIsPermitted
from rero_ils.modules.items.api import Item
from rero_ils.modules.items.models import ItemCirculationAction
from rero_ils.modules.items.utils import item_pid_to_object
from rero_ils.modules.libraries.api import Library
from rero_ils.modules.loans.api import Loan
from rero_ils.modules.patrons.api import Patron, current_librarian, \
    current_patrons
from rero_ils.modules.views import check_authentication
from rero_ils.permissions import request_item_permission

# from rero_ils.modules.utils import profile

api_blueprint = Blueprint(
    'api_item',
    __name__,
    url_prefix='/item'
)


def check_logged_user_authentication(func):
    """Decorator to check authentication for user HTTP API."""
    @wraps(func)
    def decorated_view(*args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify({'status': 'error: Unauthorized'}), 401
        return func(*args, **kwargs)

    return decorated_view


def check_authentication_for_request(func):
    """Decorator to check authentication for item requests HTTP API."""
    @wraps(func)
    def decorated_view(*args, **kwargs):
        if not request_item_permission.require().can():
            return jsonify({'status': 'error: Forbidden'}), 403
        return func(*args, **kwargs)

    return decorated_view


def jsonify_error(func):
    """Jsonify errors."""
    @wraps(func)
    def decorated_view(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except NotFound as error:
            raise(error)
        except Exception as error:
            # raise(error)
            current_app.logger.error(str(error))
            return jsonify({'status': f'error: {error}'}), 500
    return decorated_view


def do_loan_jsonify_action(func):
    """Jsonify loan actions for non item methods.

    This method for the circulation actions that executed directly on the loan
    object and do not need to have direct access to the item object.
    """
    @wraps(func)
    def decorated_view(*args, **kwargs):
        try:
            data = flask_request.get_json()
            loan_pid = data.pop('pid', None)
            pickup_location_pid = data.get('pickup_location_pid', None)
            if not loan_pid or not pickup_location_pid:
                return jsonify({'status': 'error: Bad request'}), 400
            loan = Loan.get_record_by_pid(loan_pid)
            updated_loan = func(loan, data, *args, **kwargs)
            return jsonify(updated_loan)
        except NoCirculationActionIsPermitted as error:
            # The circulation specs do not allow updates on some loan states.
            abort(403, str(error))
    return decorated_view


def do_item_jsonify_action(func):
    """Jsonify loan actions for item methods.

    This method for the circulation actions that required access to the item
    object before executing the invenio-circulation logic.
    """
    @wraps(func)
    def decorated_view(*args, **kwargs):
        try:
            data = flask_request.get_json()
            item = Item.get_item_record_for_ui(**data)
            data.pop('item_barcode', None)

            if not item:
                abort(404)
            item_data, action_applied = \
                func(item, data, *args, **kwargs)
            for action, loan in action_applied.items():
                if loan:
                    action_applied[action] = loan.dumps_for_circulation()

            return jsonify({
                'metadata': item_data.dumps_for_circulation(),
                'action_applied': action_applied
            })
        except NoCirculationActionIsPermitted:
            # The circulation specs do not allow updates on some loan states.
            return jsonify({'status': 'error: Forbidden'}), 403
        except MissingRequiredParameterError as error:
            # Return error 400 when there is a missing required parameter
            abort(400, str(error))
        except CirculationException as error:
            abort(403, error.description or str(error))
        except NotFound as error:
            raise error
        except exceptions.RequestError as error:
            # missing required parameters
            return jsonify({'status': f'error: {error}'}), 400
        except Exception as error:
            # TODO: need to know what type of exception and document there.
            # raise error
            current_app.logger.error(str(error))
            return jsonify({'status': f'error: {error}'}), 400
    return decorated_view


@api_blueprint.route('/patron_request', methods=['POST'])
@check_logged_user_authentication
@check_authentication_for_request
@do_item_jsonify_action
def patron_request(item, data):
    """HTTP POST request for Item request action by a patron.

    required_parameters:
        item_pid,
        pickup_location_pid
    """
    # get the patron account of the same org of the location pid
    def get_patron(item):
        for ptrn in current_patrons:
            if ptrn.organisation_pid == item.organisation_pid:
                return ptrn

    patron_pid = get_patron(item).pid
    data['patron_pid'] = patron_pid
    data['transaction_user_pid'] = patron_pid
    data['transaction_location_pid'] = data['pickup_location_pid']
    return item.request(**data)


@api_blueprint.route('/request', methods=['POST'])
@check_authentication
@do_item_jsonify_action
def librarian_request(item, data):
    """HTTP POST request for Item request action.

    required_parameters:
        item_pid_value,
        pickup_location_pid,
        patron_pid,
        transaction_location_pid or transaction_library_pid,
        transaction_user_pid
    """
    return item.request(**data)


@api_blueprint.route('/cancel_item_request', methods=['POST'])
@check_logged_user_authentication
@do_item_jsonify_action
def cancel_item_request(item, data):
    """HTTP GET request for cancelling and item request action.

    required_parameters:
        pid (loan pid)
        transaction_location_pid or transaction_library_pid,
        transaction_user_pid
    """
    return item.cancel_item_request(**data)


@api_blueprint.route('/checkout', methods=['POST'])
# @profile(sort_by='cumulative', lines_to_print=100)
@check_authentication
@do_item_jsonify_action
def checkout(item, data):
    """HTTP request for Item checkout action.

    required_parameters:
        patron_pid,
        item_pid,
        transaction_location_pid,
        transaction_user_pid
    """
    data['override_blocking'] = flask_request.args.get(
        'override_blocking', False)
    return item.checkout(**data)


@api_blueprint.route("/checkin", methods=['POST'])
# @profile(sort_by='cumulative', lines_to_print=100)
@check_authentication
@do_item_jsonify_action
def checkin(item, data):
    """HTTP GET request for item return action.

    required_parameters:
        item_pid or item_barcode
        transaction_location_pid or transaction_library_pid,
        transaction_user_pid
    """
    return item.checkin(**data)


@api_blueprint.route("/update_loan_pickup_location", methods=['POST'])
@check_authentication
@do_loan_jsonify_action
def update_loan_pickup_location(loan, data):
    """HTTP POST request for change a pickup location for a loan.

    required_parameters:
        pid (loan pid)
        pickup_location_pid
    """
    return loan.update_pickup_location(**data)


@api_blueprint.route('/validate_request', methods=['POST'])
@check_authentication
@do_item_jsonify_action
def validate_request(item, data):
    """HTTP GET request for Item request validation action.

    required_parameters:
        pid (loan pid)
        transaction_location_pid or transaction_library_pid,
        transaction_user_pid
    """
    return item.validate_request(**data)


@api_blueprint.route('/receive', methods=['POST'])
@check_authentication
@do_item_jsonify_action
def receive(item, data):
    """HTTP HTTP request for receive item action.

    required_parameters: item_pid
    """
    return item.receive(**data)


@api_blueprint.route('/return_missing', methods=['POST'])
@check_authentication
@do_item_jsonify_action
def return_missing(item, data=None):
    """HTTP request for Item return_missing action.

    required_parameters: item_pid
    """
    return item.return_missing()


@api_blueprint.route('/extend_loan', methods=['POST'])
@check_logged_user_authentication
@do_item_jsonify_action
def extend_loan(item, data):
    """HTTP request for Item due date extend action.

    required_parameters: item_pid
    """
    return item.extend_loan(**data)


@api_blueprint.route('/requested_loans/<library_pid>', methods=['GET'])
@check_authentication
@jsonify_error
def requested_loans(library_pid):
    """HTTP GET request for sorted requested loans for a library."""
    sort_by = flask_request.args.get('sort')
    items_loans = Item.get_requests_to_validate(
        library_pid=library_pid, sort_by=sort_by)
    metadata = []
    for item, loan in items_loans:
        metadata.append({
            'item': item.dumps_for_circulation(sort_by=sort_by),
            'loan': loan.dumps_for_circulation()
        })
    return jsonify({
        'hits': {
            'total': {
                'value': len(metadata)
            },
            'hits': metadata
        }
    })


@api_blueprint.route('/loans/<patron_pid>', methods=['GET'])
@check_authentication
@jsonify_error
def loans(patron_pid):
    """HTTP GET request for sorted loans for a patron pid."""
    sort_by = flask_request.args.get('sort')
    items = Item.get_checked_out_items(patron_pid=patron_pid, sort_by=sort_by)
    metadata = []
    for item in items:
        item_data = item.replace_refs()
        metadata.append({
            'item': {
                'pid': item.pid,
                'organisation_pid': item_data.get('organisation').get('pid'),
                'barcode': item.get('barcode')
            }
        })
    return jsonify({
        'hits': {
            'total': {
                'value': len(metadata)
            },
            'hits': metadata
        }
    })


@api_blueprint.route('/barcode/<item_barcode>', methods=['GET'])
@check_authentication
@jsonify_error
def item(item_barcode):
    """HTTP GET request for requested loans for a library item and patron."""
    item = Item.get_item_by_barcode(
        item_barcode, current_librarian.organisation_pid)
    if not item:
        abort(404)
    loan = get_loan_for_item(item_pid_to_object(item.pid))
    if loan:
        loan = Loan.get_record_by_pid(loan.get('pid')).dumps_for_circulation()
    item_dumps = item.dumps_for_circulation()
    patron_pid = flask_request.args.get('patron_pid')

    if patron_pid:
        patron = Patron.get_record_by_pid(patron_pid)
        organisation_pid = item.organisation_pid
        library_pid = item.library_pid
        patron_type_pid = patron.patron_type_pid
        item_type_pid = item.item_type_circulation_category_pid
        circ_policy = CircPolicy.provide_circ_policy(
            organisation_pid=organisation_pid,
            library_pid=library_pid,
            patron_type_pid=patron_type_pid,
            item_type_pid=item_type_pid
        )
        new_actions = []
        # If circulation policy doesn't allow checkout operation no need to
        # perform special check describe below.
        if circ_policy.can_checkout:
            for action in item_dumps.get('actions', []):
                if action == 'checkout':
                    if item.number_of_requests() > 0:
                        if item.patron_request_rank(patron) == 1:
                            new_actions.append(action)
                    else:
                        new_actions.append(action)
                elif action == 'receive' and item.number_of_requests() == 0:
                    new_actions.append('checkout')
        item_dumps['actions'] = new_actions
    return jsonify({
        'metadata': {
            'item': item_dumps,
            'loan': loan
        }
    })


@api_blueprint.route('/availabilty/<item_pid>', methods=['GET'])
@check_authentication
@jsonify_error
def item_availability(item_pid):
    """HTTP GET request for item availability."""
    item = Item.get_record_by_pid(item_pid)
    if not item:
        abort(404)
    return jsonify({
        'availability': item.available
    })


@api_blueprint.route('/<item_pid>/can_request', methods=['GET'])
@check_logged_user_authentication
@jsonify_error
def can_request(item_pid):
    """HTTP request to check if an item can be requested.

    Depending of query string argument, either only check if configuration
    allows the request of this item ; either if a librarian can request an
    item for a patron.

    `api/item/<item_pid>/can_request` :
         --> only check config
    `api/item/<item_pid>/can_request?library_pid=<library_pid>&patron_barcode=<barcode>`:
         --> check if the patron can request this item (check the cipo)
    """
    kwargs = {}
    item = Item.get_record_by_pid(item_pid)
    if not item:
        abort(404, 'Item not found')
    patron_barcode = flask_request.args.get('patron_barcode')
    if patron_barcode:
        kwargs['patron'] = Patron.get_patron_by_barcode(
            patron_barcode, item.organisation_pid)
        if not kwargs['patron']:
            abort(404, 'Patron not found')
    library_pid = flask_request.args.get('library_pid')
    if library_pid:
        kwargs['library'] = Library.get_record_by_pid(library_pid)
        if not kwargs['library']:
            abort(404, 'Library not found')

    # ask to item if the request is possible with these data.
    can, reasons = item.can(ItemCirculationAction.REQUEST, **kwargs)

    # check the `reasons_not_request` array. If it's empty, the request is
    # allowed ; if not the request is disallow and we need to return the
    # reasons why
    response = {'can': can}
    if reasons:
        response['reasons'] = {
            'others': {reason: True for reason in reasons}
        }
    return jsonify(response)


@api_blueprint.route('/<item_pid>/pickup_locations', methods=['GET'])
@check_logged_user_authentication
@jsonify_error
def get_pickup_locations(item_pid):
    """HTTP request to return the available pickup locations for an item.

    :param item_pid: the item pid
    """
    item = Item.get_record_by_pid(item_pid)
    if not item:
        abort(404, 'Item not found')
    locations = item_library_pickup_locations(item)
    return jsonify({
        'locations': locations
    })
