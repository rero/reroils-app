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

"""rero-ils UNIMARC model definition."""


import jsonref
from dojson import utils
from dojson.utils import GroupableOrderedDict
from pkg_resources import resource_string

from rero_ils.dojson.utils import ReroIlsUnimarcOverdo, TitlePartList, \
    add_note, get_field_items, get_field_link_data, make_year, \
    not_repetitive, remove_trailing_punctuation
from rero_ils.modules.documents.api import Document

_ISSUANCE_MAIN_TYPE_PER_BIB_LEVEL = {
    'a': 'rdami:1001',
    'c': 'rdami:1001',
    'i': 'rdami:1004',
    'm': 'rdami:1001',
    's': 'rdami:1003'
}

_ISSUANCE_SUBTYPE_PER_BIB_LEVEL = {
    'a': 'article',
    'c': 'privateFile',
    'm': 'materialUnit'
}

_ISSUANCE_SUBTYPE_PER_SERIAL_TYPE = {
    'a': 'periodical',
    'b': 'monographicSeries',
    'e': 'updatingLoose-leaf',
    'f': 'updatingWebsite',
    'g': 'updatingWebsite',
    'h': 'updatingWebsite'
}

_COUNTRY_UNIMARC_MARC21 = {
    'AD': 'an',
    'AE': 'ts',
    'AF': 'af',
    'AG': 'aq',
    'AI': 'am',
    'AL': 'aa',
    'AM': 'ai',
    'AO': 'ao',
    'AQ': 'ay',
    'AR': 'ag',
    'AS': 'as',
    'AT': 'au',
    'AU': 'at',
    'AUT': 'at',
    'AW': 'aw',
    'AZ': 'aj',
    'BA': 'bn',
    'BB': 'bb',
    'BD': 'bg',
    'BE': 'be',
    'BF': 'uv',
    'BG': 'bu',
    'BH': 'ba',
    'BI': 'bd',
    'BJ': 'dm',
    'BL': 'sc',
    'BM': 'bm',
    'BN': 'bx',
    'BO': 'bo',
    'BR': 'bl',
    'BS': 'bf',
    'BT': 'bt',
    'BV': 'bv',
    'BW': 'bs',
    'BZ': 'bh',
    'CA': 'xxc',
    'CC': 'xb',
    'CD': 'cf',
    'CF': 'cx',
    'CG': 'cg',
    'CH': 'sz',
    'CI': 'iv',
    'CK': 'cw',
    'CL': 'cl',
    'CM': 'cm',
    'CN': 'cc',
    'CO': 'ck',
    'CR': 'cr',
    'CU': 'cu',
    'CW': 'co',
    'CX': 'xa',
    'CY': 'cy',
    'DE': 'gw',
    'DJ': 'ft',
    'DK': 'dk',
    'DM': 'dq',
    'DZ': 'ae',
    'EC': 'ec',
    'EE': 'er',
    'EG': 'ua',
    'EH': 'ss',
    'ER': 'ea',
    'ES': 'sp',
    'ET': 'et',
    'FI': 'fi',
    'FJ': 'fj',
    'FM': 'fm',
    'FO': 'fa',
    'FR': 'fr',
    'GA': 'go',
    'GB': 'xxk',
    'GD': 'gd',
    'GE': 'gau',
    'GF': 'fg',
    'GG': 'gg',
    'GH': 'gh',
    'GI': 'gi',
    'GL': 'gl',
    'GM': 'gm',
    'GN': 'gv',
    'GP': 'gp',
    'GQ': 'eg',
    'GR': 'gr',
    'GS': 'xs',
    'GT': 'gt',
    'GU': 'gu',
    'GW': 'pg',
    'GY': 'gy',
    'HM': 'hm',
    'HN': 'ho',
    'HR': 'ci',
    'HT': 'ht',
    'HU': 'hu',
    'ID': 'io',
    'IE': 'ie',
    'IL': 'is',
    'IM': 'im',
    'IN': 'ii',
    'IQ': 'iq',
    'IR': 'ir',
    'IS': 'ic',
    'IT': 'it',
    'JE': 'je',
    'JM': 'jm',
    'JO': 'jo',
    'JP': 'ja',
    'KE': 'ke',
    'KG': 'kg',
    'KH': 'cb',
    'KI': 'gb',
    'KM': 'cq',
    'KN': 'xd',
    'KP': 'kn',
    'KR': 'ko',
    'KW': 'ku',
    'KY': 'cj',
    'KZ': 'kz',
    'LA': 'ls',
    'LB': 'le',
    'LC': 'xk',
    'LI': 'lh',
    'LK': 'ce',
    'LR': 'lb',
    'LS': 'lo',
    'LT': 'li',
    'LU': 'lu',
    'LV': 'lv',
    'LY': 'ly',
    'MA': 'mr',
    'MC': 'mc',
    'MD': 'mv',
    'ME': 'mo',
    'MG': 'mg',
    'MH': 'xe',
    'MK': 'xn',
    'ML': 'ml',
    'MM': 'br',
    'MN': 'mp',
    'MP': 'nw',
    'MQ': 'mq',
    'MR': 'mu',
    'MS': 'mj',
    'MT': 'mm',
    'MU': 'mf',
    'MV': 'xc',
    'MW': 'mw',
    'MX': 'mx',
    'MY': 'my',
    'MZ': 'mz',
    'NA': 'sx',
    'NC': 'nl',
    'NE': 'ng',
    'NF': 'nx',
    'NG': 'nr',
    'NI': 'nq',
    'NL': 'ne',
    'NO': 'no',
    'NP': 'np',
    'NR': 'nu',
    'NU': 'xh',
    'NZ': 'nz',
    'OM': 'mk',
    'PA': 'pn',
    'PE': 'pe',
    'PF': 'fp',
    'PG': 'pp',
    'PH': 'ph',
    'PK': 'pk',
    'PL': 'pl',
    'PM': 'xl',
    'PN': 'pc',
    'PR': 'pr',
    'PT': 'po',
    'PW': 'pw',
    'PY': 'py',
    'QA': 'qa',
    'RE': 're',
    'RO': 'rm',
    'RU': 'ru',
    'RW': 'rw',
    'SA': 'su',
    'SB': 'bp',
    'SC': 'se',
    'SD': 'sj',
    'SE': 'sw',
    'SG': 'si',
    'SH': 'xj',
    'SI': 'xv',
    'SK': 'xo',
    'SL': 'sl',
    'SM': 'st',
    'SN': 'sg',
    'SO': 'so',
    'SR': 'sr',
    'SS': 'sd',
    'ST': 'sf',
    'SV': 'es',
    'SX': 'sn',
    'SZ': 'sq',
    'TC': 'tc',
    'TD': 'cd',
    'TF': 'fs',
    'TG': 'tg',
    'TH': 'th',
    'TJ': 'ta',
    'TK': 'tl',
    'TL': 'em',
    'TM': 'tk',
    'TN': 'ti',
    'TO': 'to',
    'TR': 'tu',
    'TT': 'tr',
    'TV': 'tv',
    'TZ': 'tz',
    'UA': 'un',
    'UG': 'ug',
    'US': 'xxu',
    'UY': 'uy',
    'UZ': 'uz',
    'VA': 'vc',
    'VC': 'xm',
    'VE': 've',
    'VN': 'vm',
    'VU': 'nn',
    'WF': 'wf',
    'WS': 'ws',
    'XX': 'xx',
    'YE': 'ye',
    'YT': 'ot',
    'ZA': 'sa',
    'ZM': 'za',
    'ZW': 'rh',
}

