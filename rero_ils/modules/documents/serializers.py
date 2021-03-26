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

"""Document serialization."""

from dcxml import simpledc
from dojson._compat import iteritems, string_types
from dojson.contrib.to_marc21.utils import dumps
from dojson.utils import GroupableOrderedDict
from flask import current_app, request
from invenio_records_rest.serializers.dc import \
    DublinCoreSerializer as BaseDublinCoreSerializer
from invenio_records_rest.serializers.response import record_responsify, \
    search_responsify
from lxml import etree
from lxml.builder import ElementMaker

from .dojson.contrib.jsontodc import dublincore
from .dojson.contrib.jsontomarc21 import to_marc21
from .dojson.contrib.jsontomarc21.model import replace_contribution_sources
from .utils import create_contributions, filter_document_type_buckets
from ..contributions.api import ContributionsSearch
from ..documents.api import Document
from ..documents.utils import title_format_text_head
from ..documents.views import create_title_alternate_graphic, \
    create_title_responsibilites, create_title_variants
from ..libraries.api import Library
from ..organisations.api import Organisation
from ..serializers import JSONSerializer, RecordSchemaJSONV1

DEFAULT_LANGUAGE = 'en'


class DocumentJSONSerializer(JSONSerializer):
    """Mixin serializing records as JSON."""

    def preprocess_record(self, pid, record, links_factory=None, **kwargs):
        """Prepare a record and persistent identifier for serialization."""
        rec = record
        titles = rec.get('title', [])
        # build responsibility data for display purpose
        responsibility_statement = rec.get('responsibilityStatement', [])
        responsibilities = \
            create_title_responsibilites(responsibility_statement)
        if responsibilities:
            rec['ui_responsibilities'] = responsibilities
        # build alternate graphic title data for display purpose
        altgr_titles = create_title_alternate_graphic(titles)
        if altgr_titles:
            rec['ui_title_altgr'] = altgr_titles
        altgr_titles_responsibilities = create_title_alternate_graphic(
            titles,
            responsibility_statement
        )
        if altgr_titles_responsibilities:
            rec['ui_title_altgr_responsibilities'] = \
                altgr_titles_responsibilities

        variant_titles = create_title_variants(titles)
        # build variant title data for display purpose
        if variant_titles:
            rec['ui_title_variants'] = variant_titles
        if request and request.args.get('resolve') == '1':
            # We really have to replace the refs for the MEF here!
            rec_refs = record.replace_refs()
            contributions = create_contributions(
                rec_refs.get('contribution', [])
            )
            if contributions:
                rec['contribution'] = contributions
        return super().preprocess_record(
            pid=pid, record=rec, links_factory=links_factory, kwargs=kwargs)

    def post_process_serialize_search(self, results, pid_fetcher):
        """Post process the search results."""
        # Item filters.
        viewcode = request.args.get('view',  current_app.config.get(
                'RERO_ILS_SEARCH_GLOBAL_VIEW_CODE'
        ))
        records = results.get('hits', {}).get('hits', {})
        for record in records:
            metadata = record.get('metadata', {})
            available = Document.get_record_by_pid(
                metadata.get('pid')).is_available(viewcode)
            metadata['available'] = available
            titles = metadata.get('title', [])
            text_title = title_format_text_head(titles, with_subtitle=False)
            if text_title:
                metadata['ui_title_text'] = text_title
            responsibility = metadata.get('responsibilityStatement', [])
            text_title = title_format_text_head(titles, responsibility,
                                                with_subtitle=False)
            if text_title:
                metadata['ui_title_text_responsibility'] = text_title

        if viewcode != current_app.config.get(
                'RERO_ILS_SEARCH_GLOBAL_VIEW_CODE'
        ):
            view_id = Organisation.get_record_by_viewcode(viewcode)['pid']
            for record in records:
                metadata = record.get('metadata', {})
                items = metadata.get('items', [])
                if items:
                    output = []
                    for item in items:
                        if item.get('organisation')\
                                .get('organisation_pid') == view_id:
                            output.append(item)
                    record['metadata']['items'] = output

        # Add organisation name
        for org_term in results.get('aggregations', {}).get(
                'organisation', {}).get('buckets', []):
            pid = org_term.get('key')
            org = Organisation.get_record_by_pid(pid)
            name = org.get('name')
            org_term['name'] = name
            lib_buckets = self._process_library_buckets(org, org_term.get(
                'library', {}).get('buckets', [])
            )
            if lib_buckets:
                org_term['library']['buckets'] = lib_buckets

        # TODO: Move this logic in the front end (needs backend adaptation)
        if (viewcode is not None) and (viewcode != current_app.config.get(
            'RERO_ILS_SEARCH_GLOBAL_VIEW_CODE'
        )):
            org = Organisation.get_record_by_viewcode(viewcode)
            org_buckets = results.get('aggregations', {}).get(
                'organisation', {}).get('buckets', [])
            for bucket in org_buckets:
                if bucket.get('key') == org.pid:
                    lib_agg = bucket.get('library')
                    if lib_agg:
                        results['aggregations']['library'] = lib_agg
                        del results['aggregations']['organisation']

        # Correct document type buckets
        new_type_buckets = []
        type_buckets = results['aggregations']['document_type']['buckets']
        results['aggregations']['document_type']['buckets'] = \
            filter_document_type_buckets(type_buckets)

        return super().post_process_serialize_search(results, pid_fetcher)

    @classmethod
    def _process_library_buckets(cls, org, lib_buckets):
        """Process library buckets.

        Add library names
        :param org: current organisation
        :param lib_buckets: library buckets

        :return processed buckets
        """
        processed_buckets = []
        lib_pids = list(org.get_libraries_pids())
        for bucket in lib_buckets:
            if bucket.get('key') in lib_pids:
                bucket['name'] = Library.get_record_by_pid(
                    bucket.get('key')).get('name')
                processed_buckets.append(bucket)

        return processed_buckets


