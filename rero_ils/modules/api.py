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

"""API for manipulating records."""

from copy import deepcopy
from uuid import uuid4

import click
import pytz
from celery import current_app as current_celery_app
from elasticsearch import VERSION as ES_VERSION
from elasticsearch.exceptions import NotFoundError
from elasticsearch.helpers import bulk
from elasticsearch.helpers import expand_action as default_expand_action
from flask import current_app
from invenio_db import db
from invenio_indexer import current_record_to_index
from invenio_indexer.api import RecordIndexer
from invenio_indexer.signals import before_record_index
from invenio_indexer.utils import _es7_expand_action
from invenio_pidstore.errors import PIDDoesNotExistError
from invenio_pidstore.models import PersistentIdentifier, PIDStatus
from invenio_records.api import Record
from invenio_records_rest.utils import obj_or_import_string
from invenio_search import current_search
from invenio_search.api import RecordsSearch
from jsonschema.exceptions import ValidationError
from kombu.compat import Consumer
from sqlalchemy import text
from sqlalchemy.orm.exc import NoResultFound

from .utils import extracted_data_from_ref


class IlsRecordError:
    """Base class for errors in the IlsRecordClass."""

    class Deleted(Exception):
        """IlsRecord is deleted."""

    class NotDeleted(Exception):
        """IlsRecord is not deleted."""

    class PidMissing(Exception):
        """IlsRecord pid missing."""

    class PidChange(Exception):
        """IlsRecord pid change."""

    class PidAlreadyUsed(Exception):
        """IlsRecord pid already used."""

    class PidDoesNotExist(Exception):
        """Pid does not exist."""

    class DataMissing(Exception):
        """Data missing in record."""


class IlsRecordsSearch(RecordsSearch):
    """Search Class for ils."""

    class Meta:
        """Search only on item index."""

        index = 'records'
        doc_types = None
        fields = ('*', )
        facets = {}

        default_filter = None

    @classmethod
    def flush(cls):
        """Flush index."""
        current_search.flush_and_refresh(cls.Meta.index)


