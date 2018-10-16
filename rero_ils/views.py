# -*- coding: utf-8 -*-
#
# This file is part of RERO ILS.
# Copyright (C) 2017 RERO.
#
# RERO ILS is free software; you can redistribute it
# and/or modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 2 of the
# License, or (at your option) any later version.
#
# RERO ILS is distributed in the hope that it will be
# useful, but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with RERO ILS; if not, write to the
# Free Software Foundation, Inc., 59 Temple Place, Suite 330, Boston,
# MA 02111-1307, USA.
#
# In applying this license, RERO does not
# waive the privileges and immunities granted to it by virtue of its status
# as an Intergovernmental Organization or submit itself to any jurisdiction.

"""Blueprint used for loading templates."""

from __future__ import absolute_import, print_function

from functools import partial

from flask import Blueprint, current_app, redirect, render_template, request
from flask_babelex import gettext as _
from flask_login import current_user
from flask_menu import current_menu
from invenio_i18n.ext import current_i18n

from .version import __version__

blueprint = Blueprint(
    'rero_ils',
    __name__,
    template_folder='templates',
    static_folder='static',
)


@blueprint.before_app_first_request
def init_menu():
    """Create the header menus."""
    item = current_menu.submenu('main.menu')
    item.register(
        endpoint=None,
        text=_(
            '%(icon)s <span class="visible-md-inline visible-lg-inline">'
            'Menu</span>',
            icon='<i class="fa fa-bars"></i>'),
        order=0)

    order = 10

    def return_language(lang):
        return dict(lang_code=lang)

    def hide_language(lang):
        return current_i18n.language != lang

    for language_item in current_i18n.get_locales():
        item = current_menu.submenu(
            'main.menu.lang_{language}'.format(
                language=language_item.language))
        item.register(
            endpoint='invenio_i18n.set_lang',
            endpoint_arguments_constructor=partial(
                return_language, language_item.language),
            text=_(
                '%(icon)s %(language)s',
                icon='<i class="fa fa-language"></i>',
                language=language_item.language),
            visible_when=partial(hide_language, language_item.language),
            order=order)
        order += 1

    item = current_menu.submenu('main.menu.help')
    item.register(
        endpoint='rero_ils.help',
        text=_('%(icon)s Help', icon='<i class="fa fa-info"></i>'),
        order=100)

    item = current_menu.submenu('main.profile')
    item.register(
        endpoint=None,
        text=_(
            '%(icon)s <span class="visible-md-inline visible-lg-inline">My '
            'Account</span>',
            icon='<i class="fa fa-user"></i>'),
        order=1)

    item = current_menu.submenu('main.profile.login')
    item.register(
        endpoint='security.login',
        endpoint_arguments_constructor=lambda: dict(next=request.path),
        visible_when=lambda: not current_user.is_authenticated,
        text=_('%(icon)s Login', icon='<i class="fa fa-sign-in"></i>'),
        order=1)

    item = current_menu.submenu('main.profile.logout')
    item.register(
        endpoint='security.logout',
        visible_when=lambda: current_user.is_authenticated,
        text=_('%(icon)s Logout', icon='<i class="fa fa-sign-out"></i>'),
        order=1)

    item = current_menu.submenu('main.profile.signup')
    item.register(
        endpoint='security.register',
        visible_when=lambda: not current_user.is_authenticated,
        text=_('%(icon)s Sign Up', icon='<i class="fa fa-user-plus"></i>'),
        order=2)


@blueprint.route('/ping', methods=['HEAD', 'GET'])
def ping():
    """Load balancer ping view."""
    return 'OK'


@blueprint.route('/')
def index():
    """Home Page."""
    return render_template('rero_ils/frontpage.html',
                           version=__version__)


@blueprint.route('/help')
def help():
    """Help Page."""
    return redirect(
        current_app.config.get('RERO_ILS_APP_HELP_PAGE'),
        code=302)


@blueprint.app_template_filter()
def nl2br(string):
    r"""Replace \n to <br>."""
    return string.replace("\n", "<br>")