class DocumentMARCXMLSerializer(JSONSerializer):
    """DoJSON based MARCXML serializer for documents.

    Note: This serializer is not suitable for serializing large number of
    records due to high memory usage.
    """

    def __init__(self, xslt_filename=None, schema_class=None):
        """Initialize serializer.

        :param dojson_model: The DoJSON model able to convert JSON through the
            ``do()`` function.
        :param xslt_filename: XSLT filename. (Default: ``None``)
        :param schema_class: The schema class. (Default: ``None``)
        """
        # xslt_filename = resource_filename(
        #     'rero_ils', 'xslts/MARC21slim2MODS3-6.xsl')
        self.dumps_kwargs = {}
        if xslt_filename:
            self.dumps_kwargs = dict(xslt_filename=xslt_filename)

        self.schema_class = schema_class
        super().__init__()

    def transform_record(self, pid, record, language,
                         links_factory=None, **kwargs):
        """Transform record into an intermediate representation."""
        return to_marc21.do(record, language=language,
                            with_holdings_items=True)

    def transform_search_hit(self, pid, record_hit, language,
                             links_factory=None, **kwargs):
        """Transform search result hit into an intermediate representation."""
        return to_marc21.do(record_hit, language=language,
                            with_holdings_items=True)

    def serialize(self, pid, record, links_factory=None):
        """Serialize a single record and persistent identifier.

        :param pid: The :class:`invenio_pidstore.models.PersistentIdentifier`
            instance.
        :param record: The :class:`invenio_records.api.Record` instance.
        :param links_factory: Factory function for the link generation,
            which are added to the response.
        :returns: The object serialized.
        """
        language = request.args.get('ln', DEFAULT_LANGUAGE)
        return dumps(
            self.transform_record(pid, record, language, links_factory),
            **self.dumps_kwargs
        )

    def transform_records(self, hits, pid_fetcher, language,
                          item_links_factory=None):
        """Transform records into an intermediate representation."""
        # get all linked contributions
        contribution_pids = []
        for hit in hits:
            for contribution in hit['_source'].get('contribution', []):
                contribution_pid = contribution.get('agent', {}).get('pid')
                if contribution_pid:
                    contribution_pids.append(contribution_pid)
        search = ContributionsSearch(). \
            filter('terms', pid=list(set(contribution_pids)))
        es_contributions = {}
        for hit in search.scan():
            contribution = hit.to_dict()
            es_contributions[contribution['pid']] = contribution

        order = current_app.config.get(
            'RERO_ILS_CONTRIBUTIONS_LABEL_ORDER', [])
        source_order = order.get(language, order.get(order['fallback'], []))
        records = []
        for hit in hits:
            document = hit['_source']
            contributions = document.get('contribution', [])
            for contribution in contributions:
                contribution_pid = contribution.get('agent', {}).get('pid')
                if contribution_pid in es_contributions:
                    contribution['agent'] = es_contributions[contribution_pid]
                    replace_contribution_sources(
                        contribution=contribution,
                        source_order=source_order
                    )

            record = self.transform_search_hit(
                pid=pid_fetcher(hit['_id'], document),
                record_hit=document,
                language=language,
                links_factory=item_links_factory
            )
            # complete the contributions from refs

            records.append(record)
        return records

    def serialize_search(self, pid_fetcher, search_result,
                         item_links_factory=None, **kwargs):
        """Serialize a search result.

        :param pid_fetcher: Persistent identifier fetcher.
        :param search_result: Elasticsearch search result.
        :param item_links_factory: Factory function for the items in result.
            (Default: ``None``)
        :returns: The objects serialized.
        """
        language = request.args.get('ln', DEFAULT_LANGUAGE)
        records = self.transform_records(
            hits=search_result['hits']['hits'],
            pid_fetcher=pid_fetcher,
            language=language,
            item_links_factory=item_links_factory
        )
        return dumps(records, **self.dumps_kwargs)