class IlsRecord(Record):
    """ILS Record class."""

    minter = None
    fetcher = None
    provider = None
    object_type = 'rec'
    pids_exist_check = None
    pid_check = True

    @classmethod
    def get_indexer_class(cls):
        """Get the indexer from config."""
        try:
            indexer = obj_or_import_string(
                current_app.config['RECORDS_REST_ENDPOINTS'][
                    cls.provider.pid_type
                ]['indexer_class']
            )
        except Exception:
            # provide default indexer if no indexer is defined in config.
            indexer = IlsRecordsIndexer
        return indexer

    def _validate(self, **kwargs):
        """Validate record against schema.

        extended validation per record class
        and test of pid existence.
        """
        if self.get('_draft'):
            # No validation is needed for draft records
            return self
        json = super()._validate(**kwargs)
        validation_message = self.extended_validation(**kwargs)
        # We only like to run pids_exist_check if validation_message is True
        # and not a string with error from extended_validation
        if validation_message is True and self.pid_check and \
                self.pids_exist_check:
            from .utils import pids_exists_in_data
            validation_message = pids_exists_in_data(
                info=f'{self.provider.pid_type} ({self.pid})',
                data=self,
                required=self.pids_exist_check.get('required', {}),
                not_required=self.pids_exist_check.get('not_required', {})
            ) or True
        if validation_message is not True:
            raise ValidationError(validation_message)
        return json

    def extended_validation(self, **kwargs):
        """Returns reasons for validation failures, otherwise True.

        Override this function for classes that require extended validations
        """
        return True

    @classmethod
    def create(cls, data, id_=None, delete_pid=False,
               dbcommit=False, reindex=False, pidcheck=True, **kwargs):
        """Create a new ils record."""
        assert cls.minter
        assert cls.provider
        if '$schema' not in data:
            type = cls.provider.pid_type
            schemas = current_app.config.get('RECORDS_JSON_SCHEMA')
            if type in schemas:
                from .utils import get_schema_for_resource
                data['$schema'] = get_schema_for_resource(type)
        pid = data.get('pid')
        if delete_pid and pid:
            del data['pid']
        else:
            if pid:
                test_rec = cls.get_record_by_pid(pid)
                if test_rec is not None:
                    raise IlsRecordError.PidAlreadyUsed(
                        'PidAlreadyUsed {pid_type} {pid} {uuid}'.format(
                            pid_type=cls.provider.pid_type,
                            pid=test_rec.pid,
                            uuid=test_rec.id
                        )
                    )
        if not id_:
            id_ = uuid4()
        cls.minter(id_, data)
        cls.pid_check = pidcheck
        record = super().create(data=data, id_=id_, **kwargs)
        if dbcommit:
            record.dbcommit(reindex)
        return record

    @classmethod
    def get_record_by_pid(cls, pid, with_deleted=False, verbose=False):
        """Get ils record by pid value."""
        if verbose:
            click.echo(f'\t\tget_record_by_pid: {cls.__name__} {pid}')
        if pid:
            assert cls.provider
            try:
                persistent_identifier = PersistentIdentifier.get(
                    cls.provider.pid_type,
                    pid
                )
                record = super().get_record(
                    persistent_identifier.object_uuid,
                    with_deleted=with_deleted
                )
                return record
            # TODO: is it better to raise a error or to return None?
            except (NoResultFound, PIDDoesNotExistError):
                return None

    @classmethod
    def record_pid_exists(cls, pid):
        """Check if a persistent identifier exists.

        :param pid: The PID value.
        :returns: `True` if the PID exists.
        """
        assert cls.provider
        try:
            PersistentIdentifier.get(
                cls.provider.pid_type,
                pid
            )
            return True

        except (NoResultFound, PIDDoesNotExistError):
            return False

    @classmethod
    def get_pid_by_id(cls, id):
        """Get pid by uuid."""
        persistent_identifier = cls.get_persistent_identifier(id)
        return str(persistent_identifier.pid_value)

    @classmethod
    def get_id_by_pid(cls, pid):
        """Get uuid by pid."""
        assert cls.provider
        try:
            persistent_identifier = PersistentIdentifier.get(
                cls.provider.pid_type,
                pid
            )
            return persistent_identifier.object_uuid
        except Exception:
            return None

    @classmethod
    def get_record_by_id(cls, id, with_deleted=False):
        """Get ils record by uuid."""
        return super().get_record(id, with_deleted=with_deleted)

    @classmethod
    def get_persistent_identifier(cls, id):
        """Get Persistent Identifier."""
        return PersistentIdentifier.get_by_object(
            cls.provider.pid_type,
            cls.object_type,
            id
        )

    @classmethod
    def _get_all(cls, with_deleted=False):
        """Get all persistent identifier records."""
        query = PersistentIdentifier.query.filter_by(
            pid_type=cls.provider.pid_type
        )
        if not with_deleted:
            query = query.filter_by(status=PIDStatus.REGISTERED)
        return query

    @classmethod
    def get_all_pids(cls, with_deleted=False, limit=100000):
        """Get all records pids. Return a generator iterator."""
        query = cls._get_all(with_deleted=with_deleted)
        if limit:
            # slower, less memory
            query = query.order_by(text('pid_value')).limit(limit)
            offset = 0
            count = cls.count(with_deleted=with_deleted)
            while offset < count:
                for identifier in query.offset(offset):
                    yield identifier.pid_value
                offset += limit
        else:
            # faster, more memory
            for identifier in query:
                yield identifier.pid_value

    @classmethod
    def get_all_ids(cls, with_deleted=False, limit=100000):
        """Get all records uuids. Return a generator iterator."""
        query = cls._get_all(with_deleted=with_deleted)
        if limit:
            # slower, less memory
            query = query.order_by(text('pid_value')).limit(limit)
            offset = 0
            count = cls.count(with_deleted=with_deleted)
            while offset < count:
                for identifier in query.limit(limit).offset(offset):
                    yield identifier.object_uuid
                offset += limit
        else:
            # faster, more memory
            for identifier in query:
                yield identifier.object_uuid

    @classmethod
    def count(cls, with_deleted=False):
        """Get record count."""
        return cls._get_all(with_deleted=with_deleted).count()

    def delete(self, force=False, dbcommit=False, delindex=False):
        """Delete record and persistent identifier."""
        if self.can_delete:
            persistent_identifier = self.get_persistent_identifier(self.id)
            persistent_identifier.delete()
            if force:
                db.session.delete(persistent_identifier)
            self = super().delete(force=force)
            if dbcommit:
                db.session.commit()
            if delindex:
                self.delete_from_index()
            return self
        else:
            raise IlsRecordError.NotDeleted()

    def update(self, data, dbcommit=False, reindex=False):
        """Update data for record."""
        pid = data.get('pid')
        if pid:
            db_record = self.get_record_by_id(self.id)
            if pid != db_record.pid:
                raise IlsRecordError.PidChange(
                    '{class_n} changed pid from {old_pid} to {new_pid}'.format(
                        class_n=self.__class__.__name__,
                        old_pid=db_record.pid,
                        new_pid=pid
                    )
                )
        record = self
        super().update(data)
        if dbcommit:
            record = self.dbcommit(reindex)
            record = self.get_record_by_id(self.id)
        return record

    def replace(self, data, dbcommit=False, reindex=False):
        """Replace data in record."""
        new_data = deepcopy(data)
        pid = new_data.get('pid')
        if not pid:
            raise IlsRecordError.PidMissing(f'missing pid={self.pid}')
        self.clear()
        self = self.update(new_data, dbcommit=dbcommit, reindex=reindex)
        return self

    def revert(self, revision_id, reindex=False):
        """Revert the record to a specific revision."""
        persistent_identifier = self.get_persistent_identifier(self.id)
        if persistent_identifier.is_deleted():
            raise IlsRecordError.Deleted()
        self = super().revert(revision_id=revision_id)
        if reindex:
            self.reindex(forceindex=False)
        return self

    def undelete(self, reindex=False):
        """Undelete the record."""
        persistent_identifier = self.get_persistent_identifier(self.id)
        if persistent_identifier.is_deleted():
            with db.session.begin_nested():
                persistent_identifier.status = PIDStatus.REGISTERED
                db.session.add(persistent_identifier)
        else:
            raise IlsRecordError.NotDeleted()

        self = self.revert(self.revision_id - 2, reindex=reindex)
        return self

    def dbcommit(self, reindex=False, forceindex=False):
        """Commit changes to db."""
        self = super().commit()
        db.session.commit()
        if reindex:
            self.reindex(forceindex=forceindex)
        return self

    def reindex(self, forceindex=False):
        """Reindex record."""
        indexer = self.get_indexer_class()
        if forceindex:
            return indexer(version_type="external_gte").index(self)
        else:
            return indexer().index(self)

    def delete_from_index(self):
        """Delete record from index."""
        indexer = self.get_indexer_class()
        try:
            indexer().delete(self)
        except NotFoundError:
            current_app.logger.warning(
                'Can not delete from index {class_name}: {pid}'.format(
                    class_name=self.__class__.__name__,
                    pid=self.pid
                )
            )

    @property
    def pid(self):
        """Get ils record pid value."""
        return self.get('pid')

    @property
    def persistent_identifier(self):
        """Get Persistent Identifier."""
        return self.get_persistent_identifier(self.id)

    def get_links_to_me(self):
        """Record links."""
        return {}

    def reasons_not_to_delete(self):
        """Record deletion reasons."""
        return {}

    @property
    def can_delete(self):
        """Record can be deleted."""
        return len(self.reasons_not_to_delete()) == 0

    @property
    def organisation_pid(self):
        """Get organisation pid for circulation policy."""
        return extracted_data_from_ref(self.get('organisation'))

    @classmethod
    def get_metadata_identifier_names(cls):
        """Get metadata and identifier table names."""
        metadata = cls.model_cls.__tablename__
        identifier = cls.provider.identifier
        return metadata, identifier


