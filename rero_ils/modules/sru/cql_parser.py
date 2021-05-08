# -*- coding: utf-8 -*-
#
# RERO ILS
# Copyright (C) 2020 RERO
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


"""CQL Parser Implementation adaptation from cheshire3.

https://github.com/cheshire3/cheshire3
Author:  Rob Sanderson (azaroth@liv.ac.uk)
Version: 2.0    (CQL 1.2)
With thanks to Adam Dickmeiss and Mike Taylor for their valuable input.
"""
from io import StringIO
from shlex import shlex
from xml.sax.saxutils import escape

from lxml import etree
from lxml.builder import ElementMaker

SERVER_CHOISE_RELATION = '='
SERVER_CHOISE_INDEX = 'cql.serverchoice'

ORDER = ['=', '>', '>=', '<', '<=', '<>']
MODIFIER_SEPERATOR = '/'
BOOLEANS = ['and', 'or', 'not', 'prox']
SORT_WORD = 'sortby'

RESERVED_PREFIXES = {
    'srw': 'http://www.loc.gov/zing/cql/srw-indexes/v1.0/',
    'cql': 'info:srw/cql-context-set/1/cql-v1.1',
    'dc': 'http://purl.org/dc/elements/1.1/'
}

XCQL_NAMESPACE = 'http://www.loc.gov/zing/cql/xcql/'

ERROR_ON_EMPTY_TERM = False          # index = ''
ERROR_ON_QUOTED_IDENTIFIER = False   # '/foo/bar' = ''
ERROR_ON_DUPLICATE_PREFIX = False    # >a=b >a=c ''
FULL_RESULT_SET_NAME_CHECK = True     # cql.rsn=a and cql.rsn=a    (mutant!)


ES_INDEX_MAPPINGS = {
    'dc.anywhere': SERVER_CHOISE_INDEX,
    'dc.contributor': 'contribution.role:('
    'ape OR aqt OR arc OR art OR aus OR aut OR chr OR cll OR cmp OR com OR '
    'drt OR dsr OR enj OR fmk OR inv OR ive OR ivr OR lbt OR lsa OR lyr OR '
    'pht OR pra OR prg OR rsp OR scl) AND '
    'contribution.agent.authorized_access_point',
    'dc.creator': 'contribution.role:('
    'abr OR act OR adi OR adp OR aft OR anm OR ann OR apl OR arr OR ato OR '
    'auc OR aui OR bkd OR bnd OR brd OR brl OR bsl OR cas OR clr OR clt OR '
    'cmm OR cnd OR cng OR cns OR col OR cor OR cou OR cre OR crt OR csl OR '
    'cst OR ctb OR ctg OR ctr OR cur OR cwt OR dfd OR dgg OR dgs OR dnc OR '
    'dnr OR dpt OR drm OR dst OR dte OR dto OR dub OR edm OR edt OR egr OR '
    'etr OR exp OR fac OR fds OR fmd OR fmo OR fmp OR his OR hnr OR hst OR '
    'ill OR ilu OR ins OR isb OR itr OR jud OR jug OR lgd OR ltg OR med OR '
    'mfr OR mod OR msd OR mtk OR mus OR nrt OR orm OR osp OR oth OR own OR '
    'pan OR pat OR pbd OR pbl OR plt OR ppm OR ppt OR pre OR prf OR prm OR '
    'prn OR pro OR prs OR prt OR ptf OR rcd OR rce OR rcp OR rdd OR res OR '
    'rpc OR rsr OR sds OR sgd OR sll OR sng OR spk OR spn OR srv OR stl OR '
    'tch OR tld OR tlp OR trc OR trl OR vac OR vdg OR wac OR wal OR wat OR '
    'win OR wpr OR wst) AND '
    'contribution.agent.authorized_access_point',
    'dc.date': 'provisionActivity.type:"bf:Publication" '
               'AND provisionActivity.startDate',
    'dc.title': 'title._text.\\*',
    # TOTO: description search also in: note.label, dissertation.label and
    # supplementaryContent.discription
    'dc.description': 'summary.label',
    'dc.language': 'language.value',
    'dc.publisher': 'provisionActivity.type:"bf:Publication" AND '
                    'provisionActivity.statement.type:"bf:Agent" AND '
                    'provisionActivity.statement.label.value',
    'dc.type': 'type.main_type',
    'dc.identifier': 'identifiedBy.value',
    # TODO: relation search in: issuedWith, otherEdition, otherPhysicalFormat,
    # precededBy, relatedTo, succeededBy, supplement and supplementTo
    # 'dc.relation': '',
    # 'dc.coverage': '',
    # 'dc.format': '',
    # 'dc.rights': '',
    # 'dc.source': '',
    'dc.subject': 'subject.preferred_name',
    'dc.possessingInstitution': 'holdings.organisation.library_pid'
}

