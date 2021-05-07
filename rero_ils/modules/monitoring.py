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

"""Monitoring utilities."""

import time
from functools import wraps

import click
from elasticsearch.exceptions import NotFoundError
from flask import Blueprint, current_app, jsonify, request, url_for
from flask.cli import with_appcontext
from flask_login import current_user
from invenio_cache import current_cache
from invenio_db import db
from invenio_pidstore.models import PersistentIdentifier, PIDStatus
from invenio_search import RecordsSearch, current_search_client
from redis import Redis

from .utils import get_record_class_from_schema_or_pid_type
from ..permissions import monitoring_permission

api_blueprint = Blueprint(
    'api_monitoring',
    __name__,
    url_prefix='/monitoring'
)


def check_authentication(func):
    """Decorator to check authentication for items HTTP API."""
    @wraps(func)
    def decorated_view(*args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify({'status': 'error: Unauthorized'}), 401
        if not monitoring_permission.require().can():
            return jsonify({'status': 'error: Forbidden'}), 403
        return func(*args, **kwargs)
    return decorated_view


@api_blueprint.route('/db_connection_counts')
@check_authentication
def db_connection_counts():
    """Display DB connection counts.

    :return: jsonified count for db connections
    """
    query = """
        select
            max_conn, used, res_for_super,
            max_conn-used-res_for_super res_for_normal
        from
            (
                select count(*) used
                from pg_stat_activity
            ) t1,
            (
                select setting::int res_for_super
                from pg_settings
                where name=$$superuser_reserved_connections$$
            ) t2,
            (
                select setting::int max_conn
                from pg_settings
                where name=$$max_connections$$
            ) t3
        """
    try:
        max_conn, used, res_for_super, free = db.session.execute(query).first()
    except Exception as error:
        return jsonify({'ERROR': error})
    return jsonify({'data': {
        'max': max_conn,
        'used': used,
        'res_super': res_for_super,
        'free': free
    }})


@api_blueprint.route('/db_connections')
@check_authentication
def db_connections():
    """Display DB connections.

    :return: jsonified connections for db
    """
    query = """
        SELECT
            pid, application_name, client_addr, client_port, backend_start,
            xact_start, query_start,  wait_event, state, left(query, 64)
        FROM
            pg_stat_activity
        ORDER BY query_start DESC
    """
    try:
        results = db.session.execute(query).fetchall()
    except Exception as error:
        return jsonify({'ERROR': error})
    data = {}
    for pid, application_name, client_addr, client_port, backend_start, \
            xact_start, query_start, wait_event, state, left in results:
        data[pid] = {
            'application_name': application_name,
            'client_addr': client_addr,
            'client_port': client_port,
            'backend_start': backend_start,
            'xact_start': xact_start,
            'query_start': query_start,
            'wait_event': wait_event,
            'state': state,
            'left': left
        }
    return jsonify({'data': data})


@api_blueprint.route('/es_db_counts')
def es_db_counts():
    """Display count for elasticsearch and documents.

    Displays for all document types defind in config.py following informations:
    - index name for document type
    - count of records in database
    - count of records in elasticsearch
    - difference between the count in elasticsearch and database
    :return: jsonified count for elasticsearch and documents
    """
    difference_db_es = request.args.get('diff', False)
    with_deleted = request.args.get('deleted', False)
    return jsonify({'data': Monitoring.info(
        with_deleted=with_deleted,
        difference_db_es=difference_db_es
    )})


@api_blueprint.route('/check_es_db_counts')
def check_es_db_counts():
    """Displays health status for elasticsearch and database counts.

    If there are no problems the status in returned data will be `green`,
    otherwise the status will be `red` and in the returned error
    links will be provided with more detailed informations.
    :return: jsonified health status for elasticsearch and database counts
    """
    result = {'data': {'status': 'green'}}
    difference_db_es = request.args.get('diff', False)
    with_deleted = request.args.get('deleted', False)
    checks = Monitoring.check(
        with_deleted=with_deleted,
        difference_db_es=difference_db_es
    )
    if checks:
        result = {'data': {'status': 'red'}}
        errors = []
        for doc_type, doc_type_data in checks.items():
            links = {'about': url_for(
                'api_monitoring.check_es_db_counts', _external=True)}
            for info, count in doc_type_data.items():
                if info == 'db_es':
                    msg = 'There are {count} items from {info} missing in ES.'
                    msg = msg.format(count=count, info=doc_type)
                    links[doc_type] = url_for(
                        'api_monitoring.missing_pids',
                        doc_type=doc_type,
                        _external=True
                    )
                    errors.append({
                        'id': 'DB_ES_COUNTER_MISSMATCH',
                        'links': links,
                        'code': 'DB_ES_COUNTER_MISSMATCH',
                        'title': "DB items counts don't match ES items count.",
                        'details': msg
                    })
                elif info == 'db-':
                    msg = 'There are {count} items from {info} missing in DB.'
                    msg = msg.format(count=count, info=doc_type)
                    links[doc_type] = url_for(
                        'api_monitoring.missing_pids',
                        doc_type=doc_type,
                        _external=True
                    )
                    errors.append({
                        'id': 'DB_ES_UNEQUAL',
                        'links': links,
                        'code': 'DB_ES_UNEQUAL',
                        'title': "DB items unequal ES items.",
                        'details': msg
                    })
                elif info == 'es-':
                    msg = 'There are {count} items from {info} missing in ES.'
                    msg = msg.format(count=count, info=doc_type)
                    links[doc_type] = url_for(
                        'api_monitoring.missing_pids',
                        doc_type=doc_type,
                        _external=True
                    )
                    errors.append({
                        'id': 'DB_ES_UNEQUAL',
                        'links': links,
                        'code': 'DB_ES_UNEQUAL',
                        'title': "DB items unequal ES items.",
                        'details': msg
                    })
        result['errors'] = errors
    return jsonify(result)


@api_blueprint.route('/missing_pids/<doc_type>')
@check_authentication
def missing_pids(doc_type):
    """Displays details of counts for document type.

    Following informations will be displayed:
    - missing pids in database
    - missing pids in elasticsearch
    - pids indexed multiple times in elasticsearch
    If possible, direct links will be provieded to the corresponding records.
    This view needs an logged in system admin.

    :param doc_type: Document type to display.
    :return: jsonified details of counts for document type
    """
    try:
        api_url = url_for(
            f'invenio_records_rest.{doc_type}_list',
            _external=True
        )
    except Exception:
        api_url = None
    mon = Monitoring.missing(doc_type)
    if mon.get('ERROR'):
        return {
            'error': {
                'id': 'DOCUMENT_TYPE_NOT_FOUND',
                'code': 'DOCUMENT_TYPE_NOT_FOUND',
                'title': "Document type not found.",
                'details': mon.get('ERROR')
            }
        }
    else:
        data = {'DB': [], 'ES': [], 'ES duplicate': []}
        for pid in mon.get('DB'):
            if api_url:
                data['DB'].append(f'{api_url}?q=pid:{pid}')
            else:
                data['DB'].append(pid)
        for pid in mon.get('ES'):
            if api_url:
                data['ES'].append(f'{api_url}{pid}')
            else:
                data['ES'].append(pid)
        for pid in mon.get('ES duplicate'):
            if api_url:
                url = f'{api_url}?q=pid:{pid}'
                data['ES duplicate'][url] = len(mon.get('ES duplicate'))
            else:
                data['ES duplicate'][pid] = len(mon.get('ES duplicate'))
        return jsonify({'data': data})


@api_blueprint.route('/redis')
@check_authentication
def redis():
    """Displays redis info.

    :return: jsonified redis info.
    """
    url = current_app.config.get('ACCOUNTS_SESSION_REDIS_URL',
                                 'redis://localhost:6379')
    redis = Redis.from_url(url)
    info = redis.info()
    return jsonify({'data': info})


@api_blueprint.route('/es')
@check_authentication
def elastic_search():
    """Displays elastic search cluster info.

    :return: jsonified elastic search cluster info.
    """
    info = current_search_client.cluster.health()
    return jsonify({'data': info})


@api_blueprint.route('/timestamps')
@check_authentication
def timestamps():
    """Get time stamps from current cache.

    Makes the saved timestamps accessible via url requests.

    :return: jsonified timestamps.
    """
    data = {}
    time_stamps = current_cache.get('timestamps')
    if time_stamps:
        for name, values in time_stamps.items():
            data[name] = {}
            for key, value in values.items():
                if key == 'time':
                    data[name]['utctime'] = value.strftime(
                        "%Y-%m-%d %H:%M:%S"
                    )
                    data[name]['unixtime'] = time.mktime(value.timetuple())
                else:
                    data[name][key] = value

    return jsonify({'data': data})


class Monitoring(object):
    """Monitoring class.

    The main idea here is to check the consistency between the database and
    the search index. We need to check that all documents presents in the
    database are also present in the search index and vice versa.
    Addidionaly timestamps could be accessed for monitoring of execution
    times of selected functions.
    """

    def __str__(self):
        """Table representation of database and elasticsearch differences.

        :return: string representation of database and elasticsearch
        differences. Following columns are in the string:
            1. database count minus elasticsearch count
            2. document type
            3. database count
            4. elasticsearch index
            5. elasticsearch count
        """
        result = ''
        msg_head = 'DB - ES  {doc_type:>6} {count_db:>10}'.format(
            doc_type='type',
            count_db='count'
        )
        msg_head += '  {index:>25} {count_es:>10}\n'.format(
            index='index',
            count_es='count'
        )
        msg_head += '{:-^64s}\n'.format('')

        for doc_type, info in sorted(self.info().items()):
            msg = '{db_es:>7}  {doc_type:>6} {count_db:>10}'.format(
                db_es=info.get('db-es', ''),
                doc_type=doc_type,
                count_db=info.get('db', ''),
            )
            index = info.get('index', '')
            if index:
                msg += '  {index:>25} {count_es:>10}'.format(
                    index=index,
                    count_es=info.get('es', '')
                )
            result += msg + '\n'
        return msg_head + result

    @classmethod
    def get_db_count(cls, doc_type, with_deleted=False):
        """Get database count.

        Get count of items in the database for the given document type.

        :param doc_type: document type.
        :param with_deleted: count also deleted items.
        :return: item count.
        """
        if not current_app.config.get('RECORDS_REST_ENDPOINTS').get(doc_type):
            return f'No >>{doc_type}<< in DB'
        query = PersistentIdentifier.query.filter_by(pid_type=doc_type)
        if not with_deleted:
            query = query.filter_by(status=PIDStatus.REGISTERED)
        return query.count()

    @classmethod
    def get_es_count(cls, index):
        """Get elasticsearch count.

        Get count of items in elasticsearch for the given index.

        :param index: index.
        :return: items count.
        """
        try:
            result = RecordsSearch(index=index).query().count()
        except NotFoundError:
            result = f'No >>{index}<< in ES'
        return result

    @classmethod
    def get_es_db_missing_pids(cls, doc_type, with_deleted=False):
        """Get ES and DB counts."""
        endpoint = current_app.config.get(
            'RECORDS_REST_ENDPOINTS'
        ).get(doc_type, {})
        index = endpoint.get('search_index')
        record_class = get_record_class_from_schema_or_pid_type(
            pid_type=doc_type
        )
        pids_es_double = []
        pids_es = []
        pids_db = []
        if index:
            pids_es = {}
            for hit in RecordsSearch(index=index).source('pid').scan():
                if pids_es.get(hit.pid):
                    pids_es_double.append(hit.pid)
                pids_es[hit.pid] = 1
            pids_db = []
            for pid in record_class.get_all_pids(with_deleted=with_deleted):
                if pids_es.get(pid):
                    pids_es.pop(pid)
                else:
                    pids_db.append(pid)
            pids_es = [v for v in pids_es]
        return pids_es, pids_db, pids_es_double, index

    @classmethod
    def info(cls, with_deleted=False, difference_db_es=False):
        """Info.

        Get count details for all records rest endpoints in json format.

        :param with_deleted: count also deleted items in database.
        :return: dictionary with database, elasticsearch and databse minus
        elasticsearch count informations.
        """
        info = {}
        for doc_type, endpoint in current_app.config.get(
            'RECORDS_REST_ENDPOINTS'
        ).items():
            info[doc_type] = {}
            count_db = cls.get_db_count(doc_type, with_deleted=with_deleted)
            info[doc_type]['db'] = count_db
            index = endpoint.get('search_index', '')
            if index:
                count_es = cls.get_es_count(index)
                db_es = count_db - count_es
                info[doc_type]['index'] = index
                info[doc_type]['es'] = count_es
                info[doc_type]['db-es'] = db_es
                if db_es == 0 and difference_db_es:
                    missing_in_db, missing_in_es, pids_es_double, index = \
                        cls.get_es_db_missing_pids(
                            doc_type=doc_type,
                            with_deleted=with_deleted
                        )
                    if index:
                        if missing_in_db:
                            info[doc_type]['db-'] = list(missing_in_db)
                        if missing_in_es:
                            info[doc_type]['es-'] = list(missing_in_es)
        return info

    @classmethod
    def check(cls, with_deleted=False, difference_db_es=False):
        """Compaire elasticsearch with database counts.

        :param with_deleted: count also deleted items in database.
        :return: dictionary with all document types with a difference in
        databse and elasticsearch counts.
        """
        checks = {}
        for info, data in cls.info(
            with_deleted=with_deleted,
            difference_db_es=difference_db_es
        ).items():
            db_es = data.get('db-es', '')
            if db_es not in [0, '']:
                checks.setdefault(info, {})
                checks[info]['db_es'] = db_es
            if data.get('db-'):
                checks.setdefault(info, {})
                checks[info]['db-'] = len(data.get('db-'))
            if data.get('es-'):
                checks.setdefault(info, {})
                checks[info]['es-'] = len(data.get('es-'))
        return checks

    @classmethod
    def missing(cls, doc_type, with_deleted=False):
        """Get missing pids.

        Get missing pids in database and elasticsearch and find duplicate
        pids in elasticsearch.

        :param doc_type: doc type to get missing pids.
        :return: dictionary with all missing pids.
        """
        missing_in_db, missing_in_es, pids_es_double, index =\
            cls.get_es_db_missing_pids(
                doc_type=doc_type,
                with_deleted=with_deleted
            )
        if index:
            return {
                'DB': list(missing_in_db),
                'ES': list(missing_in_es),
                'ES duplicate': pids_es_double
            }
        else:
            return {'ERROR': f'Document type not found: {doc_type}'}

    @classmethod
    def print_missing(cls, doc_type):
        """Print missing pids for the given document type.

        :param doc_type: doc type to print.
        """
        for info, data in cls.missing(doc_type=doc_type).items():
            if data:
                if info == 'ES duplicate':
                    msg = 'duplicate in ES'
                else:
                    msg = f'pids missing in {info}'
                click.secho(f'{doc_type}: {msg}:', fg='red')
                if info == 'ES duplicate':
                    pid_counts = []
                    for pid, count in data.items():
                        pid_counts.append(f'{pid}: {count}')
                    click.echo(', '.join(pid_counts))
                else:
                    click.echo(', '.join(data))


@click.group()
def monitoring():
    """Monitoring commands."""


@monitoring.command('es_db_counts')
@click.option('-m', '--missing', 'missing', is_flag=True, default=False,
              help='display missing pids')
@with_appcontext
def es_db_counts_cli(missing):
    """Print ES and DB counts.

    Prints a table representation of database and elasticsearch counts.
    Columes:
    1. database count minus elasticsearch count
    2. document type
    3. database count
    4. elasticsearch index
    5. elasticsearch count
    """
    missing_doc_types = []
    mon = Monitoring()
    msg_head = 'DB - ES  {doc_type:>6} {count_db:>10}'.format(
        doc_type='type',
        count_db='count'
    )
    msg_head += '  {index:>25} {count_es:>10}\n'.format(
        index='index',
        count_es='count'
    )
    msg_head += '{:-^64s}'.format('')
    click.echo(msg_head)
    info = mon.info(with_deleted=False, difference_db_es=False)
    for doc_type in sorted(info):
        db_es = info[doc_type].get('db-es', '')
        msg = '{db_es:>7}  {doc_type:>6} {count_db:>10}'.format(
            db_es=db_es,
            doc_type=doc_type,
            count_db=info[doc_type].get('db', ''),
        )
        index = info[doc_type].get('index', '')
        if index:
            msg += '  {index:>25} {count_es:>10}'.format(
                index=index,
                count_es=info[doc_type].get('es', '')
            )
        if db_es not in [0, '']:
            click.secho(msg, fg='red')
        else:
            click.echo(msg)
        if missing and index:
            missing_doc_types.append(doc_type)
    for missing_doc_type in missing_doc_types:
        mon.print_missing(missing_doc_type)


@monitoring.command('es_db_missing')
@click.argument('doc_type')
@with_appcontext
def es_db_missing_cli(doc_type):
    """Print missing pids informations."""
    Monitoring().print_missing(doc_type)


@monitoring.command('time_stamps')
@with_appcontext
def time_stamps_cli():
    """Print time_stampss informations."""
    for key, value in current_cache.get('timestamps').items():
        time = value.pop('time')
        args = [f'{k}={v}' for k, v in value.items()]
        click.echo(f'{time}: {key} {" | ".join(args)}')
