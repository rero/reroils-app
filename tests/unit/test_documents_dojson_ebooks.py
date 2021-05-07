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

"""DOJSON transiformation for ebooks module tests."""

from __future__ import absolute_import, print_function

from dojson.contrib.marc21.utils import create_record

from rero_ils.modules.ebooks.dojson.contrib.marc21 import marc21


def test_marc21_to_isbn_ebooks():
    """Test dojson isbn transformation."""
    marc21xml = """
    <record>
      <datafield tag="020" ind1=" " ind2=" ">
        <subfield code="a">9782812933868</subfield>
      </datafield>
    </record>
    """
    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)
    assert data.get('identifiedBy') == [
        {
            'type': 'bf:Isbn',
            'value': '9782812933868'
        }
    ]

    marc21xml = """
    <record>
      <datafield tag="020" ind1=" " ind2=" ">
        <subfield code="a">9782812</subfield>
      </datafield>
    </record>
    """
    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)
    assert data.get('identifiedBy') is None

    marc21xml = """
    <record>
      <datafield tag="020" ind1=" " ind2=" ">
        <subfield code="a">feedhttps-www-feedbooks-com-book-414-epub</subfield>
      </datafield>
    </record>
    """
    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)
    assert not data.get('identifiedBy')


def test_marc21_to_languages_ebooks_from_008():
    """Test languages from field 008."""
    marc21xml = """
    <record>
        <leader>00501naa a2200133 a 4500</leader>
        <controlfield tag=
            "008">160315s2015    cc ||| |  ||||00|  |fre d</controlfield>
    </record>
    """
    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)
    assert data.get('language') == [{'type': 'bf:Language', 'value': 'fre'}]


def test_marc21_to_languages_ebooks():
    """Test languages transformation.

    Test languages in multiples fields 041.
    """
    marc21xml = """
    <record>
      <datafield tag="041" ind1=" " ind2=" ">
        <subfield code="a">fre</subfield>
      </datafield>
      <datafield tag="041" ind1="1" ind2=" ">
        <subfield code="h">eng</subfield>
      </datafield>
    </record>
    """
    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)
    assert data.get('language') == [{'type': 'bf:Language', 'value': 'fre'}]


def test_marc21_to_type_ebooks():
    """Test Other Standard Identifier transformation."""
    marc21xml = """
    <record>
      <datafield tag="024" ind1="8" ind2=" ">
        <subfield code="a">http://cantookstation.com/resources/1</subfield>
      </datafield>
    </record
    """
    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)
    assert data.get('type') == [{
        'main_type': 'docmaintype_book',
        'subtype': 'docsubtype_e-book'
    }]


def test_marc21_to_identifier_rero_id():
    """Test reroID transformation."""
    marc21xml = """
    <record>
      <datafield tag="035" ind1=" " ind2=" ">
        <subfield code="a">cantook-EDEN496624</subfield>
      </datafield>
    </record>
    """
    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)
    identifiers = data.get('identifiedBy', [])
    assert identifiers[0] == {
        'type': 'bf:Local',
        'value': 'cantook-EDEN496624'
    }


def test_marc21_to_title():
    """Test title transformation."""
    marc21xml = """
    <record>
      <datafield tag="245" ind1=" " ind2=" ">
        <subfield code="a">Elena et les joueuses</subfield>
      </datafield>
    </record>
    """
    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)
    assert data.get('title') == [{
        'mainTitle': [{'value': 'Elena et les joueuses'}],
        'type': 'bf:Title'
    }]


def test_marc21_to_extent():
    """Test extent transformation.

    Transformation of nb pages, volumes... field 300 $a.
    """
    marc21xml = """
    <record>
      <datafield tag="300" ind1=" " ind2=" ">
        <subfield code="a">1234</subfield>
        </datafield>
    </record>
    """
    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)
    assert data.get('extent') == '1234'


