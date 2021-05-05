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

"""Dojson utils."""

import re
import sys
import traceback
from copy import deepcopy

import click
from dojson import Overdo, utils

_UNIMARC_LANGUAGES_SCRIPTS = {
    'ba': 'latn',  # Latin
    'ca': 'cyrl',  # Cyrillic
    'da': 'jpan',  # Japanese - undefined writing
    'db': 'hani',  # Japanese - Kanji
    'dc': 'hrkt',  # Japanese - Kana
    'ea': 'hani',  # Chinese characters (Chinese, Japanese, Korean)
    'fa': 'arab',  # Arabic
    'ga': 'grek',  # Greek
    'ha': 'hebr',  # Hebrew
    'ia': 'thai',  # Thai
    'ja': 'deva',  # devanagari
    'ka': 'kore',  # Korean
    'la': 'taml',  # Tamil
    'ma': 'geor',  # Georgian
    'mb': 'armn',  # Armenian
    'zz': 'zyyy'   # other
}

_LANGUAGES_SCRIPTS = {
    'armn': ('arm', ),
    'arab': ('ara', 'per'),
    'cyrl': ('bel', 'chu', 'mac', 'rus', 'srp', 'ukr'),
    'deva': ('awa', 'bho', 'bra', 'doi', 'hin', 'kas', 'kok', 'mag', 'mai',
             'mar', 'mun', 'nep', 'pli', 'pra', 'raj', 'san', 'sat', 'snd'),
    'geor': ('geo', ),
    'grek': ('grc', 'gre'),
    'hani': ('chi', 'jpn'),
    'hebr': ('heb', 'lad', 'yid'),
    'hrkt': ('jpn', ),
    'jpan': ('jpn', ),
    'kore': ('kor', ),
    'taml': ('tam', ),
    'thai': ('tha', ),
    'zyyy': ('chi', )
}

_SCRIPT_PER_LANG_ASIA = {
    'jpn': 'jpan',
    'kor': 'kore',
    'chi': 'hani'
}

_SCRIPT_PER_LANG_NOT_ASIA = {
    'arm': 'armn',
    'geo': 'geor',
    'gre': 'grek',
    'grc': 'grek',
    'ara': 'arab',
    'per': 'arab',
    'bel': 'cyrl',
    'rus': 'cyrl',
    'mac': 'cyrl',
    'srp': 'cyrl',
    'tha': 'thai',
    'ukr': 'cyrl',
    'chu': 'cyrl',
    'yid': 'hebr',
    'heb': 'hebr',
    'lad': 'hebr',
    'chi': 'hani'
}

_SCRIPT_PER_CODE = {
    '(S': 'grek',
    '(3': 'arab',
    '(B': 'latn',
    '(N': 'cyrl',
    '(2': 'hebr'
}

_ILLUSTRATIVE_CONTENT_REGEXP = {
    'illustrations':
        re.compile(
            r'ill?(\.|\s|:|,|;|s\.|us.*)|ill$|iil|^il$|^il(\.)|'
            r'fig(\.|\s|,|ur|s)|fig$|abb(\.|\s|,|ild)|abb$|bild|zeichn|'
            r'front(\.|is|esp|\s|,|s)|front$|dessin',
            re.IGNORECASE),
    'maps':
        re.compile(
            r'cartes?|cartogra|cartin|cart\.|carta(\s|s)|carta$|maps?|kart',
            re.IGNORECASE),
    'portraits':
        re.compile(r'port(\.|r|\s|s)|portr$|ritr', re.IGNORECASE),
    'graphs':
        re.compile(r'gra(ph|f)(\.)|^gra(ph|f)|\sgra(ph|f)|diag',
                   re.IGNORECASE),
    'photographs':
        re.compile(r'(f|ph)oto(g|s|\s|,|typ|\.)|(f|ph)oto^', re.IGNORECASE),
    'facsimiles': re.compile(r'fa(c|k)', re.IGNORECASE),
    'coats of arms': re.compile(r'armoirie|arms|wappe|stemm', re.IGNORECASE),
    'genealogical tables': re.compile(r'genea|généa', re.IGNORECASE),
    'plans': re.compile(r'plan[^c]|plan$|piant', re.IGNORECASE),
    'forms': re.compile(r'form[^a|e]|modul', re.IGNORECASE),
    'illuminations':
        re.compile(r'enlum|illum|miniatur|buchmale', re.IGNORECASE),
    'samples': re.compile(r'sample|échant|muster|campion', re.IGNORECASE)
}

_PRODUCTION_METHOD_FROM_EXTENT_AND_PHYSICAL_DETAILS = {
    'rdapm:1001': re.compile(r'blueline', re.IGNORECASE),
    'rdapm:1002': re.compile(r'cyano|blaudr|bluepr', re.IGNORECASE),
    'rdapm:1003': re.compile(r'collot|lichtdr|(ph|f)otot', re.IGNORECASE),
    'rdapm:1004': re.compile(r'daguerr', re.IGNORECASE),
    'rdapm:1005': re.compile(r'stich|engrav|grav', re.IGNORECASE),
    'rdapm:1006': re.compile(r'eauforte|radier|etch', re.IGNORECASE),
    'rdapm:1007': re.compile(r'litho', re.IGNORECASE),
    'rdapm:1008': re.compile(r'(ph|f)oto[ck]o', re.IGNORECASE),
    'rdapm:1009': re.compile(r'photograv|fotograv|photoengrav', re.IGNORECASE),
    # The rdapm:1010  extraction is done only from PHYSICAL_DETAILS by the code
    # 'rdapm:1010': r'impr|druck|print|offset|s[ée]riegr'
    'rdapm:1011': re.compile(r'white print',  re.IGNORECASE),
    'rdapm:1012': re.compile(r'grav.+?sur bois|holzschn|woodc', re.IGNORECASE),
    'rdapm:1014': re.compile(r'hélio|helio', re.IGNORECASE),
    'rdapm:1015': re.compile(r'brûl|einbren|burn', re.IGNORECASE),
    'rdapm:1016': re.compile(r'inscript|inscrib', re.IGNORECASE),
    'rdapm:1017': re.compile(r'estamp|stempel|stamping|lino', re.IGNORECASE),
    'rdapm:1018': re.compile(r'emboss|präg', re.IGNORECASE),
    'rdapm:1019': re.compile(r'point rigide|solid dot', re.IGNORECASE),
    'rdapm:1020': re.compile(r'thermog|schwell|swell|minolta', re.IGNORECASE),
    'rdapm:1021': re.compile(r'thermof|va[ck]uum|moul.+?vide', re.IGNORECASE)
}

_COLOR_CONTENT_REGEXP = {
    # monochrom
    'rdacc:1002': re.compile(
            r'noir|black|schwarz|nero|n\.\set|schw|b\&w|'
            r'b\/n|s\/w|^n\set\sb|\sn\set\sb',
            re.IGNORECASE
        ),

    # polychrome
    'rdacc:1003': re.compile(
            r'cou?l(\.|,|eur|ou?r|\s)|cou?l$|farb',
            re.IGNORECASE
        ),
}

_CANTON = [
    'ag', 'ai', 'ar', 'be', 'bl', 'bs', 'fr', 'ge', 'gl', 'gr', 'ju', 'lu',
    'ne', 'nw', 'ow', 'sg', 'sh', 'so', 'sz', 'tg', 'ti', 'ur', 'vd', 'vs',
    'zg', 'zh'
]