class DocumentMARCXMLSRUSerializer(DocumentMARCXMLSerializer):
    """DoJSON based MARCXML SRU serializer for documents.

    Note: This serializer is not suitable for serializing large number of
    records due to high memory usage.
    """

    MARC21_NS = "http://www.loc.gov/MARC21/slim"
    """MARCXML XML Schema"""

    def dumps_etree(self, total, records, sru, xslt_filename=None,
                    prefix=None):
        """Dump records into a etree."""
        element = ElementMaker(
            namespace=self.MARC21_NS,
            nsmap={prefix: self.MARC21_NS}
        )

        def dump_record(record):
            """Dump a single record."""
            rec = element.record()

            leader = record.get('leader')
            if leader:
                rec.append(element.leader(leader))

            if isinstance(record, GroupableOrderedDict):
                items = record.iteritems(with_order=False, repeated=True)
            else:
                items = iteritems(record)

            for df, subfields in items:
                # Control fields
                if len(df) == 3:
                    if isinstance(subfields, string_types):
                        controlfield = element.controlfield(subfields)
                        controlfield.attrib['tag'] = df[0:3]
                        rec.append(controlfield)
                    elif isinstance(subfields, (list, tuple, set)):
                        for subfield in subfields:
                            controlfield = element.controlfield(subfield)
                            controlfield.attrib['tag'] = df[0:3]
                            rec.append(controlfield)
                else:
                    # Skip leader.
                    if df == 'leader':
                        continue

                    if not isinstance(subfields, (list, tuple, set)):
                        subfields = (subfields,)

                    df = df.replace('_', ' ')
                    for subfield in subfields:
                        if not isinstance(subfield, (list, tuple, set)):
                            subfield = [subfield]

                        for s in subfield:
                            datafield = element.datafield()
                            datafield.attrib['tag'] = df[0:3]
                            datafield.attrib['ind1'] = df[3]
                            datafield.attrib['ind2'] = df[4]

                            if isinstance(s, GroupableOrderedDict):
                                items = s.iteritems(
                                    with_order=False, repeated=True)
                            elif isinstance(s, dict):
                                items = iteritems(s)
                            else:
                                datafield.append(element.subfield(s))

                                items = tuple()

                            for code, value in items:
                                if not isinstance(value, string_types):
                                    for v in value:
                                        datafield.append(
                                            element.subfield(v, code=code))
                                else:
                                    datafield.append(element.subfield(
                                        value, code=code))

                            rec.append(datafield)
            return rec

        if isinstance(records, dict):
            root = dump_record(records)
        else:
            number_of_records = total['value']
            start_record = sru.get('start_record', 0)
            maximum_records = sru.get('maximum_records', 0)
            query = sru.get('query')
            next_record = start_record + maximum_records
            root = element.searchRetrieveResponse()
            root.append(element.version('1.1'))
            root.append(element.numberOfRecords(str(number_of_records)))
            if next_record > 1 and next_record < number_of_records:
                root.append(element.nextRecordPosition(str(next_record)))
            data = element.records()
            for record in records:
                data.append(dump_record(record))
            root.append(data)
            echoed_search_rr = element.echoedSearchRetrieveRequest()
            if query:
                echoed_search_rr.append(element.query(query))
            if start_record:
                echoed_search_rr.append(
                    element.startRecord(str(start_record)))
            if maximum_records:
                echoed_search_rr.append(
                    element.maximumRecords(str(maximum_records)))
            echoed_search_rr.append(element.recordPacking('XML'))
            echoed_search_rr.append(
                element.recordSchema(
                    'info:sru/schema/1/marcxml-v1.1-light'))
            echoed_search_rr.append(element.resultSetTTL('0'))
            root.append(echoed_search_rr)

        if xslt_filename is not None:
            xslt_root = etree.parse(open(xslt_filename))
            transform = etree.XSLT(xslt_root)
            root = transform(root).getroot()

        return root

    def dumps(self, total, records, sru, xslt_filename=None, **kwargs):
        """Dump records into a MarcXMLSRU file."""
        root = self.dumps_etree(
            total=total,
            records=records,
            sru=sru,
            xslt_filename=xslt_filename
        )
        return etree.tostring(
            root,
            pretty_print=True,
            xml_declaration=True,
            encoding='UTF-8',
            **kwargs
        )

    def serialize_search(self, pid_fetcher, search_result,
                         item_links_factory=None, **kwargs):
        """Serialize a search result.

        :param pid_fetcher: Persistent identifier fetcher.
        :param search_result: Elasticsearch search result.
        :param item_links_factory: Factory function for the items in result.
            (Default: ``None``)
        :returns: The objects serialized.
        """
        language = request.args.get('ln', DEFAULT_LANGUAGE)
        records = self.transform_records(
            hits=search_result['hits']['hits'],
            pid_fetcher=pid_fetcher,
            language=language,
            item_links_factory=item_links_factory
        )
        return self.dumps(
            total=search_result['hits']['total'],
            sru=search_result['hits']['total'].get('sru', {}),
            records=records,
            **self.dumps_kwargs
        )


