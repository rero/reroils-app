# -*- coding: utf-8 -*-
#
# RERO ILS
# Copyright (C) 2021 RERO
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

"""rero-ils Doublin Core model definition."""

from dojson import Overdo, utils
from flask_babelex import gettext as _

from rero_ils.modules.contributions.utils import \
    get_contribution_localized_value
from rero_ils.modules.documents.utils import title_format_text_head


class DublinCoreOverdo(Overdo):
    """Specialized Overdo for Dublin Core."""

    def do(self, blob, ignore_missing=True, exception_handlers=None,
           language='fr'):
        """Translate blob values and instantiate new model instance.

        Raises ``MissingRule`` when no rule matched and ``ignore_missing``
        is ``False``.

        :param blob: ``dict``-like object on which the matching rules are
                     going to be applied.
        :param ignore_missing: Set to ``False`` if you prefer to raise
                               an exception ``MissingRule`` for the first
                               key that it is not matching any rule.
        :param exception_handlers: Give custom exception handlers to take care
                                   of non-standard codes that are installation
                                   specific.
        :param language: Language to use.
        """
        self.language = language

        result = super().do(
            blob,
            ignore_missing=ignore_missing,
            exception_handlers=exception_handlers
        )
        titles = blob.get('title', [])
        bf_titles = list(filter(lambda t: t['type'] == 'bf:Title', titles))

        text = title_format_text_head(
            titles=bf_titles,
            responsabilities=blob.get('responsibilityStatement', []),
            with_subtitle=True
        )
        if text:
            result['titles'] = [text]

        pid = blob.get('pid')
        if pid:
            identifiers = result.get('identifiers', [])
            identifiers.insert(0, f'bf:Local|{pid}')
        return result


dublincore = DublinCoreOverdo()
CREATOR_ROLES = [
    'aut', 'cmp', 'pht', 'ape', 'aqt', 'arc', 'art', 'aus', 'chr', 'cll',
    'com', 'drt', 'dsr', 'enj', 'fmk', 'inv', 'ive', 'ivr', 'lbt', 'lsa',
    'lyr', 'pra', 'prg', 'rsp', 'scl'
]


# creator and contributor
@dublincore.over('creators', 'contribution')
@utils.for_each_value
@utils.ignore_value
def json_to_contributors(self, key, value):
    """Get creators and contributors data."""
    authorized_access_point = get_contribution_localized_value(
        contribution=value.get('agent', {}),
        key='authorized_access_point',
        language=dublincore.language
    )
    if authorized_access_point:
        result = authorized_access_point
    else:
        result = value.get('agent', {}).get('preferred_name')

    if result:
        if value.get('role') in CREATOR_ROLES:
            return result

        contributors = self.get('contributors', [])
        contributors.append(result)
        # save contributors directly into self
        self['contributors'] = contributors


@dublincore.over('descriptions',
                 '^(summary|note|dissertation|supplementaryContent)')
@utils.ignore_value
def json_to_descriptions(self, key, value):
    """Get descriptions data."""
    descriptions = self.get('descriptions', [])
    for data in utils.force_list(value):
        if key == 'supplementaryContent':
            descriptions.append(data)
        elif key == 'summary':
            labels = data.get('label', [])
            for label in labels:
                descriptions.append(label['value'])
        else:
            label = data.get('label')
            if label:
                descriptions.append(label)
    if descriptions:
        # write the discriptions directly into self
        self['descriptions'] = descriptions


@dublincore.over('languages', '^language')
@utils.ignore_value
def json_to_languages(self, key, value):
    """Get languages data."""
    languages = [language.get('value') for language in utils.force_list(value)]
    return languages or None


@dublincore.over('publishers', '^provisionActivity')
@utils.ignore_value
def json_to_dates(self, key, value):
    """Get publishers data and date."""
    publishers = self.get('publisher', [])
    dates = self.get('dates', [])
    for data in value:
        # only take the first date:
        if data.get('type') == 'bf:Publication' and not self.get('date'):
            start_date = str(data.get('startDate', ''))
            date = [start_date]
            end_date = str(data.get('endDate', ''))
            if end_date:
                date.append(end_date)
            if date:
                dates.append('-'.join(date))
        statements = data.get('statement', [])
        for statement in statements:
            if statement['type'] == 'bf:Agent':
                # TODO: witch value do we need to take?
                publishers.append(statement['label'][0].get('value'))
    if dates:
        # write the dates directly into self
        self['dates'] = dates
    if publishers:
        # write the publishers directly into self
        self['publishers'] = publishers


@dublincore.over('types', '^type')
@utils.for_each_value
@utils.ignore_value
def json_to_types(self, key, value):
    """Get types data."""
    main_type = value.get('main_type')
    subtype_type = value.get('subtype')
    if subtype_type:
        return ' / '.join([_(main_type), _(subtype_type)])
    else:
        return _(main_type)


@dublincore.over('identifiers', '^identifiedBy')
@utils.for_each_value
@utils.ignore_value
def json_to_identifiers(self, key, value):
    """Get identifiers data."""
    itype = value.get('type')
    identifier_value = value.get('value')
    source = value.get('source')
    if source:
        return f'{itype}|{identifier_value}({source})'
    return f'{itype}|{identifier_value}'


@dublincore.over('relations',
                 '^(issuedWith|otherEdition|otherPhysicalFormat|precededBy|'
                 'relatedTo|succeededBy|supplement|supplementTo)')
@utils.for_each_value
@utils.ignore_value
def json_to_relations(self, key, value):
    """Get relations data."""
    label = value.get('label')
    if label:
        return label
    else:
        # TODO: make shure the $ref was replaced and had a _text field.
        return value.get('_text')


@dublincore.over('subjects', '^subjects')
@utils.for_each_value
@utils.ignore_value
def json_to_subject(self, key, value):
    """Get subject data."""
    result = ''
    subject_type = value.get('type')
    if subject_type in ['bf:Person', 'bf:Organisation', 'bf:Place']:
        # TODO: set the language
        authorized_access_point = get_contribution_localized_value(
            contribution=value,
            key='authorized_access_point',
            language=dublincore.language
        )
        if authorized_access_point:
            result = authorized_access_point
        else:
            result = value.get('preferred_name')
    elif subject_type == 'bf:Work':
        work = []
        creator = value.get('creator')
        if creator:
            work.append(creator)
        work.append(value.get('title'))
        result = '. - '.join(work)
    elif subject_type in ['bf:Topic', 'bf:Temporal']:
        result = value.get('term')
    return result or None


# @dublincore.over('coverage', '^coverage')
# @utils.ignore_value
# def json_to_coverage(self, key, value):
#     """Get coverage data."""


# @dublincore.over('format', '^formats')
# @utils.ignore_value
# def json_to_formats(self, key, value):
#     """Get dates data."""


# @dublincore.over('rights', '^rights')
# @utils.ignore_value
# def json_to_rights(self, key, value):
#     """Get rights data."""


# @dublincore.over('sources', '^sources')
# @utils.ignore_value
# def json_to_sources(self, key, value):
#     """Get sources data."""
