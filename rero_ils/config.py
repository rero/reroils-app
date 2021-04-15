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

"""Default configuration for rero-ils.

You overwrite and set instance-specific configuration by either:

- Configuration file: ``<virtualenv prefix>/var/instance/invenio.cfg``
- Environment variables: ``APP_<variable name>``
"""
from __future__ import absolute_import, print_function

import os
from datetime import timedelta
from functools import partial

from celery.schedules import crontab
from flask import request
from invenio_circulation.pidstore.pids import CIRCULATION_LOAN_FETCHER, \
    CIRCULATION_LOAN_MINTER, CIRCULATION_LOAN_PID_TYPE
from invenio_circulation.search.api import LoansSearch
from invenio_circulation.transitions.transitions import CreatedToPending, \
    ItemAtDeskToItemOnLoan, ItemInTransitHouseToItemReturned, \
    ItemOnLoanToItemInTransitHouse, ItemOnLoanToItemOnLoan, \
    ItemOnLoanToItemReturned, PendingToItemAtDesk, \
    PendingToItemInTransitPickup, ToCancelled, ToItemOnLoan
from invenio_records_rest.facets import terms_filter

from .modules.acq_accounts.api import AcqAccount
from .modules.acq_accounts.permissions import AcqAccountPermission
from .modules.acq_invoices.api import AcquisitionInvoice
from .modules.acq_invoices.permissions import AcqInvoicePermission
from .modules.acq_order_lines.api import AcqOrderLine
from .modules.acq_order_lines.permissions import AcqOrderLinePermission
from .modules.acq_orders.api import AcqOrder
from .modules.acq_orders.permissions import AcqOrderPermission
from .modules.budgets.api import Budget
from .modules.budgets.permissions import BudgetPermission
from .modules.circ_policies.api import CircPolicy
from .modules.circ_policies.permissions import CirculationPolicyPermission
from .modules.collections.api import Collection
from .modules.collections.permissions import CollectionPermission
from .modules.contributions.api import Contribution
from .modules.contributions.permissions import ContributionPermission
from .modules.documents.api import Document
from .modules.documents.permissions import DocumentPermission
from .modules.holdings.api import Holding
from .modules.holdings.permissions import HoldingPermission
from .modules.ill_requests.api import ILLRequest
from .modules.ill_requests.permissions import ILLRequestPermission
from .modules.item_types.api import ItemType
from .modules.item_types.permissions import ItemTypePermission
from .modules.items.api import Item
from .modules.items.models import ItemCirculationAction, ItemIssueStatus
from .modules.items.permissions import ItemPermission
from .modules.items.utils import item_location_retriever
from .modules.libraries.api import Library
from .modules.libraries.permissions import LibraryPermission
from .modules.loans.api import Loan, LoanState
from .modules.loans.permissions import LoanPermission
from .modules.loans.utils import can_be_requested, get_default_loan_duration, \
    get_extension_params, is_item_available_for_checkout, \
    loan_build_document_ref, loan_build_item_ref, loan_build_patron_ref, \
    validate_item_pickup_transaction_locations, validate_loan_duration
from .modules.local_fields.api import LocalField
from .modules.local_fields.permissions import LocalFieldPermission
from .modules.locations.api import Location
from .modules.locations.permissions import LocationPermission
from .modules.notifications.api import Notification
from .modules.notifications.permissions import NotificationPermission
from .modules.operation_logs.api import OperationLog
from .modules.operation_logs.permissions import OperationLogPermission
from .modules.organisations.api import Organisation
from .modules.organisations.permissions import OrganisationPermission
from .modules.patron_transaction_events.api import PatronTransactionEvent
from .modules.patron_transaction_events.permissions import \
    PatronTransactionEventPermission
from .modules.patron_transactions.api import PatronTransaction
from .modules.patron_transactions.permissions import \
    PatronTransactionPermission
from .modules.patron_types.api import PatronType
from .modules.patron_types.permissions import PatronTypePermission
from .modules.patrons.api import Patron
from .modules.patrons.permissions import PatronPermission
from .modules.permissions import record_permission_factory
from .modules.selfcheck.permissions import seflcheck_permission_factory
from .modules.templates.api import Template
from .modules.templates.permissions import TemplatePermission
from .modules.users.api import get_profile_countries, \
    get_readonly_profile_fields
from .modules.vendors.api import Vendor
from .modules.vendors.permissions import VendorPermission
from .permissions import librarian_delete_permission_factory, \
    librarian_permission_factory, librarian_update_permission_factory, \
    wiki_edit_ui_permission, wiki_edit_view_permission
from .query import acquisition_filter, and_i18n_term_filter, and_term_filter
from .utils import get_current_language


def _(x):
    """Identity function used to trigger string extraction."""
    return x


# Rate limiting
# =============
#: Storage for ratelimiter.
RATELIMIT_STORAGE_URL = 'redis://localhost:6379/3'
RATELIMIT_DEFAULT = '5000/second'
RATELIMIT_ENABLED = False

# I18N
# ====
#: Default language
BABEL_DEFAULT_LANGUAGE = 'en'
#: Default time zone
BABEL_DEFAULT_TIMEZONE = 'Europe/Zurich'
#: Other supported languages (do not include the default language in list).
I18N_LANGUAGES = [
    ('fr', _('French')),
    ('de', _('German')),
    ('it', _('Italian')),
]
# Define the default system currency in used. Each organisation can override
# this parameter using the 'default_currency' field
RERO_ILS_DEFAULT_CURRENCY = 'CHF'

# Base templates
# ==============
#: Global base template.
BASE_TEMPLATE = 'rero_ils/page.html'
#: Cover page base template (used for e.g. login/sign-up).
COVER_TEMPLATE = 'rero_ils/page_cover.html'
#: Footer base template.
FOOTER_TEMPLATE = 'rero_ils/footer.html'
#: Header base template.
HEADER_TEMPLATE = 'rero_ils/header.html'
#: Settings base template
SETTINGS_TEMPLATE = 'rero_ils/page_settings.html'
#: Admin base template
# ADMIN_BASE_TEMPLATE = BASE_TEMPLATE

# Miscellaneous variable around templates
# =======================
#: Template for security pages.
SECURITY_LOGIN_USER_TEMPLATE = 'rero_ils/login_user.html'
SECURITY_REGISTER_USER_TEMPLATE = 'rero_ils/register_user.html'
SECURITY_FORGOT_PASSWORD_TEMPLATE = 'rero_ils/forgot_password.html'
SECURITY_RESET_PASSWORD_TEMPLATE = 'rero_ils/reset_password.html'
RERO_ILS_SEARCH_TEMPLATE = 'rero_ils/search.html'

# Theme configuration
# ===================
#: Brand logo.
THEME_LOGO = 'images/logo_rero_ils.png'
#: Site name
THEME_SITENAME = _('rero-ils')
#: Use default frontpage.
THEME_FRONTPAGE = False
#: Frontpage title.
THEME_FRONTPAGE_TITLE = _('rero-ils')
#: Frontpage template.
THEME_FRONTPAGE_TEMPLATE = 'rero_ils/frontpage.html'
#: Theme base template.
THEME_BASE_TEMPLATE = BASE_TEMPLATE
#: Cover page theme template (used for e.g. login/sign-up).
THEME_COVER_TEMPLATE = COVER_TEMPLATE
#: Footer theme template.
THEME_FOOTER_TEMPLATE = FOOTER_TEMPLATE
#: Header theme template.
THEME_HEADER_TEMPLATE = HEADER_TEMPLATE
#: Settings page template used for e.g. display user settings views.
THEME_SETTINGS_TEMPLATE = SETTINGS_TEMPLATE
#: Template for error pages.
THEME_ERROR_TEMPLATE = 'rero_ils/page_error.html'
# External CSS for each organisation customization
RERO_ILS_THEME_ORGANISATION_CSS_ENDPOINT = 'https://resources.rero.ch/ils/test/css/'
#: Template for including a tracking code for web analytics.
THEME_TRACKINGCODE_TEMPLATE = 'rero_ils/trackingcode.html'
THEME_JAVASCRIPT_TEMPLATE = 'rero_ils/javascript.html'

# WEBPACKEXT_PROJECT = 'rero_ils.webpack.project'
# Logings
# =======
#: Sentry level
LOGGING_SENTRY_LEVEL = "ERROR"
#: Sentry: use celery or not
LOGGING_SENTRY_CELERY = True

# Email configuration
# ===================
#: Email address for support.
SUPPORT_EMAIL = "software@rero.ch"
#: Disable email sending by default.
MAIL_SUPPRESS_SEND = True

# Assets
# ======
#: Static files collection method (defaults to symbolic link to files).
COLLECT_STORAGE = 'flask_collect.storage.link'

# Accounts
# ========
#: Email address used as sender of account registration emails.
SECURITY_EMAIL_SENDER = SUPPORT_EMAIL
#: Email subject for account registration emails.
SECURITY_EMAIL_SUBJECT_REGISTER = _("Welcome to RERO-ILS!")
#: Email subjects for password reset
SECURITY_EMAIL_SUBJECT_PASSWORD_RESET = _('RERO ID password reset')
SECURITY_EMAIL_SUBJECT_PASSWORD_NOTICE = _('Your RERO ID password has been reset')
#: Redis session storage URL.
ACCOUNTS_SESSION_REDIS_URL = 'redis://localhost:6379/1'
#: Enable session/user id request tracing. This feature will add X-Session-ID
#: and X-User-ID headers to HTTP response. You MUST ensure that NGINX (or other
#: proxies) removes these headers again before sending the response to the
#: client. Set to False, in case of doubt.
ACCOUNTS_USERINFO_HEADERS = False
# Disable User Profiles
USERPROFILES = True
USERPROFILES_COUNTRIES = get_profile_countries
USERPROFILES_DEFAULT_COUNTRY = 'sz'
USERPROFILES_READONLY_FIELDS = get_readonly_profile_fields

# Custom login view
ACCOUNTS_REST_AUTH_VIEWS = {
    "login": "rero_ils.accounts_views:LoginView",
    "logout": "invenio_accounts.views.rest:LogoutView",
    "user_info": "invenio_accounts.views.rest:UserInfoView",
    "register": "invenio_accounts.views.rest:RegisterView",
    "forgot_password": "invenio_accounts.views.rest:ForgotPasswordView",
    "reset_password": "invenio_accounts.views.rest:ResetPasswordView",
    "change_password": "rero_ils.accounts_views:ChangePasswordView",
    "send_confirmation":
        "invenio_accounts.views.rest:SendConfirmationEmailView",
    "confirm_email": "invenio_accounts.views.rest:ConfirmEmailView",
    "sessions_list": "invenio_accounts.views.rest:SessionsListView",
    "sessions_item": "invenio_accounts.views.rest:SessionsItemView"
}

ACCOUNTS_REGISTER_BLUEPRINT = True
"""Needed to generate reset password link."""

SECURITY_LOGIN_URL = '/signin/'
"""URL endpoint for login."""

SECURITY_LOGOUT_URL = '/signout/'
"""URL endpoint for logout."""


# Celery configuration
# ====================

BROKER_URL = 'amqp://guest:guest@localhost:5672/'
#: URL of message broker for Celery (default is RabbitMQ).
CELERY_BROKER_URL = 'amqp://guest:guest@localhost:5672/'
#: URL of backend for result storage (default is Redis).
CELERY_RESULT_BACKEND = 'redis://localhost:6379/2'
#: Scheduled tasks configuration (aka cronjobs).
CELERY_BEAT_SCHEDULE = {
    'scheduler-timestamp': {
        'task': ('rero_ils.modules.tasks.scheduler_timestamp'),
        'schedule': timedelta(minutes=1),
        'enabled': False
        # Save a timestamp so we can externaly test the timestamp changed
        # every minute. If the timestamp is not changing the scheduller
        # is not working.
    },
    'bulk-indexer': {
        'task': 'rero_ils.modules.tasks.process_bulk_queue',
        'schedule': timedelta(minutes=1),
        'enabled': False
    },
    'accounts': {
        'task': 'invenio_accounts.tasks.clean_session_table',
        'schedule': timedelta(minutes=60),
        'enabled': False
    },
    'ebooks-harvester': {
        'task': 'invenio_oaiharvester.tasks.list_records_from_dates',
        'schedule': timedelta(minutes=60),
        'kwargs': {'name': 'ebooks'},
        'enabled': False
    },
    'notification-creation': {
        'task': 'rero_ils.modules.notifications.tasks.create_notifications',
        'schedule': crontab(minute="*/5"),
        'kwargs': {
            'types': [
                Notification.DUE_SOON_NOTIFICATION_TYPE,
                Notification.OVERDUE_NOTIFICATION_TYPE
            ]
        },
        'enabled': False,
        # TODO: in production set this up once a day
    },
    'claims-creation': {
        'task': ('rero_ils.modules.items.tasks'
                 '.process_late_claimed_issues'),
        'schedule': crontab(minute=0, hour=6),  # Every day at 06:00 UTC,
        'enabled': False
    },
    'clear_obsolete_temporary_item_types': {
        'task': ('rero_ils.modules.items.tasks'
                 '.clean_obsolete_temporary_item_types'),
        'schedule': crontab(minute=15, hour=2),  # Every day at 02:15 UTC,
        'enabled': False
    },
    'anonymize-loans': {
        'task': ('rero_ils.modules.loans.tasks'
                 '.loan_anonymizer'),
        'schedule': crontab(minute=0, hour=7),  # Every day at 07:00 UTC,
        'enabled': False
    },
    'clear_and_renew_subscriptions': {
        'task': ('rero_ils.modules.patrons.tasks'
                 '.task_clear_and_renew_subscriptions'),
        'schedule': crontab(minute=2, hour=2),  # Every day at 02:02 UTC,
        'enabled': False
    }
    # 'mef-harvester': {
    #     'task': 'rero_ils.modules.apiharvester.tasks.harvest_records',
    #     'schedule': timedelta(minutes=60),
    #     'kwargs': {'name': 'mef', 'enabled': False),
    # },

}
CELERY_BROKER_HEARTBEAT = 0
INDEXER_BULK_REQUEST_TIMEOUT = 60