class DublinCoreSerializer(BaseDublinCoreSerializer):
    """Dublin Core serializer for records.

    Note: This serializer is not suitable for serializing large number of
    records.
    """

    from ..utils import get_base_url

    # Default namespace mapping.
    namespace = {
        'dc': 'http://purl.org/dc/elements/1.1/',
        'xml': 'xml',
    }
    # Default container element attributes.
    # TODO: save local dc schema
    container_attribs = {
        '{http://www.w3.org/2001/XMLSchema-instance}schemaLocation':
        'https://www.loc.gov/standards/sru '
        'https://www.loc.gov/standards/sru/recordSchemas/dc-schema.xsd',
    }
    # Default container element.
    container_element = 'record'

    def transform_record(self, pid, record, links_factory=None,
                         language=DEFAULT_LANGUAGE, **kwargs):
        """Transform record into an intermediate representation."""
        record = record.replace_refs()
        contributions = create_contributions(
            record.get('contribution', [])
        )
        if contributions:
            record['contribution'] = contributions
        record = dublincore.do(record, language=language)
        return record

    def transform_search_hit(self, pid, record, links_factory=None,
                             language=DEFAULT_LANGUAGE, **kwargs):
        """Transform search result hit into an intermediate representation."""
        record = Document.get_record_by_pid(pid)
        return self.transform_record(
            pid=pid,
            record=record,
            links_factory=links_factory,
            language=language,
            **kwargs
        )

    def serialize(self, pid, record, links_factory=None, **kwargs):
        """Serialize a single record and persistent identifier.

        :param pid: Persistent identifier instance.
        :param record: Record instance.
        :param links_factory: Factory function for record links.
        """
        language = request.args.get('ln', DEFAULT_LANGUAGE)
        element_record = simpledc.dump_etree(
            self.transform_record(
                pid=pid,
                record=record,
                links_factory=links_factory,
                language=language,
                **kwargs
            ),
            container=self.container_element,
            nsmap=self.namespace,
            attribs=self.container_attribs
        )
        return etree.tostring(element_record, encoding='utf-8', method='xml',
                              pretty_print=True)

    def serialize_search(self, pid_fetcher, search_result, links=None,
                         item_links_factory=None, **kwargs):
        """Serialize a search result.

        :param pid_fetcher: Persistent identifier fetcher.
        :param search_result: Elasticsearch search result.
        :param links: Dictionary of links to add to response.
        """
        total = search_result['hits']['total']['value']
        sru = search_result['hits']['total'].get('sru', {})
        start_record = sru.get('start_record', 0)
        maximum_records = sru.get('maximum_records', 0)
        query = sru.get('query')
        next_record = start_record + maximum_records + 1

        element = ElementMaker()
        xml_root = element.searchRetrieveResponse()
        if sru:
            xml_root.append(element.version('1.1'))
        xml_root.append(element.numberOfRecords(str(total)))
        xml_records = element.records()

        language = request.args.get('ln', DEFAULT_LANGUAGE)
        for hit in search_result['hits']['hits']:
            record = hit['_source']
            pid = record['pid']
            record = self.transform_search_hit(
                pid=pid,
                record=record,
                links_factory=item_links_factory,
                language=language,
                **kwargs
            )

            element_record = simpledc.dump_etree(
                record,
                container=self.container_element,
                nsmap=self.namespace,
                attribs=self.container_attribs
            )
            xml_records.append(element_record)
        xml_root.append(xml_records)

        if sru:
            echoed_search_rr = element.echoedSearchRetrieveRequest()
            if query:
                echoed_search_rr.append(element.query(query))
            if start_record:
                echoed_search_rr.append(element.startRecord(str(start_record)))
            if maximum_records:
                echoed_search_rr.append(element.maximumRecords(
                    str(maximum_records)))
            echoed_search_rr.append(element.recordPacking('XML'))
            xml_root.append(echoed_search_rr)
        else:
            xml_links = element.links()
            self_link = links.get('self')
            if self_link:
                xml_links.append(element.self(f'{self_link}&format=dc'))
            next_link = links.get('next')
            if next_link:
                xml_links.append(element.next(f'{next_link}&format=dc'))
            xml_root.append(xml_links)
        return etree.tostring(xml_root, encoding='utf-8', method='xml',
                              pretty_print=True)


json_doc = DocumentJSONSerializer(RecordSchemaJSONV1)
"""JSON v1 serializer."""
xml_dc = DublinCoreSerializer(RecordSchemaJSONV1)
"""XML DUBLIN CORE v1 serializer."""
xml_marcxml = DocumentMARCXMLSerializer()
"""XML MARCXML v1 serializer."""
xml_marcxmlsru = DocumentMARCXMLSRUSerializer()
"""XML MARCXML SRU v1 serializer."""

json_doc_search = search_responsify(json_doc, 'application/rero+json')
json_doc_response = record_responsify(json_doc, 'application/rero+json')
json_dc_search = search_responsify(xml_dc, 'application/xml')
json_dc_response = record_responsify(xml_dc, 'application/xml')
xml_marcxml_search = search_responsify(xml_marcxml, 'application/xml')
xml_marcxml_response = record_responsify(xml_marcxml, 'application/xml')
xml_marcxmlsru_search = search_responsify(xml_marcxmlsru, 'application/xml')