# field 336 mapping
_CONTENT_TYPE_MAPPING = {
    'cri': 'rdaco:1002',
    'crm': 'rdaco:1003',
    'crt': 'rdaco:1004',
    'crn': 'rdaco:1005',
    'cod': 'rdaco:1007',
    'crd': 'rdaco:1001',
    'crf': 'rdaco:1006',
    'tdi': 'rdaco:1023',
    'tdm': 'rdaco:1022',
    'sti': 'rdaco:1014',
    'tci': 'rdaco:1015',
    'prm': 'rdaco:1011',
    'ntv': 'rdaco:1009',
    'tcn': 'rdaco:1017',
    'tdf': 'rdaco:1021',
    'tcf': 'rdaco:1019',
    'ntm': 'rdaco:1010',
    'tcm': 'rdaco:1016',
    'cop': 'rdaco:1008',
    'snd': 'rdaco:1012',
    'txt': 'rdaco:1020',
    'tct': 'rdaco:1018',
    'spw': 'rdaco:1013',
    'xxx': 'other'
}

# field 337 $b and field 338 (first char of $b) mapping
_MEDIA_TYPE_MAPPING = {
    's': 'rdamt:1001',
    'h': 'rdamt:1002',
    'c': 'rdamt:1003',
    'p': 'rdamt:1004',
    'g': 'rdamt:1005',
    'm': 'rdamt:1005',  # only in 338 (first char of $b)
    'e': 'rdamt:1006',
    'n': 'rdamt:1007',
    'v': 'rdamt:1008',
    'x': 'other',
    'z': 'other'  # only in 338 (first char of $b)
}

# field 338 mapping
_CARRIER_TYPE_MAPPING = {
    'zu': 'unspecified',
    'sg': 'rdact:1002',
    'se': 'rdact:1003',
    'sd': 'rdact:1004',
    'si': 'rdact:1005',
    'sq': 'rdact:1006',
    'ss': 'rdact:1007',
    'st': 'rdact:1008',
    'sw': 'rdact:1071',
    'sz': 'other',
    'ha': 'rdact:1021',
    'he': 'rdact:1022',
    'hf': 'rdact:1023',
    'hb': 'rdact:1024',
    'hc': 'rdact:1025',
    'hd': 'rdact:1026',
    'hh': 'rdact:1027',
    'hg': 'rdact:1028',
    'hj': 'rdact:1056',
    'hz': 'other',
    'ck': 'rdact:1011',
    'cb': 'rdact:1012',
    'cd': 'rdact:1013',
    'ce': 'rdact:1014',
    'ca': 'rdact:1015',
    'cf': 'rdact:1016',
    'ch': 'rdact:1017',
    'cr': 'rdact:1018',
    'cz': 'other',
    'pp': 'rdact:1030',
    'pz': 'other',
    'mc': 'rdact:1032',
    'mf': 'rdact:1033',
    'mr': 'rdact:1034',
    'gd': 'rdact:1035',
    'gf': 'rdact:1036',
    'gc': 'rdact:1037',
    'gt': 'rdact:1039',
    'gs': 'rdact:1040',
    'mo': 'rdact:1069',
    'mz': 'other',
    'eh': 'rdact:1042',
    'es': 'rdact:1043',
    'ez': 'other',
    'no': 'rdact:1045',
    'nn': 'rdact:1046',
    'na': 'rdact:1047',
    'nb': 'rdact:1048',
    'nc': 'rdact:1049',
    'nr': 'rdact:1059',
    'nz': 'other',
    'vc': 'rdact:1051',
    'vf': 'rdact:1052',
    'vr': 'rdact:1053',
    'vd': 'rdact:1060',
    'vz': 'other'
}


_ENCODING_LEVEL_MAPPING = {
    ' ': 'Full level',
    '1': 'Full level, material not examined',
    '2': 'Less-than-full level, material not examined',
    '3': 'Abbreviated level',
    '4': 'Core level',
    '5': 'Partial (preliminary) level',
    '7': 'Minimal level',
    '8': 'Prepublication level',
    'u': 'Unknown',
    'z': 'Not applicable'
}


def error_print(*args):
    """Error printing to sdtout."""
    msg = ''
    for arg in args:
        msg += str(arg) + '\t'
    msg.strip()
    click.echo(msg)
    sys.stdout.flush()


def make_year(date):
    """Test if string is integer and between 1000 to 9999."""
    try:
        int_date = int(date)
        if int_date >= 1000 and int_date < 9999:
            return int_date
    except Exception:
        pass
    return None


def not_repetitive(bibid, reroid, key, value, subfield, default=None):
    """Get the first value if the value is a list or tuple."""
    if default is None:
        data = value.get(subfield)
    else:
        data = value.get(subfield, default)
    if isinstance(data, (list, tuple)):
        error_print('WARNING NOT REPETITIVE:', bibid, reroid, key, subfield,
                    value)
        data = data[0]
    return data


def get_field_link_data(value):
    """Get field link data from subfield $6."""
    subfield_6 = value.get('6', '')
    tag_link = subfield_6.split('-')
    link = ''
    if len(tag_link) == 2:
        link = tag_link[1]
    return tag_link, link


def get_field_items(value):
    """Get field items."""
    if isinstance(value, utils.GroupableOrderedDict):
        return value.iteritems(repeated=True)
    else:
        return utils.iteritems(value)


def build_string_from_subfields(value, subfield_selection, separator=' '):
    """Build a string parsing the selected subfields in order."""
    items = get_field_items(value)
    parts = [value for key, value in items if key in subfield_selection]
    return separator.join(parts)


def remove_trailing_punctuation(
        data,
        punctuation=',',
        spaced_punctuation=':;/-'):
    """Remove trailing punctuation from data.

    :param data: string to process
    :type data: str
    :param punctuation: punctuation characters to be removed
        (preceded by a space or not)
    :type punctuation: str
    :param spaced_punctuation: punctuation characters needing
        one or more preceding space(s) in order to be removed.
    :type spaced_punctuation: str

    :return: the data string with specific trailing punctuation removed
    :rtype: list
    """
    # escape chars: .[]^-
    if punctuation:
        punctuation = re.sub(r'([\.\[\]\^\\-])', r'\\\1', punctuation)
    if spaced_punctuation:
        spaced_punctuation = \
            re.sub(r'([\.\[\]\^\\-])', r'\\\1', spaced_punctuation)

    return re.sub(
        r'([{0}]|\s+[{1}])$'.format(punctuation, spaced_punctuation),
        '',
        data.rstrip()).rstrip()


def add_note(new_note, data):
    """Add a new note to the data avoiding duplicate notes.

    :param new_note: the note object to add
    :type new_note: object
    :param data: the object data on which the new note will be added
    :type data: object
    """
    def note_key(note):
        """Generate a note key by concataning the noteType and the label.

        :param note: the note objet for which the key is to be generated
        :type note: object
        :return: the note key (concatenation of the noteType and the label)
        :rtype: str
        """
        return '|'.join((note['noteType'], note['label']))

    notes = data.get('note', [])
    note_set = set()
    for existing_note in notes:
        note_set.add(note_key(existing_note))
    if new_note and new_note.get('label') and new_note.get('noteType'):
        new_note_key = note_key(new_note)
        if new_note_key not in note_set:
            notes.append(new_note)
        data['note'] = notes


def add_data_and_sort_list(key, new_data, data):
    """Add strings to data[keys] list avoiding duplicates (the list is sorted).

    :param key: the key of object to add
    :type key: str
    :param new_data: the new_data (list of string) to add to data[key]
    :type new_data: list
    :param data: the object data on which the new data will be added
    :type data: object
    """
    existing_data = data.get(key, [])
    if new_data:
        new_set = set(existing_data)
        for value_data in new_data:
            new_set.add(value_data)
        data[key] = sorted(list(new_set))


