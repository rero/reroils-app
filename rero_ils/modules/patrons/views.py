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

import re
from functools import wraps

from flask import Blueprint, abort, current_app, flash, jsonify, \
    render_template, request, url_for
from flask_babelex import format_currency
from flask_babelex import gettext as _
from flask_babelex import lazy_gettext
from flask_breadcrumbs import register_breadcrumb
from flask_login import current_user, login_required
from flask_menu import register_menu
from invenio_i18n.ext import current_i18n
from werkzeug.exceptions import NotFound
from werkzeug.utils import redirect

from .api import Patron
from .permissions import get_allowed_roles_management
from .utils import user_has_patron
from ..items.api import Item
from ..items.utils import item_pid_to_object
from ..loans.api import Loan, get_loans_stats_by_patron_pid, patron_profile
from ..locations.api import Location
from ..utils import get_base_url
from ...permissions import login_and_librarian

api_blueprint = Blueprint(
    'api_patrons',
    __name__,
    url_prefix='/patrons',
    template_folder='templates',
    static_folder='static',
)


_PID_REGEX = re.compile(r'NOT\s+pid:\s*(\w+)\s*')
_EMAIL_REGEX = re.compile(r'email:"\s*(.*?)\s*"')
_USERNAME_REGEX = re.compile(r'username:"\s*(.*?)\s*"')


def check_permission(fn):
    """Decorate to check permission access.

    The access is allow when the connected user is a librarian.
    """
    @wraps(fn)
    def is_logged_librarian(*args, **kwargs):
        """Decorated view."""
        login_and_librarian()
        return fn(*args, **kwargs)
    return is_logged_librarian

@api_blueprint.route('/<patron_pid>/circulation_informations', methods=['GET'])
@check_permission
def patron_circulation_informations(patron_pid):
    """Get the circulation statistics and info messages about a patron."""
    patron = Patron.get_record_by_pid(patron_pid)
    if not patron:
        abort(404, 'Patron not found')
    return jsonify({
        'statistics': get_loans_stats_by_patron_pid(patron_pid),
        'messages': patron.get_circulation_messages()
    })


blueprint = Blueprint(
    'patrons',
    __name__,
    template_folder='templates',
    static_folder='static',
)


@blueprint.route('/patrons/logged_user', methods=['GET'])
def logged_user():
    """Current logged user informations in JSON."""
    patron = Patron.get_patron_by_user(current_user)
    if patron and 'resolve' in request.args:
        organisation_pid = patron.organisation_pid
        patron = patron.replace_refs()
        patron = patron.dumps()
        for index, library in enumerate(patron.get('libraries', [])):
            data = {
                'pid': library['pid'],
                'organisation': {
                    'pid': organisation_pid
                }
            }
            patron['libraries'][index] = data
    data = {
        'settings': {
            'language': current_i18n.locale.language,
            'global_view': current_app.config.get(
                'RERO_ILS_SEARCH_GLOBAL_VIEW_CODE'),
            'baseUrl': get_base_url(),
            'contributionsLabelOrder': current_app.config.get(
                'RERO_ILS_CONTRIBUTIONS_LABEL_ORDER', {}),
            'contributionSources': current_app.config.get(
                'RERO_ILS_CONTRIBUTIONS_SOURCES', []
            ),
            'operation_logs': current_app.config.get(
                'RERO_ILS_ENABLE_OPERATION_LOG', []
            )
        }
    }
    if patron:
        data['metadata'] = patron
    return jsonify(data)


@blueprint.route('/global/patrons/profile', defaults={'viewcode': 'global'},
                 methods=['GET', 'POST'])