# End of 'configurable' stuff


class Diagnostic(Exception):
    """Diagnostic Exceptions."""

    code = 10         # default to generic broken query diagnostic
    uri = 'info:srw/diagnostic/1/'
    message = ''
    details = ''
    xml_root = None

    def __str__(self):
        """String representation of the object."""
        return f'{self.uri}{self.code} [{self.message}]: {self.details}'

    def __init__(self, code=10, message='Malformed Query', details='',
                 query='???'):
        """Constructor."""
        self.code = code
        self.message = message
        self.details = details
        self.query = query
        Exception.__init__(self)

    def xml_str(self, pretty_print=True):
        """Xml as string."""
        self.init_xml()
        return etree.tostring(self.xml_root, pretty_print=pretty_print)

    def init_xml(self):
        """Init XML."""
        srw_ns = 'http://www.loc.gov/zing/srw/'
        element_srw = ElementMaker(
            namespace=srw_ns,
            nsmap={'srw': srw_ns}
        )
        srw_diag_ns = 'http://www.loc.gov/zing/srw/diagnostic/'
        element_srw_diag = ElementMaker(
            namespace=srw_diag_ns,
            nsmap={'diag': srw_diag_ns}
        )
        self.xml_root = element_srw.searchRetrieveResponse()
        self.xml_root.append(element_srw.version('1.1'))

        echoed_search_rr = element_srw.echoedSearchRetrieveRequest()
        echoed_search_rr.append(element_srw.version('1.1'))
        echoed_search_rr.append(element_srw.query(self.query))
        echoed_search_rr.append(element_srw.recordPacking('xml'))
        self.xml_root.append(echoed_search_rr)
        diagnostics = element_srw_diag.diagnostics()
        diagnostics.append(element_srw_diag.uri(f'{self.uri}{self.code}'))
        diagnostics.append(element_srw_diag.details(self.details))
        diagnostics.append(element_srw_diag.message(f'{self.message}'))
        self.xml_root.append(diagnostics)


class PrefixableObject:
    """Root object for triple and searchClause."""

    prefixes = {}
    parent = None
    config = None
    error_on_duplicate_prefix = ERROR_ON_DUPLICATE_PREFIX

    def __init__(self, query):
        """Constructor."""
        self.prefixes = {}
        self.parent = None
        self.config = None
        self.query = query

    def to_xcql(self, depth=0):
        """To XCQL."""
        space = '  ' * depth
        xml = [f'{space}<prefixes>\n']
        for key, value in self.prefixes.items():
            identifier = escape(value)
            xml.extend([f'{space}  <prefix>\n',
                        f'{space}    <name>{key}</name>\n',
                        f'{space}    <identifier>{identifier}</identifier>\n',
                        f'{space}  </prefix>\n'])
        xml.append(f'{space}</prefixes>\n')
        return ''.join(xml)

    def add_prefix(self, name, identifier):
        """Add prefix."""
        if self.error_on_duplicate_prefix and \
                (name in self.prefixes or name in RESERVED_PREFIXES):
            # Maybe error
            diag = Diagnostic()
            diag.code = 45
            diag.details = name
            diag.query = self.query
            raise diag
        self.prefixes[name] = identifier

    def resolve_prefix(self, name):
        """Resolve prefix."""
        # Climb tree
        if name in RESERVED_PREFIXES:
            return RESERVED_PREFIXES[name]
        if name in self.prefixes:
            return self.prefixes[name]
        if self.parent is not None:
            return self.parent.resolve_prefix(name)
        if self.config is not None:
            # Config is some sort of server config which specifies defaults
            return self.config.resolve_prefix(name)
        # Top of tree, no config, no resolution->Unknown indexset
        # For client we need to allow no prefix?
        # diag = Diagnostic15()
        # diag.details = name
        # diag.query = self.query
        # raise diag
        return None


