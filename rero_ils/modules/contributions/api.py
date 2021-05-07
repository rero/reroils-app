# -*- coding: utf-8 -*-
#
# RERO ILS
# Copyright (C) 2019 RERO
# Copyright (C) 2020 UCLouvain
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

"""API for manipulating documents."""

from functools import partial

import requests
from elasticsearch_dsl import A
from flask import current_app
from invenio_db import db
from requests import codes as requests_codes

from .models import ContributionIdentifier, ContributionMetadata
from ..api import IlsRecord, IlsRecordsIndexer, IlsRecordsSearch
from ..documents.api import DocumentsSearch
from ..fetchers import id_fetcher
from ..minters import id_minter
from ..providers import Provider
from ...utils import get_i18n_supported_languages

# provider
ContributionProvider = type(
    'ContributionProvider',
    (Provider,),
    dict(identifier=ContributionIdentifier, pid_type='cont')
)
# minter
contribution_id_minter = partial(id_minter, provider=ContributionProvider)
# fetcher
contribution_id_fetcher = partial(id_fetcher, provider=ContributionProvider)


class ContributionType:
    """Class holding all availabe contribution types."""

    ORGANISATION = 'bf:Organisation'
    PERSON = 'bf:Person'


class ContributionsSearch(IlsRecordsSearch):
    """Mef contribution search."""

    class Meta():
        """Meta class."""

        index = 'contributions'
        doc_types = None
        fields = ('*', )
        facets = {}

        default_filter = None