def join_alternate_graphic_data(alt_gr_1, alt_gr_2, join_str):
    """
    Build the alternate graphical data by joining the alt_gr strings.

    The given join_str id used for joining the strings.

    :param alt_gr_1: the alternate graphic 1
    :type alt_gr_1: array
    :param alt_gr_2: the alternate graphic 2
    :type alt_gr_12: array
    :param join_str: the string used as separator of concatenated strings
    :type join_str: str
    :return: atl_gr structure with joined strings from alt_gr_1 and alt_gr_2
    :rtype: list
    """
    new_alt_gr_data = []
    for idx, data in enumerate(alt_gr_1):
        new_data = deepcopy(data)
        try:
            str_to_join = alt_gr_2[idx]['value']
            if str_to_join:
                new_data['value'] = \
                    join_str.join((new_data['value'], str_to_join))
        except Exception as err:
            pass
        new_alt_gr_data.append(new_data)
    return new_alt_gr_data


class BookFormatExtraction(object):
    """Extract book formats from a marc subfield data.

    The regular expression patterns needed to extract book formats are build by
    the constructor.
    The method 'extract_book_formats_from' is provided for extract book formats
    from a given marc subfield data.
    """

    def __init__(self):
        """Constructor method.

        The regular expression patterns needed to extract book formats are
        build by this constructor.
        """
        self._format_values = \
            (1, 2, 4, 8, 12, 16, 18, 24, 32, 36, 48, 64, 72, 96, 128)
        self._book_format_code_and_regexp = {}
        self._specific_for_1248 = {
            1:    'plano',
            2:    r'fol[i.\s°⁰)]|fol',
            4:    'quarto',
            8:    'octavo'
        }

        def _buid_regexp(value):
            """Build regular expression pattern for the given value.

            :param value: format (1,2,4,8,12,16,18,24,32,36,48,64,72,96,128)
            :type value: int
            :return: an expression pattern according to the given value
            :rtype: str
            """
            # generic regexp valid for all values
            regexp = \
                r'(^|[^\d]){val}\s?[°⁰]|in(-|-gr\.)*\s*{val}($|[^\d])'.format(
                    val=value)
            # add specific value regexp
            if value in self._specific_for_1248:
                regexp = '|'.join([regexp, self._specific_for_1248[value]])
            else:
                additional = r'[^\d]{val}mo|^{val}mo'.format(val=value)
                regexp = '|'.join([regexp, additional])
            return '({regexp})'.format(regexp=regexp)

        def _populate_regexp():
            """Populate all the expression patterns."""
            for value in self._format_values:
                self._book_format_code_and_regexp[value] = {}
                format_code = 'in-plano'
                if value > 1:
                    format_code = '{val}º'.format(val=value)
                self._book_format_code_and_regexp[value]['code'] = format_code
                self._book_format_code_and_regexp[value]['regexp'] = \
                    re.compile(_buid_regexp(value), re.IGNORECASE)

        _populate_regexp()

    def extract_book_formats_from(self, subfield_data):
        """Extract book formats from a marc subfield data.

        :param subfield_data: marc subfield data source for format extraction
        :type subfield_data: str
        :return: a list of book formats
        :rtype: list
        """
        book_formats = []
        for value in self._format_values:
            regexp = self._book_format_code_and_regexp[value]['regexp']
            if regexp.search(subfield_data):
                book_formats.append(
                    self._book_format_code_and_regexp[value]['code'])
        return book_formats