unimarc = ReroIlsUnimarcOverdo()


@unimarc.over('type_and_issuance', 'leader')
@utils.ignore_value
def unimarc_type_and_issuance(self, key, value):
    """
    Get document type and mode of issuance.

    Books: LDR/6-7: am
    Journals: LDR/6-7: as
    Articles: LDR/6-7: aa + add field 773 (journal title)
    Scores: LDR/6: c|d
    Videos: LDR/6: g + 007/0: m|v
    Sounds: LDR/6: i|j
    E-books (imported from Cantook)
    """
    type = [{"main_type": "docmaintype_other"}]
    if unimarc.record_type == 'a':
        if unimarc.bib_level == 'm':
            type = [{
                "main_type": "docmaintype_book",
                "subtype": "docsubtype_other_book"
            }]
        elif unimarc.bib_level == 's':
            type = [{
                "main_type": "docmaintype_serial"
            }]
        elif unimarc.bib_level == 'a':
            type = [{
                "main_type": "docmaintype_article",
            }]
    elif unimarc.record_type in ['c', 'd']:
        type = [{
            "main_type": "docmaintype_score",
            "subtype": "docsubtype_printed_score"
        }]
    elif unimarc.record_type in ['i', 'j']:
        type = [{
            "main_type": "docmaintype_audio",
            "subtype": "docsubtype_music"
        }]
    elif unimarc.record_type == 'g':
        type = [{
            "main_type": "docmaintype_movie_series",
            "subtype": "docsubtype_movie"
        }]
        # Todo 007
    self['type'] = type

    # get the mode of issuance
    self['issuance'] = {}
    main_type = _ISSUANCE_MAIN_TYPE_PER_BIB_LEVEL.get(
        unimarc.bib_level, 'rdami:1001')
    sub_type = 'NOT_DEFINED'
    if unimarc.bib_level in _ISSUANCE_SUBTYPE_PER_BIB_LEVEL:
        sub_type = _ISSUANCE_SUBTYPE_PER_BIB_LEVEL[unimarc.bib_level]
    if unimarc.serial_type in _ISSUANCE_SUBTYPE_PER_SERIAL_TYPE:
        sub_type = _ISSUANCE_SUBTYPE_PER_SERIAL_TYPE[unimarc.serial_type]
    self['issuance'] = dict(main_type=main_type, subtype=sub_type)