class PrefixedObject:
    """Root object for index, relation, relationModifier."""

    prefix = ''
    prefix_uri = ''
    value = ''
    parent = None

    def __init__(self, val, query,
                 error_on_quoted_identifier=ERROR_ON_QUOTED_IDENTIFIER):
        """Constructor."""
        # All prefixed things are case insensitive
        self.error_on_quoted_identifier = error_on_quoted_identifier
        self.orig_value = val
        self.query = query
        val = val.lower()
        if val and val[0] == '"' and val[-1] == '"':
            if self.error_on_quoted_identifier:
                diag = Diagnostic()
                diag.code = 14
                diag.details = val
                diag.query = self.query
                raise diag
            val = val[1:-1]
        self.value = val
        self.split_value()

    def __str__(self):
        """String representation of the object."""
        if self.prefix:
            return f'{self.prefix}.{self.value}'
        return f'{self.value}'

    def split_value(self):
        """Split value."""
        find_point = self.value.find(".")
        if self.value.count('.') > 1:
            diag = Diagnostic()
            diag.code = 15
            diag.details = f'Multiple "." characters: {self.value}'
            diag.query = self.query
            raise diag
        if find_point == 0:
            diag = Diagnostic()
            diag.code = 15
            diag.details = 'Null indexset'
            diag.query = self.query
            raise diag
        if find_point >= 0:
            self.prefix = self.value[:find_point].lower()
            self.value = self.value[find_point + 1:].lower()

    def resolve_prefix(self):
        """Resolve prefix."""
        if not self.prefix_uri:
            if isinstance(self.parent, PrefixedObject):
                self.prefix_uri = self.parent.resolve_prefix()
            else:
                self.prefix_uri = self.parent.resolve_prefix(self.prefix)
        return self.prefix_uri


class ModifiableObject():
    """Mofifiable object."""

    # Treat modifiers as keys on boolean/relation?
    modifiers = []

    def __getitem__(self, key):
        """Get item."""
        if isinstance(key, int):
            try:
                return self.modifiers[key]
            except Exception:
                return None
        for modifier in self.modifiers:
            if (str(modifier.type) == key or modifier.type.value == key):
                return modifier
        return None


class Triple(PrefixableObject):
    """Object to represent a CQL triple."""

    left_operand = None
    right_operand = None
    boolean = None
    sort_keys = []

    def to_xcql(self, depth=0):
        """Create the XCQL representation of the object."""
        space = '  ' * depth
        if depth == 0:
            xml = [f'<triple xmlns="{XCQL_NAMESPACE}">\n']
        else:
            xml = [f'{space}<triple>\n']

        if self.prefixes:
            xml.append(PrefixableObject.to_xcql(self, depth + 1))

        xml.append(self.boolean.to_xcql(depth + 1))
        xml.append(f'{space}  <left_operand>\n')
        xml.append(self.left_operand.to_xcql(depth + 2))
        xml.append(f'{space}  </left_operand>\n')
        xml.append(f'{space} <right_operand>\n')
        xml.append(self.right_operand.to_xcql(depth + 2))
        xml.append(f'{space}  </right_operand>\n')

        if self.sort_keys:
            xml.append(f'  {space}<sort_keys>\n')
            for key in self.sort_keys:
                xml.append(key.to_xcql(depth + 2))
            xml.append(f'  {space}</sort_keys>\n')

        xml.append(f'{space}</triple>\n')
        return ''.join(xml)

    def to_cql(self):
        """Create the CQL representation of the object."""
        txt = []
        if self.prefixes:
            ptxt = []
            for key, value in self.prefixes.items():
                if key != '':
                    ptxt.append(f'>{key}="self.prefixes[p]"')
                else:
                    ptxt.append(f'>"{value}"')
            prefs = ' '.join(ptxt)
            txt.append(prefs)
        txt.append(self.left_operand.to_cql())
        txt.append(self.boolean.to_cql())
        txt.append(self.right_operand.to_cql())
        # Add sort_keys
        if self.sort_keys:
            txt.append('sortBy')
            for sort_key in self.sort_keys:
                txt.append(sort_key.to_cql())
        return f'({" ".join(txt)})'

    def to_es(self):
        """Create the ES representation of the object."""
        txt = []
        boolean = self.boolean.to_es()
        if boolean == 'prox':
            diag = Diagnostic()
            diag.code = 37
            diag.message = 'Unsupported boolean operator'
            diag.details = 'prox'
            diag.query = self.query
            raise diag

        txt.append(self.left_operand.to_es())
        if boolean == 'not':
            txt.append('AND')
        else:
            txt.append(boolean.upper())
        txt.append(self.right_operand.to_es())
        # Add sort_keys
        if self.sort_keys:
            diag = Diagnostic()
            diag.code = 80
            diag.message = 'Sort not supported'
            diag.query = self.query
            raise diag
            # txt.append('sortBy')
            # for sort_key in self.sort_keys:
            #     txt.append(sort_key.to_es())
        pre = '-' if boolean == 'not' else ''
        return f'{pre}({" ".join(txt)})'

    def get_result_set_id(self, top=None):
        """Get result set id."""
        if FULL_RESULT_SET_NAME_CHECK == 0 or \
                self.boolean.value in ['not', 'prox']:
            return ''

        if top is None:
            top_level = 1
            top = self
        else:
            top_level = 0

        # Iterate over operands and build a list
        rs_list = []
        if isinstance(self.left_operand, Triple):
            rs_list.extend(self.left_operand.get_result_set_id(top))
        else:
            rs_list.append(self.left_operand.get_result_set_id(top))
        if isinstance(self.right_operand, Triple):
            rs_list.extend(self.right_operand.get_result_set_id(top))
        else:
            rs_list.append(self.right_operand.get_result_set_id(top))

        if top_level == 1:
            # Check all elements are the same
            # if so we're a fubar form of present
            if len(rs_list) == rs_list.count(rs_list[0]):
                return rs_list[0]
            return ''
        return rs_list


