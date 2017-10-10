# -*- coding: utf-8 -*-

"""reroils-app base Invenio configuration."""

from __future__ import absolute_import, print_function

from invenio_search import RecordsSearch


# Identity function for string extraction
def _(x):
    return x

# Default language and timezone
BABEL_DEFAULT_LANGUAGE = 'en'
BABEL_DEFAULT_TIMEZONE = 'Europe/Zurich'
I18N_LANGUAGES = [
    ('fr', _('French')),
    ('de', _('German')),
    ('it', _('Italian'))
]

HEADER_TEMPLATE = 'invenio_theme/header.html'
BASE_TEMPLATE = 'invenio_theme/page.html'
COVER_TEMPLATE = 'invenio_theme/page_cover.html'
SETTINGS_TEMPLATE = 'invenio_theme/page_settings.html'
THEME_FOOTER_TEMPLATE = 'reroils_app/footer.html'
THEME_LOGO = 'images/logo_rero_ils.png'


# WARNING: Do not share the secret key - especially do not commit it to
# version control.
SECRET_KEY = 'vdJLhU0z3elI6NyfB0y8ZSJwabuJ4B3mgjXtVxBKUGaqKxfoirLUrVjJAMQx3zKCzPqo6YwT0cprOsamTEI2vVMWdmOTp7Xn0GjzcIFs1n3baDQlicLhbI5dzyWqGBrKZS6rOpipZMdnwP1yMBtmu5dTBVfVjLd5yaTCx1iUKHjLNYMdY6k4XWUWDSIdNMfM5GF63Ar1qfRcCtzivQtYMX4UujM03rC5Ciu6osoxDMsxEwfwaMXhkUn1Py6WtttM'

# Theme
THEME_SITENAME = _('reroils-app')

# For dev
APP_ENABLE_SECURE_HEADERS=False

# no needs for redis
CACHE_TYPE='simple'


USER_EMAIL='software@rero.ch'
USER_PASS='uspass123'

SQLALCHEMY_DATABASE_URI='postgresql+psycopg2://reroils:dbpass123@postgresql:5432/reroils'
SEARCH_ELASTIC_HOSTS='elasticsearch'
CELERY_BROKER_URL='amqp://guest:guest@rabbitmq:5672//'
CELERY_RESULT_BACKEND='redis://redis:6379/1'

JSONSCHEMAS_ENDPOINT='/schema'
JSONSCHEMAS_HOST='ils.test.rero.ch'

RECORDS_REST_ENDPOINTS = dict(
    recid=dict(
        pid_type='recid',
        pid_minter='bibid',
        pid_fetcher='bibid',
        search_class=RecordsSearch,
        search_index=None,
        search_type=None,
        record_serializers={
            'application/json': ('invenio_records_rest.serializers'
                                 ':json_v1_response'),
        },
        search_serializers={
            'application/json': ('invenio_records_rest.serializers'
                                 ':json_v1_search'),
        },
        list_route='/records/',
        item_route='/records/<pid(recid):pid_value>',
        default_media_type='application/json',
        max_result_window=10000,
    ),
)
