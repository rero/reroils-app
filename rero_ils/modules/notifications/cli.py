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

"""Click command-line interface for notifications."""

from __future__ import absolute_import, print_function

import click
from flask.cli import with_appcontext

from .api import Notification
from .tasks import process_notifications


@click.group()
def notifications():
    """Notification management commands."""


@with_appcontext
@notifications.command('process')
@click.option('-t', '--type', 'notification_type', help="Notification Type.",
              multiple=True, default=Notification.ALL_NOTIFICATIONS)
@click.option('-k', '--enqueue', 'enqueue', is_flag=True, default=False,
              help="Enqueue record creation.")
@click.option('-v', '--verbose', 'verbose', is_flag=True, default=False,
              help='verbose')
@with_appcontext
def process(notification_type, enqueue, verbose):
    """Process notifications."""
    results = {}
    enqueue_results = {}
    for n_type in notification_type:
        if n_type not in Notification.ALL_NOTIFICATIONS:
            click.secho(
                f'Notification type does not exist: {n_type}', fg='red')
            break
        click.secho(
            f'Process notification: {n_type}', fg='green')
        if enqueue:
            enqueue_results[n_type] = process_notifications.delay(
                notification_type=n_type, verbose=verbose)
        else:
            results[n_type] = process_notifications(
                notification_type=n_type, verbose=verbose)

    if verbose:
        if enqueue_results:
            for key, value in enqueue_results.items():
                results[key] = value.get()

        for key, value in results.items():
            result_values = ' '.join([f'{k}={v}' for k, v in value.items()])
            click.secho(f'Notification {key:12}: {result_values}')