@unimarc.over('identifiedBy', '^003')
@utils.ignore_value
def unimarc_bnf_id(self, key, value):
    """Get ID.

    identifier bnfID 003
    """
    identifiers = self.get('identifiedBy', [])
    if value.startswith('http://catalogue.bnf.fr/'):
        identifiers.append({
            "type": "bf:Local",
            "source": "BNF",
            "value":  value.replace('http://catalogue.bnf.fr/', '')
        })
    return identifiers


@unimarc.over('title', '^200..')
@utils.ignore_value
def unimarc_title(self, key, value):
    """Get title data.

    field 200: non repetitive
        $a : repetitive
        $e : repetitive
        $f : repetitive
        $g : repetitive
        $h : repetitive
        $i : repetitive
    field 510,512,514,515,516,517,518,519,532: repetitive
        $a : non repetitive
        $e : repetitive
        $h : repetitive
        $i : repetitive
    """
    title_list = []
    title = self.get('title', [])
    # this function will be called for each fields 200, but as we already
    # process all of them in the first run and the tittle is already build,
    # there is nothing to do if the title has already been build.
    if not title:
        language = unimarc.lang_from_101
        responsibilites = []
        for tag in ['200', '510',
                    '512', '514', '515', '516', '517', '518', '519', '532']:
            for field in unimarc.get_alt_graphic_fields(tag=tag):
                title_data = {}
                part_list = TitlePartList(
                    part_number_code='h',
                    part_name_code='i'
                )
                subfields_6 = unimarc.get_subfields(field, '6')
                subfields_7 = unimarc.get_subfields(field, '7')
                subfields_a = unimarc.get_subfields(field, 'a')
                subfields_e = unimarc.get_subfields(field, 'e')
                language_script_code = ''
                if subfields_7:
                    language_script_code = \
                        unimarc.get_language_script(subfields_7[0])
                title_type = 'bf:VariantTitle'
                if tag == '200':
                    title_type = 'bf:Title'
                elif tag == '510':
                    title_type = 'bf:ParallelTitle'
                # build title parts
                index = 1
                link = ''
                if subfields_6:
                    link = subfields_6[0]
                items = get_field_items(field['subfields'])
                for blob_key, blob_value in items:
                    if blob_key == 'a':
                        value_data = \
                            unimarc.build_value_with_alternate_graphic(
                                tag, blob_key, blob_value,
                                index, link, ',.', ':;/-=')
                        title_data['mainTitle'] = value_data
                    if blob_key == 'e':
                        value_data = \
                            unimarc.build_value_with_alternate_graphic(
                                tag, blob_key, blob_value,
                                index, link, ',.', ':;/-=')
                        title_data['subtitle'] = value_data
                    if blob_key in ['f', 'g'] and tag == '200':
                        value_data = \
                            unimarc.build_value_with_alternate_graphic(
                                tag, blob_key, blob_value,
                                index, link, ',.', ':;/-=')
                        responsibilites.append(value_data)
                    if blob_key in ['h', 'i']:
                        part_list.update_part(
                            [dict(value=blob_value)], blob_key, blob_value)
                    if blob_key != '__order__':
                        index += 1
                title_data['type'] = title_type
                the_part_list = part_list.get_part_list()
                if the_part_list:
                    title_data['part'] = the_part_list
                if title_data:
                    title_list.append(title_data)

        # extract responsibilities
        if responsibilites:
            new_responsibility = self.get('responsibilityStatement', [])
            for resp in responsibilites:
                new_responsibility.append(resp)
            self['responsibilityStatement'] = new_responsibility
    return title_list or None