@blueprint.route('/<string:viewcode>/patrons/profile')
@login_required
@register_menu(
    blueprint,
    'settings.patron_profile',
    lazy_gettext('%(icon)s My loans', icon='<i class="fa fa-book fa-fw"></i>'),
    visible_when=user_has_patron,
    id="my-profile-menu",
    order=-1
)
@register_breadcrumb(
    blueprint, 'breadcrumbs.settings.patron_profile', _('Patron Profile')
)
def profile(viewcode):
    """Patron Profile Page."""
    tab = request.args.get('tab', 'loans')
    allowed_tabs = [
        'loans',
        'requests',
        'fees',
        'history',
        'ill_request',
        'personal'
    ]
    if tab not in allowed_tabs:
        abort(400)
    patron = Patron.get_patron_by_user(current_user)
    if patron is None:
        raise NotFound()
    if not patron.is_patron:
        abort(403)
    if request.method == 'POST':
        loan = Loan.get_record_by_pid(request.values.get('loan_pid'))
        item = Item.get_record_by_pid(loan.get('item_pid', {}).get('value'))
        if request.form.get('type') == 'cancel':
            tab = 'requests'
            cancel_params = {
                'pid': loan.pid,
                'transaction_location_pid': item.location_pid,
                'transaction_user_pid': patron.pid
            }
            try:
                item.cancel_item_request(**cancel_params)
                flash(_('The request for item %(item_id)s has been canceled.',
                        item_id=item.pid), 'success')
            except Exception:
                flash(_('Error during the cancellation of the request of \
                item %(item_id)s.', item_id=item.pid), 'danger')
        elif request.form.get('type') == 'renew':
            data = {
                'item_pid': item.pid,
                'pid': request.values.get('loan_pid'),
                'transaction_location_pid': item.location_pid,
                'transaction_user_pid': patron.pid
            }
            try:
                item.extend_loan(**data)
                flash(_('The item %(item_id)s has been renewed.',
                        item_id=item.pid), 'success')
            except Exception:
                flash(_('Error during the renewal of the item %(item_id)s.',
                        item_id=item.pid), 'danger')
        return redirect(url_for(
            'patrons.profile', viewcode=viewcode) + '?tab={0}'.format(tab))

    loans, requests, fees, history, ill_requests = patron_profile(patron)

    # patron messages list
    messages = patron.get_circulation_messages(True)
    if patron.get_pending_subscriptions():
        messages.append({
            'type': 'warning',
            'content': _('You have a pending subscription fee.')
        })
    bootstrap_alert_mapping = {
        'error': 'danger'
    }
    for message in messages:
        msg_type = message['type']
        message['type'] = bootstrap_alert_mapping.get(msg_type, msg_type)

    return render_template(
        'rero_ils/patron_profile.html',
        record=patron,
        loans=loans,
        requests=requests,
        fees=fees,
        history=history,
        ill_requests=ill_requests,
        messages=messages,
        viewcode=viewcode,
        tab=tab
    )


@blueprint.app_template_filter('format_currency')
def format_currency_filter(value, currency):
    """Format currency with current locale."""
    if value:
        return format_currency(value, currency)


@api_blueprint.route('/roles_management_permissions', methods=['GET'])
@api_blueprint.route('/roles_management_permissions/<patron_pid>',
                     methods=['GET'])
@check_permission
def get_roles_management_permissions(patron_pid=None):
    """Get the roles that current logged user could manage on a patron."""
    return jsonify({
        'roles': get_allowed_roles_management(patron_pid)
    })


@blueprint.app_template_filter('get_patron_from_barcode')
def get_patron_from_barcode(value):
    """Get patron from barcode."""
    return Patron.get_patron_by_barcode(value)


@blueprint.app_template_filter('get_patron_from_checkout_item_pid')
def get_patron_from_checkout_item_pid(item_pid):
    """Get patron from a checked out item pid."""
    from invenio_circulation.api import get_loan_for_item
    patron_pid = get_loan_for_item(item_pid_to_object(item_pid))['patron_pid']
    return Patron.get_record_by_pid(patron_pid)


@blueprint.app_template_filter('get_checkout_loan_for_item')
def get_checkout_loan_for_item(item_pid):
    """Get patron from a checkout item pid."""
    from invenio_circulation.api import get_loan_for_item
    return get_loan_for_item(item_pid_to_object(item_pid))


@blueprint.app_template_filter('get_patron_from_pid')
def get_patron_from_pid(patron_pid):
    """Get patron from pid."""
    return Patron.get_record_by_pid(patron_pid)


@blueprint.app_template_filter('get_location_name_from_pid')
def get_location_name_from_pid(location_pid):
    """Get location from pid."""
    return Location.get_record_by_pid(location_pid)['name']