CELERY_BEAT_SCHEDULER = 'rero_ils.schedulers.RedisScheduler'
CELERY_REDIS_SCHEDULER_URL = 'redis://localhost:6379/4'

RERO_IMPORT_CACHE = 'redis://localhost:6379/5'
RERO_IMPORT_CACHE_EXPIRE = 10

# Database
# ========
#: Database URI including user and password
SQLALCHEMY_DATABASE_URI = (
    'postgresql+psycopg2://rero-ils:rero-ils@localhost/rero-ils'
)
#: Disable Versioning due to Bad Performance
DB_VERSIONING = False
#: Disable warning
SQLALCHEMY_TRACK_MODIFICATIONS = False

# Flask configuration
# ===================
# See details on
# http://flask.pocoo.org/docs/0.12/config/#builtin-configuration-values

#: Secret key - each installation (dev, production, ...) needs a separate key.
#: It should be changed before deploying.
SECRET_KEY = 'CHANGE_ME'
#: Max upload size for form data via application/mulitpart-formdata.
MAX_CONTENT_LENGTH = 100 * 1024 * 1024  # 100 MiB
#: For dev. Set to false when testing on localhost in no debug mode
APP_ENABLE_SECURE_HEADERS = True
# TODO: review theses rules for security purposes
APP_DEFAULT_SECURE_HEADERS = {
    # disabled as https is not used by the application:
    # https is done by the haproxy
    'force_https': False,
    'force_https_permanent': False,
    'force_file_save': False,
    'frame_options': 'sameorigin',
    'frame_options_allow_from': None,
    'strict_transport_security': True,
    'strict_transport_security_preload': False,
    'strict_transport_security_max_age': 31556926,  # One year in seconds
    'strict_transport_security_include_subdomains': True,
    'content_security_policy': {
        'default-src': ['*'],
        'img-src': [
            '*',
            "'self'",
            'data:'
        ],
        'style-src': [
            '*',
            "'unsafe-inline'"
        ],
        'script-src': [
            "'self'",
            "'unsafe-eval'",
            "'unsafe-inline'",
            # '*.rero.ch',
            'https://www.googletagmanager.com',
            'https://www.google-analytics.com',
            'https://services.test.rero.ch',
            'https://services.rero.ch'
        ]
    },
    'content_security_policy_report_uri': None,
    'content_security_policy_report_only': False,
    'session_cookie_secure': True,
    'session_cookie_http_only': True,
}
#: Sets cookie with the secure flag (by default False)
SESSION_COOKIE_SECURE = False
#: Since HAProxy and Nginx route all requests no matter the host header
#: provided, the allowed hosts variable is set to localhost. In production it
#: should be set to the correct host and it is strongly recommended to only
#: route correct hosts to the application.
APP_ALLOWED_HOSTS = ['localhost', '127.0.0.1']

# TODO: Check if needed one day
# Previewers
# ==========
#: Include IIIF preview for images.
# PREVIEWER_PREFERENCE = ['iiif_image'] + BASE_PREFERENCE

# Debug
# =====
# Flask-DebugToolbar is by default enabled when the application is running in
# debug mode. More configuration options are available at
# https://flask-debugtoolbar.readthedocs.io/en/latest/#configuration

#: Switches off incept of redirects by Flask-DebugToolbar.
DEBUG_TB_INTERCEPT_REDIRECTS = False

# REST API Configuration
# ======================
RERO_ILS_APP_DISABLE_PERMISSION_CHECKS = False
"""Disable permission checks during API calls. Useful when API is test from
command line or progams like postman."""

RECORDS_REST_DEFAULT_CREATE_PERMISSION_FACTORY = librarian_permission_factory
"""Default create permission factory: reject any request."""

RECORDS_REST_DEFAULT_LIST_PERMISSION_FACTORY = librarian_permission_factory
"""Default list permission factory: allow all requests"""

RECORDS_REST_DEFAULT_READ_PERMISSION_FACTORY = librarian_permission_factory
"""Default read permission factory: check if the record exists."""

RECORDS_REST_DEFAULT_UPDATE_PERMISSION_FACTORY = \
    librarian_update_permission_factory
"""Default update permission factory: reject any request."""

RECORDS_REST_DEFAULT_DELETE_PERMISSION_FACTORY = \
    librarian_delete_permission_factory
"""Default delete permission factory: reject any request."""

REST_MIMETYPE_QUERY_ARG_NAME = 'format'
"""Name of the query argument to specify the mimetype wanted for the output."""

MAX_RESULT_WINDOW = 20000
"""max result window for ES, must be the same in json mapping files."""