class SearchClause(PrefixableObject):
    """Object to represent a CQL search clause."""

    index = None
    relation = None
    term = None
    sort_keys = []

    def __init__(self, ind, rel, term, query):
        """Constructor."""
        PrefixableObject.__init__(self, query)
        self.index = ind
        self.relation = rel
        self.term = term
        ind.parent = self
        rel.parent = self
        term.parent = self

    def to_xcql(self, depth=0):
        """Create the XCQL representation of the object."""
        space = '  ' * depth
        if depth == 0:
            xml = [f'<searchClause xmlns="{XCQL_NAMESPACE}">\n']
        else:
            xml = [f'{space}<searchClause>\n']

        if self.prefixes:
            xml.append(PrefixableObject.to_xcql(self, depth + 1))

        xml.append(self.index.to_xcql(depth + 1))
        xml.append(self.relation.to_xcql(depth + 1))
        xml.append(self.term.to_xcql(depth + 1))

        if self.sort_keys:
            xml.append(f'  {space}<sort_keys>\n')
            for key in self.sort_keys:
                xml.append(key.to_xcql(depth + 2))
            xml.append(f'  {space}</sort_keys>\n')

        xml.append(f'{space}</searchClause>\n')
        return ''.join(xml)

    def to_cql(self):
        """Create the CQL representation of the object."""
        text = []
        for key, value in self.prefixes.items():
            if key != '':
                text.append(f'>{key}="{value}"')
            else:
                text.append(f'>"{value}"')
        text.append(
            f'{self.index} {self.relation.to_cql()} "{self.term.to_cql()}"'
        )
        # Add sort_keys
        if self.sort_keys:
            text.append('sortBy')
            for sort_key in self.sort_keys:
                text.append(sort_key.to_cql())
        return ' '.join(text)

    def to_es(self):
        """Create the ES representation of the object."""
        def index_term(index, relation, term):
            """Clean term."""
            index = ES_INDEX_MAPPINGS.get(index, index)
            if relation in ['=', 'all', 'any']:
                relation = ''
            if str(index) == SERVER_CHOISE_INDEX:
                return f'{relation}{term}'
            return f'{index}:{relation}{term}'

        index = self.index.to_es()
        relation = self.relation.to_es()
        if relation in ['=', '>', '>=', '<', '<=']:
            text = index_term(index, relation, self.term.to_es())
        elif relation == '<>':
            text = index_term(index, '-', self.term.to_es())
        else:
            texts = []
            for term in self.term.to_es().split(' '):
                texts.append(index_term(index, relation, term))
            if relation == 'any':
                text = f'({" OR ".join(texts)})'
            elif relation == 'all':
                text = f'({" AND ".join(texts)})'
            else:
                diag = Diagnostic()
                diag.code = 19
                diag.message = 'Unsupported relation'
                diag.details = relation
                diag.query = self.query
                raise diag
        # Add sort_keys
        if self.sort_keys:
            diag = Diagnostic()
            diag.code = 80
            diag.message = 'Sort not supported'
            diag.query = self.query
            raise diag
            # text.append('sortBy')
            # for sort_key in self.sort_keys:
            #     text.append(sort_key.to_es())
        return text

    def get_result_set_id(self, top=None):
        """Get result set id."""
        idx = self.index
        idx.resolve_prefix()
        if idx.prefix_uri == RESERVED_PREFIXES['cql'] and \
                idx.value.lower() == 'resultsetid':
            return self.term.value
        return ''


