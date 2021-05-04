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

"""rero-ils MARC21 model definition."""

import re

from dojson import utils
from isbnlib import EAN13

from rero_ils.dojson.utils import ReroIlsMarc21Overdo, TitlePartList, \
    add_note, extract_subtitle_and_parallel_titles_from_field_245_b, \
    get_field_items, get_field_link_data, make_year, \
    remove_trailing_punctuation

marc21 = ReroIlsMarc21Overdo()


@marc21.over('issuance', 'leader')
@utils.ignore_value
def marc21_to_type(self, key, value):
    """Set the mode of issuance."""
    self['issuance'] = dict(
        main_type='rdami:1001',
        subtype='materialUnit'
    )


@marc21.over('language', '^008')
@utils.ignore_value
def marc21_to_language_from_008(self, key, value):
    """Get languages.

    languages: 008 and 041 [$a, repetitive]
    """
    language = self.get('language', [])

    # put 008 language in first place
    language.insert(0, {'type': 'bf:Language', 'value': value.strip()[35:38]})
    return language


@marc21.over('identifiedBy', '^020..')
@utils.ignore_value
def marc21_to_identifier_isbn(self, key, value):
    """Get identifier isbn.

    identifiers_isbn: 020 $a
    """
    isbn13 = EAN13(value.get('a'))
    if isbn13:
        identifiers = self.get('identifiedBy', [])
        identifier = {
            'type': 'bf:Isbn',
            'value': isbn13
        }
        identifiers.append(identifier)
        return identifiers
    return None


@marc21.over('type', '^0248.$')
def marc21_to_type(self, key, value):
    """Get document type."""
    if value.get('a').find('cantook') > -1:
        return [{
            'main_type': 'docmaintype_book',
            'subtype': 'docsubtype_e-book'
        }]
    return None


@marc21.over('identifiedBy', '^035..')
@utils.ignore_value
def marc21_to_identifier_rero_id(self, key, value):
    """Get identifier reroId.

    identifiers:reroID: 035$a
    """
    identifiers = self.get('identifiedBy', [])
    identifier = {
        'type': 'bf:Local',
        'value': value.get('a')
    }
    identifiers.append(identifier)
    return identifiers


@marc21.over('translatedFrom', '^041..')
@utils.ignore_value
def marc21_to_translated_from(self, key, value):
    """Get translatedFrom.

    translatedFrom: 041 [$h repetitive]
    languages: 008 and 041 [$a, repetitive]
    """
    languages = self.get('language', [])
    unique_lang = []
    if languages != []:
        for language in languages:
            unique_lang.append(language['value'])

    language = value.get('a')
    if language:
        for lang in utils.force_list(language):
            if lang not in unique_lang:
                unique_lang.append(lang)
                languages.append({'type': 'bf:Language', 'value': lang})

    self['language'] = languages

    translated = value.get('h')
    if translated:
        return list(utils.force_list(translated))

    return None