RECORDS_REST_ENDPOINTS = dict(
    coll=dict(
        pid_type='coll',
        pid_minter='collection_id',
        pid_fetcher='collection_id',
        search_class='rero_ils.modules.collections.api:CollectionsSearch',
        search_index='collections',
        search_type=None,
        indexer_class='rero_ils.modules.collections.api:CollectionsIndexer',
        record_serializers={
            'application/json': (
                'rero_ils.modules.serializers:json_v1_response'
            )
        },
        search_serializers={
            'application/json': (
                'rero_ils.modules.serializers:json_v1_search'
            ),
            'application/rero+json': (
                'rero_ils.modules.collections.serializers:json_coll_search'
            )
        },
        record_loaders={
            'application/json': lambda: Collection(request.get_json()),
        },
        record_class='rero_ils.modules.collections.api:Collection',
        list_route='/collections/',
        item_route='/collections/<pid(coll, record_class='
        '"rero_ils.modules.collections.api:Collection"):pid_value>',
        default_media_type='application/json',
        max_result_window=MAX_RESULT_WINDOW,
        search_factory_imp='rero_ils.query:view_search_collection_factory',
        list_permission_factory_imp=lambda record: record_permission_factory(
            action='list', record=record, cls=CollectionPermission),
        read_permission_factory_imp=lambda record: record_permission_factory(
            action='read', record=record, cls=CollectionPermission),
        create_permission_factory_imp=lambda record: record_permission_factory(
            action='create', record=record, cls=CollectionPermission),
        update_permission_factory_imp=lambda record: record_permission_factory(
            action='update', record=record, cls=CollectionPermission),
        delete_permission_factory_imp=lambda record: record_permission_factory(
            action='delete', record=record, cls=CollectionPermission)
    ),
    doc=dict(
        pid_type='doc',
        pid_minter='document_id',
        pid_fetcher='document_id',
        search_class='rero_ils.modules.documents.api:DocumentsSearch',
        search_index='documents',
        search_type=None,
        indexer_class='rero_ils.modules.documents.api:DocumentsIndexer',
        record_serializers={
            'application/json': (
                'rero_ils.modules.serializers:json_v1_response'
            ),
            'application/rero+json': (
                'rero_ils.modules.documents.serializers:json_doc_response'
            ),
            'application/xml+dc': (
                'rero_ils.modules.documents.serializers:json_dc_response'
            ),
            'application/xml+marc': (
                'rero_ils.modules.documents.serializers:xml_marcxml_response'
            )
        },
        record_serializers_aliases={
            'json': 'application/json',
            'rero': 'application/rero+json',
            'dc': 'application/xml+dc',
            'marcxml': 'application/xml+marc'
        },
        search_serializers={
            'application/json': (
                'rero_ils.modules.serializers:json_v1_search'
            ),
            'application/rero+json': (
                'rero_ils.modules.documents.serializers:json_doc_search'
            ),
            'application/xml+dc': (
                'rero_ils.modules.documents.serializers:json_dc_search'
            ),
            'application/xml+marc': (
                'rero_ils.modules.documents.serializers:xml_marcxml_search'
            ),
            'application/xml+marc+sru': (
                'rero_ils.modules.documents.serializers:xml_marcxmlsru_search'
            )

        },
        search_serializers_aliases={
            'json': 'application/json',
            'rero': 'application/rero+json',
            'dc': 'application/xml+dc',
            'marcxml': 'application/xml+marc',
            'marcxmlsru': 'application/xml+marc+sru'
        },
        record_loaders={
            'application/marcxml+xml':
            'rero_ils.modules.documents.loaders:marcxml_loader',
            'application/json': lambda: Document(request.get_json()),
        },

        list_route='/documents/',
        record_class='rero_ils.modules.documents.api:Document',
        item_route=('/documents/<pid(doc, record_class='
                    '"rero_ils.modules.documents.api:Document"):pid_value>'),
        # suggesters=dict(
        #     title={
        #         'completion': {
        #             'field': 'title_suggest',
        #             'size': 10,
        #             'skip_duplicates': True
        #         }
        #     },
        # ),
        default_media_type='application/json',
        max_result_window=MAX_RESULT_WINDOW,
        search_factory_imp='rero_ils.query:documents_search_factory',
        list_permission_factory_imp=lambda record: record_permission_factory(
            action='list', record=record, cls=DocumentPermission),
        read_permission_factory_imp=lambda record: record_permission_factory(
            action='read', record=record, cls=DocumentPermission),
        create_permission_factory_imp=lambda record: record_permission_factory(
            action='create', record=record, cls=DocumentPermission),
        update_permission_factory_imp=lambda record: record_permission_factory(
            action='update', record=record, cls=DocumentPermission),
        delete_permission_factory_imp=lambda record: record_permission_factory(
            action='delete', record=record, cls=DocumentPermission)
    ),
    illr=dict(
        pid_type='illr',
        pid_minter='ill_request_id',
        pid_fetcher='ill_request_id',
        search_class='rero_ils.modules.ill_requests.api:ILLRequestsSearch',
        search_index='ill_requests',
        search_type=None,
        indexer_class='rero_ils.modules.ill_requests.api:ILLRequestsIndexer',
        record_serializers={
            'application/json': (
                'rero_ils.modules.serializers:json_v1_response'
            ),
            'application/rero+json': (
                'rero_ils.modules.ill_requests.serializers:json_ill_request'
            )
        },
        search_serializers_aliases={
            'json': 'application/json',
            'rero+json': 'application/rero+json',
        },
        search_serializers={
            'application/json': (
                'rero_ils.modules.serializers:json_v1_search'
            ),
            'application/rero+json': (
                'rero_ils.modules.ill_requests.serializers:'
                'json_ill_request_search'
            )
        },
        record_loaders={
            'application/json': lambda: ILLRequest(request.get_json()),
        },
        record_class='rero_ils.modules.ill_requests.api:ILLRequest',
        list_route='/ill_requests/',
        item_route='/ill_requests/<pid(illr, record_class='
        '"rero_ils.modules.ill_requests.api:ILLRequest"):pid_value>',
        default_media_type='application/json',
        max_result_window=MAX_RESULT_WINDOW,
        search_factory_imp='rero_ils.query:ill_request_search_factory',
        list_permission_factory_imp=lambda record: record_permission_factory(
            action='list', record=record, cls=ILLRequestPermission),
        read_permission_factory_imp=lambda record: record_permission_factory(
            action='read', record=record, cls=ILLRequestPermission),
        create_permission_factory_imp=lambda record: record_permission_factory(
            action='create', record=record, cls=ILLRequestPermission),
        update_permission_factory_imp=lambda record: record_permission_factory(
            action='update', record=record, cls=ILLRequestPermission),
        delete_permission_factory_imp=lambda record: record_permission_factory(
            action='delete', record=record, cls=ILLRequestPermission)
    ),
    item=dict(
        pid_type='item',
        pid_minter='item_id',
        pid_fetcher='item_id',
        search_class='rero_ils.modules.items.api:ItemsSearch',
        search_index='items',
        search_type=None,
        indexer_class='rero_ils.modules.items.api:ItemsIndexer',
        record_serializers={
            'application/json': (
                'rero_ils.modules.serializers:json_v1_response'
            ),
            'application/rero+json': (
                'rero_ils.modules.items.serializers:json_item_search'
            )
        },
        search_serializers_aliases={
            'json': 'application/json',
            'rero+json': 'application/rero+json',
            'csv': 'text/csv',
        },
        search_serializers={
            'application/json': (
                'rero_ils.modules.serializers:json_v1_search'
            ),
            'application/rero+json': (
                'rero_ils.modules.items.serializers:json_item_search'
            ),
            'text/csv': (
                'rero_ils.modules.items.serializers:csv_item_search'
            ),
        },
        list_route='/items/',
        record_loaders={
            'application/json': lambda: Item(request.get_json()),
        },
        record_class='rero_ils.modules.items.api:Item',
        item_route=('/items/<pid(item, record_class='
                    '"rero_ils.modules.items.api:Item"):pid_value>'),
        default_media_type='application/json',
        max_result_window=MAX_RESULT_WINDOW,
        search_factory_imp='rero_ils.query:items_search_factory',
        list_permission_factory_imp=lambda record: record_permission_factory(
            action='list', record=record, cls=ItemPermission),
        read_permission_factory_imp=lambda record: record_permission_factory(
            action='read', record=record, cls=ItemPermission),
        create_permission_factory_imp=lambda record: record_permission_factory(
            action='create', record=record, cls=ItemPermission),
        update_permission_factory_imp=lambda record: record_permission_factory(
            action='update', record=record, cls=ItemPermission),
        delete_permission_factory_imp=lambda record: record_permission_factory(
            action='delete', record=record, cls=ItemPermission)
    ),
    itty=dict(
        pid_type='itty',
        pid_minter='item_type_id',
        pid_fetcher='item_type_id',
        search_class='rero_ils.modules.item_types.api:ItemTypesSearch',
        search_index='item_types',
        indexer_class='rero_ils.modules.item_types.api:ItemTypesIndexer',
        search_type=None,
        record_serializers={
            'application/json': (
                'rero_ils.modules.serializers:json_v1_response'
            )
        },
        record_serializers_aliases={
            'json': 'application/json',
        },
        search_serializers={
            'application/json': (
                'rero_ils.modules.serializers:json_v1_search'
            )
        },
        list_route='/item_types/',
        record_loaders={
            'application/json': lambda: ItemType(request.get_json()),
        },
        record_class='rero_ils.modules.item_types.api:ItemType',
        item_route=('/item_types/<pid(itty, record_class='
                    '"rero_ils.modules.item_types.api:ItemType"):pid_value>'),
        default_media_type='application/json',
        max_result_window=MAX_RESULT_WINDOW,
        search_factory_imp='rero_ils.query:organisation_search_factory',
        list_permission_factory_imp=lambda record: record_permission_factory(
            action='list', record=record, cls=ItemTypePermission),
        read_permission_factory_imp=lambda record: record_permission_factory(
            action='read', record=record, cls=ItemTypePermission),
        create_permission_factory_imp=lambda record: record_permission_factory(
            action='create', record=record, cls=ItemTypePermission),
        update_permission_factory_imp=lambda record: record_permission_factory(
            action='update', record=record, cls=ItemTypePermission),
        delete_permission_factory_imp=lambda record: record_permission_factory(
            action='delete', record=record, cls=ItemTypePermission)
    ),
    hold=dict(
        pid_type='hold',
        pid_minter='holding_id',
        pid_fetcher='holding_id',
        search_class='rero_ils.modules.holdings.api:HoldingsSearch',
        search_index='holdings',
        indexer_class='rero_ils.modules.holdings.api:HoldingsIndexer',
        search_type=None,
        record_serializers={
            'application/json': (
                'rero_ils.modules.serializers:json_v1_response'
            )
        },
        record_serializers_aliases={
            'json': 'application/json',
        },
        search_serializers={
            'application/json': (
                'rero_ils.modules.serializers:json_v1_search'
            ),
            'application/rero+json': (
                'rero_ils.modules.holdings.serializers:json_holdings_search'
            )
        },
        list_route='/holdings/',
        record_loaders={
            'application/json': lambda: Holding(request.get_json()),
        },
        record_class='rero_ils.modules.holdings.api:Holding',
        item_route=('/holdings/<pid(hold, record_class='
                    '"rero_ils.modules.holdings.api:Holding"):pid_value>'),
        default_media_type='application/json',
        max_result_window=MAX_RESULT_WINDOW,
        search_factory_imp='rero_ils.query:holdings_search_factory',
        list_permission_factory_imp=lambda record: record_permission_factory(
            action='list', record=record, cls=HoldingPermission),
        read_permission_factory_imp=lambda record: record_permission_factory(
            action='read', record=record, cls=HoldingPermission),
        create_permission_factory_imp=lambda record: record_permission_factory(
            action='create', record=record, cls=HoldingPermission),
        update_permission_factory_imp=lambda record: record_permission_factory(
            action='update', record=record, cls=HoldingPermission),
        delete_permission_factory_imp=lambda record: record_permission_factory(
            action='delete', record=record, cls=HoldingPermission)
    ),
    lofi=dict(
        pid_type='lofi',
        pid_minter='local_field_id',
        pid_fetcher='local_field_id',
        search_class='rero_ils.modules.local_fields.api:LocalFieldsSearch',
        search_index='local_fields',
        search_type=None,
        indexer_class='rero_ils.modules.local_fields.api:LocalFieldsIndexer',
        record_serializers={
            'application/json': (
                'rero_ils.modules.serializers:json_v1_response'
            )
        },
        record_serializers_aliases={
            'json': 'application/json',
        },
        search_serializers={
            'application/json': (
                'rero_ils.modules.serializers:json_v1_search'
            )
        },
        record_loaders={
            'application/json': lambda: LocalField(request.get_json()),
        },
        record_class='rero_ils.modules.local_fields.api:LocalField',
        list_route='/local_fields/',
        item_route='/local_fields/<pid(lofi, record_class='
        '"rero_ils.modules.local_fields.api:LocalField"):pid_value>',
        default_media_type='application/json',
        max_result_window=MAX_RESULT_WINDOW,
        search_factory_imp='rero_ils.query:organisation_search_factory',
        list_permission_factory_imp=lambda record: record_permission_factory(
            action='list', record=record, cls=LocalFieldPermission),
        read_permission_factory_imp=lambda record: record_permission_factory(
            action='read', record=record, cls=LocalFieldPermission),
        create_permission_factory_imp=lambda record: record_permission_factory(
            action='create', record=record, cls=LocalFieldPermission),
        update_permission_factory_imp=lambda record: record_permission_factory(
            action='update', record=record, cls=LocalFieldPermission),
        delete_permission_factory_imp=lambda record: record_permission_factory(
            action='delete', record=record, cls=LocalFieldPermission)
    ),
    ptrn=dict(
        pid_type='ptrn',
        pid_minter='patron_id',
        pid_fetcher='patron_id',
        search_class='rero_ils.modules.patrons.api:PatronsSearch',
        search_index='patrons',
        indexer_class='rero_ils.modules.patrons.api:PatronsIndexer',
        search_type=None,
        record_serializers={
            'application/json': (
                'rero_ils.modules.serializers:json_v1_response'
            )
        },
        record_serializers_aliases={
            'json': 'application/json',
            'rero+json': 'application/rero+json',
        },
        search_serializers={
            'application/json': (
                'rero_ils.modules.serializers:json_v1_search'
            ),
            'application/rero+json': (
                'rero_ils.modules.patrons.serializers:json_patron_search'
            )
        },
        list_route='/patrons/',
        record_loaders={
            'application/json': lambda: Patron.load(request.get_json()),
        },
        record_class='rero_ils.modules.patrons.api:Patron',
        item_route=('/patrons/<pid(ptrn, record_class='
                    '"rero_ils.modules.patrons.api:Patron"):pid_value>'),
        default_media_type='application/json',
        max_result_window=MAX_RESULT_WINDOW,
        search_factory_imp='rero_ils.query:organisation_search_factory',
        list_permission_factory_imp=lambda record: record_permission_factory(
            action='list', record=record, cls=PatronPermission),
        read_permission_factory_imp=lambda record: record_permission_factory(
            action='read', record=record, cls=PatronPermission),
        create_permission_factory_imp=lambda record: record_permission_factory(
            action='create', record=record, cls=PatronPermission),
        update_permission_factory_imp=lambda record: record_permission_factory(
            action='update', record=record, cls=PatronPermission),
        delete_permission_factory_imp=lambda record: record_permission_factory(
            action='delete', record=record, cls=PatronPermission)
    ),
    pttr=dict(
        pid_type='pttr',
        pid_minter='patron_transaction_id',
        pid_fetcher='patron_transaction_id',
        search_class=('rero_ils.modules.patron_transactions.api:'
                      'PatronTransactionsSearch'),
        search_index='patron_transactions',
        search_type=None,
        indexer_class=('rero_ils.modules.patron_transactions.api:'
                       'PatronTransactionsIndexer'),
        record_serializers={
            'application/json': (
                'rero_ils.modules.serializers:json_v1_response'
            )
        },
        record_serializers_aliases={
            'json': 'application/json',
        },
        search_serializers={
            'application/json': (
                'rero_ils.modules.serializers:json_v1_search'
            ),
            'application/rero+json': (
                'rero_ils.modules.patron_transactions.serializers'
                ':json_patron_transactions_search'
            )
        },
        record_loaders={
            'application/json': lambda: PatronTransaction(request.get_json()),
        },
        record_class=('rero_ils.modules.patron_transactions.api:'
                      'PatronTransaction'),
        list_route='/patron_transactions/',
        item_route=('/patron_transactions/<pid(pttr, record_class='
                    '"rero_ils.modules.patron_transactions.api:'
                    'PatronTransaction"):pid_value>'),
        default_media_type='application/json',
        max_result_window=MAX_RESULT_WINDOW,
        search_factory_imp='rero_ils.query:patron_transactions_search_factory',
        list_permission_factory_imp=lambda record: record_permission_factory(
            action='list', record=record, cls=PatronTransactionPermission),
        read_permission_factory_imp=lambda record: record_permission_factory(
            action='read', record=record, cls=PatronTransactionPermission),
        create_permission_factory_imp=lambda record: record_permission_factory(
            action='create', record=record, cls=PatronTransactionPermission),
        update_permission_factory_imp=lambda record: record_permission_factory(
            action='update', record=record, cls=PatronTransactionPermission),
        delete_permission_factory_imp=lambda record: record_permission_factory(
            action='delete', record=record, cls=PatronTransactionPermission)
    ),
    ptre=dict(
        pid_type='ptre',
        pid_minter='patron_transaction_event_id',
        pid_fetcher='patron_transaction_event_id',
        search_class=('rero_ils.modules.patron_transaction_events.api:'
                      'PatronTransactionEventsSearch'),
        search_index='patron_transaction_events',
        search_type=None,
        indexer_class=('rero_ils.modules.patron_transaction_events.api:'
                       'PatronTransactionEventsIndexer'),
        record_serializers={
            'application/json': (
                'rero_ils.modules.serializers:json_v1_response'
            )
        },
        record_serializers_aliases={
            'json': 'application/json',
        },
        search_serializers={
            'application/json': (
                'rero_ils.modules.serializers:json_v1_search'
            ),
            'application/rero+json': (
                'rero_ils.modules.patron_transaction_events.serializers'
                ':json_patron_transaction_events_search'
            )
        },
        record_loaders={
            'application/json': lambda: PatronTransactionEvent(
                request.get_json()),
        },
        record_class=('rero_ils.modules.patron_transaction_events.api:'
                      'PatronTransactionEvent'),
        list_route='/patron_transaction_events/',
        item_route=('/patron_transaction_events/<pid(ptre, record_class='
                    '"rero_ils.modules.patron_transaction_events.api:'
                    'PatronTransactionEvent"):pid_value>'),
        default_media_type='application/json',
        max_result_window=MAX_RESULT_WINDOW,
        search_factory_imp='rero_ils.query:patron_transactions_search_factory',
        list_permission_factory_imp=lambda record: record_permission_factory(
            action='list',
            record=record,
            cls=PatronTransactionEventPermission
        ),
        read_permission_factory_imp=lambda record: record_permission_factory(
            action='read',
            record=record,
            cls=PatronTransactionEventPermission
        ),
        create_permission_factory_imp=lambda record: record_permission_factory(
            action='create',
            record=record,
            cls=PatronTransactionEventPermission
        ),
        update_permission_factory_imp=lambda record: record_permission_factory(
            action='update',
            record=record,
            cls=PatronTransactionEventPermission
        ),
        delete_permission_factory_imp=lambda record: record_permission_factory(
            action='delete',
            record=record,
            cls=PatronTransactionEventPermission
        )
    ),
    ptty=dict(
        pid_type='ptty',
        pid_minter='patron_type_id',
        pid_fetcher='patron_type_id',
        search_class='rero_ils.modules.patron_types.api:PatronTypesSearch',
        search_index='patron_types',
        search_type=None,
        indexer_class='rero_ils.modules.patron_types.api:PatronTypesIndexer',
        record_serializers={
            'application/json': (
                'rero_ils.modules.serializers:json_v1_response'
            )
        },
        record_serializers_aliases={
            'json': 'application/json',
        },
        search_serializers={
            'application/json': (
                'rero_ils.modules.serializers:json_v1_search'
            )
        },
        list_route='/patron_types/',
        record_loaders={
            'application/json': lambda: PatronType(request.get_json()),
        },
        record_class='rero_ils.modules.patron_types.api:PatronType',
        item_route=('/patron_types/<pid(ptty, record_class='
                    '"rero_ils.modules.patron_types.api:'
                    'PatronType"):pid_value>'),
        default_media_type='application/json',
        max_result_window=MAX_RESULT_WINDOW,
        search_factory_imp='rero_ils.query:organisation_search_factory',
        list_permission_factory_imp=lambda record: record_permission_factory(
            action='list', record=record, cls=PatronTypePermission),
        read_permission_factory_imp=lambda record: record_permission_factory(
            action='read', record=record, cls=PatronTypePermission),
        create_permission_factory_imp=lambda record: record_permission_factory(
            action='create', record=record, cls=PatronTypePermission),
        update_permission_factory_imp=lambda record: record_permission_factory(
            action='update', record=record, cls=PatronTypePermission),
        delete_permission_factory_imp=lambda record: record_permission_factory(
            action='delete', record=record, cls=PatronTypePermission)
    ),
    org=dict(
        pid_type='org',
        pid_minter='organisation_id',
        pid_fetcher='organisation_id',
        search_class='rero_ils.modules.organisations.api:OrganisationsSearch',
        search_index='organisations',
        indexer_class=('rero_ils.modules.organisations.api:'
                       'OrganisationsIndexer'),
        search_type=None,
        record_serializers={
            'application/json': (
                'rero_ils.modules.serializers:json_v1_response'
            )
        },
        record_serializers_aliases={
            'json': 'application/json',
        },
        search_serializers={
            'application/json': (
                'rero_ils.modules.serializers:json_v1_search'
            )
        },
        list_route='/organisations/',
        record_loaders={
            'application/json': lambda: Organisation(request.get_json()),
        },
        record_class='rero_ils.modules.organisations.api:Organisation',
        item_route=('/organisations/<pid(org, record_class='
                    '"rero_ils.modules.organisations.api:'
                    'Organisation"):pid_value>'),
        default_media_type='application/json',
        max_result_window=MAX_RESULT_WINDOW,
        search_factory_imp=('rero_ils.query:'
                            'organisation_organisation_search_factory'),
        list_permission_factory_imp=lambda record: record_permission_factory(
            action='list', record=record, cls=OrganisationPermission),
        read_permission_factory_imp=lambda record: record_permission_factory(
            action='read', record=record, cls=OrganisationPermission),
        create_permission_factory_imp=lambda record: record_permission_factory(
            action='create', record=record, cls=OrganisationPermission),
        update_permission_factory_imp=lambda record: record_permission_factory(
            action='update', record=record, cls=OrganisationPermission),
        delete_permission_factory_imp=lambda record: record_permission_factory(
            action='delete', record=record, cls=OrganisationPermission)
    ),
    lib=dict(
        pid_type='lib',
        pid_minter='library_id',
        pid_fetcher='library_id',
        search_class='rero_ils.modules.libraries.api:LibrariesSearch',
        search_index='libraries',
        indexer_class='rero_ils.modules.libraries.api:LibrariesIndexer',
        search_type=None,
        record_serializers={
            'application/json': (
                'rero_ils.modules.serializers:json_v1_response'
            )
        },
        record_serializers_aliases={
            'json': 'application/json',
        },
        search_serializers={
            'application/json': (
                'rero_ils.modules.serializers:json_v1_search'
            )
        },
        list_route='/libraries/',
        record_loaders={
            'application/json': lambda: Library(request.get_json()),
        },
        record_class='rero_ils.modules.libraries.api:Library',
        item_route=('/libraries/<pid(lib, record_class='
                    '"rero_ils.modules.libraries.api:Library"):pid_value>'),
        default_media_type='application/json',
        max_result_window=MAX_RESULT_WINDOW,
        search_factory_imp='rero_ils.query:organisation_search_factory',
        list_permission_factory_imp=lambda record: record_permission_factory(
            action='list', record=record, cls=LibraryPermission),
        read_permission_factory_imp=lambda record: record_permission_factory(
            action='read', record=record, cls=LibraryPermission),
        create_permission_factory_imp=lambda record: record_permission_factory(
            action='create', record=record, cls=LibraryPermission),
        update_permission_factory_imp=lambda record: record_permission_factory(
            action='update', record=record, cls=LibraryPermission),
        delete_permission_factory_imp=lambda record: record_permission_factory(
            action='delete', record=record, cls=LibraryPermission)
    ),
    loc=dict(
        pid_type='loc',
        pid_minter='location_id',
        pid_fetcher='location_id',
        search_class='rero_ils.modules.locations.api:LocationsSearch',
        search_index='locations',
        indexer_class='rero_ils.modules.locations.api:LocationsIndexer',
        search_type=None,
        record_serializers={
            'application/json': (
                'rero_ils.modules.serializers:json_v1_response'
            )
        },
        record_serializers_aliases={
            'json': 'application/json',
        },
        search_serializers={
            'application/json': (
                'rero_ils.modules.serializers:json_v1_search'
            )
        },
        list_route='/locations/',
        record_loaders={
            'application/json': lambda: Location(request.get_json()),
        },
        record_class='rero_ils.modules.locations.api:Location',
        item_route=('/locations/<pid(loc, record_class='
                    '"rero_ils.modules.locations.api:Location"):pid_value>'),
        default_media_type='application/json',
        max_result_window=MAX_RESULT_WINDOW,
        search_factory_imp='rero_ils.query:viewcode_patron_search_factory',
        list_permission_factory_imp=lambda record: record_permission_factory(
            action='list', record=record, cls=LocationPermission),
        read_permission_factory_imp=lambda record: record_permission_factory(
            action='read', record=record, cls=LocationPermission),
        create_permission_factory_imp=lambda record: record_permission_factory(
            action='create', record=record, cls=LocationPermission),
        update_permission_factory_imp=lambda record: record_permission_factory(
            action='update', record=record, cls=LocationPermission),
        delete_permission_factory_imp=lambda record: record_permission_factory(
            action='delete', record=record, cls=LocationPermission)
    ),
    cont=dict(
        pid_type='cont',
        pid_minter='contribution_id',
        pid_fetcher='contribution_id',
        search_class='rero_ils.modules.contributions.api:ContributionsSearch',
        search_index='contributions',
        indexer_class='rero_ils.modules.contributions.api:ContributionsIndexer',
        search_type=None,
        record_serializers={
            'application/json': (
                'rero_ils.modules.serializers:json_v1_response'
            )
        },
        record_serializers_aliases={
            'json': 'application/json',
        },
        search_serializers={
            'application/json': (
                'rero_ils.modules.serializers:json_v1_search'
            )
        },
        list_route='/contributions/',
        record_loaders={
            'application/json': lambda: Contribution(request.get_json()),
        },
        record_class='rero_ils.modules.contributions.api:Contribution',
        item_route=('/contributions/<pid(cont, record_class='
                    '"rero_ils.modules.contributions.api:Contribution"):'
                    'pid_value>'),
        default_media_type='application/json',
        max_result_window=MAX_RESULT_WINDOW,
        search_factory_imp='rero_ils.query:contribution_view_search_factory',
        list_permission_factory_imp=lambda record: record_permission_factory(
            action='list', record=record, cls=ContributionPermission),
        read_permission_factory_imp=lambda record: record_permission_factory(
            action='read', record=record, cls=ContributionPermission),
        create_permission_factory_imp=lambda record: record_permission_factory(
            action='create', record=record, cls=ContributionPermission),
        update_permission_factory_imp=lambda record: record_permission_factory(
            action='update', record=record, cls=ContributionPermission),
        delete_permission_factory_imp=lambda record: record_permission_factory(
            action='delete', record=record, cls=ContributionPermission)
    ),
    cipo=dict(
        pid_type='cipo',
        pid_minter='circ_policy_id',
        pid_fetcher='circ_policy_id',
        search_class='rero_ils.modules.circ_policies.api:CircPoliciesSearch',
        search_index='circ_policies',
        indexer_class='rero_ils.modules.circ_policies.api:CircPoliciesIndexer',
        search_type=None,
        record_serializers={
            'application/json': (
                'rero_ils.modules.serializers:json_v1_response'
            )
        },
        record_serializers_aliases={
            'json': 'application/json',
        },
        search_serializers={
            'application/json': (
                'rero_ils.modules.serializers:json_v1_search'
            )
        },
        record_loaders={
            'application/json': lambda: CircPolicy(request.get_json()),
        },
        list_route='/circ_policies/',
        record_class='rero_ils.modules.circ_policies.api:CircPolicy',
        item_route=('/circ_policies/<pid(cipo, record_class='
                    '"rero_ils.modules.circ_policies.api:'
                    'CircPolicy"):pid_value>'),
        default_media_type='application/json',
        max_result_window=MAX_RESULT_WINDOW,
        search_factory_imp='rero_ils.query:organisation_search_factory',
        list_permission_factory_imp=lambda record: record_permission_factory(
            action='list', record=record, cls=CirculationPolicyPermission),
        read_permission_factory_imp=lambda record: record_permission_factory(
            action='read', record=record, cls=CirculationPolicyPermission),
        create_permission_factory_imp=lambda record: record_permission_factory(
            action='create', record=record, cls=CirculationPolicyPermission),
        update_permission_factory_imp=lambda record: record_permission_factory(
            action='update', record=record, cls=CirculationPolicyPermission),
        delete_permission_factory_imp=lambda record: record_permission_factory(
            action='delete', record=record, cls=CirculationPolicyPermission)
    ),
    notif=dict(
        pid_type='notif',
        pid_minter='notification_id',
        pid_fetcher='notification_id',
        search_class='rero_ils.modules.notifications.api:NotificationsSearch',
        search_index='notifications',
        indexer_class=('rero_ils.modules.notifications.api:'
                       'NotificationsIndexer'),
        search_type=None,
        record_serializers={
            'application/json': (
                'rero_ils.modules.serializers:json_v1_response'
            )
        },
        record_serializers_aliases={
            'json': 'application/json',
        },
        search_serializers={
            'application/json': (
                'rero_ils.modules.serializers:json_v1_search'
            )
        },
        record_loaders={
            'application/json': lambda: Notification(request.get_json()),
        },
        list_route='/notifications/',
        record_class='rero_ils.modules.notifications.api:Notification',
        item_route=('/notifications/<pid(notif, record_class='
                    '"rero_ils.modules.notifications.api:'
                    'Notification"):pid_value>'),
        default_media_type='application/json',
        max_result_window=MAX_RESULT_WINDOW,
        search_factory_imp='rero_ils.query:organisation_search_factory',
        list_permission_factory_imp=lambda record: record_permission_factory(
            action='list', record=record, cls=NotificationPermission),
        read_permission_factory_imp=lambda record: record_permission_factory(
            action='read', record=record, cls=NotificationPermission),
        create_permission_factory_imp=lambda record: record_permission_factory(
            action='create', record=record, cls=NotificationPermission),
        update_permission_factory_imp=lambda record: record_permission_factory(
            action='update', record=record, cls=NotificationPermission),
        delete_permission_factory_imp=lambda record: record_permission_factory(
            action='delete', record=record, cls=NotificationPermission)
    ),
    vndr=dict(
        pid_type='vndr',
        pid_minter='vendor_id',
        pid_fetcher='vendor_id',
        search_class='rero_ils.modules.vendors.api:VendorsSearch',
        search_index='vendors',
        search_type=None,
        indexer_class='rero_ils.modules.vendors.api:VendorsIndexer',
        record_serializers={
            'application/json': (
                'rero_ils.modules.serializers:json_v1_response'
            )
        },
        record_serializers_aliases={
            'json': 'application/json',
        },
        search_serializers={
            'application/json': (
                'rero_ils.modules.serializers:json_v1_search'
            )
        },
        record_loaders={
            'application/json': lambda: Vendor(request.get_json()),
        },
        record_class='rero_ils.modules.vendors.api:Vendor',
        list_route='/vendors/',
        item_route=('/vendors/<pid(vndr, record_class='
                    '"rero_ils.modules.vendors.api:Vendor"):pid_value>'),
        default_media_type='application/json',
        max_result_window=MAX_RESULT_WINDOW,
        search_factory_imp='rero_ils.query:organisation_search_factory',
        list_permission_factory_imp=lambda record: record_permission_factory(
            action='list', record=record, cls=VendorPermission),
        read_permission_factory_imp=lambda record: record_permission_factory(
            action='read', record=record, cls=VendorPermission),
        create_permission_factory_imp=lambda record: record_permission_factory(
            action='create', record=record, cls=VendorPermission),
        update_permission_factory_imp=lambda record: record_permission_factory(
            action='update', record=record, cls=VendorPermission),
        delete_permission_factory_imp=lambda record: record_permission_factory(
            action='delete', record=record, cls=VendorPermission)
    ),
    acac=dict(
        pid_type='acac',
        pid_minter='acq_account_id',
        pid_fetcher='acq_account_id',
        search_class='rero_ils.modules.acq_accounts.api:AcqAccountsSearch',
        search_index='acq_accounts',
        search_type=None,
        indexer_class='rero_ils.modules.acq_accounts.api:AcqAccountsIndexer',
        record_serializers={
            'application/json': (
                'rero_ils.modules.serializers:json_v1_response'
            )
        },
        record_serializers_aliases={
            'json': 'application/json',
        },
        search_serializers={
            'application/json': (
                'rero_ils.modules.serializers:json_v1_search'
            ),
            'application/rero+json': (
                'rero_ils.modules.acq_accounts.serializers:'
                'json_acq_account_search'
            ),
        },
        record_loaders={
            'application/json': lambda: AcqAccount(request.get_json()),
        },
        record_class='rero_ils.modules.acq_accounts.api:AcqAccount',
        list_route='/acq_accounts/',
        item_route=('/acq_accounts/<pid(acac, record_class='
                    '"rero_ils.modules.acq_accounts.api:'
                    'AcqAccount"):pid_value>'),
        default_media_type='application/json',
        max_result_window=MAX_RESULT_WINDOW,
        search_factory_imp='rero_ils.query:acq_accounts_search_factory',
        list_permission_factory_imp=lambda record: record_permission_factory(
            action='list', record=record, cls=AcqAccountPermission),
        read_permission_factory_imp=lambda record: record_permission_factory(
            action='read', record=record, cls=AcqAccountPermission),
        create_permission_factory_imp=lambda record: record_permission_factory(
            action='create', record=record, cls=AcqAccountPermission),
        update_permission_factory_imp=lambda record: record_permission_factory(
            action='update', record=record, cls=AcqAccountPermission),
        delete_permission_factory_imp=lambda record: record_permission_factory(
            action='delete', record=record, cls=AcqAccountPermission)
    ),
    budg=dict(
        pid_type='budg',
        pid_minter='budget_id',
        pid_fetcher='budget_id',
        search_class='rero_ils.modules.budgets.api:BudgetsSearch',
        search_index='budgets',
        search_type=None,
        indexer_class='rero_ils.modules.budgets.api:BudgetsIndexer',
        record_serializers={
            'application/json': (
                'rero_ils.modules.serializers:json_v1_response'
            )
        },
        record_serializers_aliases={
            'json': 'application/json',
        },
        search_serializers={
            'application/json': (
                'rero_ils.modules.serializers:json_v1_search'
            )
        },
        record_loaders={
            'application/json': lambda: Budget(request.get_json()),
        },
        record_class='rero_ils.modules.budgets.api:Budget',
        list_route='/budgets/',
        item_route=('/budgets/<pid(budg, record_class='
                    '"rero_ils.modules.budgets.api:Budget"):pid_value>'),
        default_media_type='application/json',
        max_result_window=MAX_RESULT_WINDOW,
        search_factory_imp='rero_ils.query:organisation_search_factory',
        list_permission_factory_imp=lambda record: record_permission_factory(
            action='list', record=record, cls=BudgetPermission),
        read_permission_factory_imp=lambda record: record_permission_factory(
            action='read', record=record, cls=BudgetPermission),
        create_permission_factory_imp=lambda record: record_permission_factory(
            action='create', record=record, cls=BudgetPermission),
        update_permission_factory_imp=lambda record: record_permission_factory(
            action='update', record=record, cls=BudgetPermission),
        delete_permission_factory_imp=lambda record: record_permission_factory(
            action='delete', record=record, cls=BudgetPermission)
    ),
    acor=dict(
        pid_type='acor',
        pid_minter='acq_order_id',
        pid_fetcher='acq_order_id',
        search_class='rero_ils.modules.acq_orders.api:AcqOrdersSearch',
        search_index='acq_orders',
        search_type=None,
        indexer_class='rero_ils.modules.acq_orders.api:AcqOrdersIndexer',
        record_serializers={
            'application/json': (
                'rero_ils.modules.serializers:json_v1_response'
            )
        },
        record_serializers_aliases={
            'json': 'application/json',
        },
        search_serializers={
            'application/json': (
                'rero_ils.modules.serializers:json_v1_search'
            ),
            'application/rero+json': (
                'rero_ils.modules.acq_orders.serializers:json_acq_order_search'
            ),
        },
        record_loaders={
            'application/json': lambda: AcqOrder(request.get_json()),
        },
        record_class='rero_ils.modules.acq_orders.api:AcqOrder',
        list_route='/acq_orders/',
        item_route=('/acq_orders/<pid(acor, record_class='
                    '"rero_ils.modules.acq_orders.api:AcqOrder"):pid_value>'),
        default_media_type='application/json',
        max_result_window=MAX_RESULT_WINDOW,
        search_factory_imp='rero_ils.query:organisation_search_factory',
        list_permission_factory_imp=lambda record: record_permission_factory(
            action='list', record=record, cls=AcqOrderPermission),
        read_permission_factory_imp=lambda record: record_permission_factory(
            action='read', record=record, cls=AcqOrderPermission),
        create_permission_factory_imp=lambda record: record_permission_factory(
            action='create', record=record, cls=AcqOrderPermission),
        update_permission_factory_imp=lambda record: record_permission_factory(
            action='update', record=record, cls=AcqOrderPermission),
        delete_permission_factory_imp=lambda record: record_permission_factory(
            action='delete', record=record, cls=AcqOrderPermission)
    ),
    acol=dict(
        pid_type='acol',
        pid_minter='acq_order_line_id',
        pid_fetcher='acq_order_line_id',
        search_class=('rero_ils.modules.acq_order_lines.api:'
                      'AcqOrderLinesSearch'),
        search_index='acq_order_lines',
        search_type=None,
        indexer_class=('rero_ils.modules.acq_order_lines.api:'
                       'AcqOrderLinesIndexer'),
        record_serializers={
            'application/json': (
                'rero_ils.modules.serializers:json_v1_response'
            )
        },
        record_serializers_aliases={
            'json': 'application/json',
        },
        search_serializers={
            'application/json': (
                'rero_ils.modules.serializers:json_v1_search'
            )
        },
        record_loaders={
            'application/json': lambda: AcqOrderLine(request.get_json()),
        },
        record_class='rero_ils.modules.acq_order_lines.api:AcqOrderLine',
        list_route='/acq_order_lines/',
        item_route=('/acq_order_lines/<pid(acol, record_class='
                    '"rero_ils.modules.acq_order_lines.api:'
                    'AcqOrderLine"):pid_value>'),
        default_media_type='application/json',
        max_result_window=MAX_RESULT_WINDOW,
        search_factory_imp='rero_ils.query:organisation_search_factory',
        list_permission_factory_imp=lambda record: record_permission_factory(
            action='list', record=record, cls=AcqOrderLinePermission),
        read_permission_factory_imp=lambda record: record_permission_factory(
            action='read', record=record, cls=AcqOrderLinePermission),
        create_permission_factory_imp=lambda record: record_permission_factory(
            action='create', record=record, cls=AcqOrderLinePermission),
        update_permission_factory_imp=lambda record: record_permission_factory(
            action='update', record=record, cls=AcqOrderLinePermission),
        delete_permission_factory_imp=lambda record: record_permission_factory(
            action='delete', record=record, cls=AcqOrderLinePermission)
    ),
    acin=dict(
        pid_type='acin',
        pid_minter='acq_invoice_id',
        pid_fetcher='acq_invoice_id',
        search_class=('rero_ils.modules.acq_invoices.api:'
                      'AcquisitionInvoicesSearch'),
        search_index='acq_invoices',
        search_type=None,
        indexer_class=('rero_ils.modules.acq_invoices.api:'
                       'AcquisitionInvoicesIndexer'),
        record_serializers={
            'application/json': (
                'rero_ils.modules.serializers:json_v1_response'
            )
        },
        record_serializers_aliases={
            'json': 'application/json',
        },
        search_serializers={
            'application/json': (
                'rero_ils.modules.serializers:json_v1_search'
            ),
            'application/rero+json': (
                'rero_ils.modules.acq_invoices.serializers:'
                'json_acquisition_invoice_search'
            )
        },
        record_loaders={
            'application/json': lambda: AcquisitionInvoice(request.get_json()),
        },
        record_class='rero_ils.modules.acq_invoices.api:AcquisitionInvoice',
        list_route='/acq_invoices/',
        item_route=('/acq_invoices/<pid(acin, record_class='
                    '"rero_ils.modules.acq_invoices.api:'
                    'AcquisitionInvoice"):pid_value>'),
        default_media_type='application/json',
        max_result_window=MAX_RESULT_WINDOW,
        search_factory_imp='rero_ils.query:organisation_search_factory',
        list_permission_factory_imp=lambda record: record_permission_factory(
            action='list', record=record, cls=AcqInvoicePermission),
        read_permission_factory_imp=lambda record: record_permission_factory(
            action='read', record=record, cls=AcqInvoicePermission),
        create_permission_factory_imp=lambda record: record_permission_factory(
            action='create', record=record, cls=AcqInvoicePermission),
        update_permission_factory_imp=lambda record: record_permission_factory(
            action='update', record=record, cls=AcqInvoicePermission),
        delete_permission_factory_imp=lambda record: record_permission_factory(
            action='delete', record=record, cls=AcqInvoicePermission)
    ),
    tmpl=dict(
        pid_type='tmpl',
        pid_minter='template_id',
        pid_fetcher='template_id',
        search_class='rero_ils.modules.templates.api:TemplatesSearch',
        search_index='templates',
        indexer_class='rero_ils.modules.templates.api:TemplatesIndexer',
        search_type=None,
        record_serializers={
            'application/json': (
                'rero_ils.modules.serializers:json_v1_response'
            )
        },
        record_serializers_aliases={
            'json': 'application/json',
        },
        search_serializers={
            'application/json': (
                'rero_ils.modules.serializers:json_v1_search'
            )
        },
        record_loaders={
            'application/json': lambda: Template(request.get_json()),
        },
        list_route='/templates/',
        record_class='rero_ils.modules.templates.api:Template',
        item_route=('/templates/<pid(tmpl, record_class='
                    '"rero_ils.modules.templates.api:'
                    'Template"):pid_value>'),
        default_media_type='application/json',
        max_result_window=MAX_RESULT_WINDOW,
        search_factory_imp='rero_ils.query:templates_search_factory',
        list_permission_factory_imp=lambda record: record_permission_factory(
            action='list', record=record, cls=TemplatePermission),
        read_permission_factory_imp=lambda record: record_permission_factory(
            action='read', record=record, cls=TemplatePermission),
        create_permission_factory_imp=lambda record: record_permission_factory(
            action='create', record=record, cls=TemplatePermission),
        update_permission_factory_imp=lambda record: record_permission_factory(
            action='update', record=record, cls=TemplatePermission),
        delete_permission_factory_imp=lambda record: record_permission_factory(
            action='delete', record=record, cls=TemplatePermission)
    ),
    oplg=dict(
        pid_type='oplg',
        pid_minter='operation_log_id',
        pid_fetcher='operation_log_id',
        search_class='rero_ils.modules.operation_logs.api:OperationLogsSearch',
        search_index='operation_logs',
        search_type=None,
        indexer_class='rero_ils.modules.operation_logs.api:OperationLogsIndexer',
        record_serializers={
            'application/json': (
                'rero_ils.modules.serializers:json_v1_response'
            )
        },
        record_serializers_aliases={
            'json': 'application/json',
        },
        search_serializers={
            'application/json': (
                'rero_ils.modules.serializers:json_v1_search'
            )
        },
        record_loaders={
            'application/json': lambda: OperationLog(request.get_json()),
        },
        record_class='rero_ils.modules.operation_logs.api:OperationLog',
        list_route='/operation_logs/',
        item_route='/operation_logs/<pid(oplg, record_class='
        '"rero_ils.modules.operation_logs.api:OperationLog"):pid_value>',
        default_media_type='application/json',
        max_result_window=MAX_RESULT_WINDOW,
        list_permission_factory_imp=lambda record: record_permission_factory(
            action='list', record=record, cls=OperationLogPermission),
        read_permission_factory_imp=lambda record: record_permission_factory(
            action='read', record=record, cls=OperationLogPermission),
        create_permission_factory_imp=lambda record: record_permission_factory(
            action='create', record=record, cls=OperationLogPermission),
        update_permission_factory_imp=lambda record: record_permission_factory(
            action='update', record=record, cls=OperationLogPermission),
        delete_permission_factory_imp=lambda record: record_permission_factory(
            action='delete', record=record, cls=OperationLogPermission)
    )
)


