# -*- coding: utf-8 -*-
#
# RERO ILS
# Copyright (C) 2019 RERO
# Copyright (C) 2020 UCLOUVAIN
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

"""Query factories for REST API."""

from __future__ import absolute_import, print_function

import re

from elasticsearch_dsl.query import Q
from flask import current_app, request
from invenio_i18n.ext import current_i18n
from invenio_records_rest.errors import InvalidQueryRESTError

from .facets import i18n_facets_factory
from .modules.organisations.api import Organisation
from .modules.patrons.api import current_librarian, current_patrons
from .modules.templates.api import TemplateVisibility
from .utils import get_i18n_supported_languages

_PUNCTUATION_REGEX = re.compile(r'[:,\?,\,,\.,;,!,=,-]+(\s+|$)')


def and_term_filter(field):
    """Create a term filter.

    :param field: Field name.
    :return: Function that returns a boolean AND query between term values.
    """
    def inner(values):
        must = []
        for value in values:
            must.append(Q('term', **{field: value}))
        return Q('bool', must=must)
    return inner


def and_i18n_term_filter(field):
    """Create a i18n term filter.

    :param field: Field name.
    :return: Function that returns a boolean AND query between term values.
    """
    def inner(values):
        language = request.args.get("lang", current_i18n.language)
        if not language or language not in get_i18n_supported_languages():
            language = current_app.config.get('BABEL_DEFAULT_LANGUAGE', 'en')
        i18n_field = '{field}_{language}'.format(
            field=field,
            language=language
        )
        must = []
        for value in values:
            must.append(Q('term', **{i18n_field: value}))
        return Q('bool', must=must)
    return inner


def acquisition_filter():
    """Create a nested filter for new acquisition.

    :return: Function that returns a nested query to retrieve new acquisition
    """
    def inner(values):

        # `values` params could contains one or two values. Values must be
        # separate by a ':' character. Values are :
        #   1) from_date (optional) : the lower limit range acquisition_date.
        #        this date will be included into the search result ('<=').
        #        if not specified the '*' value will be used
        #   2) until_date (optional) : the upper limit range acquisition_date.
        #        this date will be excluded from the search result ('>').
        #        if not specified the current timestamp value will be used
        #  !!! Other filers could be used to restrict data result : This
        #      function will check for 'organisation' and/or 'library' and/or
        #      'location' url parameter to limit query result.
        #
        #   SOME EXAMPLES :
        #     * ?new_acquisition=2020-01-01&organisation=1
        #       --> all new acq for org with pid=1 from 2020-01-01 to now
        #     * ?library=3&new_acquisition=2020-01-01:2021-01-01
        #       --> all new acq for library with pid=3 for the 2020 year
        #     * ?location=17&library=2&new_acquisition=:2020-01-01
        #       --> all new acq for (location with pid=17 and library with
        #           pid=2) until Jan, 1 2020

        # build acquisition date range query
        values = dict(zip(['from', 'to'], values.pop().split(':')))
        range_acquisition_dates = {'lt': values.get('to') or 'now/d'}
        if values.get('from'):
            range_acquisition_dates['gte'] = values.get('from')

        # build general 'match' query (including acq date range query)
        must_queries = [Q(
            'range',
            holdings__items__acquisition__date=range_acquisition_dates
        )]

        # Check others filters from command line and add them to the query if
        # needed
        for level in ['location', 'library', 'organisation']:
            arg = request.args.get(level)
            if arg:
                field = 'holdings__items__acquisition__{0}_pid'.format(level)
                must_queries.append(Q('match', **{field: arg}))

        return Q(
            'nested',
            path='holdings.items.acquisition',
            query=Q(
                'bool',
                must=must_queries
            )
        )
    return inner


def documents_search_factory(self, search, query_parser=None):
    """Search factory with view code parameter."""
    view = request.args.get('view')
    search, urlkwargs = search_factory(self, search)
    # public interface
    if view:
        if view != current_app.config.get('RERO_ILS_SEARCH_GLOBAL_VIEW_CODE'):
            org = Organisation.get_record_by_viewcode(view)
            search = search.filter(
                'term', holdings__organisation__organisation_pid=org['pid']
            )
        search = search.filter('bool', must_not=[Q('term', _masked=True)])
    # exclude draft records
    search = search.filter('bool', must_not=[Q('term', _draft=True)])

    return search, urlkwargs


def viewcode_patron_search_factory(self, search, query_parser=None):
    """Search factory with viewcode or current patron."""
    search, urlkwargs = search_factory(self, search)
    view = request.args.get('view')
    # Public interface
    if view:
        if view != current_app.config.get('RERO_ILS_SEARCH_GLOBAL_VIEW_CODE'):
            org = Organisation.get_record_by_viewcode(view)
            search = search.filter('term', organisation__pid=org['pid'])
    # Admin interface
    elif current_librarian:
        search = search.filter(
            'term', organisation__pid=current_librarian.organisation_pid
        )
    # exclude draft records
    search = search.filter('bool', must_not=[Q('term', _draft=True)])
    return search, urlkwargs