@unimarc.over('part_of', '^(410|46[234])..')
@utils.for_each_value
@utils.ignore_value
def marc21_to_part_of(self, key, value):
    """Get part_of."""
    part_of = {}
    subfield_x = not_repetitive(
        unimarc.bib_id, 'unimarc', key, value, 'x', default='').strip()
    linked_pid = None
    if subfield_x:
        for pid in Document.get_document_pids_by_issn(subfield_x):
            linked_pid = pid
            break
    if linked_pid:
        part_of['document'] = {
            '$ref': f'https://ils.rero.ch/api/documents/{linked_pid}'
        }
        subfield_v = not_repetitive(
            unimarc.bib_id, 'unimarc', key, value, 'v', default='').strip()
        if subfield_v:
            part_of['numbering'] = subfield_v
        self['partOf'] = self.get('partOf', [])
        self['partOf'].append(part_of)


@unimarc.over('language', '^101')
@utils.ignore_value
def unimarc_languages(self, key, value):
    """Get languages.

    languages: 008 and 041 [$a, repetitive]
    """
    languages = utils.force_list(value.get('a'))
    to_return = []
    schema_in_bytes = resource_string(
        'rero_ils.jsonschemas',
        'common/languages-v0.0.1.json'
    )
    schema = jsonref.loads(schema_in_bytes.decode('utf8'))
    langs = schema['language']['enum']

    for language in languages:
        if language in langs:
            to_return.append({'value': language, 'type': 'bf:Language'})

    return to_return


@unimarc.over('contribution', '7[01][0123]..')
@utils.for_each_value
@utils.ignore_value
def unimarc_to_contribution(self, key, value):
    """Get contribution.

    contribution: loop:
    700 Nom de personne – Responsabilité principale
    701 Nom de personne – Autre responsabilité principale
    702 Nom de personne – Responsabilité secondaire
    710 Nom de collectivité – Responsabilité principale
    711 Nom de collectivité – Autre responsabilité principale
    712 Nom de collectivité – Responsabilité secondaire
    """
    agent = {}
    agent['preferred_name'] = ', '.join(utils.force_list(value.get('a', '')))
    agent['type'] = 'bf:Person'

    if key[:3] in ['700', '701', '702', '703']:
        if agent['preferred_name']:
            if value.get('b'):
                agent['preferred_name'] += \
                    ', ' + ', '.join(utils.force_list(value.get('b')))
        if value.get('d'):
            agent['numeration'] = value.get('d')

        if value.get('c'):
            agent['qualifier'] = value.get('c')

        if value.get('f'):
            date = utils.force_list(value.get('f'))[0]
            date = date.replace('-....', '-')
            dates = date.split('-')
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

    if key[:3] in ['710', '711', '712']:
        agent['type'] = 'bf:Organisation'
        agent['conference'] = key[3] == '1'
        if agent['preferred_name']:
            if value.get('c'):
                agent['preferred_name'] += \
                    ', ' + ', '.join(utils.force_list(value.get('c')))
        if value.get('b'):
            agent['subordinate_unit'] = utils.force_list(value.get('b'))
        if value.get('d'):
            numbering = utils.force_list(value.get('d'))[0]
            agent['numbering'] = remove_trailing_punctuation(
                numbering
            ).lstrip('(').rstrip(')')
        if value.get('e'):
            place = utils.force_list(value.get('e'))[0]
            agent['place'] = remove_trailing_punctuation(
                place
            ).lstrip('(').rstrip(')')
        if value.get('f'):
            conference_date = utils.force_list(value.get('f'))[0]
            agent['conference_date'] = remove_trailing_punctuation(
                conference_date
            ).lstrip('(').rstrip(')')
    IDREF_ROLE_CONV = {
        "070": "aut",
        "230": "cmp",
        "205": "ctb",
        "340": "edt",
        "420": "hnr",
        "440": "ill",
        "600": "pht",
        "590": "prf",
        "730": "trl",
        "080": "aui",
        "160": "bsl",
        "220": "com",
        "300": "drt",
        "430": "ilu",
        "651": "pbd",
        "350": "egr",
        "630": "pro",
        "510": "ltg",
        "365": "exp",
        "727": "dgs",
        "180": "ctg",
        "220": "com",
        "210": "cmm",
        "200": "chr",
        "110": "bnd",
        "720": "ato",
        "030": "arr",
        "020": "ann",
        "632": "adi",
        "005": "act",
        "390": "fmo",
        "545": "mus"
    }
    roles = []
    if value.get('4'):
        for role in utils.force_list(value.get('4')):
            role_conv = IDREF_ROLE_CONV.get(role)
            if role_conv:
                roles.append(role_conv)
        roles = list(set(roles))
    if not roles:
        roles = ['aut']

    return {
        'agent': agent,
        'role': roles
    }