class ReroIlsOverdo(Overdo):
    """Specialized Overdo.

    The purpose of this class is to store the blob record in order to
    have access to all the record fields during the Overdo processing.
    This class provide also record field manipulation functions.
    """

    _blob_record = None
    leader = None
    record_type = ''  # LDR 06
    bib_level = '?'  # LDR 07
    extract_description_subfield = None
    extract_series_statement_subfield = None

    def __init__(self, bases=None, entry_point_group=None):
        """Reroilsoverdo init."""
        super().__init__(
            bases=bases, entry_point_group=entry_point_group)

    def do(self, blob, ignore_missing=True, exception_handlers=None):
        """Translate blob values and instantiate new model instance."""
        self._blob_record = blob
        self.leader = blob.get('leader', '')
        if self.leader:
            self.record_type = self.leader[6]  # LDR 06
            self.bib_level = self.leader[7]  # LDR 07

        result = super().do(
            blob,
            ignore_missing=ignore_missing,
            exception_handlers=exception_handlers
        )
        return result

    def get_fields(self, tag=None):
        """Get all fields having the given tag value."""
        fields = []
        items = get_field_items(self._blob_record)
        for blob_key, blob_value in items:
            field_data = {}
            tag_value = blob_key[0:3]
            if (tag_value == tag) or not tag:
                field_data['tag'] = tag_value
                if len(blob_key) == 3:  # if control field
                    field_data['data'] = blob_value.rstrip()
                else:
                    field_data['ind1'] = blob_key[3:4]
                    field_data['ind2'] = blob_key[4:5]
                    field_data['subfields'] = blob_value
                fields.append(field_data)
        return fields

    def get_control_field_data(self, field):
        """Get control fields data."""
        field_data = None
        if int(field['tag']) < 10:
            field_data = field['data']
        else:
            raise ValueError('control field expected (tag < 01x)')
        return field_data

    def get_subfields(self, field, code=None):
        """Get all subfields having the given subfield code value."""
        subfields = []
        if int(field['tag']) >= 10:
            items = get_field_items(field['subfields'])
            for subfield_code, subfield_data in items:
                if (subfield_code == code) or not code:
                    subfields.append(subfield_data)
        else:
            raise ValueError('data field expected (tag >= 01x)')
        return subfields

    def build_value_with_alternate_graphic(
            self, tag, code, label, index, link,
            punct=None, spaced_punct=None):
        """
        Build the data structure for alternate graphical representation.

        :param tag: the marc field tag
        :param code: contains the subfield code. Used for debug only
        :param label: the subfield data value
        :param index: the subfield index position in the field
        :param link: the link code to the alternate graphic field 880
        :param punct: punctuation chars to remove i.e. ',.'
        :param spaced_punct: punctuation chars preceded by a space to remove
        :return: a list of 1 value, or 2 values if alternate graphical exists
        :rtype: list

        Example of return value:
        [
            {
                "value": "B.I. Bursov"
            },
            {
                "value": "Б.И. Бурсов",
                "language": "rus-cyrl"
            }
        ]
        """
        def clean_punctuation(value, punct, spaced_punct):
            return remove_trailing_punctuation(
                value,
                punctuation=punct,
                spaced_punctuation=spaced_punct)

        # build_value_with_alternate_graphic starts here

        data = []
        value = clean_punctuation(label, punct, spaced_punct).strip()
        if value:
            data = [{'value': value}]
        else:
            error_print('WARNING NO VALUE:', self.bib_id, self.rero_id, tag,
                        code, label)
        try:
            alt_gr = self.alternate_graphic[tag][link]
            subfield = self.get_subfields(alt_gr['field'])[index]
            data.append({
                'value': clean_punctuation(subfield, punct, spaced_punct),
                'language': self.get_language_script(alt_gr['script'])
            })
        except Exception as err:
            pass
        return data or None

    def extract_description_from_marc_field(self, key, value, data):
        """Extract the physical descriptions data from marc field data.

        This function automatically selects the subfield codes according to
        the Marc21 or Unimarc format. The extracted data are:
        - productionMethod
        - extent
        - bookFormat
        - dimensions
        - physical_detail
        - colorContent
        - duration
        - illustrativeContent
        - otherPhysicalDetails and accompanyingMaterial note

        :param key: the field tag and indicators
        :type key: str
        :param value: the subfields data
        :type value: object
        :param data: the object data on which the extracted data will be added
        :type data: object
        """
        # extract production_method from extent and physical_details
        extent_and_physical_detail_data = []
        extent = []
        physical_details = []
        physical_details_str = ''
        if value.get('a'):
            extent = utils.force_list(value.get('a', []))[0]
            extent_and_physical_detail_data.append(extent)
            data['extent'] = remove_trailing_punctuation(
                data=extent,
                punctuation=':;',
                spaced_punctuation=':;'
            )
            # extract the duration
            regexp = re.compile(
                r'(\((\[?{circa_env}\]?\s*{hour_min}.*?)\))|'
                r'(\[({circa_env}\s*{hour_min}.*?)\])'.format(
                        circa_env=r'\s*(ca\.?|env\.?)?\s*\d+',
                        hour_min=r'(h|St(d|\.|u)|[mM]in)'),
                re.IGNORECASE)
            match = regexp.search(extent)
            if match and match.group(1):
                duration = match.group(1).strip('()')
                add_data_and_sort_list('duration', [duration], data)

        # note_list = data.get('note', [])
        # intital_note_count = len(note_list)
        subfield_code = self.extract_description_subfield['physical_detail']
        for physical_detail in utils.force_list(value.get(subfield_code, [])):
            physical_detail = remove_trailing_punctuation(
                                    physical_detail, ':;', ':;')
            physical_details.append(physical_detail)
            extent_and_physical_detail_data.append(physical_detail)
            # to avoid empty note after removing punctuation
            if physical_detail:
                add_note(
                    dict(
                        noteType='otherPhysicalDetails',
                        label=physical_detail
                    ),
                    data)

        physical_details_str = '|'.join(physical_details)
        extent_and_physical_detail_str = \
            '|'.join(extent_and_physical_detail_data)

        color_content_set = set()
        for key in _COLOR_CONTENT_REGEXP:
            regexp = _COLOR_CONTENT_REGEXP[key]
            if regexp.search(physical_details_str):
                color_content_set.add(key)
        add_data_and_sort_list('colorContent', color_content_set, data)

        production_method_set = set()
        for key in _PRODUCTION_METHOD_FROM_EXTENT_AND_PHYSICAL_DETAILS:
            regexp = _PRODUCTION_METHOD_FROM_EXTENT_AND_PHYSICAL_DETAILS[key]
            if regexp.search(extent_and_physical_detail_str):
                production_method_set.add(key)

        # extract build illustrativeContent data
        # remove 'couv. ill' and the extra '|' resulting of the remove
        physical_detail_ill_str = \
            re.sub(r'couv\. ill', '', physical_details_str)
        physical_detail_ill_str = \
            re.sub(r'\|\||^\||\|$', '', physical_detail_ill_str)

        illustration_set = set()
        for key in _ILLUSTRATIVE_CONTENT_REGEXP:
            regexp = _ILLUSTRATIVE_CONTENT_REGEXP[key]
            if regexp.search(physical_detail_ill_str):
                illustration_set.add(key)
        add_data_and_sort_list('illustrativeContent', illustration_set, data)

        # remove 'rdapm:1005' if specific production_method exists
        if ('rdapm:1005') in production_method_set:
            del_set = \
                set(('rdapm:1009', 'rdapm:1012', 'rdapm:1014', 'rdapm:1016'))
            if production_method_set.intersection(del_set):
                production_method_set.remove('rdapm:1005')

        # extract production_method from physical_details only
        if re.search(
                r'impr|druck|print|offset|s[ée]riegr',
                physical_details_str,
                re.IGNORECASE):
            production_method_set.add('rdapm:1010')

        # build productionMethod data
        add_data_and_sort_list('productionMethod', production_method_set, data)

        # extract book_format from $c
        book_formats = []
        tool = BookFormatExtraction()
        subfield_code = self.extract_description_subfield['book_format']
        for dimension in utils.force_list(value.get(subfield_code, [])):
            formats = tool.extract_book_formats_from(dimension)
            for book_format in formats:
                book_formats.append(book_format)
            dim = remove_trailing_punctuation(
                data=dimension.rstrip(),
                punctuation='+,:;&'
            )
            if dim:
                add_data_and_sort_list(
                    'dimensions', utils.force_list(dim), data)
        add_data_and_sort_list('bookFormat', book_formats, data)

        # extract accompanyingMaterial note from $e
        if value.get('e'):
            material_notes = []
            if type(self) == ReroIlsMarc21Overdo:
                material_note = utils.force_list(value.get('e', []))[0]
                material_notes = material_note.split('+')
            elif type(self) == ReroIlsUnimarcOverdo:
                material_notes = utils.force_list(value.get('e', []))
            for material_note in material_notes:
                if material_note:
                    add_note(
                        dict(
                            noteType='accompanyingMaterial',
                            label=material_note.strip()
                        ),
                        data)

    def extract_series_statement_from_marc_field(self, key, value, data):
        """Extract the seriesStatement data from marc field data.

        This function automatically selects the subfield codes according field
        tag in the Marc21 or Unimarc format. The extracted data are:
        - seriesTitle
        - seriesEnumeration

        :param key: the field tag and indicators
        :type key: str
        :param value: the subfields data
        :type value: object
        :param data: the object data on which the extracted data will be added
        :type data: object
        """
        # extract production_method from extent and physical_details
        tag_link, link = get_field_link_data(value)
        items = get_field_items(value)
        index = 1
        series = {}
        subseries = []
        count = 0
        tag = key[:3]
        series_title_subfield_code = \
            self.extract_series_statement_subfield[tag]['series_title']
        series_enumeration_subfield_code = \
            self.extract_series_statement_subfield[tag]['series_enumeration']
        subfield_selection = \
            {series_title_subfield_code, series_enumeration_subfield_code}
        subfield_visited = ''
        for blob_key, blob_value in items:
            if blob_key in subfield_selection:
                subfield_visited += blob_key
                value_data = self.build_value_with_alternate_graphic(
                    tag, blob_key, blob_value, index, link, ',.', ':;/-=')
                if blob_key == series_title_subfield_code:
                    count += 1
                    if count == 1:
                        series['seriesTitle'] = value_data
                    else:
                        subseries.append({'subseriesTitle': value_data})
                elif blob_key == series_enumeration_subfield_code:
                    if count == 1:
                        if 'seriesEnumeration' in series:
                            series['seriesEnumeration'] = \
                                join_alternate_graphic_data(
                                    alt_gr_1=series['seriesEnumeration'],
                                    alt_gr_2=value_data,
                                    join_str=', '
                                )
                        else:
                            series['seriesEnumeration'] = value_data
                    elif count > 1:
                        if 'subseriesEnumeration' in subseries[count-2]:
                            alt_gr_1 = \
                                subseries[count-2]['subseriesEnumeration']
                            subseries[count-2]['subseriesEnumeration'] = \
                                join_alternate_graphic_data(
                                    alt_gr_1=alt_gr_1,
                                    alt_gr_2=value_data,
                                    join_str=', '
                                )
                        else:
                            subseries[count-2]['subseriesEnumeration'] = \
                                value_data
            if blob_key != '__order__':
                index += 1

        error_msg = ''
        regexp = re.compile(r'^[^{}]'.format(series_title_subfield_code))
        if regexp.search(subfield_visited):
            error_msg = \
                'missing leading subfield ${code} in field {tag}'.format(
                    code=series_title_subfield_code,
                    tag=tag
                )
            error_print('ERROR BAD FIELD FORMAT:', self.bib_id, self.rero_id,
                        error_msg)
        else:
            if subseries:
                series['subseriesStatement'] = subseries
            series_statement = data.get('seriesStatement', [])
            if series:
                series_statement.append(series)
                data['seriesStatement'] = series_statement


