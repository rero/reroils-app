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

import copy
import re
from functools import partial, wraps

from flask import Blueprint, abort, current_app, jsonify, redirect, \
    render_template, request, session, url_for
from flask_babelex import gettext as _
from flask_login import current_user
from flask_menu import current_menu
from invenio_i18n.ext import current_i18n
from invenio_jsonschemas import current_jsonschemas
from invenio_jsonschemas.errors import JSONSchemaNotFound

from rero_ils.modules.organisations.api import Organisation
from rero_ils.modules.patrons.api import Patron, current_patron
from rero_ils.permissions import can_access_professional_view

from ..version import __version__

blueprint = Blueprint(
    'rero_ils',
    __name__,
    template_folder='templates',
    static_folder='static',
)


def rero_register(
    item,
    endpoint=None,
    text=None,
    order=0,
    external_url=None,
    endpoint_arguments_constructor=None,
    dynamic_list_constructor=None,
    active_when=None,
    visible_when=None,
    expected_args=None,
        **kwargs):
    """Take care each element in kwargs doesn't already exists in item."""
    # Check which option in kwargs already exists in `item`.
    to_delete = []
    for option in kwargs.keys():
        if hasattr(item, option):
            to_delete.append(option)
    # Delete all existing options in kwargs
    for element in to_delete:
        del kwargs[element]

    return item.register(
        endpoint,
        text,
        order,
        external_url,
        endpoint_arguments_constructor,
        dynamic_list_constructor,
        active_when,
        visible_when,
        expected_args,
        **kwargs)


def init_menu_tools():
    """Create the header tool menu."""
    item = current_menu.submenu('main.tool')
    rero_register(
        item,
        endpoint=None,
        text='{icon} <span class="{visible}">{menu}'.format(
            icon='<i class="fa fa-wrench"></i>',
            visible='visible-md-inline visible-lg-inline',
            menu=_('Tools')
        ),
        order=0,
        id='tools-menu'
    )

    item = current_menu.submenu('main.tool.ill_request')
    rero_register(
        item,
        endpoint='ill_requests.ill_request_form',
        visible_when=lambda: Patron.get_patron_by_user(current_user).is_patron,
        text='{icon} {help}'.format(
            icon='<i class="fa fa-shopping-basket"></i>',
            help=_('Interlibrary loan request')
        ),
        order=10,
        id='ill-request-menu'
    )

    item = current_menu.submenu('main.tool.collections')
    rero_register(
        item,
        endpoint='rero_ils.search',
        endpoint_arguments_constructor=lambda: dict(
            viewcode=request.view_args.get(
                'viewcode', current_app.config.get(
                    'RERO_ILS_SEARCH_GLOBAL_VIEW_CODE')),
            recordType='collections'
        ),
        visible_when=lambda: current_app.config.get(
            'RERO_ILS_SEARCH_GLOBAL_VIEW_CODE'
            ) != request.view_args.get(
                'viewcode', current_app.config.get(
                    'RERO_ILS_SEARCH_GLOBAL_VIEW_CODE')),
        text='{icon} {help}'.format(
            icon='<i class="fa fa-graduation-cap"></i>',
            help=_('Collections')
        ),
        order=2,
        id='collections-menu'
    )

    item = current_menu.submenu('main.tool.help')
    rero_register(
        item,
        endpoint='wiki.page',
        endpoint_arguments_constructor=lambda: {'url': 'public'},
        text='{icon} {help}'.format(
            icon='<i class="fa fa-info"></i>',
            help=_('Help')
        ),
        order=100,
        id='help-menu'
    )