@unimarc.over('editionStatement', '^205..')
@utils.for_each_value
@utils.ignore_value
def unimarc_to_edition_statement(self, key, value):
    """Get edition statement data.

    editionDesignation: 205 [$a non repetitive] (without trailing ponctuation)
    responsibility: 205 [$f non repetitive]
    """
    edition_data = {}
    subfields_a = utils.force_list(value.get('a'))
    if subfields_a:
        subfield_a = subfields_a[0]
        edition_data['editionDesignation'] = [{'value': subfield_a}]
    subfields_f = utils.force_list(value.get('f'))
    if subfields_f:
        subfield_f = subfields_f[0]
        edition_data['responsibility'] = [{'value': subfield_f}]
    return edition_data or None


@unimarc.over('provisionActivity', '^21[04]..')
@utils.for_each_value
@utils.ignore_value
def unimarc_publishers_provision_activity_publication(self, key, value):
    """Get provision activity dates."""
    def build_place_or_agent_data(code, label, index):
        type_per_code = {
            'a': 'bf:Place',
            'c': 'bf:Agent',
            'e': 'bf:Place',
            'g': 'bf:Agent'
        }
        place_or_agent_data = {
            'type': type_per_code[code],
            'label': [{'value': remove_trailing_punctuation(label)}]
        }
        return place_or_agent_data

    def build_place():
        # country from 102
        place = {}
        field_102 = unimarc.get_fields(tag='102')
        if field_102:
            field_102 = field_102[0]
            country_codes = unimarc.get_subfields(field_102, 'a')
            if country_codes:
                country = _COUNTRY_UNIMARC_MARC21.get(country_codes[0])
                if country:
                    place['country'] = country
                    place['type'] = 'bf:Place'
        return place

    # only take 214 if exists
    publication = {}
    ind2 = key[4]
    type_per_ind2 = {
        ' ': 'bf:Publication',
        '_': 'bf:Publication',
        '0': 'bf:Publication',
        '1': 'bf:Production',
        '2': 'bf:Distribution',
        '3': 'bf:Manufacture'
    }
    if ind2 == '4':
        field_d = value.get('d')
        if field_d:
            field_d = utils.force_list(field_d)[0]
            copyright_date = self.get('copyrightDate', [])
            if field_d[0] == 'P':
                copyright_date.append('℗ ' + field_d[2:])
            else:
                copyright_date.append('© ' + field_d)
            self['copyrightDate'] = copyright_date
    else:
        start_date = None
        end_date = None
        place = build_place()
        field_100 = unimarc.get_fields('100')
        if field_100:
            field_100 = field_100[0]
            subfield_a = unimarc.get_subfields(field_100, 'a')
            if subfield_a:
                subfield_a = subfield_a[0]
                start_date = make_year(subfield_a[9:13])
                end_date = make_year(subfield_a[14:17])

        if key[:3] == '210':
            if not unimarc.get_fields(tag='214'):
                publications = self.setdefault('provisionActivity', [])
                items = get_field_items(value)
                index = 1
                publication = {}
                statement = []
                for blob_key, blob_value in items:
                    if blob_key in ('a', 'c'):
                        type = 'bf:Publication'
                        if index == 1:
                            old_type = 'bf:Publication'
                            publication = {'type': type, 'statement': []}
                        if type != old_type:
                            subfields_h = utils.force_list(value.get('h'))
                            publication['statement'] = statement
                            if subfields_h:
                                subfields_h = subfields_h[0]
                                publication['statement'].append({
                                    'label': [{'value': subfields_h}],
                                    'type': 'Date'
                                })
                            statement = []
                            publications.append(publication)
                            publication = {
                                'type': type,
                                'statement': [],
                            }
                            old_type = type

                        place_or_agent_data = build_place_or_agent_data(
                            blob_key, blob_value, index)
                        statement.append(place_or_agent_data)
                    if blob_key in ('e', 'g'):
                        type = 'bf:Manufacture'
                        if index == 1:
                            old_type = 'bf:Manufacture'
                            publication = {'type': type, 'statement': []}
                        if type != old_type:
                            subfields_d = utils.force_list(value.get('d'))
                            publication['statement'] = statement
                            if subfields_d:
                                subfield_d = subfields_d[0]
                                publication['statement'].append({
                                    'label': [{'value': subfield_d}],
                                    'type': 'Date'
                                })
                            if start_date:
                                publication['startDate'] = start_date
                            if end_date:
                                publication['endDate'] = end_date
                            if place:
                                publication['place'] = [place]
                            statement = []
                            publications.append(publication)
                            publication = {
                                'type': type,
                                'statement': [],
                            }
                            old_type = type
                        place_or_agent_data = build_place_or_agent_data(
                            blob_key, blob_value, index)
                        statement.append(place_or_agent_data)
                    if blob_key != '__order__':
                        index += 1
                if statement:
                    publication = {
                        'type': type,
                        'statement': statement,
                    }
                    date_subfield = 'd'
                    if type == 'bf:Manufacture':
                        date_subfield = 'h'
                    subfields = utils.force_list(value.get(date_subfield))
                    if subfields:
                        subfield = subfields[0]
                        publication['statement'].append({
                            'label': [{'value': subfield}],
                            'type': 'Date'
                        })
                    if publication['type'] == 'bf:Publication':
                        if start_date:
                            publication['startDate'] = start_date
                        if end_date:
                            publication['endDate'] = end_date
                        if place:
                            publication['place'] = [place]

                    publications.append(publication)
                if publications:
                    self['provisionActivity'] = publications
                return None
        else:
            publication = {
                'type': type_per_ind2[ind2],
                'statement': [],
            }
            statement = []
            items = get_field_items(value)
            index = 1
            for blob_key, blob_value in items:
                if blob_key in ('a', 'c'):
                    place_or_agent_data = build_place_or_agent_data(
                        blob_key, blob_value, index)
                    statement.append(place_or_agent_data)
                if blob_key != '__order__':
                    index += 1
            if statement:
                publication['statement'] = statement
            if publication['type'] == 'bf:Publication':
                if place:
                    publication['place'] = [place]

            subfields_d = utils.force_list(value.get('d'))
            if subfields_d:
                subfield_d = subfields_d[0]
                publication['statement'].append({
                    'label': [{'value': subfield_d}],
                    'type': 'Date'
                })
            if publication['type'] == 'bf:Publication':
                if start_date:
                    publication['startDate'] = start_date
                if end_date:
                    publication['endDate'] = end_date

    if not publication.get('statement'):
        publication = None
    return publication or None


