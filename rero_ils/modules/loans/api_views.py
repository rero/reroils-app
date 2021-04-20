# -*- coding: utf-8 -*-
#
# RERO ILS
# Copyright (C) 2021 RERO
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

"""Blueprint used for loans."""

from flask import Blueprint, abort, jsonify
from flask_login import login_required

from rero_ils.modules.items.api import Item
from rero_ils.modules.items.models import ItemCirculationAction
from rero_ils.modules.items.views.api_views import \
    check_logged_user_authentication, jsonify_error
from rero_ils.modules.loans.api import Loan
from rero_ils.modules.loans.utils import sum_for_fees

api_blueprint = Blueprint(
    'api_loan',
    __name__,
    url_prefix='/loan'
)


@api_blueprint.route('/<loan_pid>/overdue/preview', methods=['GET'])
@login_required
def preview_loan_overdue(loan_pid):
    """HTTP GET request for overdue preview about a loan."""
    loan = Loan.get_record_by_pid(loan_pid)
    if not loan:
        abort(404)
    fees = loan.get_overdue_fees
    fees = [(fee[0], fee[1].isoformat()) for fee in fees]  # format date
    return jsonify({
        'total': sum_for_fees(fees),
        'steps': fees
    })


@api_blueprint.route('/<loan_pid>/can_extend', methods=['GET'])
@check_logged_user_authentication
@jsonify_error
def can_extend(loan_pid):
    """Loan can extend."""
    loan = Loan.get_record_by_pid(loan_pid)
    item_pid = loan.get('item_pid', {}).get('value')
    can_extend = {
        'can': False,
        'reasons': []
    }
    if item_pid:
        item = Item.get_record_by_pid(item_pid)
        can, reasons = item.can(
            ItemCirculationAction.EXTEND,
            loan=loan
        )
        can_extend = {
            'can': can,
            'reasons': reasons
        }
    return jsonify(can_extend)