class ReroIlsMarc21Overdo(ReroIlsOverdo):
    """Specialized Overdo for Marc21.

    This class adds RERO Marc21 properties and functions to the ReroIlsOverdo.
    """

    bib_id = ''
    field_008_data = ''
    lang_from_008 = None
    date1_from_008 = None
    date2_from_008 = None
    original_date_from_008 = None
    date = {'start_date'}
    date_type_from_008 = ''
    serial_type = ''  # 008 pos 21
    langs_from_041_a = []
    langs_from_041_h = []
    alternate_graphic = {}
    is_top_level_record = False  # has 019 $a Niveau supérieur
    has_field_490 = False
    has_field_580 = False
    content_media_carrier_type = None

    def __init__(self, bases=None, entry_point_group=None):
        """Reroilsmarc21overdo init."""
        super().__init__(
            bases=bases, entry_point_group=entry_point_group)
        self.count = 0
        self.extract_description_subfield = {
            'physical_detail': 'b',
            'book_format': 'c'
        }
        self.extract_series_statement_subfield = {
            '490': {
                'series_title': 'a',
                'series_enumeration': 'v'
            },
            '773': {
                'series_title': 't',
                'series_enumeration': 'g'
            },
            '800': {
                'series_title': 't',
                'series_enumeration': 'v'
            },
            '830': {
                'series_title': 'a',
                'series_enumeration': 'v'
            }
        }

    def do(self, blob, ignore_missing=True, exception_handlers=None):
        """Translate blob values and instantiate new model instance."""
        self.count += 1
        result = None
        try:
            # extract record leader
            self._blob_record = blob
            self.leader = blob.get('leader', '')
            try:
                self.bib_id = self.get_fields(tag='001')[0]['data']
            except Exception:
                self.bib_id = '???'
            try:
                fields_035 = self.get_fields(tag='035')
                self.rero_id = self.get_subfields(fields_035[0], 'a')[0]
            except Exception:
                self.rero_id = '???'
            self.field_008_data = ''
            self.date1_from_008 = None
            self.date2_from_008 = None
            self.date_type_from_008 = ''
            self.date = {'start_date': None}
            fields_008 = self.get_fields(tag='008')
            if fields_008:
                self.field_008_data = self.get_control_field_data(
                    fields_008[0]).rstrip()
                self.serial_type = self.field_008_data[21]
                self.date1_from_008 = self.field_008_data[7:11]
                self.date2_from_008 = self.field_008_data[11:15]
                self.date_type_from_008 = self.field_008_data[6]
                if self.date_type_from_008 == 'r':
                    self.original_date_from_008 = self.date2_from_008
            self.admin_meta_data = {}

            enc_level = ''
            if self.leader:
                enc_level = self.leader[17]  # LDR 17
            if enc_level in _ENCODING_LEVEL_MAPPING:
                encoding_level = _ENCODING_LEVEL_MAPPING[enc_level]
            else:
                encoding_level = _ENCODING_LEVEL_MAPPING['u']
            self.admin_meta_data['encodingLevel'] = encoding_level

            self.init_lang()
            self.init_country()
            self.init_alternate_graphic()
            self.init_date()
            self.init_content_media_carrier_type()

            # get notes from 019 $a or $b and
            # identifiy a top level record (has 019 $a Niveau supérieur)
            regexp = re.compile(r'Niveau sup[eé]rieur', re.IGNORECASE)
            fields_019 = self.get_fields(tag='019')
            note = ''
            notes_from_019_and_351 = []
            for field_019 in fields_019:
                for subfield_a in self.get_subfields(field_019, 'a'):
                    note += ' | ' + subfield_a
                    if regexp.search(subfield_a):
                        self.is_top_level_record = True
                for subfield_b in self.get_subfields(field_019, 'b'):
                    note += ' | ' + subfield_b
                for subfield_9 in self.get_subfields(field_019, '9'):
                    note += ' (' + subfield_9 + ')'
                    break
                if note:
                    notes_from_019_and_351.append(note[3:])

            fields_351 = self.get_fields(tag='351')
            for field_351 in fields_351:
                note = ' | '.join(self.get_subfields(field_351, 'c'))
                if note:
                    notes_from_019_and_351.append(note)

            if notes_from_019_and_351:
                self.admin_meta_data['note'] = notes_from_019_and_351

            fields_040 = self.get_fields(tag='040')
            for field_040 in fields_040:
                for subfield_a in self.get_subfields(field_040, 'a'):
                    self.admin_meta_data['source'] = subfield_a
                for subfield_b in self.get_subfields(field_040, 'b'):
                    self.admin_meta_data['descriptionLanguage'] = subfield_b
                description_modifier = []
                for subfield_d in self.get_subfields(field_040, 'd'):
                    description_modifier.append(subfield_d)
                if description_modifier:
                    self.admin_meta_data['descriptionModifier'] = \
                        description_modifier
                description_conventions = []
                for subfield_e in self.get_subfields(field_040, 'e'):
                    description_conventions.append(subfield_e)
                if description_conventions:
                    self.admin_meta_data['descriptionConventions'] = \
                        description_conventions
            # check presence of specific fields
            self.has_field_490 = len(self.get_fields(tag='490')) > 0
            self.has_field_580 = len(self.get_fields(tag='580')) > 0
            result = super().do(
                blob,
                ignore_missing=ignore_missing,
                exception_handlers=exception_handlers
            )
        except Exception as err:
            error_print('ERROR:', self.bib_id, self.rero_id, self.count, err)
            traceback.print_exc()
        return result

    def get_link_data(self, subfields_6_data):
        """Extract link and script data from subfields $6 data."""
        link = None
        tag, extra_data = subfields_6_data.split('-')
        if extra_data:
            link_and_script_data = extra_data.split('/')
            link = link_and_script_data[0]
            try:
                script_code = link_and_script_data[1]
            except Exception as err:
                script_code = 'latn'
            try:
                script_dir = link_and_script_data[2]
            except Exception as err:
                script_dir = ''
        return tag, link, script_code, script_dir

    def init_country(self):
        """Initialization country (008 and 044)."""
        self.country = None
        self.cantons = []
        fields_044 = self.get_fields(tag='044')
        if fields_044:
            field_044 = fields_044[0]
            cantons_codes = self.get_subfields(field_044, 'c')
            for cantons_codes in self.get_subfields(field_044, 'c'):
                try:
                    canton = cantons_codes.split('-')[1].strip()
                    if canton:
                        if canton in _CANTON:
                            self.cantons.append(canton)
                        else:
                            error_print('WARNING INIT CANTONS:', self.bib_id,
                                        self.rero_id, cantons_codes)
                except Exception as err:
                    error_print('WARNING INIT CANTONS:', self.bib_id,
                                self.rero_id, cantons_codes)
            if self.cantons:
                self.country = 'sz'
        else:
            try:
                self.country = self.field_008_data[15:18].rstrip()
            except Exception as err:
                pass

    def init_lang(self):
        """Initialization languages (008 and 041)."""
        def init_lang_from(fields_041, code):
            """Construct list of language codes from data."""
            langs_from_041 = []
            for field_041 in fields_041:
                lang_codes = self.get_subfields(field_041, code)
                for lang_from_041 in lang_codes:
                    if lang_from_041 not in langs_from_041:
                        langs_from_041.append(lang_from_041)
            return langs_from_041

        self.lang_from_008 = ''
        self.langs_from_041_a = []
        self.langs_from_041_h = []
        try:
            self.lang_from_008 = self.field_008_data[35:38]
        except Exception as err:
            self.lang_from_008 = 'und'
            error_print("WARNING: set 008 language to 'und'", self.bib_id,
                        self.rero_id)

        fields_041 = self.get_fields(tag='041')
        self.langs_from_041_a = init_lang_from(fields_041, code='a')
        self.langs_from_041_h = init_lang_from(fields_041, code='h')

    def init_date(self):
        """Initialization start and end date.

        1. get dates from 008
        2. get dates from 264 Ind2 1,0,2,4,3 $c
        3. get dates from 773 $g
        4. set start_date to 2050
        """
        if (self.date_type_from_008 == 'q' or self.date_type_from_008 == 'n'):
            self.date['note'] = 'Date(s) uncertain or unknown'
        start_date = make_year(self.date1_from_008)
        if not(start_date and start_date >= -9999 and start_date <= 2050):
            start_date = None
        if not start_date:
            fields_264 = self.get_fields('264')
            for ind2 in ['1', '0', '2', '4', '3']:
                for field_264 in fields_264:
                    if ind2 == field_264['ind2']:
                        subfields_c = self.get_subfields(field_264, 'c')
                        if subfields_c:
                            year = re.search(r"(-?\d{1,4})", subfields_c[0])
                            if year:
                                year = int(year.group(0))
                            if year and year <= -9999 and year >= 2050:
                                start_date = year
                                break
                else:
                    # Continue if the inner loop wasn't broken.
                    continue
                # Inner loop was broken, break the outer.
                break
        if not start_date:
            fields_773 = self.get_fields('773')
            for field_773 in fields_773:
                subfields_g = self.get_subfields(field_773, 'g')
                if subfields_g:
                    year = re.search(r"(-?\d{4})", subfields_g[0])
                    if year:
                        year = int(year.group(0))
                    if year and year <= -9999 and year >= 2050:
                        start_date = year
        if not start_date:
            start_date = 2050
            self.date['note'] = \
                'Date not available and automatically set to 2050'
            error_print('WARNING START DATE 264:', self.bib_id, self.rero_id,
                        self.date1_from_008)
        self.date['start_date'] = start_date

        end_date = make_year(self.date2_from_008)
        if end_date and end_date >= -9999 and end_date <= 2050:
            self.date['end_date'] = end_date

    def init_alternate_graphic(self):
        """Initialization of alternate graphic representation.

        Parse all the 880 fields and populate a dictionary having as first
        level keys the tag of the linked_data field and as second level key the
        link code (from $6) of the linked_data field. The language script is
        extracted from $6 and used to qualify the alternate graphic value.
        """
        def get_script_from_lang(asian=False):
            """Initialization of alternate graphic representation."""
            script = None
            default_script = 'zyyy'
            script_per_lang = _SCRIPT_PER_LANG_NOT_ASIA
            if asian:
                default_script = 'hani'
                script_per_lang = _SCRIPT_PER_LANG_ASIA
            script = script_per_lang.get(self.lang_from_008, None)
            if not script:
                for lang in self.langs_from_041_a:
                    if lang in script_per_lang:
                        script = script_per_lang[lang]
                        break
                if not script:
                    script = default_script
            return script

        # function init_alternate_graphic start here
        self.alternate_graphic = {}
        fields_880 = self.get_fields(tag='880')
        for field_880 in fields_880:
            try:
                subfields_6 = self.get_subfields(field_880, code='6')
                for subfield_6 in subfields_6:
                    tag, link, script_code, script_dir = self.get_link_data(
                        subfield_6)
                    tag_data = self.alternate_graphic.get(tag, {})
                    link_data = tag_data.get(link, {})
                    if script_code == '$1':
                        script = get_script_from_lang(asian=True)
                    elif script_code in _SCRIPT_PER_CODE:
                        script = _SCRIPT_PER_CODE[script_code]
                    else:
                        script = get_script_from_lang()
                    link_data['script'] = script
                    link_data['field'] = field_880
                    if script_dir == 'r':
                        link_data['right_to_left'] = True
                    tag_data[link] = link_data
                    self.alternate_graphic[tag] = tag_data
            except Exception as exp:
                click.secho(
                    'Error in init_alternate_graphic: {error}'.format(
                        error=exp
                    ),
                    fg='red'
                )

    def get_language_script(self, script_code):
        """Build the `language-script` code.

        This code is built according to the format
        <lang_code>-<script_code> for example: chi-hani;
        the <lang_code> is retrived from field 008 and 041
        the <script_code> is received as parameter

        :param script_code: the script code
        :param script_code: str
        :return: language script code in the format `<lang_code>-<script_code>`
        :rtype: str
        """
        if script_code in _LANGUAGES_SCRIPTS:
            languages = (
                [self.lang_from_008] +
                self.langs_from_041_a +
                self.langs_from_041_h)
            for lang in languages:
                if lang in _LANGUAGES_SCRIPTS[script_code]:
                    return '-'.join([lang, script_code])
            error_print('WARNING LANGUAGE SCRIPTS:', self.bib_id, self.rero_id,
                        script_code,  '008:', self.lang_from_008,
                        '041$a:', self.langs_from_041_a,
                        '041$h:', self.langs_from_041_h)
        return '-'.join(['und', script_code])

    def build_variant_title_data(self, string_set):
        """Build variant title data form fields 246.

        :param string_set: the marc field tag
        :type string_set: set
        :return: a list of variant_title object
        :rtype: list
        """
        variant_list = []
        fields_246 = self.get_fields(tag='246')
        for field_246 in fields_246:
            variant_data = {}
            subfield_246_a = ''
            subfields_246_a = self.get_subfields(field_246, 'a')
            if subfields_246_a:
                subfield_246_a = subfields_246_a[0]
            subfield_246_a_cleaned = remove_trailing_punctuation(
                                        subfield_246_a, ',.', ':;/-=')
            if subfield_246_a_cleaned not in string_set:
                # parse all subfields in order
                index = 1
                items = get_field_items(field_246['subfields'])
                tag_link, link = get_field_link_data(field_246)
                part_list = TitlePartList(
                    part_number_code='n',
                    part_name_code='p'
                )

                subfield_selection = {'a', 'n', 'p'}
                for blob_key, blob_value in items:
                    if blob_key in subfield_selection:
                        if blob_key == 'a':
                            subfield_a_parts = blob_value.split(':')
                            part_index = 0
                            for subfield_a_part in subfield_a_parts:
                                value_data = self. \
                                    build_value_with_alternate_graphic(
                                        '246', blob_key, subfield_a_part,
                                        index, link, ',.', ':;/-=')
                                if value_data:
                                    if part_index == 0:
                                        variant_data['type'] = \
                                            'bf:VariantTitle'
                                        variant_data['mainTitle'] = value_data
                                    else:
                                        variant_data['subtitle'] = value_data
                                    part_index += 1
                        elif blob_key in ['n', 'p']:
                            value_data = self. \
                                build_value_with_alternate_graphic(
                                    '246', blob_key, blob_value,
                                    index, link, ',.', ':;/-=')
                            if value_data:
                                part_list.update_part(
                                    value_data, blob_key, blob_value)
                    if blob_key != '__order__':
                        index += 1
                the_part_list = part_list.get_part_list()
                if the_part_list:
                    variant_data['part'] = the_part_list
                if variant_data:
                    variant_list.append(variant_data)
            else:
                pass
                # for showing the variant title skipped for debugging purpose
                # print('variant skipped', subfield_246_a_cleaned)
        return variant_list

    def init_content_media_carrier_type(self):
        """Initialization content/media/carrier type (336, 337 and 338)."""
        content_media_carrier_type_per_tag = {
            '336': 'contentType',
            '337': 'mediaType',
            '338': 'carrierType'
        }
        content_media_carrier_map_per_tag = {
            '336': _CONTENT_TYPE_MAPPING,
            '337': _MEDIA_TYPE_MAPPING,
            '338': _CARRIER_TYPE_MAPPING
        }

        content_media_carrier_type = {}
        media_type_from_unlinked_337 = ''
        for tag in ['336', '337', '338']:  # parsing tag in the right order
            type_key = content_media_carrier_type_per_tag[tag]
            fields = self.get_fields(tag=tag)
            for field in fields:
                subfields_8 = self.get_subfields(field, '8')
                if not subfields_8:
                    subfields_8 = ['0']
                for subfield_b in self.get_subfields(field, 'b'):
                    type_found = False
                    for link in subfields_8:
                        linked_data = content_media_carrier_type.get(link, {})
                        if tag == '336':
                            linked_data_type_value = \
                                linked_data.get(type_key, [])
                            type_value = \
                                content_media_carrier_map_per_tag[tag].get(
                                    subfield_b, None)
                            if type_value and \
                                    type_value not in linked_data_type_value:
                                linked_data_type_value.append(type_value)
                                linked_data[type_key] = linked_data_type_value
                                type_found = True
                        else:
                            if link == '0' and tag == '337':
                                media_type_from_unlinked_337 = \
                                    content_media_carrier_map_per_tag[tag].get(
                                        subfield_b, None)
                            linked_data_type_value = \
                                linked_data.get(type_key, '')
                            type_value = \
                                content_media_carrier_map_per_tag[tag].get(
                                    subfield_b, None)
                            if type_value:
                                linked_data_type_value = type_value
                                linked_data[type_key] = linked_data_type_value
                                type_found = True
                                if tag == '338':
                                    # extract mediaType for the fist char of $b
                                    media_type_from_338 = \
                                        _MEDIA_TYPE_MAPPING.get(
                                            subfield_b[0], None)
                                    if media_type_from_338:
                                        linked_data['mediaTypeFrom338'] = \
                                            media_type_from_338
                        if type_found:
                            content_media_carrier_type[link] = linked_data
                    break  # subfield $b in not repetitive
        self.content_media_carrier_type = []
        for link, value in content_media_carrier_type.items():
            media_type = value.get('mediaType', None)
            media_type_from_338 = value.get('mediaTypeFrom338', None)
            # set mediaType from 338 if not get it form 337
            if media_type_from_338:
                if not media_type:
                    value['mediaType'] = media_type_from_338
                elif media_type_from_338 != media_type:
                    value['mediaType'] = media_type_from_338
                    error_print(
                        'WARNING MEDIA TYPE:',
                        self.bib_id, self.rero_id, media_type)

            if media_type_from_338 and not media_type:
                value['mediaType'] = media_type_from_338
            value.pop('mediaTypeFrom338', None)
            if 'contentType' in value:
                if media_type_from_unlinked_337 and 'mediaType' not in value:
                    value['mediaType'] = media_type_from_unlinked_337
                self.content_media_carrier_type.append(value)