@unimarc.over('extent', '^215..')
@utils.ignore_value
def unimarc_description(self, key, value):
    """Get physical description.

    Extract:
    - extent
    - duration
    - colorContent
    - productionMethod
    - illustrativeContent
    - note of type otherPhysicalDetails and accompanyingMaterial
    - book_formats
    - dimensions

    215 [$a repetitive (the first one if many)]: extent, duration:
    215 [$c non repetitive]: colorContent, productionMethod,
        illustrativeContent, note of type otherPhysicalDetails
    215 [$d repetitive]: dimensions, book_formats
    215 [$e repetitive]: accompanying material note
    """
    unimarc.extract_description_from_marc_field(key, value, self)
    return None


@unimarc.over('series', '^225..')
@utils.for_each_value
@utils.ignore_value
def unimarc_series_statement(self, key, value):
    """Get seriesStatement.

    series.name: [225$a repetitive]
    series.number: [225$v repetitive]
    """
    # normalize the value by building couple of $a, $v
    # $v can be missing  in a couple
    items = get_field_items(value)
    new_data = []
    fist_a_value = None
    pending_v_values = []
    subfield_selection = {'a', 'e', 'i', 'v'}
    for blob_key, blob_value in items:
        if blob_key in subfield_selection:
            if blob_key == 'a':
                fist_a_value = blob_value
                try:
                    subfield_selection.remove('a')
                except KeyError:
                    pass
            elif blob_key == 'e':
                fist_a_value += ': ' + blob_value
            elif blob_key == 'i':
                # we keep on the $e associeted to the $a
                try:
                    subfield_selection.remove('e')
                except KeyError:
                    pass
                if fist_a_value:
                    new_data.append(('a', fist_a_value))
                    for v_value in pending_v_values:
                        new_data.append(('v', v_value))
                    fist_a_value = None
                    pending_v_values = []
                new_data.append(('a', blob_value))
            elif blob_key == 'v':
                pending_v_values.append(blob_value)
    if fist_a_value:
        new_data.append(('a', fist_a_value))
    for v_value in pending_v_values:
        new_data.append(('v', v_value))

    new_value = GroupableOrderedDict(tuple(new_data))
    unimarc.extract_series_statement_from_marc_field(key, new_value, self)