class IlsRecordsIndexer(RecordIndexer):
    """Indexing class for ils."""

    record_cls = IlsRecord

    def index(self, record):
        """Indexing a record."""
        return_value = super().index(record)
        index_name, doc_type = current_record_to_index(record)
        # TODO: Do we need to flush everytime the ES index?
        # Tests depends on this at the moment.
        current_search.flush_and_refresh(index_name)
        return return_value

    def delete(self, record):
        """Delete a record.

        :param record: Record instance.
        """
        return_value = super().delete(record)
        index_name, doc_type = current_record_to_index(record)
        current_search.flush_and_refresh(index_name)
        return return_value

    def bulk_index(self, record_id_iterator, doc_type=None):
        """Bulk index records.

        :param record_id_iterator: Iterator yielding record UUIDs.
        """
        self._bulk_op(record_id_iterator, op_type='index', doc_type=doc_type)

    def process_bulk_queue(self, es_bulk_kwargs=None, stats_only=True):
        """Process bulk indexing queue.

        :param dict es_bulk_kwargs: Passed to
            :func:`elasticsearch:elasticsearch.helpers.bulk`.
        :param boolean stats_only: if `True` only report number of
            successful/failed operations instead of just number of
            successful and a list of error responses
        """
        with current_celery_app.pool.acquire(block=True) as conn:
            consumer = Consumer(
                connection=conn,
                queue=self.mq_queue.name,
                exchange=self.mq_exchange.name,
                routing_key=self.mq_routing_key,
            )

            req_timeout = current_app.config['INDEXER_BULK_REQUEST_TIMEOUT']

            es_bulk_kwargs = es_bulk_kwargs or {}
            count = bulk(
                self.client,
                self._actionsiter(consumer.iterqueue()),
                stats_only=stats_only,
                request_timeout=req_timeout,
                expand_action_callback=(
                    _es7_expand_action if ES_VERSION[0] >= 7
                    else default_expand_action
                ),
                **es_bulk_kwargs
            )

            consumer.close()

        return count

    def _get_record_class(self, payload):
        """Get the record class from payload."""
        from .utils import get_record_class_from_schema_or_pid_type

        # take the first defined doc type for finding the class
        pid_type = payload.get('doc_type', 'rec')
        return get_record_class_from_schema_or_pid_type(pid_type=pid_type)

    def _actionsiter(self, message_iterator):
        """Iterate bulk actions.

        :param message_iterator: Iterator yielding messages from a queue.
        """
        for message in message_iterator:
            payload = message.decode()
            try:
                indexer = self._get_record_class(payload).get_indexer_class()
                if payload['op'] == 'delete':
                    yield indexer()._delete_action(payload=payload)
                else:
                    yield indexer()._index_action(payload=payload)
                message.ack()
            except NoResultFound:
                message.reject()
            except Exception:
                message.reject()
                current_app.logger.error(
                    "Failed to index record {id}".format(id=payload.get('id')),
                    exc_info=True)

    def _index_action(self, payload):
        """Bulk index action.

        :param payload: Decoded message body.
        :return: Dictionary defining an Elasticsearch bulk 'index' action.
        """
        with db.session.begin_nested():
            record = self.record_cls.get_record(payload['id'])
        index, doc_type = self.record_to_index(record)

        arguments = {}
        body = self._prepare_record(record, index, doc_type, arguments)
        action = {
            '_op_type': 'index',
            '_index': index,
            '_type': doc_type,
            '_id': str(record.id),
            '_version': record.revision_id,
            '_version_type': self._version_type,
            '_source': body
        }
        action.update(arguments)

        return action

    @staticmethod
    def _prepare_record(record, index, doc_type, arguments=None, **kwargs):
        """Prepare record data for indexing.

        :param record: The record to prepare.
        :param index: The Elasticsearch index.
        :param doc_type: The Elasticsearch document type.
        :param arguments: The arguments to send to Elasticsearch upon indexing.
        :param **kwargs: Extra parameters.
        :return: The record metadata.
        """
        if current_app.config['INDEXER_REPLACE_REFS']:
            data = record.replace_refs().dumps()
        else:
            data = record.dumps()

        data['_created'] = pytz.utc.localize(record.created).isoformat() \
            if record.created else None
        data['_updated'] = pytz.utc.localize(record.updated).isoformat() \
            if record.updated else None

        # Allow modification of data prior to sending to Elasticsearch.
        before_record_index.send(
            current_app._get_current_object(),
            json=data,
            record=record,
            index=index,
            doc_type=doc_type,
            arguments={} if arguments is None else arguments,
            **kwargs
        )
        return data