def test_marc21_to_description():
    """Test description transformation.

    300 [$a repetitive]: extent, duration:
    300 [$a non repetitive]: colorContent, productionMethod,
        illustrativeContent, note of type otherPhysicalDetails
    300 [$c rep
    """
    marc21xml = """
    <record>
      <datafield tag="300" ind1=" " ind2=" ">
        <subfield code="a">116 p.</subfield>
        <subfield code="b">ill.</subfield>
        <subfield code="c">22 cm</subfield>
      </datafield>
    </record>
    """
    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)
    assert data.get('extent') == '116 p.'

    marc21xml = """
    <record>
      <datafield tag="300" ind1=" " ind2=" ">
        <subfield code="a">116 p.</subfield>
        <subfield code="b">ill.</subfield>
        <subfield code="c">22 cm</subfield>
        <subfield code="c">12 x 15</subfield>
      </datafield>
      <datafield tag="300" ind1=" " ind2=" ">
        <subfield code="a">200 p.</subfield>
        <subfield code="b">ill.</subfield>
        <subfield code="c">19 cm</subfield>
      </datafield>
    </record>
    """
    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)
    assert data.get('extent') == '116 p.'

    marc21xml = """
    <record>
      <datafield tag="300" ind1=" " ind2=" ">
        <subfield code="a">116 p.</subfield>
        <subfield code="b">ill.</subfield>
        <subfield code="x">22 cm</subfield>
      </datafield>
    </record>
    """
    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)
    assert data.get('extent') == '116 p.'


def test_marc21_to_notes():
    """Test notes transformation.

    Transformation notes field 500 $a.
    """

    marc21xml = """
    <record>
      <datafield tag="500" ind1=" " ind2=" ">
        <subfield code="a">note 1</subfield>
      </datafield>
      <datafield tag="500" ind1=" " ind2=" ">
        <subfield code="a">note 2</subfield>
      </datafield>
    </record>
    """
    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)
    assert data.get('note') == [{
            'noteType': 'general',
            'label': 'note 1'
        }, {
            'noteType': 'general',
            'label': 'note 2'
        }
    ]


def test_marc21_to_edition_statement_one_field_250():
    """Test dojson edition statement.
    - 1 edition designation and 1 responsibility from field 250
    """
    marc21xml = """
    <record>
      <datafield tag="250" ind1=" " ind2=" ">
        <subfield code="a">2e ed.</subfield>
        <subfield code="b">avec un avant-propos par Jean Faret</subfield>
      </datafield>
    </record>
    """
    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)
    assert data.get('editionStatement') == [{
        'editionDesignation': [
            {
                'value': '2e ed.'
            }
        ],
        'responsibility': [
            {
                'value': 'avec un avant-propos par Jean Faret'
            }
        ]
    }]


def test_marc21_to_provision_activity_ebooks_from_field_260():
    """Test provision activity Place and Date from field 260 transformation."""
    marc21xml = """
    <record>
      <datafield tag="260" ind1=" " ind2=" ">
        <subfield code="a">Lausanne :</subfield>
        <subfield code="b"/>
        <subfield code="c">[2006]</subfield>
      </datafield>
    </record>
    """
    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)
    assert data.get('provisionActivity') == [
        {
            'type': 'bf:Publication',
            'statement': [
                {
                    'label': [
                        {'value': 'Lausanne'}
                    ],
                    'type': 'bf:Place'
                },
                {
                    'label': [
                        {'value': '[2006]'}
                    ],
                    'type': 'Date'
                }

            ],
            'startDate': 2006
        }
    ]


# Copyright Date: [264 _4 $c non repetitive]
def test_marc21copyrightdate_ebooks_from_field_264_04():
    """Test dojson Copyright Date."""

    marc21xml = """
    <record>
      <datafield tag="264" ind1=" " ind2="4">
        <subfield code="c">© 1971</subfield>
      </datafield>
    </record>
    """
    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)
    assert data.get('copyrightDate') == ['© 1971']

    marc21xml = """
    <record>
      <datafield tag="264" ind1=" " ind2="4">
        <subfield code="c">© 1971 [extra 1973]</subfield>
      </datafield>
    </record>
    """
    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)
    assert data.get('copyrightDate') == ['© 1971 [extra 1973]']