@marc21.over('contribution', '[17][01][01]..')
@utils.for_each_value
@utils.ignore_value
def marc21_to_contribution(self, key, value):
    """Get contribution."""
    if not key[4] == '2' and key[:3] in ['100', '700', '710', '711']:
        agent = {'type': 'bf:Person'}
        if value.get('a'):
            name = utils.force_list(value.get('a'))[0]
            agent['preferred_name'] = remove_trailing_punctuation(name)

        # 100|700 Person
        if key[:3] in ['100', '700']:
            if value.get('b'):
                numeration = utils.force_list(value.get('b'))[0]
                agent['numeration'] = remove_trailing_punctuation(
                    numeration)
            if value.get('c'):
                qualifier = utils.force_list(value.get('c'))[0]
                agent['qualifier'] = remove_trailing_punctuation(qualifier)
            if value.get('d'):
                date = utils.force_list(value.get('d'))[0]
                date = date.rstrip(',')
                dates = remove_trailing_punctuation(date).split('-')
                try:
                    date_of_birth = dates[0].strip()
                    if date_of_birth:
                        agent['date_of_birth'] = date_of_birth
                except Exception:
                    pass
                try:
                    date_of_death = dates[1].strip()
                    if date_of_death:
                        agent['date_of_death'] = date_of_death
                except Exception:
                    pass
            if value.get('q'):
                fuller_form_of_name = utils.force_list(value.get('q'))[0]
                agent['fuller_form_of_name'] = remove_trailing_punctuation(
                    fuller_form_of_name
                ).lstrip('(').rstrip(')')

        # 710|711 Organisation
        elif key[:3] in ['710', '711']:
            agent['type'] = 'bf:Organisation'
            if key[:3] == '711':
                agent['conference'] = True
            else:
                agent['conference'] = False
            if value.get('e'):
                subordinate_units = []
                for subordinate_unit in utils.force_list(value.get('e')):
                    subordinate_units.append(subordinate_unit.rstrip('.'))
                agent['subordinate_unit'] = subordinate_units
            if value.get('n'):
                numbering = utils.force_list(value.get('n'))[0]
                agent['numbering'] = remove_trailing_punctuation(
                    numbering
                ).lstrip('(').rstrip(')')
            if value.get('d'):
                conference_date = utils.force_list(value.get('d'))[0]
                conference_date = remove_trailing_punctuation(
                    conference_date
                ).lstrip('(').rstrip(')')
                if conference_date:
                    agent['conference_date'] = conference_date
            if value.get('c'):
                place = utils.force_list(value.get('c'))[0]
                place = remove_trailing_punctuation(
                    place
                ).lstrip('(').rstrip(')')
                if place:
                    agent['place'] = place
        roles = ['aut']
        if value.get('4'):
            roles = []
            for role in utils.force_list(value.get('4')):
                roles.append(role)
        else:
            if key[:3] == '100':
                roles = ['cre']
            elif key[:3] == '711':
                roles = ['aut']
            else:
                roles = ['ctb']
        return {
            'agent': agent,
            'role': roles
        }
    else:
        return None


@marc21.over('title', '^245..')
@utils.ignore_value
def marc21_to_title(self, key, value):
    """Get title data.

    field 245:
        $a : non repetitive
        $b : non repetitive
        $c : non repetitive
        $n : repetitive
        $p : repetitive
        $6 : non repetitive
    field 246:
        $a : non repetitive
        $n : repetitive
        $p : repetitive
        $6 : non repetitive
    """
    subfield_245_a = ''
    subfield_245_b = ''
    fields_245 = marc21.get_fields(tag='245')
    if fields_245:
        subfields_245_a = marc21.get_subfields(fields_245[0], 'a')
        subfields_245_b = marc21.get_subfields(fields_245[0], 'b')
        if subfields_245_a:
            subfield_245_a = subfields_245_a[0]
        if subfields_245_b:
            subfield_245_b = subfields_245_b[0]
    field_245_a_end_with_equal = re.search(r'\s*=\s*$', subfield_245_a)
    field_245_a_end_with_colon = re.search(r'\s*:\s*$', subfield_245_a)
    field_245_a_end_with_semicolon = re.search(r'\s*;\s*$', subfield_245_a)
    field_245_b_contains_equal = re.search(r'=', subfield_245_b)

    fields_246 = marc21.get_fields(tag='246')
    subfield_246_a = ''
    if fields_246:
        subfields_246_a = marc21.get_subfields(fields_246[0], 'a')
        if subfields_246_a:
            subfield_246_a = subfields_246_a[0]

    tag_link, link = get_field_link_data(value)
    items = get_field_items(value)
    index = 1
    title_list = []
    title_data = {}
    part_list = TitlePartList(
                    part_number_code='n',
                    part_name_code='p'
                )
    parallel_titles = []
    pararalel_title_data_list = []
    pararalel_title_string_set = set()
    responsibility = {}

    subfield_selection = {'a', 'b', 'c', 'n', 'p'}
    for blob_key, blob_value in items:
        if blob_key in subfield_selection:
            value_data = marc21.build_value_with_alternate_graphic(
                '245', blob_key, blob_value, index, link, ',.', ':;/-=')
            if blob_key in {'a', 'b', 'c'}:
                subfield_selection.remove(blob_key)
            if blob_key == 'a':
                title_data['mainTitle'] = value_data
            elif blob_key == 'b':
                if subfield_246_a:
                    subtitle, parallel_titles, pararalel_title_string_set = \
                        extract_subtitle_and_parallel_titles_from_field_245_b(
                            value_data, field_245_a_end_with_equal)
                    if subtitle:
                        title_data['subtitle'] = subtitle
                elif not subfield_246_a and value_data:
                    title_data['subtitle'] = value_data
            elif blob_key == 'c':
                responsibility = marc21.build_responsibility_data(value_data)
            elif blob_key in ['n', 'p']:
                part_list.update_part(value_data, blob_key, blob_value)
        if blob_key != '__order__':
            index += 1
    title_data['type'] = 'bf:Title'
    the_part_list = part_list.get_part_list()
    if the_part_list:
        title_data['part'] = the_part_list
    if title_data:
        title_list.append(title_data)
    variant_title_list = \
        marc21.build_variant_title_data(pararalel_title_string_set)

    for parallel_title in parallel_titles:
        title_list.append(parallel_title)
    for variant_title_data in variant_title_list:
        title_list.append(variant_title_data)
    if responsibility:
        self['responsibilityStatement'] = responsibility
    return title_list or None