class ReroIlsUnimarcOverdo(ReroIlsOverdo):
    """Specialized Overdo for UNIMARC.

    This class adds UNIMARC properties and functions to the ReroIlsOverdo.
    """

    bib_id = ''
    rero_id = 'unimarc'
    lang_from_101 = None
    alternate_graphic = {}
    serial_type = ''

    def __init__(self, bases=None, entry_point_group=None):
        """Constructor."""
        super().__init__(
            bases=bases, entry_point_group=entry_point_group)
        self.count = 0
        self.extract_description_subfield = {
            'physical_detail': 'c',
            'book_format': 'd',
        }
        self.extract_series_statement_subfield = {
            '225': {
                'series_title': 'a',
                'series_enumeration': 'v'
            }
        }

    def do(self, blob, ignore_missing=True, exception_handlers=None):
        """Translate blob values and instantiate new model instance."""
        self.count += 1
        result = None
        try:
            self._blob_record = blob
            try:
                self.bib_id = self.get_fields(tag='001')[0]['data']
            except Exception as err:
                self.bib_id = '???'

            # get the language code
            fields_101 = self.get_fields(tag='101')
            if fields_101:
                field_101_a = self.get_subfields(fields_101[0], 'a')
                field_101_g = self.get_subfields(fields_101[0], 'g')
                if field_101_a:
                    self.lang_from_101 = field_101_a[0]
                if field_101_g:
                    self.lang_from_101 = field_101_g[0]

            # get the type of continuing ressource
            fields_110 = self.get_fields(tag='110')
            if fields_110:
                field_110_a = self.get_subfields(fields_110[0], 'a')
                if field_110_a and len(field_110_a[0]) > 0:
                    self.serial_type = field_110_a[0][0]

            result = super().do(
                blob,
                ignore_missing=ignore_missing,
                exception_handlers=exception_handlers
            )
        except Exception as err:
            error_print('ERROR:', self.bib_id, self.rero_id, self.count, err)
            traceback.print_exc()
        return result

    def get_alt_graphic_fields(self, tag=None):
        """Get all alternate graphic fields having the given tag value.

        :param unimarc_script_code: the unimarc script code
        :type unimarc_script_code: str
        :return: a list of alternate graphic fields
        :rtype: list
        """
        fields = []
        items = get_field_items(self._blob_record)
        for blob_key, blob_value in items:
            field_data = {}
            tag_value = blob_key[0:3]
            if (tag_value == tag) or not tag:
                field_data['tag'] = tag_value
                if len(blob_key) == 3:  # if control field
                    field_data['data'] = blob_value.rstrip()
                else:
                    field_data['ind1'] = blob_key[3:4]
                    field_data['ind2'] = blob_key[4:5]
                    field_data['subfields'] = blob_value
                subfields_6 = self.get_subfields(field_data, '6')
                subfields_7 = self.get_subfields(field_data, '7')
                # alternate graphic link code start with 'a'
                if subfields_6 and subfields_6[0][0] == 'a' \
                        and subfields_7 and subfields_7[0] != 'ba':  # ba=latin
                    tag_data = self.alternate_graphic.get(tag, {})
                    tag_data[subfields_6[0]] = {}
                    tag_data[subfields_6[0]]['field'] = field_data
                    tag_data[subfields_6[0]]['script'] = subfields_7[0]
                    self.alternate_graphic[tag] = tag_data
                else:
                    fields.append(field_data)
        return fields

    def get_language_script(self, unimarc_script_code):
        """Build the `language-script` code.

        This code is built according to the format
        <lang_code>-<script_code> for example: chi-hani;
        the <lang_code> is retrived from field 101
        the <script_code> is build from the given <unimarc_script_code>

        :param unimarc_script_code: the unimarc script code
        :param unimarc_script_code: str
        :return: language script code in the format `<lang_code>-<script_code>`
        :rtype: str
        """
        if unimarc_script_code in _UNIMARC_LANGUAGES_SCRIPTS:
            script_code = _UNIMARC_LANGUAGES_SCRIPTS[unimarc_script_code]
            if script_code in _LANGUAGES_SCRIPTS:
                if self.lang_from_101 in _LANGUAGES_SCRIPTS[script_code]:
                    return '-'.join([self.lang_from_101, script_code])
                error_print('WARNING LANGUAGE SCRIPTS:', self.bib_id,
                            self.rero_id, script_code, '101:',
                            self.lang_from_101, '101$aor$g:',
                            self.lang_from_101)
        return '-'.join(['und', script_code])