# Default view code for all organisations view
# TODO: Should be taken into angular
RERO_ILS_SEARCH_GLOBAL_VIEW_CODE = 'global'

# Default number of results in facet
RERO_ILS_DEFAULT_AGGREGATION_SIZE = 30

# Number of aggregation by index name
RERO_ILS_AGGREGATION_SIZE = {
    'documents': 50,
    'organisations': 10,
    'collections': 20
}

DOCUMENTS_AGGREGATION_SIZE = RERO_ILS_AGGREGATION_SIZE.get(
    'documents', RERO_ILS_DEFAULT_AGGREGATION_SIZE)
RECORDS_REST_FACETS = dict(
    documents=dict(
        i18n_aggs=dict(
            author=dict(
                en=dict(
                    terms=dict(field='facet_contribution_en',
                               size=DOCUMENTS_AGGREGATION_SIZE)
                ),
                fr=dict(
                    terms=dict(field='facet_contribution_fr',
                               size=DOCUMENTS_AGGREGATION_SIZE)
                ),
                de=dict(
                    terms=dict(field='facet_contribution_de',
                               size=DOCUMENTS_AGGREGATION_SIZE)
                ),
                it=dict(
                    terms=dict(field='facet_contribution_it',
                               size=DOCUMENTS_AGGREGATION_SIZE)
                ),
            ),
        ),
        aggs=dict(
            # The organisation or library facet is defined
            # dynamically during the query (query.py)
            document_type=dict(
                terms=dict(field='type.main_type',
                           size=DOCUMENTS_AGGREGATION_SIZE),
                aggs=dict(
                    document_subtype=dict(
                        terms=dict(field='type.subtype',
                                   size=DOCUMENTS_AGGREGATION_SIZE)
                    )
                )
            ),
            language=dict(
                terms=dict(field='language.value',
                           size=DOCUMENTS_AGGREGATION_SIZE)
            ),
            organisation=dict(
                terms=dict(field='holdings.organisation.organisation_pid',
                           size=DOCUMENTS_AGGREGATION_SIZE),
                aggs=dict(
                    library=dict(
                        terms=dict(field='holdings.organisation.library_pid',
                                   size=DOCUMENTS_AGGREGATION_SIZE)
                    )
                )
            ),
            subject=dict(
                terms=dict(field='facet_subjects',
                           size=DOCUMENTS_AGGREGATION_SIZE)
            ),
            status=dict(
                terms=dict(field='holdings.items.status',
                           size=DOCUMENTS_AGGREGATION_SIZE)
            )
        ),
        filters={
            _('author'): and_i18n_term_filter('facet_contribution'),
            _('document_type'): and_term_filter('type.main_type'),
            _('document_subtype'): and_term_filter('type.subtype'),
            _('language'): and_term_filter('language.value'),
            _('organisation'): and_term_filter(
                'holdings.organisation.organisation_pid'
            ),
            _('library'): and_term_filter('holdings.organisation.library_pid'),
            _('subject'): and_term_filter('facet_subjects'),
            _('status'): and_term_filter('holdings.items.status'),
            _('new_acquisition'): acquisition_filter(),
        }
    ),
    items=dict(
        aggs=dict(
            document_type=dict(
                terms=dict(field='document.document_type.main_type',
                           size=DOCUMENTS_AGGREGATION_SIZE),
                aggs=dict(
                    document_subtype=dict(
                        terms=dict(field='document.document_type.subtype',
                                   size=DOCUMENTS_AGGREGATION_SIZE)
                    )
                )
            ),
            library=dict(
                terms=dict(
                    field='library.pid',
                    size=RERO_ILS_DEFAULT_AGGREGATION_SIZE)
            ),
            location=dict(
                terms=dict(
                    field='location.pid',
                    size=RERO_ILS_DEFAULT_AGGREGATION_SIZE)
            ),
            item_type=dict(
                terms=dict(
                    field='item_type.pid',
                    size=RERO_ILS_DEFAULT_AGGREGATION_SIZE)
            ),
            status=dict(
                terms=dict(
                    field='status',
                    size=RERO_ILS_DEFAULT_AGGREGATION_SIZE)
            ),
            issue_status=dict(
                terms=dict(
                    field='issue.status',
                    size=RERO_ILS_DEFAULT_AGGREGATION_SIZE,
                    include=[ItemIssueStatus.LATE, ItemIssueStatus.CLAIMED])
            ),
            vendor=dict(
                terms=dict(
                    field='vendor.pid',
                    size=RERO_ILS_DEFAULT_AGGREGATION_SIZE)
            )
        ),
        filters={
            _('document_type'): and_term_filter(
                'document.document_type.main_type'),
            _('document_subtype'): and_term_filter(
                'document.document_type.subtype'),
            _('library'): and_term_filter('library.pid'),
            _('location'): and_term_filter('location.pid'),
            _('item_type'): and_term_filter('item_type.pid'),
            _('status'): and_term_filter('status'),
            _('issue_status'): and_term_filter('issue.status'),
            _('vendor'): and_term_filter('vendor.pid'),
            # to allow multiple filters support, in this case to filter by
            # "late or claimed"
            'or_issue_status': terms_filter('issue.status')
        }
    ),
    patrons=dict(
        aggs=dict(
            roles=dict(
                terms=dict(
                    field='roles',
                    # This does not take into account
                    # env variable or instance config file
                    size=RERO_ILS_AGGREGATION_SIZE.get(
                        'patrons', RERO_ILS_DEFAULT_AGGREGATION_SIZE)
                )
            ),
            city=dict(
                terms=dict(
                    field='facet_city',
                    # This does not take into account
                    # env variable or instance config file
                    size=RERO_ILS_AGGREGATION_SIZE.get(
                        'facet_city', RERO_ILS_DEFAULT_AGGREGATION_SIZE)
                )
            ),
            patron_type=dict(
                terms=dict(
                    field='patron.type.pid',
                    # This does not take into account
                    # env variable or instance config file
                    size=RERO_ILS_AGGREGATION_SIZE.get(
                        'patron__type', RERO_ILS_DEFAULT_AGGREGATION_SIZE)
                )
            )
        ),
        filters={
            _('roles'): and_term_filter('roles'),
            _('city'): and_term_filter('facet_city'),
            _('patron_type'): and_term_filter('patron.type.pid')
        },
    ),
    acq_accounts=dict(
        aggs=dict(
            library=dict(
                terms=dict(
                    field='library.pid',
                    size=RERO_ILS_AGGREGATION_SIZE.get(
                        'acq_accounts', RERO_ILS_DEFAULT_AGGREGATION_SIZE)
                )
            ),
            budget=dict(
                terms=dict(
                    field='budget',
                    size=RERO_ILS_AGGREGATION_SIZE.get(
                        'budget', RERO_ILS_DEFAULT_AGGREGATION_SIZE)
                )
            )
        ),
        filters={
            _('library'): and_term_filter('library.pid'),
            _('budget'): and_term_filter('budget')
        },
    ),
    acq_invoices=dict(
        aggs=dict(
            library=dict(
                terms=dict(
                    field='library.pid',
                    size=RERO_ILS_AGGREGATION_SIZE.get(
                        'acq_invoices', RERO_ILS_DEFAULT_AGGREGATION_SIZE)
                )
            ),
            status=dict(
                terms=dict(
                    field='invoice_status',
                    size=RERO_ILS_AGGREGATION_SIZE.get(
                        'acq_invoices', RERO_ILS_DEFAULT_AGGREGATION_SIZE)
                )
            )
        ),
        filters={
            _('library'): and_term_filter('library.pid'),
            _('status'): and_term_filter('invoice_status')
        },
    ),
    acq_orders=dict(
        aggs=dict(
            library=dict(
                terms=dict(
                    field='library.pid',
                    size=RERO_ILS_AGGREGATION_SIZE.get(
                        'acq_orders', RERO_ILS_DEFAULT_AGGREGATION_SIZE)
                )
            ),
            status=dict(
                terms=dict(
                    field='order_status',
                    size=RERO_ILS_AGGREGATION_SIZE.get(
                        'acq_orders', RERO_ILS_DEFAULT_AGGREGATION_SIZE)
                )
            )
        ),
        filters={
            _('library'): and_term_filter('library.pid'),
            _('status'): and_term_filter('order_status')
        },
    ),
    contributions=dict(
        aggs=dict(
            sources=dict(
                terms=dict(
                    field='sources',
                    # This does not take into account
                    # env variable or instance config file
                    size=RERO_ILS_AGGREGATION_SIZE.get(
                        'contribution', RERO_ILS_DEFAULT_AGGREGATION_SIZE)
                )
            ),
            type=dict(
                terms=dict(
                    field='type',
                    # This does not take into account
                    # env variable or instance config file
                    size=RERO_ILS_AGGREGATION_SIZE.get(
                        'contribution', RERO_ILS_DEFAULT_AGGREGATION_SIZE)
                )
            )
        ),
        filters={
            _('sources'): and_term_filter('sources'),
            _('type'): and_term_filter('type')
        }
    ),
    templates=dict(
        aggs=dict(
            type=dict(
                terms=dict(
                    field='template_type',
                    # This does not take into account
                    # env variable or instance config file
                    size=RERO_ILS_AGGREGATION_SIZE.get(
                        'templates', RERO_ILS_DEFAULT_AGGREGATION_SIZE)
                )
            ),
            visibility=dict(
                terms=dict(
                    field='visibility',
                    # This does not take into account
                    # env variable or instance config file
                    size=RERO_ILS_AGGREGATION_SIZE.get(
                        'visibility', RERO_ILS_DEFAULT_AGGREGATION_SIZE)
                )
            )
        ),
        filters={
            _('type'): and_term_filter('template_type'),
            _('visibility'): and_term_filter('visibility')
        }
    ),
    collections=dict(
        aggs=dict(
            type=dict(
                terms=dict(
                    field='collection_type',
                    # This does not take into account
                    # env variable or instance config file
                    size=RERO_ILS_AGGREGATION_SIZE.get(
                        'collections', RERO_ILS_DEFAULT_AGGREGATION_SIZE)
                )
            ),
            library=dict(
                terms=dict(
                    field='libraries.pid',
                    # This does not take into account
                    # env variable or instance config file
                    size=RERO_ILS_AGGREGATION_SIZE.get(
                        'collections', RERO_ILS_DEFAULT_AGGREGATION_SIZE)
                )
            ),
            subject=dict(
                terms=dict(
                    field='subjects.name',
                    # This does not take into account
                    # env variable or instance config file
                    size=RERO_ILS_AGGREGATION_SIZE.get(
                        'collections', RERO_ILS_DEFAULT_AGGREGATION_SIZE)
                )
            ),
            teacher=dict(
                terms=dict(
                    field='teachers.facet',
                    # This does not take into account
                    # env variable or instance config file
                    size=RERO_ILS_AGGREGATION_SIZE.get(
                        'collections', RERO_ILS_DEFAULT_AGGREGATION_SIZE)
                )
            )
        ),
        filters={
            _('type'): and_term_filter('collection_type'),
            _('library'): and_term_filter('libraries.pid'),
            _('subject'): and_term_filter('subjects.name'),
            _('teacher'): and_term_filter('teachers.facet')
        }
    ),
    ill_requests=dict(
        aggs=dict(
            status=dict(
                terms=dict(
                    field='status',
                    size=RERO_ILS_AGGREGATION_SIZE.get(
                        'ill_requests', RERO_ILS_DEFAULT_AGGREGATION_SIZE)
                )
            ),
            loan_status=dict(
                terms=dict(
                    field='loan_status',
                    size=RERO_ILS_AGGREGATION_SIZE.get(
                        'ill_requests', RERO_ILS_DEFAULT_AGGREGATION_SIZE)
                )
            ),
            requester=dict(
                terms=dict(
                    field='patron.facet',
                    size=RERO_ILS_AGGREGATION_SIZE.get(
                        'ill_requests', RERO_ILS_DEFAULT_AGGREGATION_SIZE)
                )
            ),
            library=dict(
                terms=dict(
                    field='library.pid',
                    size=RERO_ILS_AGGREGATION_SIZE.get(
                        'ill_requests', RERO_ILS_DEFAULT_AGGREGATION_SIZE)
                )
            )
        ),
        filters={
            _('status'): and_term_filter('status'),
            _('loan_status'): and_term_filter('loan_status'),
            _('requester'): and_term_filter('patron.facet'),
            _('library'): and_term_filter('library.pid')
        }
    ),
    patron_transactions=dict(
        aggs=dict(
            total=dict(
                sum=dict(
                    field='total_amount'
                )
            )
        )
    )
)