def init_menu_lang():
    """Create the header language menu."""
    item = current_menu.submenu('main.menu')
    ui_language = 'ui_language_{lang}'.format(lang=current_i18n.language)
    # Bug: when you reload the page with register(**kwargs), it failed
    # We so check that 'id' already exists. If yes, do not create again
    # the item.
    rero_register(
        item,
        endpoint=None,
        text='{icon} <span class="{visible}">{menu}'.format(
            icon='<i class="fa fa-language"></i>',
            visible='visible-md-inline visible-lg-inline',
            menu=_(ui_language)
        ),
        order=0,
        id='language-menu'
    )

    order = 10

    def return_language(lang):
        return dict(lang_code=lang)

    def hide_language(lang):
        return current_i18n.language != lang

    for language_item in current_i18n.get_locales():
        item = current_menu.submenu(
            'main.menu.lang_{language}'.format(
                language=language_item.language))
        ui_language = 'ui_language_{lang}'.format(lang=language_item.language)
        rero_register(
            item,
            endpoint='invenio_i18n.set_lang',
            endpoint_arguments_constructor=partial(
                return_language, language_item.language),
            text='{icon} {language}'.format(
                icon='<i class="fa fa-language"></i>',
                language=_(ui_language)
            ),
            visible_when=partial(hide_language, language_item.language),
            order=order,
            id='language-menu-{language}'.format(
                language=language_item.language))
        order += 1


def init_menu_profile():
    """Create the profile header menu."""
    item = current_menu.submenu('main.profile')
    if current_patron:
        session['user_name'] = current_patron.formatted_name
    else:
        try:
            session['user_name'] = current_user.email
        # AnonymousUser
        except AttributeError:
            session.pop('user_name', None)
    account = session.get('user_name', _('My account'))
    if len(account) > 30:
        account = account[:30] + '…'

    rero_register(
        item,
        endpoint=None,
        text='<span class="btn btn-sm btn-success">{icon} '
             '<span class="{visible}">{account}</span><span>'.format(
                 icon='<i class="fa fa-user"></i>',
                 visible='visible-md-inline visible-lg-inline',
                 account=account
             ),
        order=1,
        id='my-account-menu',
        cssClass='py-1'
    )

    item = current_menu.submenu('main.profile.login')

    rero_register(
        item,
        endpoint='security.login',
        endpoint_arguments_constructor=lambda: dict(
            next=request.full_path
        ),
        visible_when=lambda: not current_user.is_authenticated,
        text='{icon} {login}'.format(
            icon='<i class="fa fa-sign-in"></i>',
            login=_('Login')
        ),
        order=1,
        id='login-menu',
    )

    item = current_menu.submenu('main.profile.professional')
    rero_register(
        item,
        endpoint='rero_ils.professional',
        visible_when=lambda: current_patron.is_librarian,
        text='{icon} {professional}'.format(
            icon='<i class="fa fa-briefcase"></i>',
            professional=_('Professional interface')
        ),
        order=1,
        id='professional-interface-menu',
    )

    item = current_menu.submenu('main.profile.logout')
    rero_register(
        item,
        endpoint='security.logout',
        endpoint_arguments_constructor=lambda: dict(
            next='/{viewcode}'.format(viewcode=request.view_args.get(
                'viewcode', current_app.config.get(
                    'RERO_ILS_SEARCH_GLOBAL_VIEW_CODE'))
            )
        ),
        visible_when=lambda: current_user.is_authenticated,
        text='{icon} {logout}'.format(
            icon='<i class="fa fa-sign-out"></i>',
            logout=_('Logout')
        ),
        order=2,
        id='logout-menu',
    )

    item = current_menu.submenu('main.profile.profile')
    rero_register(
        item,
        endpoint='invenio_userprofiles.profile',
        visible_when=lambda: current_user.is_authenticated,
        text='{icon} {profile}'.format(
            icon='<i class="fa fa-user"></i>',
            profile=_('RERO ID')
        ),
        order=1,
        id='profile-menu',
    )

    item = current_menu.submenu('main.profile.signup')
    rero_register(
        item,
        endpoint='security.register',
        visible_when=lambda: not current_user.is_authenticated,
        text='{icon} {signup}'.format(
            icon='<i class="fa fa-user-plus"></i>',
            signup=_('Sign Up')
        ),
        order=2,
        id='signup-menu',
    )


@blueprint.before_app_request
def init_menu():
    """Create the header menus."""
    if (request.endpoint not in ['patrons.logged_user',
                                 'rero_ils.schemaform',
                                 'invenio_i18n.set_lang',
                                 'static',
                                 'security.login',
                                 'patrons.logged_user',
                                 '_debug_toolbar.static'] and
            request.method == 'GET'):
        init_menu_tools()
        init_menu_lang()
        init_menu_profile()


