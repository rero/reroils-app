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

"""Common pytest fixtures and plugins."""
import json
import os
import shutil
import sys
import tempfile
from os.path import dirname, join

import pytest
from dotenv import load_dotenv

pytest_plugins = (
    'celery.contrib.pytest',
    'fixtures.circulation',
    'fixtures.metadata',
    'fixtures.organisations',
    'fixtures.acquisition',
    'fixtures.sip2',
    'fixtures.basics'
)


@pytest.fixture(scope='module')
def es(appctx):
    """Setup and teardown all registered Elasticsearch indices.

    Scope: module
    This fixture will create all registered indexes in Elasticsearch and remove
    once done. Fixtures that perform changes (e.g. index or remove documents),
    should used the function-scoped :py:data:`es_clear` fixture to leave the
    indexes clean for the following tests.
    """
    from invenio_search import current_search, current_search_client
    from invenio_search.errors import IndexAlreadyExistsError

    try:
        list(current_search.put_templates())
    except IndexAlreadyExistsError:
        current_search_client.indices.delete_template('*')
        list(current_search.put_templates())

    try:
        list(current_search.create())
    except IndexAlreadyExistsError:
        list(current_search.delete(ignore=[404]))
        list(current_search.create())
    current_search_client.indices.refresh()

    try:
        yield current_search_client
    finally:
        current_search_client.indices.delete(index='*')
        current_search_client.indices.delete_template('*')


@pytest.fixture(scope="module")
def data():
    """Load fixture data file."""
    with open(join(dirname(__file__), 'data/data.json')) as f:
        data = json.load(f)
        return data


@pytest.fixture(scope="module")
def acquisition():
    """Load fixture acquisition file."""
    with open(join(dirname(__file__), 'data/acquisition.json')) as f:
        data = json.load(f)
        return data


@pytest.fixture(scope="module")
def holdings():
    """Load fixture holdings file."""
    with open(join(dirname(__file__), 'data/holdings.json')) as f:
        data = json.load(f)
        return data


@pytest.fixture(scope="module")
def local_fields():
    """Load local fields file."""
    with open(join(dirname(__file__), 'data/local_fields.json')) as f:
        data = json.load(f)
        return data


@pytest.fixture(scope="session")
def csv_header():
    """Load json headers."""
    return [
        ('Accept', 'text/csv'),
        ('Content-Type', 'application/json')
    ]


@pytest.fixture(scope="session")
def json_header():
    """Load json headers."""
    return [
        ('Accept', 'application/json'),
        ('Content-Type', 'application/json')
    ]


@pytest.fixture(scope="session")
def rero_marcxml_header():
    """Load marcxml headers."""
    return [
        ('Accept', 'application/json'),
        ('Content-Type', 'application/marcxml+xml')
    ]


@pytest.fixture(scope="session")
def rero_json_header():
    """Load json headers."""
    return [
        ('Accept', 'application/rero+json'),
        ('Content-Type', 'application/json')
    ]


@pytest.fixture(scope="session")
def can_delete_json_header():
    """Load can_delete json headers."""
    return [
        ('Accept', 'application/can-delete+json'),
        ('Content-Type', 'application/json')
    ]


