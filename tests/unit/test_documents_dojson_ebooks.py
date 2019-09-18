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
        <subfield code="a">feedhttps-www-feedbooks-com-book-414-epub</subfield>
      </datafield>
    </record>
    """
    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)
    assert not data.get('identifiedBy')


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
    assert data.get('type') == 'ebook'


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
    assert data.get('title') == 'Elena et les joueuses'


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


def test_marc21_to_abstracts():
    """Test abstracts transformation.

    Test abstracts in multiples fields 520.
    """
    marc21xml = """
    <record>
      <datafield tag="520" ind1=" " ind2=" ">
        <subfield code="a">Il fait si chaud à Paris l’après-midi</subfield>
        </datafield>
      <datafield tag="520" ind1=" " ind2=" ">
        <subfield code="a">Promenade à Paris</subfield>
        </datafield>
    </record>
    """
    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)
    assert data.get('abstracts') == [
        'Il fait si chaud à Paris l’après-midi',
        'Promenade à Paris'
    ]


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
                }
            ],
            'startDate': '2006',
            'date': '[2006]'
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
                }
            ],
            'startDate': '2006',
            'endDate': '2010',
            'date': '[2006-2010]'
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
                }
            ],
            'date': '[2006-2010]'
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
        'Croissance personnelle',
        'Self-Help',
        'Santé',
        'Health',
        'Développement Personnel',
        'Self-Help'
    ]


def test_marc21_to_authors():
    """Test authors transformation.

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
    assert data.get('authors') == [
        {'type': 'person', 'name': 'Collectif'}
    ]


def test_marc21_to_authors_and_translator():
    """Test authors and translator transformation.

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
    assert data.get('authors') == [
        {'type': 'person', 'name': 'Peeters, Hagar'},
        {'type': 'person', 'name': 'Maufroy, Sandrine'}
    ]


def test_marc21_electronic_location_ebooks():
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
    assert data.get('electronic_location') == [
        {
            'source': 'ebibliomedia',
            'uri': 'http://site1.org/resources/1'
        },
        {
            'source': 'mv-cantook',
            'uri': 'http://site5.org/resources/1'
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
    assert data.get('cover_art') == 'http://site2.org/resources/2'
