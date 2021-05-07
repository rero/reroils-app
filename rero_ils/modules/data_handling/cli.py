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

"""Click command-line interface for Data handling record management."""

from __future__ import absolute_import, print_function

import json
import os

import click
from flask.cli import with_appcontext

from ..item_types.api import ItemType
from ..utils import get_record_class_from_schema_or_pid_type, \
    get_ref_for_pid, read_json_record


@click.command('set_circulation_category')
@click.option('-l', '--lazy', 'lazy', is_flag=True, default=False)
@click.option('-e', '--save_errors', 'save_errors', type=click.File('w'))
@click.option('-o', '--output', 'output', type=click.File('w'))
@click.option('-t', '--record_type', 'record_type', is_flag=False,
              default='item')
@click.option('-v', '--verbose', 'verbose', is_flag=True, default=False)
@click.option('-d', '--debug', 'debug', is_flag=True, default=False)
@click.argument('infile', type=click.File('r'))
@with_appcontext
def set_circulation_category(
        infile, lazy, save_errors, output, record_type, verbose, debug):
    """Set circulation category for items and holdings.

    infile: Json file contains record pid and the new category.
    :param record_type: either item or hold as in RECORDS_REST_ENDPOINTS.
    :param lazy: lazy reads file.
    :param save_errors: save error records to file.
    :param output: save modified records to file.
    """
    # TODO: move this method and other similar methods to a new project that
    # deals with correction masss in REROILS.
    if record_type not in ['item', 'hold']:
        click.secho(
            f'{record_type} is an unsupported record type', fg='red')
        exit()
    if output:
        name, ext = os.path.splitext(infile.name)
        out_file_name = f'{name}_output{ext}'
        out_file = open(out_file_name, 'w')
        out_file.write('[\n')

    if save_errors:
        name, ext = os.path.splitext(infile.name)
        err_file_name = f'{name}_errors{ext}'
        error_file = open(err_file_name, 'w')
        error_file.write('[\n')

    if lazy:
        file_data = read_json_record(infile)
    else:
        file_data = json.load(infile)

    click.secho(f'Setting circulation category {record_type}', fg='green')

    counter = 0
    for counter, record in enumerate(file_data):
        record_pid = record.get('pid')
        new_circ_category = record.get('new_circulation_category')

        if not record_pid or not new_circ_category:
            click.secho(f'record # {counter} missing fields', fg='red')
            if save_errors:
                error_file.write(
                    json.dumps(record, indent=2, separators=(',', ': ')))
            continue

        record_class = get_record_class_from_schema_or_pid_type(
            pid_type=record_type)

        record = record_class.get_record_by_pid(record_pid)
        itty = ItemType.get_record_by_pid(new_circ_category)
        # we do not modify circulation category if:
        # item is not in database
        # invalid new new_circ_category
        # items of type issue
        # holdings records, need to add methods for this type
        if not record or not itty or record_type == 'holding' or (
            record_type == 'item' and record.item_record_type == 'issue'
        ):
            click.secho(
                f'unable to modify rec # {counter} pid {record_pid}', fg='red')
            if save_errors:
                error_file.write(json.dumps(record, indent=2))
            continue

        try:
            if record_type == 'item':
                record['item_type'] = {
                    '$ref': get_ref_for_pid('item_types', new_circ_category)
                }
                record.update(record, dbcommit=True, reindex=True)
            elif record_type == 'holding':
                record['circulation_category'] = {
                    '$ref': get_ref_for_pid('item_types', new_circ_category)
                }
                # TODO: need method to change holdings circ_cat for hold/items

            click.secho(f'record # {counter} created', fg='green')
            if output:
                record['old_item_type'] = new_circ_category
                out_file.write(
                    json.dumps(record, indent=2, separators=(',', ': ')))
        except Exception as err:
            text = f'record# {counter} pid {record_pid} failed creation {err}'
            click.secho(text, fg='red')
            if save_errors:
                error_file.write(
                    json.dumps(record, indent=2, separators=(',', ': ')))
    if save_errors:
        error_file.write(']')
        error_file.close()
    if output:
        out_file.write(']')
        out_file.close()