# Elasticsearch fields boosting by index
RERO_ILS_QUERY_BOOSTING = {
    'documents': {
        'autocomplete_title': 3,
        'title._text.*': 3,
        'titlesProper.*': 3,
        'contribution.name': 2,
        'contribution.name_*': 2,
        'publicationYearText': 2,
        'freeFormedPublicationDate': 2,
        'subjects.term': 2,
        'notes.label.*': 1
    },
    'patrons': {
        'barcode': 3
    }
}

# sort options
indexes = [
    'budgets',
    'circ_policies',
    'collections',
    'contributions',
    'documents',
    'holdings',
    'items',
    'item_types',
    'ill_requests',
    'libraries',
    'local_fields',
    'loans',
    'locations',
    'notifications',
    'operation_logs',
    'organisations',
    'patrons',
    'patron_transaction_events',
    'patron_transactions',
    'patron_types',
    'templates',
    'vendors'
]

RECORDS_REST_SORT_OPTIONS = dict()
RECORDS_REST_DEFAULT_SORT = dict()
for index in indexes:
    RECORDS_REST_SORT_OPTIONS[index] = dict(
        bestmatch=dict(
            fields=['-_score'], title='Best match', default_order='asc',
            order=1
        ),
        mostrecent=dict(
            fields=['-_created'], title='Most recent', default_order='desc',
            order=2
        ),
        lastupdated=dict(
            fields=['-_updated'], title='Last updated', default_order='desc',
            order=3
        ),
        created=dict(
            fields=['_created'], title='Most recent', default_order='asc',
            order=4
        ),
    )
    RECORDS_REST_DEFAULT_SORT[index] = dict(
        query='bestmatch', noquery='mostrecent')