def test_marc21_to_provision_activity_ebooks_from_field_264_1():
    """Test provision activity Place and Date from field 264_1 transform."""
    marc21xml = """
    <record>
      <datafield tag="264" ind1=" " ind2="1">
        <subfield code="a">Lausanne :</subfield>
        <subfield code="b">Payot,</subfield>
        <subfield code="c">[2006-2010]</subfield>
      </datafield>
    </record>
    """
    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)
    assert data.get('provisionActivity') == [
        {
            'type': 'bf:Publication',
            'statement': [
                {
                    'label': [
                        {'value': 'Lausanne'}
                    ],
                    'type': 'bf:Place'
                },
                {
                    'label': [
                        {'value': 'Payot'}
                    ],
                    'type': 'bf:Agent'
                },
                {
                    'label': [
                        {'value': '[2006-2010]'}
                    ],
                    'type': 'Date'
                }
            ],
            'startDate': 2006,
            'endDate': 2010
        }
    ]


def test_marc21_to_provision_activity_ebooks_from_field_264_2():
    """Test provision activity Place and Date from field 264_2 transform."""
    marc21xml = """
    <record>
      <datafield tag="264" ind1=" " ind2="2">
        <subfield code="a">Lausanne :</subfield>
        <subfield code="b">Payot,</subfield>
        <subfield code="c">[2006-2010]</subfield>
      </datafield>
    </record>
    """
    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)
    assert data.get('provisionActivity') == [
        {
            'type': 'bf:Distribution',
            'statement': [
                {
                    'label': [
                        {'value': 'Lausanne'}
                    ],
                    'type': 'bf:Place'
                },
                {
                    'label': [
                        {'value': 'Payot'}
                    ],
                    'type': 'bf:Agent'
                },
                {
                    'label': [
                        {'value': '[2006-2010]'}
                    ],
                    'type': 'Date'
                }

            ]
        }
    ]


def test_marc21_to_subjects():
    """Test subjects transformation.

    Test subjects in field 653.
    Checks applied:
    - duplicates subjects removal
    - generation of a list of all subjects.
    """
    marc21xml = """
    <record>
      <datafield tag="653" ind1=" " ind2=" ">
        <subfield code="a">Croissance personnelle</subfield>
        <subfield code="a">Self-Help</subfield>
        </datafield>
      <datafield tag="653" ind1=" " ind2=" ">
        <subfield code="a">Santé</subfield>
        <subfield code="a">Health</subfield>
        </datafield>
      <datafield tag="653" ind1=" " ind2=" ">
        <subfield code="a">Développement Personnel</subfield>
        <subfield code="a">Self-Help</subfield>
        </datafield>
    </record>
    """
    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)
    assert data.get('subjects') == [
        {'term': 'Croissance personnelle', 'type': 'bf:Topic'},
        {'term': 'Self-Help', 'type': 'bf:Topic'},
        {'term': 'Santé', 'type': 'bf:Topic'},
        {'term': 'Health', 'type': 'bf:Topic'},
        {'term': 'Développement Personnel', 'type': 'bf:Topic'},
        {'term': 'Self-Help', 'type': 'bf:Topic'}
    ]


def test_marc21_to_contribution():
    """Test contribution transformation.

    Test author in field 700 with first indicator = 0
    for Forename (name without comma separator).
    """
    marc21xml = """
    <record>
      <datafield tag="700" ind1="0" ind2=" ">
        <subfield code="a">Collectif</subfield>
        <subfield code="4">aut</subfield>
        </datafield>
    </record>
    """
    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)
    assert data.get('contribution') == [
        {
            'agent': {
                'type': 'bf:Person',
                'preferred_name': 'Collectif'
            },
            'role': ['aut']
        }
    ]

    marc21xml = """
    <record>
      <datafield tag="100" ind1=" " ind2=" ">
        <subfield code="a">Jean-Paul</subfield>
        <subfield code="b">II</subfield>
        <subfield code="c">Pape</subfield>
        <subfield code="d">1954-</subfield>
        <subfield code="4">aut</subfield>
      </datafield>
      <datafield tag="700" ind1=" " ind2=" ">
        <subfield code="a">Dumont, Jean</subfield>
        <subfield code="c">Historien</subfield>
        <subfield code="d">1921-2014</subfield>
        <subfield code="4">edt</subfield>
      </datafield>
      <datafield tag="710" ind1=" " ind2=" ">
        <subfield code="a">RERO</subfield>
      </datafield>
      <datafield tag="711" ind1="2" ind2=" ">
        <subfield code="a">Biennale de céramique contemporaine</subfield>
        <subfield code="n">(17 :</subfield>
        <subfield code="d">2003 :</subfield>
        <subfield code="c">Châteauroux)</subfield>
      </datafield>
    </record>
    """

    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)
    contribution = data.get('contribution')
    assert contribution == [
        {
            'agent': {
                'type': 'bf:Person',
                'preferred_name': 'Jean-Paul',
                'numeration': 'II',
                'date_of_birth': '1954',
                'qualifier': 'Pape'
            },
            'role': ['aut']
        },
        {
            'agent': {
                'type': 'bf:Person',
                'preferred_name': 'Dumont, Jean',
                'date_of_birth': '1921',
                'date_of_death': '2014',
                'qualifier': 'Historien'
            },
            'role': ['edt']
        },
        {
            'agent': {
                'type': 'bf:Organisation',
                'preferred_name': 'RERO',
                'conference': False
            },
            'role': ['ctb']
        },
        {
            'agent': {
                'type': 'bf:Organisation',
                'preferred_name': 'Biennale de céramique contemporaine',
                'conference_date': '2003',
                'numbering': '17',
                'place': 'Châteauroux',
                'conference': True
            },
            'role': ['aut']
        }

    ]