class TitlePartList(object):
    """The purpose of this class is to build the title part list.

    The title part list is build parsing the subfields $n, $p of fields 245
    or 246. Each title part is build for a couple of consecutive $n, $p.
    As some $n or $p can be missing, some part are build only form a $p or $n.

    To build a list of parts, you must create an instance of this class for
    a given field 245 or 246. Then you have to parse the subfields $n and $p
    in the order of appearance in the field (245 or 246) and call the "update"
    method for each of these subfields. At the end of the parsing, the method
    "get_part_list" provides the list of constructed parts.

    :param part_number_code: the specific subfield code
    :type part_number_code: char
    :param part_name_code: the specific subfield code
    :type part_name_code: char
    """

    def __init__(self, part_number_code, part_name_code):
        """Constructor method."""
        self.part_number_waiting_name = {}
        self.part_list = []
        self.part_number_code = part_number_code
        self.part_name_code = part_name_code

    def update_part(self, value_data, subfield_code, subfield_data):
        """Update part data.

        The part object is progressively build with the data collected by
        the succesive calls of the method `update_part`.

        :param subfield_code: specific subfield code for part number or name
        :type subfield_code: char
        :param subfield_data: part number or name depending of `subfield_code`
        :type subfield_data: str
        """
        if self.part_number_waiting_name:
            if subfield_code == self.part_name_code:
                self.part_list.append(
                    dict(partNumber=self.part_number_waiting_name,
                         partName=value_data)
                )
                self.part_number_waiting_name = {}
            else:
                self.part_list.append(
                    dict(partNumber=self.part_number_waiting_name)
                )
                self.part_number_waiting_name = value_data
        else:
            if subfield_code == self.part_number_code:
                self.part_number_waiting_name = value_data
            else:
                self.part_list.append(dict(partName=value_data))

    def get_part_list(self):
        """Get the part list.

        This method return a list of part object build by succesive call of
        the method `update_part`. If a part with only the `part_number` is
        pending, it is appended to the list because it will never receive a
        `part_name`.

        :return: an part list object
        :rtype: list
        """
        if self.part_number_waiting_name:
            self.part_list.append(
                dict(partNumber=self.part_number_waiting_name)
                )
        return self.part_list