class Index(PrefixedObject, ModifiableObject):
    """Object to represent a CQL index."""

    def __init__(self, val, query):
        """Constructor."""
        PrefixedObject.__init__(self, val, query)
        if self.value in ['(', ')'] + ORDER:
            diag = Diagnostic()
            diag.message = 'Invalid characters in index name'
            diag.details = self.value
            diag.query = self.query
            raise diag

    def to_xcql(self, depth=0):
        """Create the XCQL representation of the object."""
        space = '  ' * depth
        xmlns = ''
        if depth == 0:
            xmlns = f' xmlns="{XCQL_NAMESPACE}"'
        xml = [
            f'{space}<index{xmlns}>\n',
            f'  {space}<value>{escape(str(self))}</value>\n'
        ]
        if self.modifiers:
            xml.append(f'{space}  <modifiers>\n')
            for modifier in self.modifiers:
                xml.append(modifier.to_xcql(depth + 2))
            xml.append(f'{space}  </modifiers>\n')
        xml.append(f'{space}</index>\n')
        return ''.join(xml)

    def to_cql(self):
        """Create the CQL representation of the object."""
        txt = [str(self)]
        for modifier in self.modifiers:
            txt.append(str(modifier.to_cql()))
        return '/'.join(txt)

    def to_es(self):
        """Create the ES representation of the object."""
        if self.modifiers:
            diag = Diagnostic()
            diag.code = 21
            diag.message = 'Unsupported combination of relation modifers'
            diag.details = self.modifiers
            diag.query = self.query
            raise diag
        return str(self)


class Relation(PrefixedObject, ModifiableObject):
    """Object to represent a CQL relation."""

    def __init__(self, rel, query, mods=[]):
        """Constructor."""
        self.prefix = 'cql'
        PrefixedObject.__init__(self, rel, query)
        self.modifiers = mods
        for mod in mods:
            mod.parent = self

    def to_xcql(self, depth=0):
        """Create the XCQL representation of the object."""
        xmlns = ''
        if depth == 0:
            xmlns = f' xmlns="{XCQL_NAMESPACE}"'

        space = '  ' * depth

        xml = [f'{space}<relation{xmlns}>\n']
        xml.append(f'{space}  <value>{escape(self.value)}</value>\n')
        if self.modifiers:
            xml.append(f'{space}  <modifiers>\n')
            for modifier in self.modifiers:
                xml.append(modifier.to_xcql(depth + 2))
            xml.append(f'{space}  </modifiers>\n')
        xml.append(f'{space}</relation>\n')
        return ''.join(xml)

    def to_cql(self):
        """Create the CQL representation of the object."""
        txt = [self.value]
        txt.extend(map(str, self.modifiers))
        return '/'.join(txt)

    def to_es(self):
        """Create the ES representation of the object."""
        if self.modifiers:
            diag = Diagnostic()
            diag.code = 21
            diag.message = 'Unsupported combination of relation modifers'
            diag.details = self.modifiers
            diag.query = self.query
            raise diag
        return self.value


class Term:
    """Term."""

    value = ''

    def __init__(self, value, query, error_on_empty_term=ERROR_ON_EMPTY_TERM):
        """Constructor."""
        if value != '':
            # Unquoted literal
            if value in ['>=', '<=', '>', '<', '<>', '/', '=']:
                diag = Diagnostic()
                diag.code = 25
                diag.details = value
                diag.query = query
                raise diag

            # Check existence of meaningful term
            nonanchar = 0
            for char in value:
                if char != '^':
                    nonanchar = 1
                    break
            if not nonanchar:
                diag = Diagnostic()
                diag.code = 32
                diag.details = 'Only anchoring charater(s) in term: ' + value
                diag.query = query
                raise diag

            # Unescape quotes
            if (value[0] == '"' and value[-1] == '"'):
                value = value[1:-1]
            value = value.replace('\\"', '"')

            # Check for badly placed \s
            startidx = 0
            idx = value.find('\\', startidx)
            while idx > -1:
                if len(value) < idx + 2 or \
                        not value[idx + 1] in ['?', '\\', '*', '^']:
                    diag = Diagnostic()
                    diag.code = 26
                    diag.details = value
                    diag.query = query
                    raise diag
                if value[idx + 1] == '\\':
                    startidx = idx + 2
                else:
                    startidx = idx + 1
                idx = value.find('\\', startidx)
        elif error_on_empty_term:
            diag = Diagnostic()
            diag.code = 27
            diag.query = query
            raise diag
        self.value = value

    def __str__(self):
        """String representation of the object."""
        return f'{self.value}'

    def to_xcql(self, depth=0):
        """Create the XCQL representation of the object."""
        xmlns = ''
        if depth == 0:
            xmlns = f' xmlns="{XCQL_NAMESPACE}"'
        return f'{"  " * depth}<term{xmlns}>{escape(self.value)}</term>\n'

    def to_cql(self):
        """Create the CQL representation of the object."""
        return self.value.replace('"', '\\"')

    def to_es(self):
        """Create the ES representation of the object."""
        return self.value