def test_marc21_to_contribution_and_translator():
    """Test contribution and translator transformation.

    Test author and translator in fields 700 with first indicator = 1
    for Surname (name with comma separator).
    """
    marc21xml = """
    <record>
      <datafield tag="700" ind1="1" ind2=" ">
        <subfield code="a">Peeters, Hagar</subfield>
        <subfield code="4">aut</subfield>
        </datafield>
      <datafield tag="700" ind1="1" ind2=" ">
        <subfield code="a">Maufroy, Sandrine</subfield>
        <subfield code="4">trl</subfield>
        </datafield>
    </record>
    """
    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)
    assert data.get('contribution') == [
        {
            'agent': {
                'type': 'bf:Person',
                'preferred_name': 'Peeters, Hagar'
            },
            'role': ['aut']
        },
        {
            'agent': {
                'type': 'bf:Person',
                'preferred_name': 'Maufroy, Sandrine'
            },
            'role': ['trl']
        }
    ]


def test_marc21_electronicLocator_ebooks():
    """Harvested_resources tests."""
    marc21xml = """
    <record>
      <datafield tag="856" ind1="4" ind2="0">
        <subfield code="u">http://site1.org/resources/1</subfield>
        <subfield code="x">ebibliomedia</subfield>
      </datafield>
      <datafield tag="856" ind1="4" ind2="0">
        <subfield code="u">http://site5.org/resources/1</subfield>
        <subfield code="x">mv-cantook</subfield>
      </datafield>
      <datafield tag="856" ind1="4" ind2="2">
        <subfield code="3">Image de couverture</subfield>
        <subfield code="u">http://site2.org/resources/2</subfield>
      </datafield>
      <datafield tag="856" ind1="4" ind2="2">
        <subfield code="3">Extrait</subfield>
        <subfield code="u">https://www.edenlivres.fr/p/172480</subfield>
        </datafield>
    </record>
    """
    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)
    assert data.get('electronicLocator') == [
        {
            'url': 'http://site1.org/resources/1',
            'type': 'resource',
            'source': 'ebibliomedia'
        },
        {
            'url': 'http://site5.org/resources/1',
            'type': 'resource',
            'source': 'mv-cantook'
        },
        {
            'url': 'http://site2.org/resources/2',
            'type': 'relatedResource',
            'content': 'coverImage'
        }
    ]


def test_marc21_cover_art_ebooks():
    """Cover art tests."""
    marc21xml = """
    <record>
      <datafield tag="856" ind1="4" ind2="2">
        <subfield code="3">Image de couverture</subfield>
        <subfield code="u">http://site2.org/resources/2</subfield>
      </datafield>
      <datafield tag="856" ind1="4" ind2="2">
        <subfield code="3">test</subfield>
        <subfield code="u">http://site3.org/resources/2</subfield>
      </datafield>
    </record>
    """
    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)
    assert data.get('electronicLocator') == [
        {
            'url': 'http://site2.org/resources/2',
            'type': 'relatedResource',
            'content': 'coverImage'
        }
    ]