# ------ ACQUISITION ORDER LINES SORT
RECORDS_REST_SORT_OPTIONS['acq_order_lines'] = dict(
    pid=dict(
        fields=['_id'], title='Order line PID',
        default_order='asc'
    )
)

# ------ BUDGETS SORT
RECORDS_REST_SORT_OPTIONS['budgets']['name'] = dict(
    fields=['budget_name'], title='Budget name',
    default_order='asc'
)
RECORDS_REST_DEFAULT_SORT['budgets'] = dict(
    query='bestmatch', noquery='name')

# ------ CIRCULATION POLICIES SORT
RECORDS_REST_SORT_OPTIONS['circ_policies']['name'] = dict(
    fields=['circ_policy_name'], title='Circulation policy name',
    default_order='asc'
)
RECORDS_REST_DEFAULT_SORT['circ_policies'] = dict(
    query='bestmatch', noquery='name')

# ------ HOLDINGS SORT
RECORDS_REST_SORT_OPTIONS['holdings']['library_location'] = dict(
    fields=['library.pid', 'location.pid'],
    title='Holdings library location sort',
    default_order='asc'
)
RECORDS_REST_DEFAULT_SORT['holdings'] = dict(
    query='bestmatch', noquery='library_location')

# ------ ITEM SORT
RECORDS_REST_SORT_OPTIONS['items']['enumeration_chronology'] = dict(
    fields=['-enumerationAndChronology'], title='Enumeration and Chronology',
    default_order='desc'
)
RECORDS_REST_SORT_OPTIONS['items']['library'] = dict(
    fields=['library.pid'], title='Library',
    default_order='asc'
)
RECORDS_REST_DEFAULT_SORT['items'] = dict(
    query='bestmatch', noquery='enum_chronology')