class Boolean(ModifiableObject):
    """Object to represent a CQL boolean."""

    value = ''
    parent = None

    def __init__(self, bool_value, query, mods=[]):
        """Constructor."""
        self.value = bool_value
        self.modifiers = mods
        self.parent = None
        self.query = query

    def to_xcql(self, depth=0):
        """Create the XCQL representation of the object."""
        space = '  ' * depth
        xml = [f'{space}<boolean>\n']
        xml.append(f'{space}  <value>{escape(self.value)}</value>\n')
        if self.modifiers:
            xml.append(f'{space}  <modifiers>\n')
            for modifier in self.modifiers:
                xml.append(modifier.to_xcql(depth + 2))
            xml.append(f'{space}  </modifiers>\n')
        xml.append(f'{space}</boolean>\n')
        return ''.join(xml)

    def to_cql(self):
        """Create the CQL representation of the object."""
        txt = [self.value]
        for modifier in self.modifiers:
            txt.append(str(modifier.to_cql()))
        return '/'.join(txt)

    def to_es(self):
        """Create the ES representation of the object."""
        if self.modifiers:
            diag = Diagnostic()
            diag.code = 21
            diag.message = 'Unsupported combination of relation modifers'
            diag.details = self.modifiers
            diag.query = self.query
            raise diag
        return f'{self.value}'

    def resolve_prefix(self, name):
        """Resolve prefix."""
        return self.parent.resolve_prefix(name)


class ModifierTypeType(PrefixedObject):
    """Modifier type."""

    # Same as index, but we'll XCQLify in ModifierClause
    parent = None
    prefix = 'cql'


class ModifierClause:
    """Object to represent a relation modifier."""

    parent = None
    type = None
    comparison = ''
    value = ''

    def __init__(self, modifier_type, comp='', val='', query=''):
        """Constructor."""
        self.type = ModifierType(modifier_type, query)
        self.type.parent = self
        self.comparison = comp
        self.value = val

    def __str__(self):
        """String representation of the object."""
        if self.value:
            return f'{self.type}{self.comparison}{self.value}'
        return f'{self.type}'

    def to_xcql(self, depth=0):
        """Create the XCQL representation of the object."""
        e_type = escape(str(self.type))
        if self.value:
            e_comparison = escape(self.comparison)
            e_value = escape(self.value)
            return '\n'.join([
                f'{"  " * depth}<modifier>',
                f'{"  " * (depth + 1)}<type>{e_type}</type>',
                f'{"  " * (depth + 1)}<comparison>{e_comparison}</comparison>',
                f'{"  " * (depth + 1)}<value>{e_value}</value>',
                f'{"  " * depth}</modifier>\n'
            ])
        return '\n'.join([
            f'{"  " * depth}<modifier>',
            f'{"  " * (depth + 1)}<type>{e_type}</type>',
            f'{"  " * depth}</modifier>\n'
        ])

    def to_cql(self):
        """Create the CQL representation of the object."""
        return self

    def to_es(self):
        """Create the ES representation of the object."""
        return self

    def resolve_prefix(self, name):
        """Resolve prefix."""
        # Need to skip parent, which has its own resolve_prefix
        # eg boolean or relation, neither of which is prefixable
        return self.parent.parent.resolve_prefix(name)