def check_organisation_viewcode(fn):
    """Check if viewcode parameter is defined."""
    @wraps(fn)
    def decorated_view(*args, **kwargs):
        viewCodes = Organisation.all_code()
        # Add default view code
        viewCodes.append(current_app.config.get(
            'RERO_ILS_SEARCH_GLOBAL_VIEW_CODE'))
        if not kwargs['viewcode'] in viewCodes:
            abort(404)
        return fn(*args, **kwargs)

    return decorated_view


@blueprint.route('/error')
def error():
    """Error to generate exception for test purposes."""
    raise Exception('this is an error for test purposes')


@blueprint.route('/')
def index():
    """Home Page."""
    return render_template('rero_ils/frontpage.html',
                           version=__version__,
                           organisations=Organisation.get_all(),
                           viewcode=current_app.config.get(
                               'RERO_ILS_SEARCH_GLOBAL_VIEW_CODE'))


@blueprint.route('/<string:viewcode>')
@blueprint.route('/<string:viewcode>/')
@check_organisation_viewcode
def index_with_view_code(viewcode):
    """Home Page."""
    if viewcode == current_app.config.get('RERO_ILS_SEARCH_GLOBAL_VIEW_CODE'):
        return redirect(url_for(
            'rero_ils.index'
        ))
    else:
        return render_template(
            'rero_ils/frontpage.html',
            version=__version__,
            viewcode=viewcode
        )


@blueprint.route('/language', methods=['POST', 'PUT'])
def set_language():
    """Set language in session.

    The call should be a HTTP POST or PUT request with a JSON body as follows:

    .. code-block:: json

        {
            "lang": "fr"
        }
    """
    data = request.get_json()
    if not data or not data.get('lang'):
        return jsonify(
            {'errors': [{'code': 400, 'title': 'missing lang property'}]}), 400
    lang_code = data.get('lang')
    languages = dict(current_app.extensions['invenio-i18n'].get_languages())
    if lang_code not in languages:
        return jsonify(
            {'errors': [{'code': 400, 'title': 'unsupported language'}]}), 400
    session[current_app.config['I18N_SESSION_KEY']] = lang_code.lower()
    return jsonify({'lang': lang_code})


@blueprint.route('/<string:viewcode>/search/<recordType>')
@check_organisation_viewcode
def search(viewcode, recordType):
    """Search page ui."""
    return render_template(current_app.config.get('RERO_ILS_SEARCH_TEMPLATE'),
                           viewcode=viewcode)


@blueprint.app_template_filter()
def nl2br(string):
    r"""Replace \n to <br>."""
    return string.replace("\n", "<br>")


@blueprint.app_template_filter('urlActive')
def url_active(string, target):
    """Add link url on text if http detected."""
    result = re.findall('(https?://[\\w|.|\\-|\\/]+)', string)
    for link in result:
        if link:
            string = string.replace(
                link,
                '<a href="{url}" target="{target}">{url}</a>'.format(
                    url=link,
                    target=target
                )
            )
    return string


def prepare_jsonschema(schema):
    """Json schema prep."""
    schema = copy.deepcopy(schema)
    schema.pop('$schema', None)
    schema['required'].remove('pid')
    return schema


@blueprint.route('/schemaform/<document_type>')
def schemaform(document_type):
    """Return schema and form options for the editor."""
    doc_type = document_type
    doc_type = re.sub('ies$', 'y', doc_type)
    doc_type = re.sub('s$', '', doc_type)
    data = {}
    schema = None
    schema_name = None
    try:
        if current_app.debug:
            current_jsonschemas.get_schema.cache_clear()
        schema_name = '{}/{}-v0.0.1.json'.format(document_type, doc_type)
        schema = current_jsonschemas.get_schema(schema_name, with_refs=True)
        data['schema'] = prepare_jsonschema(schema)
    except JSONSchemaNotFound:
        abort(404)

    return jsonify(data)


@blueprint.route('/professional/', defaults={'path': ''})
@blueprint.route('/professional/<path:path>')
@can_access_professional_view
def professional(path):
    """Return professional view."""
    return render_template('rero_ils/professional.html')
