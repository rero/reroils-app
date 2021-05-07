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

"""Click command-line interface for record management."""

from __future__ import absolute_import, print_function

import json
import os
import sys
import traceback

import click
from flask import current_app
from flask.cli import with_appcontext
from flask_security.confirmable import confirm_user
from invenio_accounts.ext import hash_password
from invenio_db import db
from invenio_jsonschemas.proxies import current_jsonschemas
from jsonmerge import Merger
from jsonschema import validate
from jsonschema.exceptions import ValidationError
from werkzeug.local import LocalProxy

from .api import User, create_patron_from_data
from ..patrons.api import Patron, PatronProvider
from ..providers import append_fixtures_new_identifiers
from ..utils import get_schema_for_resource, read_json_record

datastore = LocalProxy(lambda: current_app.extensions['security'].datastore)
records_state = LocalProxy(lambda: current_app.extensions['invenio-records'])


@click.command('import_users')
@click.option('-a', '--append', 'append', is_flag=True, default=False)
@click.option('-v', '--verbose', 'verbose', is_flag=True, default=False)
@click.option('-p', '--password', 'password', default='123456')
@click.option('-l', '--lazy', 'lazy', is_flag=True, default=False)
@click.option('-o', '--dont-stop', 'dont_stop_on_error',
              is_flag=True, default=False)
@click.option('-d', '--debug', 'debug', is_flag=True, default=False)
@click.argument('infile', type=click.File('r'), default=sys.stdin)
@with_appcontext
def import_users(infile, append, verbose, password, lazy, dont_stop_on_error,
                 debug):
    """Import users.

    :param verbose: this function will be verbose.
    :param password: the password to use for user by default.
    :param lazy: lazy reads file
    :param dont_stop_on_error: don't stop on error
    :param infile: Json user file.
    """
    click.secho('Import users:', fg='green')

    if lazy:
        # try to lazy read json file (slower, better memory management)
        data = read_json_record(infile)
    else:
        # load everything in memory (faster, bad memory management)
        data = json.load(infile)
    pids = []
    error_records = []
    for count, patron_data in enumerate(data, 1):
        password = patron_data.get('password', password)
        username = patron_data['username']
        if password:
            patron_data.pop('password', None)
        if verbose:
            if not User.get_by_username(username):
                click.secho('{count: <8} Creating user: {username}'.format(
                    count=count,
                    username=username
                    )
                )
            else:
                click.secho('{count: <8} Existing user: {username}'.format(
                        count=count,
                        username=username
                    ),
                    fg='yellow'
                )
        try:
            # patron creation
            if not Patron.get_record_by_pid(patron_data['pid']):
                patron = create_patron_from_data(
                    data=patron_data,
                    dbcommit=False,
                    reindex=False
                )
                user = patron.user
                user.password = hash_password(password)
                user.active = True
                db.session.merge(user)
                db.session.commit()
                confirm_user(user)
                patron.reindex()
                pids.append(patron.pid)
            else:
                if verbose:
                    click.secho('{count: <8} Existing patron: {username}'
                                .format(count=count, username=username),
                                fg='yellow')
        except Exception as err:
            error_records.append(patron_data)
            click.secho(
                '{count: <8} User create error: {err}'.format(
                    count=count,
                    err=err
                ),
                fg='red'
            )
            if debug:
                traceback.print_exc()
            if not dont_stop_on_error:
                sys.exit(1)
            if debug:
                traceback.print_exc()
            db.session.rollback()

    if append:
        click.secho(f'Append fixtures new identifiers: {len(pids)}')
        identifier = Patron.provider.identifier
        try:
            append_fixtures_new_identifiers(
                identifier,
                sorted(pids, key=lambda x: int(x)),
                PatronProvider.pid_type
            )
        except Exception as err:
            click.secho(
                f'ERROR append fixtures new identifiers: {err}',
                fg='red'
            )
    if error_records:
        name, ext = os.path.splitext(infile.name)
        err_file_name = f'{name}_errors{ext}'
        click.secho(f'Write error file: {err_file_name}')
        with open(err_file_name, 'w') as error_file:
            error_file.write('[\n')
            for error_record in error_records:
                for line in json.dumps(error_record, indent=2).split('\n'):
                    error_file.write('  ' + line + '\n')
            error_file.write(']')


@click.command('users_validate')
@click.argument('jsonfile', type=click.File('r'))
@click.option('-v', '--verbose', 'verbose', is_flag=True, default=False)
@click.option('-d', '--debug', 'debug', is_flag=True, default=False)
@with_appcontext
def users_validate(jsonfile, verbose, debug):
    """Check users validation."""
    click.secho('Validate user file', fg='green')

    path = current_jsonschemas.url_to_path(get_schema_for_resource('ptrn'))
    ptrn_schema = current_jsonschemas.get_schema(path=path)
    ptrn_schema = records_state.replace_refs(ptrn_schema)
    # TODO: get user schema path programaticly
    # path = current_jsonschemas.url_to_path(get_schema_for_resource('user'))
    path = 'users/user-v0.0.1.json'
    user_schema = current_jsonschemas.get_schema(path=path)
    user_schema = records_state.replace_refs(user_schema)

    merger_schema = {
        "properties": {
            "required": {"mergeStrategy": "append"}
        }
    }
    merger = Merger(merger_schema)
    schema = merger.merge(user_schema, ptrn_schema)
    schema['required'] = [
        s for s in schema['required'] if s not in ['$schema', 'user_id']]

    datas = read_json_record(jsonfile)
    for idx, data in enumerate(datas):
        if verbose:
            click.echo(f'\tTest record: {idx} pid: {data.get("pid")}')
        try:
            validate(data, schema)
            patron = data.get('patron', {})
            if patron and patron.get('communication_channel') == 'email'\
               and data.get('email') is None \
               and patron.get('additional_communication_email') is None:
                raise ValidationError('At least one email should be defined '
                                      'for an email communication channel.')
            librarian_roles = [
                Patron.ROLE_SYSTEM_LIBRARIAN, Patron.ROLE_LIBRARIAN]
            if any(role in librarian_roles for role in data.get('roles', [])):
                if not data.get('libraries'):
                    raise ValidationError('Missing libraries')

        except ValidationError as err:
            click.secho(
                f'Error validate in record: {idx} pid: {data.get("pid")}',
                fg='red'
            )
            if debug:
                click.secho(str(err))
            else:
                trace_lines = traceback.format_exc(1).split('\n')
                click.secho(trace_lines[3].strip())