# Requires changes for:  <= >= <>, and escaped \" in "
# From shlex.py (std library for 2.2+)
class CQLshlex(shlex):
    """Shlex with additions for CQL parsing."""

    quotes = '"'
    commenters = ''
    next_token = ''

    def __init__(self, thing, query):
        """Constructor."""
        shlex.__init__(self, thing)
        self.wordchars += '!@#$%^&*-+{}[];,.?|~`:\\'
        self.query = query

    def read_token(self):
        """Read a token from the input stream (no pushback or inclusions)."""
        while 1:
            if self.next_token != '':
                self.token = self.next_token
                self.next_token = ''
                # Bah. SUPER ugly non portable
                if self.token == '/':
                    self.state = ' '
                    break

            nextchar = self.instream.read(1)
            if nextchar == '\n':
                self.lineno = self.lineno + 1

            if self.state is None:
                self.token = ''        # past end of file
                break
            if self.state == ' ':
                if not nextchar:
                    self.state = None  # end of file
                    break
                if nextchar in self.whitespace:
                    if self.token:
                        break   # emit current token
                    continue
                if nextchar in self.commenters:
                    self.instream.readline()
                    self.lineno = self.lineno + 1
                elif nextchar in self.wordchars:
                    self.token = nextchar
                    self.state = 'a'
                elif nextchar in self.quotes:
                    self.token = nextchar
                    self.state = nextchar
                elif nextchar in ['<', '>']:
                    self.token = nextchar
                    self.state = '<'
                else:
                    self.token = nextchar
                    if self.token:
                        break   # emit current token
                    continue
            elif self.state == '<':
                # Only accumulate <=, >= or <>
                if self.token == '>' and nextchar == '=':
                    self.token = self.token + nextchar
                    self.state = ' '
                    break
                if self.token == '<' and nextchar in ['>', '=']:
                    self.token = self.token + nextchar
                    self.state = ' '
                    break
                if not nextchar:
                    self.state = None
                    break
                if nextchar == '/':
                    self.state = '/'
                    self.next_token = '/'
                    break
                if nextchar in self.wordchars:
                    self.state = 'a'
                    self.next_token = nextchar
                    break
                if nextchar in self.quotes:
                    self.state = nextchar
                    self.next_token = nextchar
                    break
                self.state = ' '
                break

            elif self.state in self.quotes:
                self.token = self.token + nextchar
                # Allow escaped quotes
                if nextchar == self.state and self.token[-2] != '\\':
                    self.state = ' '
                    break
                if not nextchar:      # end of file
                    # Override SHLEX's ValueError to throw diagnostic
                    diag = Diagnostic()
                    diag.details = self.token[:-1]
                    diag.query = self.query
                    raise diag
            elif self.state == 'a':
                if not nextchar:
                    self.state = None   # end of file
                    break
                if nextchar in self.whitespace:
                    self.state = ' '
                    if self.token:
                        break   # emit current token
                    continue
                if nextchar in self.commenters:
                    self.instream.readline()
                    self.lineno = self.lineno + 1
                elif ord(nextchar) > 126 or \
                        nextchar in self.wordchars or \
                        nextchar in self.quotes:
                    self.token = self.token + nextchar
                elif nextchar in ['>', '<']:
                    self.next_token = nextchar
                    self.state = '<'
                    break
                else:
                    self.push_token(nextchar)
                    # self.pushback = [nextchar] + self.pushback
                    self.state = ' '
                    if self.token:
                        break   # emit current token
                    continue
        result = self.token
        self.token = ''
        return result