@pytest.fixture(scope='module')
def app_config(app_config):
    """Create temporary instance dir for each test."""
    app_config['BROKER_URL'] = 'memory://'
    app_config['CELERY_BROKER_URL'] = 'memory://'
    app_config['RATELIMIT_STORAGE_URL'] = 'memory://'
    app_config['CACHE_TYPE'] = 'simple'
    app_config['SEARCH_ELASTIC_HOSTS'] = None
    app_config['SQLALCHEMY_DATABASE_URI'] = \
        'postgresql+psycopg2://rero-ils:rero-ils@localhost/rero-ils'
    app_config['DB_VERSIONING'] = True
    app_config['CELERY_CACHE_BACKEND'] = "memory"
    app_config['CELERY_RESULT_BACKEND'] = "cache"
    app_config['CELERY_TASK_ALWAYS_EAGER'] = True
    app_config['CELERY_TASK_EAGER_PROPAGATES'] = True
    help_test_dir = join(dirname(__file__), 'data', 'help')
    app_config['WIKI_CONTENT_DIR'] = help_test_dir
    app_config['WIKI_UPLOAD_FOLDER'] = join(help_test_dir, 'files')
    app_config['ACCOUNTS_SESSION_REDIS_URL'] = 'redis://localhost:6379/1'
    app_config['CACHE_REDIS_URL'] = 'redis://localhost:6379/0'
    app_config['CELERY_RESULT_BACKEND'] = 'redis://localhost:6379/2'
    app_config['CELERY_REDIS_SCHEDULER_URL'] = 'redis://localhost:6379/4'
    app_config['RATELIMIT_STORAGE_URL'] = 'redis://localhost:6379/3'
    app_config['WTF_CSRF_ENABLED'] = False
    return app_config


@pytest.fixture(scope='module')
def instance_path():
    """Temporary instance path.

    Scope: module

    This fixture creates a temporary directory if the
    environment variable ``INVENIO_INSTANCE_PATH`` is not be set.
    This directory is then automatically removed.
    """
    # load .env, .flaskenv
    load_dotenv()
    invenio_instance_path = os.environ.get('INVENIO_INSTANCE_PATH')
    invenio_static_folder = os.environ.get('INVENIO_STATIC_FOLDER')
    path = invenio_instance_path
    # static folder
    if not invenio_static_folder:
        if invenio_instance_path:
            os.environ['INVENIO_STATIC_FOLDER'] = os.path.join(
                invenio_instance_path, 'static')
        else:
            os.environ['INVENIO_STATIC_FOLDER'] = os.path.join(
                sys.prefix, 'var/instance/static')
    # instance path
    if not path:
        path = tempfile.mkdtemp()
        os.environ['INVENIO_INSTANCE_PATH'] = path
    yield path
    # clean static folder variable
    if not invenio_static_folder:
        os.environ.pop('INVENIO_STATIC_FOLDER', None)
    # clean instance path variable and remove temp dir
    if not invenio_instance_path:
        os.environ.pop('INVENIO_INSTANCE_PATH', None)
        shutil.rmtree(path)


@pytest.fixture(scope="module")
def bnf_ean_any_123():
    """Load bnf ean any 123 xml file."""
    file_name = join(dirname(__file__), 'data/bnf_ean_any_123.xml')
    with open(file_name, 'rb') as file:
        return file.read()


@pytest.fixture(scope="module")
def bnf_ean_any_9782070541270():
    """Load bnf ean any 9782070541270 xml file."""
    file_name = join(dirname(__file__), 'data/bnf_ean_any_9782070541270.xml')
    with open(file_name, 'rb') as file:
        return file.read()


@pytest.fixture(scope="module")
def bnf_ean_any_9782072862014():
    """Load bnf ean any 9782072862014 xml file."""
    file_name = join(dirname(__file__), 'data/bnf_ean_any_9782072862014.xml')
    with open(file_name, 'rb') as file:
        return file.read()


@pytest.fixture(scope="module")
def bnf_recordid_all_FRBNF370903960000006():
    """Load bnf recordid all FRBNF370903960000006 xml file."""
    file_name = join(
        dirname(__file__),
        'data/bnf_recordid_all_FRBNF370903960000006.xml'
    )
    with open(file_name, 'rb') as file:
        return file.read()


@pytest.fixture(scope="module")
def bnf_anywhere_all_peter():
    """Load bnf anywhere all peter xml file."""
    file_name = join(
        dirname(__file__),
        'data/bnf_anywhere_all_peter.xml'
    )
    with open(file_name, 'rb') as file:
        return file.read()