class Contribution(IlsRecord):
    """Mef contribution class."""

    minter = contribution_id_minter
    fetcher = contribution_id_fetcher
    provider = ContributionProvider
    model_cls = ContributionMetadata

    @classmethod
    def get_contribution(cls, ref_type, ref_pid):
        """Get contribution."""
        contribution = None
        if ref_type == 'mef':
            contribution = cls.get_record_by_pid(ref_pid)
        else:
            if ref_type == 'viaf':
                result = ContributionsSearch().filter(
                    'term', viaf_pid=ref_pid
                ).source('pid').scan()
            else:
                result = ContributionsSearch().filter(
                    {'term': {f'{ref_type}.pid': ref_pid}}
                ).source('pid').scan()
            try:
                pid = next(result).pid
                contribution = cls.get_record_by_pid(pid)
            except StopIteration:
                pass
        return contribution

    @classmethod
    def get_record_by_ref(cls, ref):
        """Get a record from DB.

        If the record dos not exist get it from MEF and create it.
        """
        online = False
        ref_split = ref.split('/')
        ref_type = ref_split[-2]
        ref_pid = ref_split[-1]
        db.session.begin_nested()
        contribution = cls.get_contribution(ref_type, ref_pid)
        if not contribution:
            # We dit not find the record in DB get it from MEF and create it.
            metadata = None
            try:
                data = cls._get_mef_data_by_type(ref_pid, ref_type)
                metadata = data['metadata']
                # Register MEF contribution
                metadata.pop('$schema', None)
                # we have to commit because create
                # uses db.session.begin_nested
                contribution = cls.create(metadata, dbcommit=True,
                                          reindex=True)
                online = True
            except Exception as err:
                db.session.rollback()
                if metadata:
                    contribution = cls.get_record_by_pid(metadata.get('pid'))
                if not contribution:
                    current_app.logger.error(
                        f'Get MEF record: {ref_type}:{ref_pid} >>{err}<<'
                    )
                    # import traceback
                    # traceback.print_exc()
                return contribution, online
        db.session.commit()
        return contribution, online

    def dumps_for_document(self):
        """Transform the record into document contribution format."""
        return self._get_contribution_for_document()

    @classmethod
    def _get_mef_data_by_type(cls, pid, pid_type, verbose=False):
        """Request MEF REST API in JSON format."""
        url = current_app.config.get('RERO_ILS_MEF_URL')
        if pid_type == 'mef':
            mef_url = f'{url}?q=pid:{pid}'
        else:
            if pid_type == 'viaf':
                mef_url = f'{url}?q=viaf_pid:{pid}'
            else:
                mef_url = f'{url}?q={pid_type}.pid:{pid}'
        request = requests.get(url=mef_url, params=dict(resolve=1, sources=1))
        if request.status_code == requests_codes.ok:
            try:
                data = request.json().get('hits', {}).get('hits', [None])
                return data[0]
            except Exception as err:
                msg = f'MEF resolver no metadata: {mef_url}'
                if verbose:
                    current_app.logger.error(msg)
                raise Exception(msg)
        else:
            msg = f'Mef http error: {request.status_code} {mef_url}'
            if verbose:
                current_app.logger.error(msg)
            raise Exception(msg)

    def get_first(self, key, default=None):
        """Get the first value for given key among MEF source list."""
        value = None
        sources = current_app.config.get('RERO_ILS_CONTRIBUTIONS_SOURCES', [])
        for source in sources:
            if source in self:
                value = self[source].get(key, default)
                if value:
                    return value

    def _get_mef_localized_value(self, key, language):
        """Get the 1st localized value for given key among MEF source list."""
        order = current_app.config.get(
            'RERO_ILS_CONTRIBUTIONS_LABEL_ORDER', [])
        source_order = order.get(language, order.get(order['fallback'], []))
        for source in source_order:
            value = self.get(source, {}).get(key, None)
            if value:
                return value
        return self.get(key, None)

    def _get_contribution_for_document(self):
        """Get contribution for document."""
        agent = {
            'pid': self.pid,
        }
        for agency in current_app.config['RERO_ILS_CONTRIBUTIONS_SOURCES']:
            if self.get(agency):
                agent['type'] = self[agency]['bf:Agent']
        for language in get_i18n_supported_languages():
            value = self._get_mef_localized_value(
                'authorized_access_point', language)
            agent[f'authorized_access_point_{language}'] = value
        variant_access_points = []
        parallel_access_points = []
        for source in self.get('sources'):
            variant_access_points += self[source].get(
                'variant_access_point', [])
            parallel_access_points += self[source].get(
                'parallel_access_point', [])
        if variant_access_points:
            agent['variant_access_point'] = variant_access_points
        if parallel_access_points:
            agent['parallel_access_point'] = parallel_access_points
        return agent

    @property
    def organisation_pids(self):
        """Get organisations pids."""
        organisations = set()
        search = DocumentsSearch().filter(
            'term', contribution__agent__pid=self.pid)
        size = current_app.config.get(
            'RERO_ILS_AGGREGATION_SIZE'
        ).get('organisations')
        agg = A('terms',
                field='holdings.organisation.organisation_pid', size=size)
        search.aggs.bucket('organisation', agg)
        results = search.execute()
        for result in results.aggregations.organisation.buckets:
            if result.doc_count:
                organisations.add(result.key)
        return list(organisations)

    def get_authorized_access_point(self, language):
        """Get localized authorized_access_point.

        :param language: language for authorized access point.
        :returns: authorized access point in given lamguage.
        """
        return self._get_mef_localized_value(
            key='authorized_access_point',
            language=language
        )

    def update_online(self, dbcommit=False, reindex=False):
        """Update record online.

        :param reindex: reindex record by record
        :param dbcommit: commit record to database
        :return: updated record status and updated record
        """
        updated = False
        viaf_pid = self.get('viaf_pid')
        if viaf_pid:
            try:
                data = self._get_mef_data_by_type(viaf_pid, 'viaf')
                if data:
                    metadata = data['metadata']
                    metadata['$schema'] = self['$schema']
                    if dict(self) != metadata:
                        updated = True
                        self.replace(data=metadata, dbcommit=dbcommit,
                                     reindex=reindex)
            except Exception as err:
                pass
        return updated, self


class ContributionsIndexer(IlsRecordsIndexer):
    """Contribution indexing class."""

    record_cls = Contribution

    def bulk_index(self, record_id_iterator):
        """Bulk index records.

        :param record_id_iterator: Iterator yielding record UUIDs.
        """
        super().bulk_index(record_id_iterator, doc_type='cont')