def holdings_search_factory(self, search, query_parser=None):
    """Search factory for holdings records."""
    search, urlkwargs = search_factory(self, search)
    view = request.args.get('view')
    search = search_factory_for_all_interfaces(view, search)
    return search, urlkwargs


def items_search_factory(self, search, query_parser=None):
    """Search factory for item records."""
    search, urlkwargs = search_factory(self, search)
    view = request.args.get('view')
    search = search_factory_for_all_interfaces(view, search)
    return search, urlkwargs


def search_factory_for_all_interfaces(view, search):
    """Search factory for all interfaces based on logged user and view code."""
    # Logic for public interface
    if view:
        # logic for public organisational interface
        if view != current_app.config.get('RERO_ILS_SEARCH_GLOBAL_VIEW_CODE'):
            org = Organisation.get_record_by_viewcode(view)
            search = search.filter('term', organisation__pid=org['pid'])
        # masked records are hidden for all public interfaces
        search = search.filter('bool', must_not=[Q('term', _masked=True)])
    # Logic for admin interface
    elif current_librarian:
        search = search.filter(
            'term', organisation__pid=current_librarian.organisation_pid
        )
    return search


def contribution_view_search_factory(self, search, query_parser=None):
    """Search factory with view code parameter."""
    view = request.args.get(
        'view', current_app.config.get('RERO_ILS_SEARCH_GLOBAL_VIEW_CODE'))
    search, urlkwargs = search_factory(self, search)
    if view != current_app.config.get('RERO_ILS_SEARCH_GLOBAL_VIEW_CODE'):
        org = Organisation.get_record_by_viewcode(view)
        search = search.filter('term', organisations=org['pid'])
    return search, urlkwargs


def organisation_organisation_search_factory(self, search, query_parser=None):
    """Organisation Search factory."""
    search, urlkwargs = search_factory(self, search)
    if current_librarian:
        search = search.filter('term', pid=current_librarian.organisation_pid)
    return search, urlkwargs


def organisation_search_factory(self, search, query_parser=None):
    """Search factory with view code parameter.

    Exlcude masked record from public search.
    """
    # TODO: this is a temporary implemenation of the masked holdings records.
    # this functionality will be completed after merging the USs:
    # US1909: Performance: many items on public document detailed view
    # US1906: Complete item model
    if current_librarian:
        search = search.filter(
            'term', organisation__pid=current_librarian.organisation_pid
        )
    view = request.args.get(
        'view', current_app.config.get('RERO_ILS_SEARCH_GLOBAL_VIEW_CODE'))
    search, urlkwargs = search_factory(self, search)
    if view != current_app.config.get('RERO_ILS_SEARCH_GLOBAL_VIEW_CODE'):
        search = search.filter('bool', must_not=[Q('term', _masked=True)])

    return search, urlkwargs


def view_search_collection_factory(self, search, query_parser=None):
    """Search factory with view code parameter."""
    view = request.args.get(
        'view', current_app.config.get('RERO_ILS_SEARCH_GLOBAL_VIEW_CODE'))
    search, urlkwargs = search_factory(self, search)
    if view != current_app.config.get('RERO_ILS_SEARCH_GLOBAL_VIEW_CODE'):
        org = Organisation.get_record_by_viewcode(view)
        search = search.filter(
            'term', organisation__pid=org['pid']
        )
    published = request.args.get('published')
    if (published):
        search = search.filter(
            'term', published=bool(int(published))
        )

    return search, urlkwargs


def ill_request_search_factory(self, search, query_parser=None):
    """Ill request search factory.

    Restricts results to organisation level for librarian and sys_lib.
    Restricts results to its loans for users with role patron.
    Exclude to_anonymize loans from results.
    """
    search, urlkwargs = search_factory(self, search)

    if current_librarian:
        search = search.filter(
            'term', organisation__pid=current_librarian.organisation_pid
        )
    elif current_patrons:
        search = search.filter(
            'terms',
            patron__pid=[ptrn.pid for ptrn in current_patrons])
    # exclude to_anonymize records
    search = search.filter('bool', must_not=[Q('term', to_anonymize=True)])

    return search, urlkwargs