def extract_subtitle_and_parallel_titles_from_field_245_b(
        parallel_title_data, field_245_a_end_with_equal):
    """Extracts subtitle and parallel titles from field 245 $b.

    This function retrieves the subtitle and the parallel title list
    from field 245 $b. It also constructs a set containing the parallel title
    and these same title without the initial article.
    This set can be used to process the fields 246 to discard those fields
    that match one of the elements in the set.
    It should be noted that the deletion of the article is achieved simply
    by deleting the first word (max 4 chars) of the parallel title.
    It is not a problem if this word is not a real article because the chain
    produced will not correspond to one of the 246 fields to be discarded.

    :param parallel_title_data: list of parallel_title objects
    :param field_245_a_end_with_equal: boolean flag
    :return: a tuple
        - the main subtitle
        - a list of parallel titles
        - a set of pararalel title strings
    :rtype: tuple

    """

    def remove_leading_article(string, max_article_len=4):
        """Remove the leading article.

        - Any leading word up to 'max_article_len' chars is considered
          as an article to remove.
        - The separateur is an APOSTROPHE or a SPACE.
        :param string: the string to process
        :param max_article_len: the length of article to remove (default: 4)
        :return: the given string without the first word,
            with the given 'max_article_len' chars.
            An empty string is returned if no leading word is removed.
        """
        last_rest = ''
        for sep in ("'", ' '):
            first, sep, rest = string.partition(sep)
            len_rest = len(rest)
            if len(first) <= max_article_len \
                    and len_rest > 0 and len_rest > len(last_rest):
                last_rest = rest
        return last_rest

    data_std = ''
    data_lang = ''
    lang = ''
    main_subtitle = []
    parallel_titles = []
    pararalel_title_string_set = set()
    for parallel_title_value in parallel_title_data:
        value = parallel_title_value.get('value', '')
        lang = parallel_title_value.get('language', '')
        if lang:
            data_lang = value
        else:
            data_std = value

    data_std_items = data_std.split('=')
    data_lang_items = []
    if data_lang:
        data_lang_items = data_lang.split('=')
    index = 0
    out_data_dict = {}

    for data_std in data_std_items:
        if index == 0 and not field_245_a_end_with_equal:
            if data_std.rstrip():
                main_subtitle.append({'value': data_std.rstrip()})
                if lang and index < len(data_lang_items):
                    if data_lang_items[index].rstrip():
                        main_subtitle.append({
                            'value': data_lang_items[index].rstrip(),
                            'language': lang
                        })
        else:
            main_title = []
            subtitle = []
            data_value = \
                remove_trailing_punctuation(data_std.lstrip(), ',.', ':;/-=')
            pararalel_title_str, sep, subtitle_str = data_value.partition(':')
            pararalel_title_str = pararalel_title_str.strip()
            subtitle_str = subtitle_str.strip()
            data_lang_value = ''
            pararalel_title_altgr_str = ''
            subtitle_altgr_str = ''
            if pararalel_title_str:
                out_data_dict = {'type': 'bf:ParallelTitle'}
                main_title.append({'value': pararalel_title_str})
                if lang:
                    try:
                        data_lang_value = remove_trailing_punctuation(
                                data_lang_items[index].lstrip(), ',.', ':;/-=')
                    except Exception as err:
                        data_lang_value = '[missing data]'
                    pararalel_title_altgr_str, sep, subtitle_altgr_str = \
                        data_lang_value.partition(':')
                    if pararalel_title_altgr_str:
                        main_title.append({
                            'value': pararalel_title_altgr_str.strip(),
                            'language': lang,
                        })
                pararalel_title_without_article = \
                    remove_leading_article(pararalel_title_str)
                if pararalel_title_without_article:
                    pararalel_title_string_set.add(
                        pararalel_title_without_article
                    )
                pararalel_title_string_set.add(pararalel_title_str)

                if subtitle_str:
                    subtitle.append({'value': subtitle_str})
                    if lang and subtitle_altgr_str:
                        subtitle.append({
                            'value': subtitle_altgr_str.strip(),
                            'language': lang,
                        })
                if main_title:
                    out_data_dict['mainTitle'] = main_title
                if subtitle:
                    out_data_dict['subtitle'] = subtitle
        index += 1
        if out_data_dict:
            parallel_titles.append(out_data_dict)
    return main_subtitle, parallel_titles, pararalel_title_string_set


def build_responsibility_data(responsibility_data):
    """Build the responsibility data form subfield $c of field 245.

    :param responsibility_data: list of responsibility_data
    :return: a list of responsibility
    :rtype: list
    """
    data_std = ''
    data_lang = ''
    lang = ''
    responsibilities = []
    for responsibility_value in responsibility_data:
        value = responsibility_value.get('value', '')
        lang = responsibility_value.get('language', '')
        if lang:
            data_lang = value
        else:
            data_std = value

    data_std_items = data_std.split(';')
    data_lang_items = []
    if data_lang:
        data_lang_items = data_lang.split(';')
    index = 0
    for data_std in data_std_items:
        out_data = []
        data_value = remove_trailing_punctuation(
                        data_std.lstrip(), ',.', ':;/-=')
        if data_value:
            out_data.append({'value': data_value})
            if lang:
                try:
                    data_lang_value = \
                        remove_trailing_punctuation(
                            data_lang_items[index].lstrip(), ',.', ':;/-=')
                    if not data_lang_value:
                        raise Exception('missing data')
                except Exception as err:
                    data_lang_value = '[missing data]'
                out_data.append({'value': data_lang_value, 'language': lang})
            index += 1
            responsibilities.append(out_data)
    return responsibilities