@unimarc.over('summary', '^330..')
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
                summary_data = unimarc.build_value_with_alternate_graphic(
                    '520', blob_key, blob_value, index, link, ',.', ':;/-=')
            else:
                summary_data = blob_value
            if summary_data:
                summary[key_per_code[blob_key]] = summary_data
        if blob_key != '__order__':
            index += 1
    return summary or None


@unimarc.over('identifiedBy', '^073..')
@utils.ignore_value
def unimarc_identifier_isbn(self, key, value):
    """Get identifier isbn.

    identifiers:isbn: 010$a
    """
    from isbnlib import EAN13
    identifiers = self.get('identifiedBy', [])
    if value.get('a'):
        ean = {
            "type": "bf:Ean",
            "value": value.get('a')
        }
        check_ean = EAN13(value.get('a'))
        # Do we have to check also cancelled status?
        if not check_ean:
            ean['status'] = 'invalid'
        identifiers.append(ean)
    return identifiers


@unimarc.over('note', '^300..')
@utils.for_each_value
@utils.ignore_value
def unimarc_notes(self, key, value):
    """Get  notes.

    note: [300$a repetitive]
    """
    add_note(
        dict(
            noteType='general',
            label=value.get('a', '')
        ),
        self)

    return None


@unimarc.over('subjects', '^6((0[0-9])|(1[0-7]))..')
@utils.for_each_value
@utils.ignore_value
def unimarc_subjects(self, key, value):
    """Get subjects.

    subjects: 6xx [duplicates could exist between several vocabularies,
        if possible deduplicate]
    """
    to_return = ''
    if value.get('a'):
        to_return = value.get('a')
    if value.get('b'):
        to_return += ', ' + ', '.join(utils.force_list(value.get('b')))
    if value.get('d'):
        to_return += ' ' + ' '.join(utils.force_list(value.get('d')))
    if value.get('c'):
        to_return += ', ' + ', '.join(utils.force_list(value.get('c')))
    if value.get('f'):
        to_return += ', ' + ', '.join(utils.force_list(value.get('f')))
    if to_return:
        return {
            'type': "bf:Topic",
            'term': to_return
        }


@unimarc.over('electronicLocator', '^8564.')
@utils.for_each_value
@utils.ignore_value
def marc21_to_electronicLocator_from_field_856(self, key, value):
    """Get electronicLocator from field 856."""
    electronic_locator = None
    if value.get('u'):
        electronic_locator = {
            'url': value.get('u'),
            'type': 'resource'
        }
    return electronic_locator