def circulation_search_factory(self, search, query_parser=None):
    """Circulation search factory.

    Restricts results to organisation level for librarian and sys_lib.
    Restricts results to its loans for users with role patron.
    Exclude to_anonymize loans from results.
    """
    search, urlkwargs = search_factory(self, search)
    # a user can be patron and librarian, it should search in his own loan and
    # the loans of his profesionnal organisation

    # initial filter for OR condition
    filters = Q('match_none')
    if current_librarian:
        filters |= Q(
            'term', organisation__pid=current_librarian.organisation_pid
        )
    if current_patrons:
        filters |= Q(
            'terms',
            patron_pid=[ptrn.pid for ptrn in current_patrons]
        )
    if filters is not Q('match_none'):
        search = search.filter('bool', must=[filters])

    # exclude to_anonymize records
    search = search.filter('bool', must_not=[Q('term', to_anonymize=True)])

    return search, urlkwargs


def templates_search_factory(self, search, query_parser=None):
    """Template search factory.

    Restricts results to organisation level for librarian and sys_lib.
    Restricts results to private templates for users with role librarian.
    """
    search, urlkwargs = search_factory(self, search)
    if current_librarian:
        if current_librarian.is_system_librarian:
            search = search.filter(
                'term', organisation__pid=current_librarian.organisation_pid)
        else:
            search = search.filter(
                'term', organisation__pid=current_librarian.organisation_pid)
            search = search.filter('bool', should=[
                Q('bool', must=[
                    Q('match', creator__pid=current_librarian.pid),
                    Q('match', visibility=TemplateVisibility.PRIVATE)]),
                Q('match', visibility=TemplateVisibility.PUBLIC)])

    return search, urlkwargs


def patron_transactions_search_factory(self, search, query_parser=None):
    """Patron transaction search factory.

    Restricts results to organisation level for librarian and sys_lib.
    Restricts results to his transactions for users with role patron.
    """
    search, urlkwargs = search_factory(self, search)
    if current_librarian:
        search = search.filter(
            'term', organisation__pid=current_librarian.organisation_pid
        )
    elif current_patrons:
        search = search.filter(
            'terms',
            patron__pid=[ptrn.pid for ptrn in current_patrons])
    return search, urlkwargs


def acq_accounts_search_factory(self, search, query_parser=None):
    """Acq accounts search factory.

    Restricts results to organisation level for sys_lib.
    Restricts results to library level for librarians.
    """
    search, urlkwargs = search_factory(self, search)

    if current_librarian:
        search = search.filter(
            'term', organisation__pid=current_librarian.organisation_pid
        )
    return search, urlkwargs


def search_factory(self, search, query_parser=None):
    """Parse query using elasticsearch DSL query.

    Terms defined by: RERO_ILS_QUERY_BOOSTING will be boosted
    at the query level.

    :param self: REST view.
    :param search: Elastic search DSL search instance.
    :param query_parser: a specific query parser
    :return: Tuple with search instance and URL arguments.
    """
    def _default_parser(qstr=None, query_boosting=[]):
        """Default parser that uses the Q() from elasticsearch_dsl."""
        query_type = 'query_string'
        default_operator = 'OR'
        if request.args.get('simple') == '1':
            query_type = 'simple_query_string'
            default_operator = 'AND'

        if qstr:
            # TODO: remove this bad hack
            qstr = _PUNCTUATION_REGEX.sub(' ', qstr)
            qstr = re.sub(r'\s+', ' ', qstr).rstrip()
            if not query_boosting:
                return Q(query_type, query=qstr,
                         default_operator=default_operator)
            else:
                return Q('bool', should=[
                    Q(query_type, query=qstr, boost=2,
                        fields=query_boosting,
                        default_operator=default_operator),
                    Q(query_type, query=qstr,
                      default_operator=default_operator)
                ])
        return Q()

    def _boosting_parser(query_boosting, search_index):
        """Elasticsearch boosting fields parser."""
        boosting = []
        if search_index in query_boosting:
            for field, boost in query_boosting[search_index].items():
                boosting.append('{}^{}'.format(field, boost))
        return boosting

    from invenio_records_rest.facets import default_facets_factory
    from invenio_records_rest.sorter import default_sorter_factory

    query_string = request.values.get('q')
    display_score = request.values.get('display_score')
    if display_score:
        search = search.extra(explain=True)
    query_parser = query_parser or _default_parser

    search_index = search._index[0]
    query_boosting = _boosting_parser(
        current_app.config['RERO_ILS_QUERY_BOOSTING'],
        search_index
    )

    try:
        search = search.query(query_parser(query_string, query_boosting))
    except SyntaxError:
        current_app.logger.debug(
            'Failed parsing query: {0}'.format(request.values.get('q', '')),
            exc_info=True,
        )
        raise InvalidQueryRESTError()

    search, urlkwargs = default_facets_factory(search, search_index)
    # i18n translated facets
    search = i18n_facets_factory(search, search_index)
    search, sortkwargs = default_sorter_factory(search, search_index)
    for key, value in sortkwargs.items():
        urlkwargs.add(key, value)
    urlkwargs.add('q', query_string)
    return search, urlkwargs
