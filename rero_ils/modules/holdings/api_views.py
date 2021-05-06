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

from flask import Blueprint, abort, current_app, jsonify
from flask import request as flask_request
from jinja2.exceptions import TemplateSyntaxError, UndefinedError
from werkzeug.exceptions import NotFound

from rero_ils.modules.views import check_authentication

from .api import Holding
from ..errors import RegularReceiveNotAllowed
from ...permissions import can_receive_regular_issue

api_blueprint = Blueprint(
    'api_holding',
    __name__,
    url_prefix='/holding'
)


def jsonify_error(func):
    """Jsonify errors.

    :param func: function that use this decorator
    """
    @wraps(func)
    def decorated_view(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except NotFound as error:
            raise(error)
        except TemplateSyntaxError as error:
            return jsonify({'status': 'error: {error}'.format(
                error=error)}), 400
        except UndefinedError as error:
            return jsonify({'status': 'error: {error}'.format(
                error=error)}), 400
        except Exception as error:
            raise(error)
            current_app.logger.error(str(error))
            return jsonify({'status': 'error: {error}'.format(
                error=error)}), 500
    return decorated_view


@api_blueprint.route('/availabilty/<holding_pid>', methods=['GET'])
@check_authentication
@jsonify_error
def holding_availability(holding_pid):
    """HTTP GET request for holding availability."""
    holding = Holding.get_record_by_pid(holding_pid)
    if not holding:
        abort(404)
    return jsonify({
        'availability': holding.available
    })


@api_blueprint.route('/<holding_pid>/patterns/preview', methods=['GET'])
@check_authentication
@jsonify_error
def patterns_preview(holding_pid):
    """HTTP GET request for holdings pattern preview.

    Required parameters: holding_pid
    Optional parameters: size: number of previewed issues - by default 10
    """
    try:
        size = flask_request.args.get('size')
        number_issues = int(size) if size else 10
    except ValueError as error:
        number_issues = 10
    holding = Holding.get_record_by_pid(holding_pid)
    if holding and holding.get('holdings_type') != 'serial':
        return jsonify({'status': 'error: invalid holdings type'}), 400
    issues = holding.prediction_issues_preview(predictions=number_issues)
    return jsonify({'issues': issues})


@api_blueprint.route("/pattern/preview", methods=['POST'])
@check_authentication
@jsonify_error
def pattern_preview():
    """HTTP POST for patterns preview of first n issues for a regular patterns.

    Required parameters: data contains the json of holdings record to preview
    Optional parameters: size: number of previewed issues - by default 10
    """
    patterns_data = flask_request.get_json()
    pattern = patterns_data.get('data', {})
    size = patterns_data.get('size', 10)
    if pattern and pattern.get('frequency') == 'rdafr:1016':
        return jsonify({'status': 'error: irregular frequency'}), 400
    issues = Holding.prediction_issues_preview_for_pattern(
        pattern, number_of_predictions=size)
    return jsonify({'issues': issues})


@api_blueprint.route('/<holding_pid>/issues', methods=['POST'])
@jsonify_error
@check_authentication
def receive_regular_issue(holding_pid):
    """HTTP POST for receiving the next expected issue for a holding.

    For a quick receive, do not pass the item parameter
    For a customized receive, send the item fields in the item parameter.

    Required parameters:
        holding_pid: the pid of the holdings.
    Optional parameters:
        item: the item of type issue to create.
    """
    data = flask_request.get_json()
    holding = Holding.get_record_by_pid(holding_pid)
    if not holding:
        abort(404, "Holding not found")
    # librarian of same holdings library may receive issues
    # system librarians may receive for all libraries of organisation.
    if not can_receive_regular_issue(holding):
        abort(401)
    item = data.get('item', {})
    try:
        issue = holding.receive_regular_issue(
            item=item, dbcommit=True, reindex=True)
    except RegularReceiveNotAllowed:
        # receive allowed only on holding of type serials and regular frequency
        abort(400)
    # the created item of type issue is returned
    return jsonify({'issue': issue})