# ------ ITEM TYPES SORT
RECORDS_REST_SORT_OPTIONS['item_types']['name'] = dict(
    fields=['item_type_name'], title='Item type name',
    default_order='asc'
)
RECORDS_REST_DEFAULT_SORT['item_types'] = dict(
    query='bestmatch', noquery='name')

# ------ LIBRARIES SORT
RECORDS_REST_SORT_OPTIONS['libraries']['name'] = dict(
    fields=['library_name'], title='Library name',
    default_order='asc'
)
RECORDS_REST_DEFAULT_SORT['libraries'] = dict(
    query='bestmatch', noquery='name')

# ------ LOANS SORT
RECORDS_REST_SORT_OPTIONS['loans']['transactiondate'] = dict(
    fields=['-transaction_date'], title='Transaction date',
    default_order='desc'
)
RECORDS_REST_SORT_OPTIONS['loans']['duedate'] = dict(
    fields=['end_date'], title='Due date',
    default_order='asc'
)
RECORDS_REST_DEFAULT_SORT['loans'] = dict(
    query='bestmatch', noquery='transactiondate')

# ------ LOCATIONS SORT
RECORDS_REST_SORT_OPTIONS['locations']['name'] = dict(
    fields=['location_name'], title='Location name',
    default_order='asc'
)
RECORDS_REST_SORT_OPTIONS['locations']['pickup_name'] = dict(
    fields=['pickup_name.keyword'], title='Pickup Location name',
    default_order='asc'
)
RECORDS_REST_DEFAULT_SORT['locations'] = dict(
    query='bestmatch', noquery='name')

# ------ PATRONS SORT
RECORDS_REST_SORT_OPTIONS['patrons']['full_name'] = dict(
    fields=['last_name_sort', 'first_name_sort'], title='Patron fullname',
    default_order='asc'
)
RECORDS_REST_DEFAULT_SORT['patrons'] = dict(
    query='bestmatch', noquery='full_name')

# ------ PATRON TYPES SORT
RECORDS_REST_SORT_OPTIONS['patron_types']['name'] = dict(
    fields=['patron_type_name'], title='Patron type name',
    default_order='asc'
)
RECORDS_REST_DEFAULT_SORT['patron_types'] = dict(
    query='bestmatch', noquery='name')

# ------ VENDORS SORT
RECORDS_REST_SORT_OPTIONS['vendors']['name'] = dict(
    fields=['vendor_name'], title='Vendor name',
    default_order='asc'
)
RECORDS_REST_DEFAULT_SORT['vendors'] = dict(
    query='bestmatch', noquery='name')

# ------ ITEMS SORT
RECORDS_REST_SORT_OPTIONS['items']['issue_expected_date'] = dict(
    fields=['issue.expected_date'], title='Issue expected date',
    default_order='asc'
)
# ------ TEMPLATES SORT
RECORDS_REST_SORT_OPTIONS['templates']['name'] = dict(
    fields=['name_sort'], title='Template name',
    default_order='asc'
)
RECORDS_REST_DEFAULT_SORT['templates'] = dict(
    query='bestmatch', noquery='name')

# ------ COLLECTIONS SORT
RECORDS_REST_SORT_OPTIONS['collections']['start_date'] = dict(
    fields=['start_date', 'title_sort'], title='Start date and title',
    default_order='asc'
)
RECORDS_REST_SORT_OPTIONS['collections']['title'] = dict(
    fields=['title_sort'], title='title',
    default_order='asc'
)

RECORDS_REST_DEFAULT_SORT['collections'] = dict(
    query='bestmatch', noquery='start_date')


# Detailed View Configuration
# ===========================
RECORDS_UI_ENDPOINTS = {
    'coll': dict(
        pid_type='coll',
        route='/<string:viewcode>/collections/<pid_value>',
        template='rero_ils/detailed_view_collections.html',
        record_class='rero_ils.modules.collections.api:Collection',
        view_imp='rero_ils.modules.collections.views.collection_view_method'
    ),
    'doc': dict(
        pid_type='doc',
        route='/<string:viewcode>/documents/<pid_value>',
        template='rero_ils/detailed_view_documents.html',
        record_class='rero_ils.modules.documents.api:Document',
        view_imp='rero_ils.modules.documents.views.doc_item_view_method',

    ),
    'doc_export': dict(
        pid_type='doc',
        route='/<string:viewcode>/documents/<pid_value>/export/<format>',
        view_imp='invenio_records_ui.views.export',
        template='rero_ils/export_documents.html',
        record_class='rero_ils.modules.documents.api:Document',
    )
}

RECORDS_UI_EXPORT_FORMATS = {
    'doc': {
        'json': dict(
            title='JSON',
            serializer='invenio_records_rest.serializers' ':json_v1',
            order=1,
        )
    }
}

RECORDS_JSON_SCHEMA = {
    'acac': '/acq_accounts/acq_account-v0.0.1.json',
    'acol': '/acq_order_lines/acq_order_line-v0.0.1.json',
    'acor': '/acq_orders/acq_order-v0.0.1.json',
    'acin': '/acq_invoices/acq_invoice-v0.0.1.json',
    'budg': '/budgets/budget-v0.0.1.json',
    'cipo': '/circ_policies/circ_policy-v0.0.1.json',
    'coll': '/collections/collection-v0.0.1.json',
    'cont': '/contributions/contribution-v0.0.1.json',
    'doc': '/documents/document-v0.0.1.json',
    'hold': '/holdings/holding-v0.0.1.json',
    'illr': '/ill_requests/ill_request-v0.0.1.json',
    'item': '/items/item-v0.0.1.json',
    'itty': '/item_types/item_type-v0.0.1.json',
    'lib': '/libraries/library-v0.0.1.json',
    'loc': '/locations/location-v0.0.1.json',
    'lofi': '/local_fields/local_field-v0.0.1.json',
    'notif': '/notifications/notification-v0.0.1.json',
    'org': '/organisations/organisation-v0.0.1.json',
    'pttr': '/patron_transactions/patron_transaction-v0.0.1.json',
    'ptty': '/patron_types/patron_type-v0.0.1.json',
    'ptre': '/patron_transaction_events/patron_transaction_event-v0.0.1.json',
    'ptrn': '/patrons/patron-v0.0.1.json',
    'tmpl': '/templates/template-v0.0.1.json',
    'oplg': '/operation_logs/operation_log-v0.0.1.json',
    'vndr': '/vendors/vendor-v0.0.1.json',
}

# Operation Log Configuration
# ===================
# Keep history of peration logs for the following resources
RERO_ILS_ENABLE_OPERATION_LOG = {
    'documents': 'doc',
    'holdings': 'hold',
    'items': 'item'
}

# Notification Configuration
# ===========================
RERO_ILS_NOTIFICATIONS_ALLOWED_TEMPATE_FILES = [
    '*.txt',
    '*.tpl.*'
]

# Login Configuration
# ===================
#: Allow password change by users.
SECURITY_CHANGEABLE = True

#: Allow user to confirm their email address.
# TODO: decide what should be the workflow of the login user
SECURITY_CONFIRMABLE = False

#: Allow password recovery by users.
SECURITY_RECOVERABLE = True

#: Allow users to register.
SECURITY_REGISTERABLE = True

#: Allow sending registration email.
SECURITY_SEND_REGISTER_EMAIL = True

#: Allow users to login without first confirming their email address.
SECURITY_LOGIN_WITHOUT_CONFIRMATION = True

#: TODO: remove this when the email is sent only if the user has an email
# address
SECURITY_SEND_PASSWORD_CHANGE_EMAIL = False