@marc21.over('editionStatement', '^250..')
@utils.for_each_value
@utils.ignore_value
def marc21_to_edition_statement(self, key, value):
    """Get edition statement data.

    editionDesignation: 250 [$a non repetitive] (without trailing ponctuation)
    responsibility: 250 [$b non repetitive]
    """
    edition_data = {}
    subfields_a = utils.force_list(value.get('a'))
    if subfields_a:
        subfield_a = remove_trailing_punctuation(subfields_a[0])
        edition_data['editionDesignation'] = [{'value': subfield_a}]
    subfields_b = utils.force_list(value.get('b'))
    if subfields_b:
        subfields_b = subfields_b[0]
        edition_data['responsibility'] = [{'value': subfields_b}]
    return edition_data or None


@marc21.over('copyrightDate', '^264.4')
@utils.ignore_value
def marc21_to_copyright_date(self, key, value):
    """Get Copyright Date."""
    copyright_dates = self.get('copyrightDate', [])
    copyright_date = value.get('c')
    if copyright_date:
        match = re.search(r'^([©℗])+\s*(\d{4}.*)', copyright_date)
        if match:
            copyright_date = ' '.join((
                match.group(1),
                match.group(2)
            ))
        else:
            raise ValueError('Bad format of copyright date')
    copyright_dates.append(copyright_date)
    return copyright_dates or None


@marc21.over('provisionActivity', '^(260..|264.[ 0-3])')
@utils.for_each_value
@utils.ignore_value
def marc21_to_provision_activity(self, key, value):
    """Get publisher data.

    publisher.name: 264 [$b repetitive]
    publisher.place: 264 [$a repetitive]
    publicationDate: 264 [$c repetitive] (but take only the first one)
    """
    def build_statement(field_value, ind2):

        def build_place_or_agent_data(code, label):
            place_or_agent_data = None
            type_per_code = {
                'a': 'bf:Place',
                'b': 'bf:Agent'
            }
            value = remove_trailing_punctuation(label)
            if value:
                place_or_agent_data = {
                    'type': type_per_code[code],
                    'label': [{'value': value}]
                }
            return place_or_agent_data

        # function build_statement start here
        statement = []
        items = get_field_items(field_value)
        for blob_key, blob_value in items:
            if blob_key in ('a', 'b'):
                place_or_agent_data = build_place_or_agent_data(
                    blob_key, blob_value)
                if place_or_agent_data:
                    statement.append(place_or_agent_data)
        return statement or None

    def build_place():
        place = {}
        if marc21.country:
            place['country'] = marc21.country
        if place:
            place['type'] = 'bf:Place'
        return place

    # the function marc21_to_provisionActivity start here
    ind2 = key[4]
    type_per_ind2 = {
        ' ': 'bf:Publication',
        '0': 'bf:Production',
        '1': 'bf:Publication',
        '2': 'bf:Distribution',
        '3': 'bf:Manufacture'
    }
    if key[:3] == '260':
        ind2 = '1'  # to force type to bf:Publication for field 260
    publication = {
        'type': type_per_ind2[ind2],
        'statement': [],
    }

    publication['statement'] = build_statement(value, ind2)

    subfields_c = utils.force_list(value.get('c'))
    if subfields_c:
        subfield_c = subfields_c[0]
        publication['statement'].append({
            'label': [{'value': subfield_c}],
            'type': 'Date'
        })
        if ind2 in (' ', '1'):
            dates = subfield_c.replace('[', '').replace(']', '').split('-')
            try:
                start_date = make_year(dates[0])
                if start_date:
                    publication['startDate'] = start_date
            except Exception:
                pass
            try:
                end_date = make_year(dates[1])
                if end_date:
                    publication['endDate'] = end_date
            except Exception:
                pass
            place = build_place()
            if place:
                publication['place'] = [place]

    return publication or None


