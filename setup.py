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

"""Invenio digital library framework."""

import os

from setuptools import find_packages, setup
from setuptools.command.egg_info import egg_info


class EggInfoWithCompile(egg_info):
    def run(self):
        from babel.messages.frontend import compile_catalog
        compiler = compile_catalog()
        option_dict = self.distribution.get_option_dict('compile_catalog')
        if option_dict.get('domain'):
            compiler.domain = [option_dict['domain'][1]]
        else:
            compiler.domain = ['messages']
        compiler.use_fuzzy = True
        compiler.directory = option_dict['directory'][1]
        compiler.run()
        super().run()


readme = open('README.rst').read()

INVENIO_VERSION = "3.1.1"

packages = find_packages()


# Get the version string. Cannot be done with import!
g = {}
with open(os.path.join('rero_ils', 'version.py'), 'rt') as fp:
    exec(fp.read(), g)
    version = g['__version__']

setup(
    cmdclass={
        'egg_info': EggInfoWithCompile
    },
    name='rero-ils',
    version=version,
    description=__doc__,
    long_description=readme,
    keywords='rero-ils Invenio',
    license='GPL',
    author='RERO',
    author_email='software@rero.ch',
    url='https://github.com/rero/rero-ils',
    packages=packages,
    zip_safe=False,
    include_package_data=True,
    platforms='any',
    entry_points={
        'console_scripts': [
            'rero-ils = invenio_app.cli:cli',
        ],
        'babel.extractors': [
            'json = rero_ils.modules.babel_extractors:extract_json'
        ],
        'invenio_admin.views': [
            'selfcheck_users_accounts = \
                rero_ils.modules.selfcheck.admin:selfcheck_terminal_adminview',
        ],
        'invenio_base.apps': [
            # 'flask_debugtoolbar = flask_debugtoolbar:DebugToolbarExtension',
            'rero-ils = rero_ils.modules.ext:REROILSAPP'
        ],
        'invenio_base.api_apps': [
            'rero-ils = rero_ils.modules.ext:REROILSAPP',
            'invenio_i18n = invenio_i18n:InvenioI18N'
        ],
        'invenio_base.blueprints': [
            'collections = rero_ils.modules.collections.views:blueprint',
            'contributions = rero_ils.modules.contributions.views:blueprint',
            'documents = rero_ils.modules.documents.views:blueprint',
            'holdings = rero_ils.modules.holdings.views:blueprint',
            'ill_requests = rero_ils.modules.ill_requests.views:blueprint',
            'notifications = rero_ils.modules.notifications.views:blueprint',
            'patrons = rero_ils.modules.patrons.views:blueprint',
            'rero_ils = rero_ils.theme.views:blueprint',
            'templates = rero_ils.modules.templates.views:blueprint',
        ],
        'invenio_base.api_blueprints': [
            'api_documents = rero_ils.modules.documents.views:api_blueprint',
            'circ_policies = rero_ils.modules.circ_policies.views:blueprint',
            'contributions = rero_ils.modules.contributions.views:api_blueprint',
            'holdings = rero_ils.modules.holdings.api_views:api_blueprint',
            'item_types = rero_ils.modules.item_types.views:blueprint',
            'items = rero_ils.modules.items.views:api_blueprint',
            'libraries = rero_ils.modules.libraries.api_views:api_blueprint',
            'loans = rero_ils.modules.loans.api_views:api_blueprint',
            'monitoring = rero_ils.modules.monitoring:api_blueprint',
            'notifications = rero_ils.modules.notifications.views:blueprint',
            'patron_types = rero_ils.modules.patron_types.views:blueprint',
            'patrons = rero_ils.modules.patrons.views:api_blueprint',
            'rero_ils = rero_ils.modules.views:api_blueprint',
        ],
        'invenio_config.module': [
            'rero_ils = rero_ils.config',
        ],
        'invenio_i18n.translations': [
            'messages = rero_ils',
            'messages_wiki = flask_wiki',
        ],
        'invenio_assets.webpack': [
            'reroils_theme = rero_ils.theme.webpack:theme'
        ],
        'dojson.cli': [
            'reverse = rero_ils.dojson.cli:reverse',
            'head = rero_ils.dojson.cli:head',
        ],
        'dojson.cli.dump': [
            'pjson = rero_ils.dojson.cli:pretty_json_dump'
        ],
        'dojson.cli.rule': [
            'marc21tojson = rero_ils.modules.documents.dojson'
            '.contrib.marc21tojson:marc21tojson',
            'marc21toebooks = \
                rero_ils.modules.ebooks.dojson.contrib.marc21:marc21',
            'unimarctojson = '
            'rero_ils.modules.documents.dojson'
            '.contrib.unimarctojson:unimarc',
        ],
        'flask.commands': [
            'apiharvester = rero_ils.modules.apiharvester.cli:apiharvester',
            'fixtures = rero_ils.modules.cli:fixtures',
            'monitoring = rero_ils.modules.monitoring:monitoring',
            'notifications = rero_ils.modules.notifications.cli:notifications',
            'oaiharvester = rero_ils.modules.ebooks.cli:oaiharvester',
            'scheduler = rero_ils.schedulers:scheduler',
            'utils = rero_ils.modules.cli:utils',
        ],
        'invenio_db.models': [
            'acq_accounts = rero_ils.modules.acq_accounts.models',
            'acq_invoices = rero_ils.modules.acq_invoices.models',
            'acq_order_lines = rero_ils.modules.acq_order_lines.models',
            'acq_orders = rero_ils.modules.acq_orders.models',
            'apiharvester = rero_ils.modules.apiharvester.models',
            'budgets = rero_ils.modules.budgets.models',
            'circ_policies = rero_ils.modules.circ_policies.models',
            'collections = rero_ils.modules.collections.models',
            'documents = rero_ils.modules.documents.models',
            'holdings = rero_ils.modules.holdings.models',
            'ill_requests = rero_ils.modules.ill_requests.models',
            'item_types = rero_ils.modules.item_types.models',
            'items = rero_ils.modules.items.models',
            'libraries = rero_ils.modules.libraries.models',
            'local_fields = rero_ils.modules.local_fields.models',
            'locations = rero_ils.modules.locations.models',
            'mef = rero_ils.modules.contributions.models',
            'notifications = rero_ils.modules.notifications.models',
            'organisations = rero_ils.modules.organisations.models',
            'patron_transaction_events = rero_ils.modules.patron_transaction_events.models',
            'patron_transactions = rero_ils.modules.patron_transactions.models',
            'patron_types = rero_ils.modules.patron_types.models',
            'patrons = rero_ils.modules.patrons.models',
            'templates = rero_ils.modules.templates.models',
            'vendors = rero_ils.modules.vendors.models',
            'operation_logs = rero_ils.modules.operation_logs.models',
            'selfcheck = rero_ils.modules.selfcheck.models',
        ],
        'invenio_pidstore.minters': [
            'acq_account_id = rero_ils.modules.acq_accounts.api:acq_account_id_minter',
            'acq_invoice_id = rero_ils.modules.acq_invoices.api:acq_invoice_id_minter',
            'acq_order_id = rero_ils.modules.acq_orders.api:acq_order_id_minter',
            'acq_order_line_id = rero_ils.modules.acq_order_lines.api:acq_order_line_id_minter',
            'budget_id = rero_ils.modules.budgets.api:budget_id_minter',
            'circ_policy_id = rero_ils.modules.circ_policies.api:circ_policy_id_minter',
            'collection_id = rero_ils.modules.collections.api:collection_id_minter',
            'contribution_id = rero_ils.modules.contributions.api:contribution_id_minter',
            'document_id = rero_ils.modules.documents.api:document_id_minter',
            'holding_id = rero_ils.modules.holdings.api:holding_id_minter',
            'ill_request_id = rero_ils.modules.ill_requests.api:ill_request_id_minter',
            'item_id = rero_ils.modules.items.api:item_id_minter',
            'item_type_id = rero_ils.modules.item_types.api:item_type_id_minter',
            'library_id = rero_ils.modules.libraries.api:library_id_minter',
            'local_field_id = rero_ils.modules.local_fields.api:local_field_id_minter',
            'location_id = rero_ils.modules.locations.api:location_id_minter',
            'notification_id = rero_ils.modules.notifications.api:notification_id_minter',
            'organisation_id = rero_ils.modules.organisations.api:organisation_id_minter',
            'patron_id = rero_ils.modules.patrons.api:patron_id_minter',
            'patron_transaction_event_id = rero_ils.modules.patron_transaction_events.api:patron_transaction_event_id_minter',
            'patron_transaction_id = rero_ils.modules.patron_transactions.api:patron_transaction_id_minter',
            'patron_type_id = rero_ils.modules.patron_types.api:patron_type_id_minter',
            'template_id = rero_ils.modules.templates.api:template_id_minter',
            'vendor_id = rero_ils.modules.vendors.api:vendor_id_minter',
            'operation_log_id = rero_ils.modules.operation_logs.api:operation_log_id_minter',
        ],
        'invenio_pidstore.fetchers': [
            'acq_account_id = rero_ils.modules.acq_accounts.api:acq_account_id_fetcher',
            'acq_invoice_id = rero_ils.modules.acq_invoices.api:acq_invoice_id_fetcher',
            'acq_order_id = rero_ils.modules.acq_orders.api:acq_order_id_fetcher',
            'acq_order_line_id = rero_ils.modules.acq_order_lines.api:acq_order_line_id_fetcher',
            'budget_id = rero_ils.modules.budgets.api:budget_id_fetcher',
            'circ_policy_id = rero_ils.modules.circ_policies.api:circ_policy_id_fetcher',
            'collection_id = rero_ils.modules.collections.api:collection_id_fetcher',
            'document_id = rero_ils.modules.documents.api:document_id_fetcher',
            'contribution_id = rero_ils.modules.contributions.api:contribution_id_fetcher',
            'holding_id = rero_ils.modules.holdings.api:holding_id_fetcher',
            'ill_request_id = rero_ils.modules.ill_requests.api:ill_request_id_fetcher',
            'item_id = rero_ils.modules.items.api:item_id_fetcher',
            'item_type_id = rero_ils.modules.item_types.api:item_type_id_fetcher',
            'library_id = rero_ils.modules.libraries.api:library_id_fetcher',
            'local_field_id = rero_ils.modules.local_fields.api:local_field_id_fetcher',
            'location_id = rero_ils.modules.locations.api:location_id_fetcher',
            'notification_id = rero_ils.modules.notifications.api:notification_id_fetcher',
            'organisation_id = rero_ils.modules.organisations.api:organisation_id_fetcher',
            'patron_id = rero_ils.modules.patrons.api:patron_id_fetcher',
            'patron_transaction_event_id = rero_ils.modules.patron_transaction_events.api:patron_transaction_event_id_fetcher',
            'patron_transaction_id = rero_ils.modules.patron_transactions.api:patron_transaction_id_fetcher',
            'patron_type_id = rero_ils.modules.patron_types.api:patron_type_id_fetcher',
            'template_id = rero_ils.modules.templates.api:template_id_minter',
            'vendor_id = rero_ils.modules.vendors.api:vendor_id_fetcher',
            'operation_log_id = rero_ils.modules.operation_logs.api:operation_log_id_fetcher',
        ],
        'invenio_jsonschemas.schemas': [
            'acq_accounts = rero_ils.modules.acq_accounts.jsonschemas',
            'acq_invoices = rero_ils.modules.acq_invoices.jsonschemas',
            'acq_order_lines = rero_ils.modules.acq_order_lines.jsonschemas',
            'acq_orders = rero_ils.modules.acq_orders.jsonschemas',
            'budgets = rero_ils.modules.budgets.jsonschemas',
            'circ_policies = rero_ils.modules.circ_policies.jsonschemas',
            'collections = rero_ils.modules.collections.jsonschemas',
            'common = rero_ils.jsonschemas',
            'contributions = rero_ils.modules.contributions.jsonschemas',
            'documents = rero_ils.modules.documents.jsonschemas',
            'holdings = rero_ils.modules.holdings.jsonschemas',
            'ill_requests = rero_ils.modules.ill_requests.jsonschemas',
            'item_types = rero_ils.modules.item_types.jsonschemas',
            'items = rero_ils.modules.items.jsonschemas',
            'libraries = rero_ils.modules.libraries.jsonschemas',
            'loans = rero_ils.modules.loans.jsonschemas',
            'local_fields = rero_ils.modules.local_fields.jsonschemas',
            'locations = rero_ils.modules.locations.jsonschemas',
            'notifications = rero_ils.modules.notifications.jsonschemas',
            'organisations = rero_ils.modules.organisations.jsonschemas',
            'patron_transaction_events = rero_ils.modules.patron_transaction_events.jsonschemas',
            'patron_transactions = rero_ils.modules.patron_transactions.jsonschemas',
            'patron_types = rero_ils.modules.patron_types.jsonschemas',
            'patrons = rero_ils.modules.patrons.jsonschemas',
            'templates = rero_ils.modules.templates.jsonschemas',
            'vendors = rero_ils.modules.vendors.jsonschemas',
            'operation_logs = rero_ils.modules.operation_logs.jsonschemas',
            'users = rero_ils.modules.users.jsonschemas',
        ],
        'invenio_search.mappings': [
            'acq_accounts = rero_ils.modules.acq_accounts.mappings',
            'acq_invoices = rero_ils.modules.acq_invoices.mappings',
            'acq_order_lines = rero_ils.modules.acq_order_lines.mappings',
            'acq_orders = rero_ils.modules.acq_orders.mappings',
            'budgets = rero_ils.modules.budgets.mappings',
            'circ_policies = rero_ils.modules.circ_policies.mappings',
            'collections = rero_ils.modules.collections.mappings',
            'contributions = rero_ils.modules.contributions.mappings',
            'documents = rero_ils.modules.documents.mappings',
            'holdings = rero_ils.modules.holdings.mappings',
            'ill_requests = rero_ils.modules.ill_requests.mappings',
            'item_types = rero_ils.modules.item_types.mappings',
            'items = rero_ils.modules.items.mappings',
            'libraries = rero_ils.modules.libraries.mappings',
            'loans = rero_ils.modules.loans.mappings',
            'local_fields = rero_ils.modules.local_fields.mappings',
            'locations = rero_ils.modules.locations.mappings',
            'notifications = rero_ils.modules.notifications.mappings',
            'organisations = rero_ils.modules.organisations.mappings',
            'patron_transaction_events = rero_ils.modules.patron_transaction_events.mappings',
            'patron_transactions = rero_ils.modules.patron_transactions.mappings',
            'patron_types = rero_ils.modules.patron_types.mappings',
            'patrons = rero_ils.modules.patrons.mappings',
            'templates = rero_ils.modules.templates.mappings',
            'vendors = rero_ils.modules.vendors.mappings',
            'operation_logs = rero_ils.modules.operation_logs.mappings',
        ],
        'invenio_search.templates': [
            'base-record = rero_ils.es_templates:list_es_templates',
        ],
        'invenio_celery.tasks': [
            'apiharvester = rero_ils.modules.apiharvester.tasks',
            'ebooks = rero_ils.modules.ebooks.tasks',
            'modules = rero_ils.modules.tasks',
            'notifications = rero_ils.modules.notifications.tasks',
            'patrons = rero_ils.modules.patrons.tasks',
            'rero_ils_collections = rero_ils.modules.collections.tasks',
            'claims = rero_ils.modules.items.tasks',
            'loans = rero_ils.modules.loans.tasks',
        ],
        'invenio_records.jsonresolver': [
            'acq_accounts = rero_ils.modules.acq_accounts.jsonresolver',
            'acq_invoices = rero_ils.modules.acq_invoices.jsonresolver',
            'acq_order_lines = rero_ils.modules.acq_order_lines.jsonresolver',
            'acq_orders = rero_ils.modules.acq_orders.jsonresolver',
            'budgets = rero_ils.modules.budgets.jsonresolver',
            'collections = rero_ils.modules.collections.jsonresolver',
            'contributions = rero_ils.modules.contributions.jsonresolver',
            'documents = rero_ils.modules.documents.jsonresolver',
            'holdings = rero_ils.modules.holdings.jsonresolver',
            'ill_requests = rero_ils.modules.ill_requests.jsonresolver',
            'item_types = rero_ils.modules.item_types.jsonresolver',
            'items = rero_ils.modules.items.jsonresolver',
            'libraries = rero_ils.modules.libraries.jsonresolver',
            'loans = rero_ils.modules.loans.jsonresolver',
            'local_fields = rero_ils.modules.local_fields.jsonresolver',
            'locations = rero_ils.modules.locations.jsonresolver',
            'notifications = rero_ils.modules.notifications.jsonresolver',
            'organisations = rero_ils.modules.organisations.jsonresolver',
            'patron_transaction_events = rero_ils.modules.patron_transaction_events.jsonresolver',
            'patron_transactions = rero_ils.modules.patron_transactions.jsonresolver',
            'patron_types = rero_ils.modules.patron_types.jsonresolver',
            'patrons = rero_ils.modules.patrons.jsonresolver',
            'templates = rero_ils.modules.templates.jsonresolver',
            'vendors = rero_ils.modules.vendors.jsonresolver',
            'operation_logs = rero_ils.modules.operation_logs.jsonresolver',
        ]
    },
    classifiers=[
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GPL License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Development Status :: 3 - Alpha',
    ],
)