# Misc
INDEXER_REPLACE_REFS = True
INDEXER_RECORD_TO_INDEX = 'rero_ils.modules.indexer_utils.record_to_index'

RERO_ILS_APP_URL_SCHEME = 'https'
RERO_ILS_APP_HOST = 'ils.rero.ch'
#: Actual URL used to construct links in notifications for example
RERO_ILS_APP_URL = 'https://ils.rero.ch'

RERO_ILS_PERMALINK_RERO_URL = 'http://data.rero.ch/01-{identifier}'

#: Git commit hash. If set, a link to github commit page
#: is displayed on RERO-ILS frontpage.
RERO_ILS_APP_GIT_HASH = None
#: rero-ils-ui Git commit hash. If set, a link to github commit
#: page is displayed on RERO-ILS frontpage.
RERO_ILS_UI_GIT_HASH = None

#: RERO_ILS MEF specific configurations.
RERO_ILS_MEF_URL = 'https://{host}/api/mef/'.format(host='mef.rero.ch')
RERO_ILS_MEF_RESULT_SIZE = 100

RERO_ILS_APP_HELP_PAGE = (
    'https://github.com/rero/rero-ils/wiki/Public-demo-help'
)

#: Cover service
RERO_ILS_THUMBNAIL_SERVICE_URL = 'https://services.test.rero.ch/cover'

#: Contributions
RERO_ILS_CONTRIBUTIONS_MEF_SCHEMA = 'contributions/contribution-v0.0.1.json'
RERO_ILS_CONTRIBUTIONS_SOURCES = ['idref', 'gnd', 'rero']
RERO_ILS_CONTRIBUTIONS_AGENT_TYPES = {
    'bf:Person': 'persons',
    'bf:Organisation': 'corporate-bodies'
}
RERO_ILS_CONTRIBUTIONS_LABEL_ORDER = {
    'fallback': 'fr',
    'fr': ['idref', 'rero', 'gnd'],
    'de': ['gnd', 'idref', 'rero'],
}

#: Admin roles
RERO_ILS_LIBRARIAN_ROLES = ['librarian', 'system_librarian']


# JSONSchemas
# ===========
#: Hostname used in URLs for local JSONSchemas.
JSONSCHEMAS_URL_SCHEME = 'https'
JSONSCHEMAS_HOST = 'ils.rero.ch'
JSONSCHEMAS_REPLACE_REFS = True
JSONSCHEMAS_LOADER_CLS = 'rero_ils.jsonschemas.utils.JsonLoader'

# OAI-PMH
# =======
OAISERVER_ID_PREFIX = 'oai:ils.rero.ch:'

#: Invenio circulation configuration.
CIRCULATION_ITEM_EXISTS = Item.item_exists
CIRCULATION_PATRON_EXISTS = Patron.get_record_by_pid

CIRCULATION_ITEM_LOCATION_RETRIEVER = item_location_retriever
CIRCULATION_DOCUMENT_RETRIEVER_FROM_ITEM = \
    Item.get_document_pid_by_item_pid_object
CIRCULATION_ITEMS_RETRIEVER_FROM_DOCUMENT = Item.get_items_pid_by_document_pid

CIRCULATION_DOCUMENT_EXISTS = Document.get_record_by_pid

CIRCULATION_ITEM_REF_BUILDER = loan_build_item_ref
CIRCULATION_PATRON_REF_BUILDER = loan_build_patron_ref
CIRCULATION_DOCUMENT_REF_BUILDER = loan_build_document_ref

CIRCULATION_TRANSACTION_LOCATION_VALIDATOR = \
    Location.transaction_location_validator
CIRCULATION_TRANSACTION_USER_VALIDATOR = \
    Patron.transaction_user_validator

CIRCULATION_LOAN_LOCATIONS_VALIDATION = \
    validate_item_pickup_transaction_locations
"""Validates the item, pickup and transaction locations of pending loans."""

# This is needed for absolute URL (url_for)
# SERVER_NAME = 'localhost:5000'
# CIRCULATION_REST_ENDPOINTS = {}
"""Default circulation policies when performing an action on a Loan."""

_LOANID_CONVERTER = 'pid(loanid,record_class="invenio_circulation.api:Loan")'
"""Loan PID url converter."""

CIRCULATION_REST_ENDPOINTS = dict(
    loanid=dict(
        pid_type=CIRCULATION_LOAN_PID_TYPE,
        pid_minter=CIRCULATION_LOAN_MINTER,
        pid_fetcher=CIRCULATION_LOAN_FETCHER,
        search_class=LoansSearch,
        search_type=None,
        record_serializers={
            'application/json': ('invenio_records_rest.serializers'
                                 ':json_v1_response'),
        },
        record_serializers_aliases={
            'json': 'application/json',
        },
        search_serializers={
            'application/json': ('invenio_records_rest.serializers'
                                 ':json_v1_search'),
            'application/rero+json': (
                'rero_ils.modules.loans.serializers:'
                'json_loan_search'
            )
        },
        record_loaders={
            'application/json': lambda: Loan(request.get_json()),
        },
        record_class='rero_ils.modules.loans.api:Loan',
        search_factory_imp='rero_ils.query:circulation_search_factory',
        list_route='/loans/',
        item_route='/loans/<{0}:pid_value>'.format(
            _LOANID_CONVERTER),
        default_media_type='application/json',
        max_result_window=20000,
        error_handlers=dict(),
        list_permission_factory_imp=lambda record: record_permission_factory(
            action='list', record=record, cls=LoanPermission),
        read_permission_factory_imp=lambda record: record_permission_factory(
            action='read', record=record, cls=LoanPermission),
        create_permission_factory_imp=lambda record: record_permission_factory(
            action='create', record=record, cls=LoanPermission),
        update_permission_factory_imp=lambda record: record_permission_factory(
            action='update', record=record, cls=LoanPermission),
        delete_permission_factory_imp=lambda record: record_permission_factory(
            action='delete', record=record, cls=LoanPermission)
    )
)
"""Disable Circulation REST API."""

CIRCULATION_LOAN_TRANSITIONS = {
    'CREATED': [
        dict(
            dest=LoanState.PENDING,
            trigger='request',
            transition=CreatedToPending
        ),
        dict(
            dest=LoanState.ITEM_ON_LOAN,
            trigger='checkout',
            transition=ToItemOnLoan,
            assign_item=False
        ),
    ],
    'PENDING': [
        dict(
            dest=LoanState.ITEM_AT_DESK,
            transition=PendingToItemAtDesk,
            trigger='validate_request'
        ),
        dict(
            dest=LoanState.ITEM_IN_TRANSIT_FOR_PICKUP,
            transition=PendingToItemInTransitPickup,
            trigger='validate_request'
        ),
        dict(
            dest=LoanState.ITEM_ON_LOAN,
            transition=ToItemOnLoan,
            trigger='checkout'
        ),
        dict(
            dest=LoanState.CANCELLED,
            trigger='cancel',
            transition=ToCancelled
        )
    ],
    'ITEM_AT_DESK': [
        dict(
            dest=LoanState.ITEM_ON_LOAN,
            transition=ItemAtDeskToItemOnLoan,
            trigger='checkout'
        ),
        dict(
            dest=LoanState.CANCELLED,
            trigger='cancel',
            transition=ToCancelled
        )
    ],
    'ITEM_IN_TRANSIT_FOR_PICKUP': [
        dict(
            dest=LoanState.ITEM_AT_DESK,
            trigger='receive'
        ),
        dict(
            dest=LoanState.CANCELLED,
            trigger='cancel',
            transition=ToCancelled
        )
    ],
    'ITEM_ON_LOAN': [
        dict(
            dest=LoanState.ITEM_RETURNED,
            transition=ItemOnLoanToItemReturned,
            trigger='checkin',
            assign_item=False
        ),
        dict(
            dest=LoanState.ITEM_IN_TRANSIT_TO_HOUSE,
            transition=ItemOnLoanToItemInTransitHouse,
            trigger='checkin'
        ),
        dict(
            dest=LoanState.ITEM_ON_LOAN,
            transition=ItemOnLoanToItemOnLoan,
            trigger='extend'
        ),
        dict(
            dest=LoanState.CANCELLED,
            trigger='cancel',
            transition=ToCancelled
        )
    ],
    'ITEM_IN_TRANSIT_TO_HOUSE': [
        dict(
            dest=LoanState.ITEM_RETURNED,
            transition=ItemInTransitHouseToItemReturned,
            trigger='receive',
            assign_item=False
        ),
        dict(
            dest=LoanState.CANCELLED,
            trigger='cancel',
            transition=ToCancelled
        )
    ],
    'ITEM_RETURNED': [],
    'CANCELLED': [],
}


CIRCULATION_POLICIES = dict(
    checkout=dict(
        duration_default=get_default_loan_duration,
        duration_validate=validate_loan_duration,
        item_can_circulate=is_item_available_for_checkout
    ),
    extension=dict(
        from_end_date=False,
        duration_default=partial(
            get_extension_params, parameter_name='duration_default'),
        max_count=partial(
            get_extension_params, parameter_name='max_count'),
    ),
    request=dict(
        can_be_requested=can_be_requested
    )
)

CIRCULATION_ACTIONS_VALIDATION = {
    ItemCirculationAction.REQUEST: [
        Location.can_request,
        Item.can_request,
        CircPolicy.can_request,
        Patron.can_request,
        PatronType.can_request
    ],
    ItemCirculationAction.EXTEND: [
        Loan.can_extend,
        Patron.can_extend,
        PatronType.can_extend
    ],
    ItemCirculationAction.CHECKOUT: [
        Patron.can_checkout,
        CircPolicy.allow_checkout,
        PatronType.can_checkout
    ]
}

# WIKI
# ====
WIKI_CONTENT_DIR = './wiki'
WIKI_URL_PREFIX = '/help'
WIKI_LANGUAGES = ['en', 'fr', 'de', 'it']
WIKI_CURRENT_LANGUAGE = get_current_language
WIKI_UPLOAD_FOLDER = os.path.join(WIKI_CONTENT_DIR, 'files')
WIKI_BASE_TEMPLATE = 'rero_ils/page_wiki.html'
WIKI_EDIT_VIEW_PERMISSION = wiki_edit_view_permission
WIKI_EDIT_UI_PERMISSION = wiki_edit_ui_permission
WIKI_MARKDOWN_EXTENSIONS = set((
    'extra',
    'markdown_captions'
))

# IMPORT
# ====
RERO_IMPORT_REST_ENDPOINTS = dict(
    bnf=dict(
        import_class='rero_ils.modules.imports.api:BnfImport',
        import_size=50
    )
)

# SIP2
# ====
SIP2_SUPPORT_CHECKIN = True
SIP2_SUPPORT_CHECKOUT = True
SIP2_SUPPORT_RENEWAL_POLICY = True
SIP2_TIMEOUT_PERIOD = 10
SIP2_RETRIES_ALLOWED = 10
SIP2_SUPPORT_ONLINE_STATUS = True
SIP2_SUPPORT_OFFLINE_STATUS = True
SIP2_SUPPORT_STATUS_UPDATE = True
SIP2_DATE_FORMAT = '%Y%m%d    %H%M%S'

SIP2_PERMISSIONS_FACTORY = seflcheck_permission_factory

SIP2_REMOTE_ACTION_HANDLERS = dict(
    rero_ils=dict(
        login_handler='rero_ils.modules.selfcheck.api:selfcheck_login',
        logout_handler='rero_ils.modules.selfcheck.api:selfcheck_logout',
        system_status_handler='rero_ils.modules.selfcheck.api:system_status',
        patron_handlers=dict(
            validate_patron='rero_ils.modules.selfcheck.api:validate_patron_account',
            authorize_patron='rero_ils.modules.selfcheck.api:authorize_patron',
            enable_patron='rero_ils.modules.selfcheck.api:enable_patron',
            patron_status='rero_ils.modules.selfcheck.api:patron_status',
            account='rero_ils.modules.selfcheck.api:patron_information'
        ),
        item_handlers=dict(
            item='rero_ils.modules.selfcheck.api:item_information'
        ),
        circulation_handlers=dict(
            checkout='rero_ils.modules.selfcheck.api:selfcheck_checkout',
            checkin='rero_ils.modules.selfcheck.api:selfcheck_checkin',
        )
    )
)

#: see invenio_sip2.models.SelfcheckMediaType
SIP2_MEDIA_TYPES = dict(
    docmaintype_book='BOOK',
    docmaintype_article='MAGAZINE',
    docmaintype_serial='MAGAZINE',
    docmaintype_series='BOUND_JOURNAL',
    docmaintype_audio='AUDIO',
    docmaintype_movie_series='VIDEO',
)