@marc21.over('extent', '^300..')
@utils.ignore_value
def marc21_to_description(self, key, value):
    """Get extent.

    extent: 300$a (the first one if many)
    """
    if value.get('a'):
        if not self.get('extent', None):
            self['extent'] = remove_trailing_punctuation(
                utils.force_list(value.get('a'))[0])
    return None


@marc21.over('note', '^500..')
@utils.for_each_value
@utils.ignore_value
def marc21_to_notes(self, key, value):
    """Get  notes.

    note: [500$a repetitive]
    """
    add_note(
        dict(
            noteType='general',
            label=value.get('a', '')
        ),
        self)

    return None


@marc21.over('summary', '^520..')
@utils.for_each_value
@utils.ignore_value
def marc21_to_summary(self, key, value):
    """Get summary from repetitive field 520."""
    key_per_code = {
        'a': 'label',
        'c': 'source'
    }
    # parse field 520 subfields for extracting:
    # summary and source parts
    tag_link, link = get_field_link_data(value)
    items = get_field_items(value)
    index = 1
    summary = {}
    subfield_selection = {'a', 'c'}
    for blob_key, blob_value in items:
        if blob_key in subfield_selection:
            subfield_selection.remove(blob_key)
            if blob_key == 'a':
                summary_data = marc21.build_value_with_alternate_graphic(
                    '520', blob_key, blob_value, index, link, ',.', ':;/-=')
            else:
                summary_data = blob_value
            if summary_data:
                summary[key_per_code[blob_key]] = summary_data
        if blob_key != '__order__':
            index += 1
    return summary or None


@marc21.over('subjects', '^6....')
@utils.for_each_value
@utils.ignore_value
@utils.ignore_value
def marc21_to_subjects(self, key, value):
    """Get subjects.

    subjects: 6xx [duplicates could exist between several vocabularies,
        if possible deduplicate]
    """
    subjects = self.get('subjects', [])
    for subject in utils.force_list(value.get('a')):
        subjects.append({
            'type': "bf:Topic",
            'term': subject
        })
    self['subjects'] = subjects
    return None


@marc21.over('titlesProper', '^730..')
@utils.for_each_value
@utils.ignore_value
def marc21_to_titles_proper(self, key, value):
    """Test dojson marc21titlesProper.

    titleProper: 730$a
    """
    return value.get('a')


@marc21.over('electronicLocator', '^8564.')
@utils.for_each_value
@utils.ignore_value
def marc21_electronicLocator(self, key, value):
    """Get electronic locator."""
    indicator2 = key[4]
    electronic_locator = {}
    url = utils.force_list(value.get('u'))[0].strip()
    subfield_3 = value.get('3')
    if subfield_3:
        subfield_3 = utils.force_list(subfield_3)[0]
    if indicator2 == '2':
        if subfield_3 and subfield_3 == 'Image de couverture':
            electronic_locator = {
                'url': url,
                'type': 'relatedResource',
                'content': 'coverImage'
            }
    elif indicator2 == '0':
        subfield_x = value.get('x')
        if subfield_x:
            electronic_locator = {
                'url': url,
                'type': 'resource',
                'source': utils.force_list(subfield_x)[0]
            }
            # if subfield_3 and subfield_3 == 'Texte intégral':
            #     electronic_locator['content'] == subfield_3
    return electronic_locator or None