class CQLParser:
    """Token parser to create object structure for CQL."""

    parser = ''
    current_token = ''
    next_token = ''

    def __init__(self, parser):
        """Initialise with shlex parser."""
        self.parser = parser
        self.fetch_token()  # Fetches to next
        self.fetch_token()  # Fetches to curr

    @staticmethod
    def is_sort(token):
        """Is sort."""
        return token.lower() == SORT_WORD

    @staticmethod
    def is_boolean(token):
        """Is the token a boolean."""
        token = token.lower()
        return token in BOOLEANS

    def fetch_token(self):
        """Read ahead one token."""
        self.current_token = self.next_token
        self.next_token = self.parser.get_token()

    def prefixes(self):
        """Create prefixes dictionary."""
        prefs = {}
        while self.current_token == '>':
            # Strip off maps
            self.fetch_token()
            identifier = []
            if self.next_token == '=':
                # Named map
                name = self.current_token
                self.fetch_token()  # = is current
                self.fetch_token()  # id is current
                identifier.append(self.current_token)
            else:
                name = ''
                identifier.append(self.current_token)
            self.fetch_token()
            # URIs can have slashes, and may be unquoted (standard BNF checked)
            while self.current_token == '/' or identifier[-1] == '/':
                identifier.append(self.current_token)
                self.fetch_token()
            identifier = ''.join(identifier)
            if len(identifier) > 1 and \
                    identifier[0] == '"' and \
                    identifier[-1] == '"':
                identifier = identifier[1:-1]
            prefs[name.lower()] = identifier
        return prefs

    def query(self):
        """Parse query."""
        prefs = self.prefixes()
        left = self.sub_query()
        while 1:
            if not self.current_token:
                break
            if self.is_boolean(self.current_token):
                boolobject = self.boolean()
                right = self.sub_query()
                trip = TripleType(self.parser.query)
                # Setup objects
                trip.left_operand = left
                trip.boolean = boolobject
                trip.right_operand = right
                left.parent = trip
                right.parent = trip
                boolobject.parent = trip
                left = trip
            elif self.is_sort(self.current_token):
                # consume and parse with modified sort spec
                left.sort_keys = self.sort_query()
            else:
                break
        for key, value in prefs.items():
            left.add_prefix(key, value)
        return left

    def sort_query(self):
        """Sort query."""
        # current is 'sort' reserved word
        self.fetch_token()
        keys = []
        if not self.current_token:
            # trailing sort with no keys
            diag = Diagnostic()
            diag.message = 'No sort keys supplied'
            diag.query = self.parser.query
            raise diag
        while self.current_token:
            # current is index name
            if self.current_token == ')':
                break
            index = IndexerType(self.current_token, self.parser.query)
            self.fetch_token()
            index.modifiers = self.modifiers()
            keys.append(index)
        return keys

    def sub_query(self):
        """Find either query or clause."""
        if self.current_token == "(":
            self.fetch_token()  # Skip (
            query = self.query()
            if self.current_token == ")":
                self.fetch_token()  # Skip )
            else:
                diag = Diagnostic()
                diag.details = self.current_token
                diag.query = self.parser.query
                raise diag
        else:
            prefs = self.prefixes()
            if prefs:
                query = self.query()
                for key, value in prefs.items():
                    query.add_prefix(key, value)
            else:
                query = self.clause()
        return query

    def clause(self):
        """Find searchClause."""
        is_boolean = self.is_boolean(self.next_token)
        sort = self.is_sort(self.next_token)
        if not sort and \
                not is_boolean and \
                not (self.next_token in [')', '(', '']):
            index = IndexerType(self.current_token, self.parser.query)
            self.fetch_token()   # Skip Index
            relation = self.relation()
            if self.current_token == '':
                diag = Diagnostic()
                diag.details = 'Expected Term, got end of query.'
                diag.query = self.parser.query
                raise diag
            term = TermType(self.current_token, self.parser.query)
            self.fetch_token()   # Skip Term
            irt = RelatioSearchClauseType(index, relation, term,
                                          self.parser.query)

        elif self.current_token and \
                (is_boolean or sort or self.next_token in [')', '']):
            irt = RelatioSearchClauseType(
                IndexerType(SERVER_CHOISE_INDEX, self.parser.query),
                RelationType(SERVER_CHOISE_RELATION, self.parser.query),
                TermType(self.current_token, self.parser.query),
                self.parser.query
            )
            self.fetch_token()

        elif self.current_token == '>':
            prefs = self.prefixes()
            clause = self.clause()
            for key, value in prefs.items():
                clause.add_prefix(key, value)
            return clause

        else:
            diag = Diagnostic()
            token = self.current_token
            diag.details = f'Expected Boolean or Relation but got: {token}'
            diag.query = self.parser.query
            raise diag
        return irt

    def modifiers(self):
        """Modifiers."""
        mods = []
        while self.current_token == MODIFIER_SEPERATOR:
            self.fetch_token()
            mod = self.current_token
            mod = mod.lower()
            if mod == MODIFIER_SEPERATOR:
                diag = Diagnostic()
                diag.details = 'Null modifier'
                diag.query = self.parser.query
                raise diag
            self.fetch_token()
            comp = self.current_token
            if comp in ORDER:
                self.fetch_token()
                value = self.current_token
                self.fetch_token()
            else:
                comp = ''
                value = ''
            mods.append(ModifierClause(mod, comp, value, self.parser.query))
        return mods

    def boolean(self):
        """Find boolean."""
        self.current_token = self.current_token.lower()
        if self.current_token in BOOLEANS:
            bool_type = BooleanType(self.current_token, self.parser.query)
            self.fetch_token()
            bool_type.modifiers = self.modifiers()
            for modifier in bool_type.modifiers:
                modifier.parent = bool_type
        else:
            diag = Diagnostic()
            diag.details = self.current_token
            diag.query = self.parser.query
            raise diag
        return bool_type

    def relation(self):
        """Find relation."""
        self.current_token = self.current_token.lower()
        relation = RelationType(self.current_token, self.parser.query)
        self.fetch_token()
        relation.modifiers = self.modifiers()
        for modifier in relation.modifiers:
            modifier.parent = relation
        return relation


def parse(query):
    """Return a searchClause/triple object from CQL string."""
    query_io_string = StringIO(query)
    lexer = CQLshlex(query_io_string, query)
    parser = CQLParser(lexer)
    query = parser.query()
    if parser.current_token != '':
        diag = Diagnostic()
        diag.code = 10
        current_token = repr(parser.current_token)
        diag.details = f'Unprocessed tokens remain: {current_token}'
        diag.query = query
        raise diag
    del lexer
    del parser
    del query_io_string
    return query


# Assign our objects to generate
TripleType = Triple
BooleanType = Boolean
RelationType = Relation
RelatioSearchClauseType = SearchClause
ModifierClauseType = ModifierClause
ModifierType = ModifierTypeType
IndexerType = Index
TermType = Term
