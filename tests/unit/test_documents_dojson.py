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

"""DOJSON module tests."""

from __future__ import absolute_import, print_function

import os

import mock
from dojson.contrib.marc21.utils import create_record
from utils import mock_response

from rero_ils.dojson.utils import not_repetitive
from rero_ils.modules.documents.dojson.contrib.marc21tojson import marc21
from rero_ils.modules.documents.dojson.contrib.marc21tojson.model import \
    get_contribution_link
from rero_ils.modules.documents.views import create_publication_statement, \
    get_cover_art, get_other_accesses


def test_not_repetetive(capsys):
    """Test the function not_repetetive."""
    data_dict = {'sub': ('first', 'second')}
    data = not_repetitive(
        bibid='pid1',
        reroid='rero1',
        key='key',
        value=data_dict,
        subfield='sub'
    )
    assert data == 'first'
    out, err = capsys.readouterr()
    assert out == \
        'WARNING NOT REPETITIVE:\tpid1\trero1\tkey\tsub\t{data}\t\n'.format(
            data=str(data_dict)
        )
    data = {'sub': 'only'}
    data = not_repetitive(
        bibid='pid1',
        reroid='rero1',
        key='key',
        value=data,
        subfield='sub',
        default=''
    )
    assert data == 'only'
    out, err = capsys.readouterr()
    assert out == ''


# type: leader
def test_marc21_to_type():
    """
    Test dojson marc21_to_type.

    339
    $a: main_type
    $b: subtype
    """

    marc21xml = """
    <record>
        <leader>00501nam a2200133 a 4500</leader>
        <datafield tag="339" ind1=" " ind2=" ">
            <subfield code="a">docmaintype_book</subfield>
            <subfield code="b">docsubtype_other_book</subfield>
        </datafield>
    </record>
    """
    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)
    assert data.get('type') == [{
        'main_type': 'docmaintype_book',
        'subtype': 'docsubtype_other_book'
    }]

    marc21xml = """
    <record>
        <leader>00501nam a2200133 a 4500</leader>
        <datafield tag="339" ind1=" " ind2=" ">
            <subfield code="a">docmaintype_book</subfield>
            <subfield code="b">docsubtype_other_book</subfield>
        </datafield>
        <datafield tag="339" ind1=" " ind2=" ">
            <subfield code="a">docmaintype_score</subfield>
            <subfield code="b">docsubtype_printed_score</subfield>
        </datafield>
    </record>
    """

    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)
    assert data.get('type') == [
        {
            'main_type': 'docmaintype_book',
            'subtype': 'docsubtype_other_book'
        },
        {
            'main_type': 'docmaintype_score',
            'subtype': 'docsubtype_printed_score'
        }
    ]


def test_marc21_to_admin_metadata():
    """
    Test dojson marc21_to_admin_metadata (L34, L37, 45).
    """

    marc21xml = """
    <record>
        <leader>00501naa a2200133 a 4500</leader>
        <controlfield tag=
            "008">160315s2015    cc ||| |  ||||00|  |chi d</controlfield>
    </record>
    """
    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)
    assert data.get('adminMetadata') == {
      'encodingLevel': 'Full level'
    }

    marc21xml = """
    <record>
        <leader>00501naa a22001332a 4500</leader>
        <controlfield tag=
            "008">160315s2015    cc ||| |  ||||00|  |chi d</controlfield>
        <datafield tag="019" ind1=" " ind2=" ">
          <subfield code="a">Société de publications romanes</subfield>
          <subfield code="9">pf/08.05.1985</subfield>
        </datafield>
    </record>
    """
    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)
    assert data.get('adminMetadata') == {
      'encodingLevel': 'Less-than-full level, material not examined',
      'note': ['Société de publications romanes (pf/08.05.1985)'],
    }

    marc21xml = """
    <record>
        <leader>00501naa a22001332a 4500</leader>
        <controlfield tag=
            "008">160315s2015    cc ||| |  ||||00|  |chi d</controlfield>
        <datafield tag="019" ind1=" " ind2=" ">
          <subfield code="a">Notice privée</subfield>
          <subfield code="9">vsbcce/02.2013</subfield>
        </datafield>
        <datafield tag="351" ind1=" " ind2=" ">
          <subfield code="c">Fonds</subfield>
        </datafield>
    </record>
    """
    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)
    assert data.get('adminMetadata') == {
      'encodingLevel': 'Less-than-full level, material not examined',
      'note': [
        'Notice privée (vsbcce/02.2013)',
        'Fonds'
      ],
    }

    # field 351 with missing $c
    marc21xml = """
    <record>
        <leader>00501naa a22001332a 4500</leader>
        <controlfield tag=
            "008">160315s2015    cc ||| |  ||||00|  |chi d</controlfield>
        <datafield tag="019" ind1=" " ind2=" ">
          <subfield code="a">Notice privée</subfield>
          <subfield code="9">vsbcce/02.2013</subfield>
        </datafield>
        <datafield tag="351" ind1=" " ind2=" ">
          <subfield code="a">Fonds</subfield>
        </datafield>
    </record>
    """
    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)
    assert data.get('adminMetadata') == {
      'encodingLevel': 'Less-than-full level, material not examined',
      'note': [
        'Notice privée (vsbcce/02.2013)'
      ],
    }

    marc21xml = """
    <record>
        <leader>00501naa a2200133?a 4500</leader>
        <controlfield tag=
            "008">160315s2015    cc ||| |  ||||00|  |chi d</controlfield>
        <datafield tag="040" ind1=" " ind2=" ">
          <subfield code="a">DLC</subfield>
          <subfield code="b">ger</subfield>
          <subfield code="e">rda</subfield>
          <subfield code="d">SzZuIDS NEBIS ZBZ</subfield>
          <subfield code="d">RERO vsbcvs</subfield>
        </datafield>
    </record>
    """
    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)
    assert data.get('adminMetadata') == {
      'encodingLevel': 'Unknown',
      'source': 'DLC',
      'descriptionModifier': ['SzZuIDS NEBIS ZBZ', 'RERO vsbcvs'],
      'descriptionLanguage': 'ger',
      'descriptionConventions': ['rda'],
    }


def test_marc21_to_mode_of_issuance():
    """
    Test dojson marc21_to_mode_issuance.
    """

    marc21xml = """
    <record>
        <leader>00501naa a2200133 a 4500</leader>
        <controlfield tag=
            "008">160315s2015    cc ||| |  ||||00|  |chi d</controlfield>
    </record>
    """
    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)
    assert data.get('issuance') == {
        'main_type': 'rdami:1001',
        'subtype': 'article'
    }

    marc21xml = """
    <record>
        <leader>00501nab a2200133 a 4500</leader>
        <controlfield tag=
            "008">160315s2015    cc ||| |  ||||00|  |chi d</controlfield>
    </record>
    """
    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)
    assert data.get('issuance') == {
        'main_type': 'rdami:1003',
        'subtype': 'serialInSerial'
    }

    marc21xml = """
    <record>
        <leader>00501nac a2200133 a 4500</leader>
        <controlfield tag=
            "008">160315s2015    cc ||| |  ||||00|  |chi d</controlfield>
    </record>
    """
    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)
    assert data.get('issuance') == {
        'main_type': 'rdami:1001',
        'subtype': 'privateFile'
    }

    marc21xml = """
    <record>
        <leader>00501nad a2200133 a 4500</leader>
        <controlfield tag=
            "008">160315s2015    cc ||| |  ||||00|  |chi d</controlfield>
    </record>
    """
    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)
    assert data.get('issuance') == {
        'main_type': 'rdami:1001',
        'subtype': 'privateSubfile'
    }

    marc21xml = """
    <record>
        <leader>00501nam a2200133 a 4500</leader>
        <controlfield tag=
            "008">160315s2015    cc ||| |  ||||00|  |chi d</controlfield>
    </record>
    """
    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)
    assert data.get('issuance') == {
        'main_type': 'rdami:1001',
        'subtype': 'materialUnit'
    }

    marc21xml = """
    <record>
        <leader>00501nam a2200133 a 4500</leader>
        <controlfield tag=
            "008">160315s2015    cc ||| |  ||||00|  |chi d</controlfield>
        <datafield tag="019" ind1="3" ind2=" ">
            <subfield code="a">Note interne</subfield>
        </datafield>
        <datafield tag="019" ind1="3" ind2=" ">
            <subfield code="a">Niveau supérieur</subfield>
        </datafield>
    </record>
    """
    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)
    assert data.get('issuance') == {
        'main_type': 'rdami:1002',
        'subtype': 'set'
    }

    marc21xml = """
    <record>
        <leader>00501nai a2200133 a 4500</leader>
        <controlfield tag=
            "008">160315s2015    cc |||d|  ||||00|  |chi d</controlfield>
    </record>
    """
    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)
    assert data.get('issuance') == {
        'main_type': 'rdami:1004',
        'subtype': 'updatingWebsite'
    }

    marc21xml = """
    <record>
        <leader>00501nai a2200133 a 4500</leader>
        <controlfield tag=
            "008">160315s2015    cc |||l|  ||||00|  |chi d</controlfield>
    </record>
    """
    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)
    assert data.get('issuance') == {
        'main_type': 'rdami:1004',
        'subtype': 'updatingLoose-leaf'
    }

    marc21xml = """
    <record>
        <leader>00501nai a2200133 a 4500</leader>
        <controlfield tag=
            "008">160315s2015    cc |||w|  ||||00|  |chi d</controlfield>
    </record>
    """
    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)
    assert data.get('issuance') == {
        'main_type': 'rdami:1004',
        'subtype': 'updatingWebsite'
    }

    marc21xml = """
    <record>
        <leader>00501nas a2200133 a 4500</leader>
        <controlfield tag=
            "008">160315s2015    cc |||m|  ||||00|  |chi d</controlfield>
    </record>
    """
    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)
    assert data.get('issuance') == {
        'main_type': 'rdami:1003',
        'subtype': 'monographicSeries'
    }

    marc21xml = """
    <record>
        <leader>00501nas a2200133 a 4500</leader>
        <controlfield tag=
            "008">160315s2015    cc |||p|  ||||00|  |chi d</controlfield>
    </record>
    """
    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)
    assert data.get('issuance') == {
        'main_type': 'rdami:1003',
        'subtype': 'periodical'
    }

    marc21xml = """
    <record>
        <leader>00604cam a2200205 a 4500</leader>
          <controlfield tag=
            "008">150707m20159999fr |||m|| ||||00|| 0fre d</controlfield>
    </record>
    """
    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)
    assert data.get('issuance') == {
        'main_type': 'rdami:1002',
        'subtype': 'set'
    }


# pid: 001
def test_marc21_to_pid():
    """Test dojson marc21languages."""

    marc21xml = """
    <record>
      <controlfield tag="001">
        REROILS:123456789
      </controlfield>
    </record>
    """
    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)
    assert data.get('pid') == '123456789'
    marc21xml = """
    <record>
      <controlfield tag="001">
        123456789
      </controlfield>
    </record>
    """
    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)
    assert data.get('pid') is None


def test_marc21_to_title_245_with_sufield_c_having_square_bracket():
    """Test dojson test_marc21_to_title_245_without_246.

    - field 245 with subfields $a $b $c
    - subfields 245 $a without '='
    - subfields 245 $c with '[]'
    - field 246 is not present
    """

    marc21xml = """
    <record>
      <controlfield tag=
          "008">110729s2011    xx ||| |  ||||00|  |und d</controlfield>
      <datafield tag="035" ind1=" " ind2=" ">
        <subfield code="a">R006114538</subfield>
      </datafield>
      <datafield ind1="0" ind2="0" tag="245">
        <subfield code="a">Ma ville en vert :</subfield>
        <subfield code="b">pour un retour de la nature /</subfield>
        <subfield code="c">[Robert Klant ... [et al.] ; [Kitty B.]</subfield>
        </datafield>
    </record>
    """
    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)
    assert data.get('title') == [
        {
            'type': 'bf:Title',
            'mainTitle': [
                {'value': 'Ma ville en vert'}
            ],
            'subtitle': [
                {'value': 'pour un retour de la nature'}
            ],
        }
    ]
    assert data.get('responsibilityStatement') == [
        [
            {'value': '[Robert Klant ... [et al.]'}
        ],
        [
            {'value': '[Kitty B.]'}
        ]
    ]


def test_marc21_to_title_245_with_two_246():
    """Test dojson title with a 245 and two 246.

    - field 245 with subfields $a $b $c
    - subfields 245 $a ending with '='
    - 2 fields 246 are present
    - field 880 exists for the field 245
    """

    marc21xml = """
    <record>
        <controlfield tag=
            "008">160315s2015    cc ||| |  ||||00|  |chi d</controlfield>
        <datafield tag="035" ind1=" " ind2=" ">
            <subfield code="a">R008388656</subfield>
        </datafield>
        <datafield tag="245" ind1="0" ind2="0">
            <subfield code="6">880-01</subfield>
            <subfield code="a">Guo ji fa =</subfield>
            <subfield code="b">International law /</subfield>
            <subfield code=
            "c">Liang Xi yuan zhu zhu bian, Wang Xianshu fu zhu bian</subfield>
        </datafield>
        <datafield tag="246" ind1="3" ind2=" ">
            <subfield code="a">Guojifa</subfield>
        </datafield>
        <datafield tag="246" ind1="3" ind2=" ">
            <subfield code="a">International law</subfield>
        </datafield>
        <datafield tag="880" ind1="0" ind2="0">
            <subfield code="6">245-01/$1</subfield>
            <subfield code="a">国际法 =</subfield>
            <subfield code="b">International law /</subfield>
            <subfield code="c">梁西原著主编, 王献枢副主编</subfield>
        </datafield>
    </record>
    """
    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)
    assert data.get('title') == [
        {
            'type': 'bf:Title',
            'mainTitle': [
                {'value': 'Guo ji fa'},
                {
                    'value': '国际法',
                    'language': 'chi-hani'
                }
            ]
        },
        {
            'type': 'bf:ParallelTitle',
            'mainTitle': [
                {'value': 'International law'},
                {
                    'value': 'International law',
                    'language': 'chi-hani'
                }
            ]
        },
        {
            'type': 'bf:VariantTitle',
            'mainTitle': [{'value': 'Guojifa'}]
        }
    ]
    assert data.get('responsibilityStatement') == [
        [
            {
                'value': 'Liang Xi yuan zhu zhu bian, Wang Xianshu fu zhu bian'
            },
            {
                'value': '梁西原著主编, 王献枢副主编',
                'language': 'chi-hani'
            }
        ]
    ]


def test_marc21_to_title_245_without_246():
    """Test dojson test_marc21_to_title_245_without_246.

    - field 245 with subfields $a $b $c
    - subfields 245 $a without '='
    - field 246 is not present
    - field 880 exists for the field 245
    """

    marc21xml = """
    <record>
      <controlfield tag=
          "008">170626s2017    ru ||| |  ||||00|  |rus d</controlfield>
      <datafield tag="035" ind1=" " ind2=" ">
        <subfield code="a">0073195</subfield>
      </datafield>
      <datafield tag="245" ind1="1" ind2="0">
        <subfield code="6">880-02</subfield>
        <subfield code="a">L.N. Tolstoĭ :</subfield>
        <subfield code="b">seminariĭ /</subfield>
        <subfield code="c">B.I. Bursov</subfield>
      </datafield>
      <datafield tag="880" ind1="1" ind2="0">
        <subfield code="6">245-02/(N</subfield>
        <subfield code="a">Л.Н. Толстой :</subfield>
        <subfield code="b">семинарий /</subfield>
        <subfield code="c">Б.И. Бурсов</subfield>
      </datafield>
    </record>
    """
    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)
    assert data.get('title') == [
        {
            'type': 'bf:Title',
            'mainTitle': [
                {'value': 'L.N. Tolstoĭ'},
                {
                    'value': 'Л.Н. Толстой',
                    'language': 'rus-cyrl'
                }
            ],
            'subtitle': [
                {'value': 'seminariĭ'},
                {
                    'value': 'семинарий',
                    'language': 'rus-cyrl'
                }
            ],
        }
    ]
    assert data.get('responsibilityStatement') == [
        [
            {'value': 'B.I. Bursov'},
            {
                'value': 'Б.И. Бурсов',
                'language': 'rus-cyrl'
            }
        ]
    ]


def test_marc21_to_title_245_with_part_without_246():
    """Test dojson test_marc21_to_title_245_without_246.

    - field 245 with subfields $a $b $c $n $p
    - subfields 245 $a without '='
    - field 246 is not present
    - field 880 exists for the field 245
    """

    marc21xml = """
    <record>
      <controlfield tag=
          "008">170626s2017    ru ||| |  ||||00|  |rus d</controlfield>
      <datafield tag="035" ind1=" " ind2=" ">
        <subfield code="a">0073195</subfield>
      </datafield>
      <datafield tag="245" ind1="1" ind2="0">
        <subfield code="6">880-02</subfield>
        <subfield code="a">L.N. Tolstoĭ :</subfield>
        <subfield code="b">seminariĭ /</subfield>
        <subfield code="c">B.I. Bursov</subfield>
        <subfield code="n">part number</subfield>
        <subfield code="p">part name</subfield>
        <subfield code="n">part number 2</subfield>
      </datafield>
      <datafield tag="880" ind1="1" ind2="0">
        <subfield code="6">245-02/(N</subfield>
        <subfield code="a">Л.Н. Толстой :</subfield>
        <subfield code="b">семинарий /</subfield>
        <subfield code="c">Б.И. Бурсов</subfield>
        <subfield code="n">Part Number</subfield>
        <subfield code="p">Part Name</subfield>
        <subfield code="n">Part Number 2</subfield>
     </datafield>
    </record>
    """
    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)
    assert data.get('title') == [
        {
            'mainTitle': [
                {'value': 'L.N. Tolstoĭ'},
                {
                    'value': 'Л.Н. Толстой',
                    'language': 'rus-cyrl'
                }
            ],
            'subtitle': [
                {'value': 'seminariĭ'},
                {
                    'value': 'семинарий',
                    'language': 'rus-cyrl'
                }
            ],
            'type': 'bf:Title',
            'part': [{
                    'partNumber': [
                        {'value': 'part number'},
                        {
                            'value': 'Part Number',
                            'language': 'rus-cyrl'
                        }
                    ],
                    'partName': [
                        {'value': 'part name'},
                        {
                            'value': 'Part Name',
                            'language': 'rus-cyrl'
                        }
                    ]
                },
                {
                    'partNumber': [
                        {'value': 'part number 2'},
                        {
                            'value': 'Part Number 2',
                            'language': 'rus-cyrl'
                        }
                    ]
                }
            ]
        }
    ]
    assert data.get('responsibilityStatement') == [
        [
            {'value': 'B.I. Bursov'},
            {
                'value': 'Б.И. Бурсов',
                'language': 'rus-cyrl'
            }
        ]
    ]


def test_marc21_to_title_with_multiple_parts():
    """Test for 245 having multiples $n and $p.

    - field 245 with subfields $a $b $c $n $p
    - subfields 245 $a without '='
    - field 246 is not present
    """

    marc21xml = """
    <record>
        <controlfield tag=
          "008">170626s2017    ru ||| |  ||||00|  |rus d</controlfield>
        <datafield tag="035" ind1=" " ind2=" ">
            <subfield code="a">0015425</subfield>
        </datafield>
        <datafield tag="245" ind1="1" ind2="0">
            <subfield code="a">Statistique :</subfield>
            <subfield code="b">exercices corrigés /</subfield>
            <subfield code="c">Christian Labrousse.</subfield>
            <subfield code="n">T. 1,</subfield>
            <subfield code="p">Tome 1</subfield>
            <subfield code="n">T. 2,</subfield>
            <subfield code="p">Tome 2,</subfield>
            <subfield code="p">Tome 3,</subfield>
            <subfield code="n">T. 4,</subfield>
            <subfield code="n">T. 5,</subfield>
        </datafield>
    </record>
    """
    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)
    assert data.get('title') == [
        {
            'type': 'bf:Title',
            'mainTitle': [{'value': 'Statistique'}],
            'subtitle': [{'value': 'exercices corrigés'}],
            'part': [
                {
                    'partNumber': [{'value': 'T. 1'}],
                    'partName': [{'value': 'Tome 1'}]
                },
                {
                    'partNumber': [{'value': 'T. 2'}],
                    'partName': [{'value': 'Tome 2'}]
                },
                {
                    'partName': [{'value': 'Tome 3'}]

                },
                {
                    'partNumber': [{'value': 'T. 4'}]
                },
                {
                    'partNumber': [{'value': 'T. 5'}]
                }
            ]
        }
    ]
    assert data.get('responsibilityStatement') == [
        [
            {'value': 'Christian Labrousse'}
        ]
    ]


def test_marc21_to_title_245_and_246():
    """Test dojson test_marc21_to_title_245_without_246.

    - field 245 with subfields $a $b $c
    - subfield 245 $a did not end with '='
    - field 246 exists
    - field 880 exists for the field 245
    """

    marc21xml = """
    <record>
      <controlfield tag=
          "008">170626s2017    ru ||| |  ||||00|  |rus d</controlfield>
      <datafield tag="035" ind1=" " ind2=" ">
        <subfield code="a">0073195</subfield>
      </datafield>
      <datafield tag="245" ind1="1" ind2="0">
        <subfield code="6">880-02</subfield>
        <subfield code="a">L.N. Tolstoĭ :</subfield>
        <subfield code="b">seminariĭ /</subfield>
        <subfield code="c">B.I. Bursov</subfield>
      </datafield>
      <datafield tag="246" ind1="3" ind2=" ">
        <subfield code="a">L.N. Tolstoj : seminarij / B.I. Bursov</subfield>
      </datafield>
      <datafield tag="880" ind1="1" ind2="0">
        <subfield code="6">245-02/(N</subfield>
        <subfield code="a">Л.Н. Толстой :</subfield>
        <subfield code="b">семинарий /</subfield>
        <subfield code="c">Б.И. Бурсов</subfield>
      </datafield>
    </record>
    """
    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)
    assert data.get('title') == [
        {
            'type': 'bf:Title',
            'mainTitle': [
                {'value': 'L.N. Tolstoĭ'},
                {
                    'value': 'Л.Н. Толстой',
                    'language': 'rus-cyrl'
                }
            ],
            'subtitle': [
                {'value': 'seminariĭ'},
                {
                    'value': 'семинарий',
                    'language': 'rus-cyrl'
                }
            ]
        },
        {
            'type': 'bf:VariantTitle',
            'mainTitle': [{'value': 'L.N. Tolstoj'}],
            'subtitle': [{'value': 'seminarij / B.I. Bursov'}]
        }
    ]
    assert data.get('responsibilityStatement') == [
        [
            {'value': 'B.I. Bursov'},
            {
                'value': 'Б.И. Бурсов',
                'language': 'rus-cyrl'
            }
        ]
    ]


def test_marc21_to_title_245_and_246_with_multiple_responsibilities():
    """Test dojson test_marc21_to_title_245_without_246.

    - field 245 with subfields $a $b $c
    - subfield 245 $c contains multiple responsibilities separeted with ';'
    - field 246 exists
    - field 880 exists for the field 245
    """

    marc21xml = """
    <record>
      <controlfield tag=
          "008">170626s2017    ru ||| |  ||||00|  |rus d</controlfield>
      <datafield tag="035" ind1=" " ind2=" ">
        <subfield code="a">0073195</subfield>
      </datafield>
      <datafield tag="245" ind1="1" ind2="0">
        <subfield code="6">880-02</subfield>
        <subfield code="a">L.N. Tolstoĭ :</subfield>
        <subfield code="b">seminariĭ /</subfield>
        <subfield code="c">B.I. Bursov ; Tolstoĭ</subfield>
      </datafield>
      <datafield tag="246" ind1="3" ind2=" ">
        <subfield code="a">L.N. Tolstoj : seminarij / B.I. Bursov</subfield>
      </datafield>
      <datafield tag="880" ind1="1" ind2="0">
        <subfield code="6">245-02/(N</subfield>
        <subfield code="a">Л.Н. Толстой :</subfield>
        <subfield code="b">семинарий /</subfield>
        <subfield code="c">Б.И. Бурсов ; Толстой</subfield>
      </datafield>
    </record>
    """
    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)
    assert data.get('title') == [
        {
            'type': 'bf:Title',
            'mainTitle': [
                {'value': 'L.N. Tolstoĭ'},
                {
                    'value': 'Л.Н. Толстой',
                    'language': 'rus-cyrl'
                }
            ],
            'subtitle': [
                {'value': 'seminariĭ'},
                {
                    'value': 'семинарий',
                    'language': 'rus-cyrl'
                }
            ]
        },
        {
            'type': 'bf:VariantTitle',
            'mainTitle': [{'value': 'L.N. Tolstoj'}],
            'subtitle': [{'value': 'seminarij / B.I. Bursov'}]
        }
    ]
    assert data.get('responsibilityStatement') == [
        [
            {'value': 'B.I. Bursov'},
            {
                'value': 'Б.И. Бурсов',
                'language': 'rus-cyrl'
            }
        ],
        [
            {'value': 'Tolstoĭ'},
            {
                'value': 'Толстой',
                'language': 'rus-cyrl'
            }
        ]
    ]


def test_marc21_to_title_with_variant_without_subtitle():
    """Test dojson title with variant without subtitle.

    - field 245 with subfields $a $b $c
    - subfield 245 $a did not end with '='
    - field 246 with subfield $a $n $p
    """

    marc21xml = """
    <record>
      <controlfield tag=
        "008">000725d19802015sz |||p|| ||||0 || 0fre d</controlfield>
      <datafield tag="035" ind1=" " ind2=" ">
        <subfield code="a">0369784</subfield>
      </datafield>
      <datafield tag="245" ind1="0" ind2="0">
        <subfield code="a">TRANEL :</subfield>
        <subfield code="b">travaux neuchâtelois de linguistique /</subfield>
        <subfield code="c">Institut de linguistique, UNINE</subfield>
      </datafield>
      <datafield tag="246" ind1="3" ind2=" ">
        <subfield code="a">Travaux neuchâtelois de linguistique</subfield>
        <subfield code="n">T. 1,</subfield>
        <subfield code="p">Tome 1</subfield>
     </datafield>
    </record>
    """
    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)
    assert data.get('title') == [
        {
            'type': 'bf:Title',
            'mainTitle': [
                {'value': 'TRANEL'}
            ],
            'subtitle': [
                {'value': 'travaux neuchâtelois de linguistique'},
            ]
        },
        {
            'type': 'bf:VariantTitle',
            'mainTitle': [
                {'value': 'Travaux neuchâtelois de linguistique'}
            ],
            'part': [{
                    'partNumber': [{'value': 'T. 1'}],
                    'partName': [{'value': 'Tome 1'}]
            }]
        }
    ]
    assert data.get('responsibilityStatement') == [
        [{'value': 'Institut de linguistique, UNINE'}]
    ]


def test_marc21_to_title_with_variant_both_without_subtitle():
    """Test dojson title with variant both without subtitle.

    - field 245 with subfields $a $c
    - subfield 245 $a did not end with '='
    - field 246 with subfield $a only
    """
    marc21xml = """
    <record>
      <controlfield tag=
        "008">060608s2005    fr ||| |  ||||00|  |fre d</controlfield>
      <datafield tag="035" ind1=" " ind2=" ">
        <subfield code="a">R004471762</subfield>
      </datafield>
      <datafield tag="245" ind1="1" ind2="0">
        <subfield code="a">3 filles et 10 kilos en trop /</subfield>
        <subfield code="c">Jacqueline Wilson</subfield>
      </datafield>
      <datafield tag="246" ind1="3" ind2=" ">
        <subfield code="a">Trois filles et dix kilos en trop</subfield>
      </datafield>
    </record>
    """

    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)
    assert data.get('title') == [
        {
            'type': 'bf:Title',
            'mainTitle': [{'value': '3 filles et 10 kilos en trop'}]
        },
        {
            'type': 'bf:VariantTitle',
            'mainTitle': [{'value': 'Trois filles et dix kilos en trop'}]
        }
    ]
    assert data.get('responsibilityStatement') == [
        [{'value': 'Jacqueline Wilson'}]
    ]


def test_marc21_to_title_with_parallel_title():
    """Test dojson title with parallel title.

    - field 245 with subfields $a $b $c
    - subfield 245 $a did not end with '='
    - field 246 with subfield $a only
    """
    marc21xml = """
    <record>
      <controlfield tag=
        "008">001224s1980    sz |||||| ||||00|| |ger d</controlfield>
      <datafield tag="035" ind1=" " ind2=" ">
        <subfield code="a">0295517</subfield>
      </datafield>
      <datafield tag="245" ind1="0" ind2="0">
        <subfield code="a">Schatzkammer der Schweiz :</subfield>
        <subfield code="b">Landesmuseums = Le Patrimoine Suisse : joyaux """ \
    """= Patrimonio : oggetti preziosi /</subfield>
        <subfield code="c">Redaktion J. Schneider ; Texte R. Degan</subfield>
      </datafield>
      <datafield tag="246" ind1="3" ind2=" ">
        <subfield code="a">Patrimoine Suisse</subfield>
      </datafield>
      <datafield tag="246" ind1="3" ind2=" ">
        <subfield code="a">Patrimonio culturale della Svizzera</subfield>
      </datafield>
    </record>    """

    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)
    assert data.get('title') == [
        {
            'type': 'bf:Title',
            'mainTitle': [{'value': 'Schatzkammer der Schweiz'}],
            'subtitle': [{'value': 'Landesmuseums'}]
        },
        {
            'type': 'bf:ParallelTitle',
            'mainTitle': [{'value': 'Le Patrimoine Suisse'}],
            'subtitle': [{'value': 'joyaux'}]
        },
        {
            'type': 'bf:ParallelTitle',
            'mainTitle': [{'value': 'Patrimonio'}],
            'subtitle': [{'value': 'oggetti preziosi'}]

        },
        {
            'type': 'bf:VariantTitle',
            'mainTitle': [{'value': 'Patrimonio culturale della Svizzera'}]
        }
    ]
    assert data.get('responsibilityStatement') == [
        [{'value': 'Redaktion J. Schneider'}],
        [{'value': 'Texte R. Degan'}]
    ]


def test_marc21_to_title_245_with_parallel_title_and_246():
    """Test dojson test_marc21_to_title_245_without_246.

    - field 245 with subfields $a $b $c
    - subfield 245 $a did not end with '='
    - field 246 exists
    - field 880 exists for the field 245
    """

    marc21xml = """
    <record>
      <controlfield tag=
          "008">170626s2017    ru ||| |  ||||00|  |rus d</controlfield>
      <datafield tag="035" ind1=" " ind2=" ">
        <subfield code="a">0073195</subfield>
      </datafield>
      <datafield tag="245" ind1="1" ind2="0">
        <subfield code="6">880-02</subfield>
        <subfield code="a">L.N. Tolstoĭ :</subfield>
        <subfield code="b">seminariĭ = TOTO : TITI /</subfield>
        <subfield code="c">B.I. Bursov</subfield>
      </datafield>
      <datafield tag="246" ind1="3" ind2=" ">
        <subfield code="a">L.N. Tolstoj : seminarij / B.I. Bursov</subfield>
      </datafield>
      <datafield tag="880" ind1="1" ind2="0">
        <subfield code="6">245-02/(N</subfield>
        <subfield code="a">Л.Н. Толстой :</subfield>
        <subfield code="b">семинарий = toto : titi /</subfield>
        <subfield code="c">Б.И. Бурсов</subfield>
      </datafield>
    </record>
    """
    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)
    assert data.get('title') == [
        {
            'type': 'bf:Title',
            'mainTitle': [
                {'value': 'L.N. Tolstoĭ'},
                {
                    'value': 'Л.Н. Толстой',
                    'language': 'rus-cyrl'
                }
            ],
            'subtitle': [
                {'value': 'seminariĭ'},
                {
                    'value': 'семинарий',
                    'language': 'rus-cyrl'
                }
            ]
        },
        {
            'type': 'bf:ParallelTitle',
            'mainTitle': [
                {'value': 'TOTO'},
                {
                    'value': 'toto',
                    'language': 'rus-cyrl'
                }
            ],
            'subtitle': [
                {'value': 'TITI'},
                {
                    'value': 'titi',
                    'language': 'rus-cyrl'
                }
            ]
        },
        {
            'type': 'bf:VariantTitle',
            'mainTitle': [{'value': 'L.N. Tolstoj'}],
            'subtitle': [{'value': 'seminarij / B.I. Bursov'}]
        }
    ]
    assert data.get('responsibilityStatement') == [
        [
            {'value': 'B.I. Bursov'},
            {
                'value': 'Б.И. Бурсов',
                'language': 'rus-cyrl'
            }
        ]
    ]


# titleProper: [730$a repetitive]
def test_marc21_to_titlesProper():
    """Test dojson marc21titlesProper."""

    marc21xml = """
    <record>
      <datafield tag="730" ind1="1" ind2="0">
        <subfield code="a">proper title</subfield>
      </datafield>
    </record>
    """
    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)
    assert data.get('titlesProper') == ['proper title']

    marc21xml = """
    <record>
      <datafield tag="730" ind1=" " ind2=" ">
        <subfield code="a">proper title</subfield>
      </datafield>
      <datafield tag="730" ind1=" " ind2=" ">
         <subfield code="a">other proper title</subfield>
       </datafield>
    </record>
    """
    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)
    assert data.get('titlesProper') == ['proper title', 'other proper title']


# languages: 008 and 041 [$a, repetitive]
def test_marc21_to_language():
    """Test dojson marc21languages."""

    marc21xml = """
    <record>
      <controlfield tag="008">{field_008}</controlfield>
      <datafield tag="041" ind1=" " ind2=" ">
        <subfield code="a">ara</subfield>
        <subfield code="a">eng</subfield>
      </datafield>
    </record>
    """.format(
        field_008='881005s1984    xxu|||||| ||||00|| |ara d'
    )
    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)

    assert data.get('language') == [
        {
            'type': 'bf:Language',
            'value': 'ara'
        },
        {
            'type': 'bf:Language',
            'value': 'eng'
        }
    ]

    marc21xml = """
    <record>
      <controlfield tag="008">{field_008}</controlfield>
      <datafield tag="041" ind1=" " ind2=" ">
        <subfield code="a">eng</subfield>
      </datafield>
      <datafield tag="041" ind1=" " ind2=" ">
        <subfield code="a">fre</subfield>
      </datafield>
    </record>
    """.format(
        field_008='881005s1984    xxu|||||| ||||00|| |ara d'
    )
    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)
    assert data.get('language') == [
        {
            'type': 'bf:Language',
            'value': 'ara'
        },       {
            'type': 'bf:Language',
            'value': 'eng'
        },
        {
            'type': 'bf:Language',
            'value': 'fre'
        }
    ]

    marc21xml = """
    <record>
      <datafield tag="041" ind1=" " ind2=" ">
      <subfield code="a">eng</subfield>
    </datafield>
    <controlfield tag="008">{field_008}</controlfield>
    </record>
    """.format(
        field_008='881005s1984    xxu|||||| ||||00|| |ara d'
    )
    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)

    assert data.get('language') == [
        {
          'type': 'bf:Language',
          'value': 'ara'
        },
        {
          'type': 'bf:Language',
          'value': 'eng'
        }
    ]

    marc21xml = """
    <record>
      <controlfield tag="008">{field_008}</controlfield>
      <datafield tag="041" ind1=" " ind2=" ">
        <subfield code="a">eng</subfield>
        <subfield code="a">rus</subfield>
      </datafield>
    </record>
    """.format(
        field_008='881005s1984    xxu|||||| ||||00|| |ara d'
    )
    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)
    assert data.get('language') == [
        {
            'type': 'bf:Language',
            'value': 'ara'
        },
        {
            'type': 'bf:Language',
            'value': 'eng'
        },
        {
            'type': 'bf:Language',
            'value': 'rus'
        }
    ]

    marc21xml = """
    <record>
      <controlfield tag="008">{field_008}</controlfield>
    </record>
    """.format(
        field_008='881005s1984    xxu|||||| ||||00|| |ara d'
    )
    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)
    assert data.get('language') == [
        {
            'type': 'bf:Language',
            'value': 'ara'
        }
    ]


@mock.patch('requests.get')
def test_marc21_to_contribution(mock_get):
    """Test dojson marc21_to_contribution."""
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

    marc21xml = """
    <record>
      <datafield tag="100" ind1=" " ind2=" ">
        <subfield code="0">(IDREF)XXXXXXXX</subfield>
      </datafield>
    </record>
    """
    mock_get.return_value = mock_response(json_data={
        'hits': {
            'hits': [{
                'metadata': {
                    'type': 'bf:Person',
                    'rero': {'pid': 'XXXXXXXX'}
                }
            }]
        }
    })
    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)
    contribution = data.get('contribution')
    assert contribution == [{
        'agent': {
            'type': 'bf:Person',
            '$ref': 'https://mef.rero.ch/api/idref/XXXXXXXX'
        },
        'role': ['cre']
    }]


# Copyright Date: [264 _4 $c non repetitive]
def test_marc21copyrightdate():
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


def test_marc21_to_provisionActivity_manufacture_date():
    """Test dojson publication statement.
    - 1 manufacture place and 1 agent, 1 manufacture date
    """

    marc21xml = """
      <record>
        <controlfield tag=
          "008">070518s20062010sz ||| |  ||||00|  |fre d</controlfield>
        <datafield tag="041" ind1="0" ind2=" ">
          <subfield code="a">fre</subfield>
          <subfield code="a">ger</subfield>
        </datafield>
        <datafield tag="264" ind1=" " ind2="3">
          <subfield code="a">Bienne :</subfield>
          <subfield code="b">Impr. Weber</subfield>
          <subfield code="c">[2006]</subfield>
        </datafield>
        <datafield tag="264" ind1=" " ind2="4">
          <subfield code="c">© 2006</subfield>
        </datafield>
      </record>
    """
    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)
    assert data.get('provisionActivity') == [
        {
            'type': 'bf:Manufacture',
            'statement': [
                {
                    'label': [{'value': 'Bienne'}],
                    'type': 'bf:Place'
                },
                {
                    'label': [{'value': 'Impr. Weber'}],
                    'type': 'bf:Agent'
                },
                {
                    'label': [{'value': '[2006]'}],
                    'type': 'Date'
                }
            ]
        }
    ]


def test_marc21_provisionActivity_without_264():
    """Test dojson publication statement.

    A value should be here even 264 does not exists.
    """
    marc21xml = """
    <record>
        <controlfield tag=
          "008">070518s20062010sz ||| |  ||||00|  |fre d</controlfield>
    </record>"""
    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)
    assert data.get('provisionActivity') == [{
        'type': 'bf:Publication',
        'startDate': 2006,
        'endDate': 2010
    }]


def test_marc21_provisionActivity_with_original_date():
    """Test dojson publication statement.
    - get original_date from 008 pos 11-14 if pos 6 = r
    """
    marc21xml = """
    <record>
        <controlfield tag=
          "008">970812r19971849sz ||| | ||||00| |fre d</controlfield>
    </record>"""
    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)
    assert data.get('provisionActivity') == [{
        'type': 'bf:Publication',
        'startDate': 1997,
        'original_date': 1849,
        'endDate': 1849
    }]


def test_marc21_to_provisionActivity_canton():
    """Test dojson publication statement.
    - get canton from field 044
    - 3 publication places and 3 agents from one field 264
    """

    marc21xml = """
      <record>
        <controlfield tag=
          "008">070518s20062010sz ||| |  ||||00|  |fre d</controlfield>
        <datafield tag="041" ind1="0" ind2=" ">
          <subfield code="a">fre</subfield>
          <subfield code="a">ger</subfield>
        </datafield>
        <datafield tag="044" ind1=" " ind2=" ">
          <subfield code="a">sz</subfield>
          <subfield code="c">ch-be</subfield>
        </datafield>
        <datafield tag="264" ind1=" " ind2="1">
          <subfield code="a">Biel/Bienne :</subfield>
          <subfield code="b">Centre PasquArt ;</subfield>
          <subfield code="a">Nürnberg :</subfield>
          <subfield code="b">Verlag für Moderne Kunst ;</subfield>
          <subfield code="a">Manchester :</subfield>
          <subfield code="b">distrib. in the United Kingdom [etc.],</subfield>
          <subfield code="c">[2006-2010]</subfield>
        </datafield>
        <datafield tag="264" ind1=" " ind2="3">
          <subfield code="a">Bienne :</subfield>
          <subfield code="b">Impr. Weber</subfield>
        </datafield>
        <datafield tag="264" ind1=" " ind2="4">
          <subfield code="c">© 2006</subfield>
        </datafield>
      </record>
    """
    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)
    assert data.get('provisionActivity') == [
        {
            'type': 'bf:Publication',
            'place': [{
                'canton': 'be',
                'country': 'sz',
                'type': 'bf:Place'
            }],
            'statement': [
                {
                    'label': [{'value': 'Biel/Bienne'}],
                    'type': 'bf:Place'
                },
                {
                    'label': [{'value': 'Centre PasquArt'}],
                    'type': 'bf:Agent'
                },
                {
                    'label': [{'value': 'Nürnberg'}],
                    'type': 'bf:Place'
                },
                {
                    'label': [{'value': 'Verlag für Moderne Kunst'}],
                    'type': 'bf:Agent'
                },
                {
                    'label': [{'value': 'Manchester'}],
                    'type': 'bf:Place'
                },
                {
                    'label': [{
                        'value': 'distrib. in the United Kingdom [etc.]'
                    }],
                    'type': 'bf:Agent'
                },
                {
                    'label': [{'value': '[2006-2010]'}],
                    'type': 'Date'
                }
            ],
            'startDate': 2006,
            'endDate': 2010
        }, {
            'type': 'bf:Manufacture',
            'statement': [
                {
                    'label': [
                        {'value': 'Bienne'}
                    ],
                    'type': 'bf:Place'
                },
                {
                    'label': [
                        {'value': 'Impr. Weber'}
                    ],
                    'type': 'bf:Agent'
                }
            ]
        }
    ]


def test_marc21_to_provisionActivity_1_place_2_agents():
    """Test dojson publication statement.
    - 1 publication place and 2 agents from one field 264
    """

    marc21xml = """
      <record>
        <controlfield tag=
          "008">940202m19699999fr |||||| ||||00|| |fre d</controlfield>
        <datafield tag="264" ind1=" " ind2="1">
          <subfield code="a">[Paris] :</subfield>
          <subfield code="b">Desclée de Brouwer [puis]</subfield>
          <subfield code="b">Etudes augustiniennes,</subfield>
          <subfield code="c">1969-</subfield>
        </datafield>
      </record>
     """
    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)
    assert data.get('provisionActivity') == [
        {
            'type': 'bf:Publication',
            'place': [{
                'country': 'fr',
                'type': 'bf:Place'
            }],
            'statement': [
                {
                    'label': [{'value': '[Paris]'}],
                    'type': 'bf:Place'
                },
                {
                    'label': [{'value': 'Desclée de Brouwer [puis]'}],
                    'type': 'bf:Agent'
                },
                {
                    'label': [{'value': 'Etudes augustiniennes'}],
                    'type': 'bf:Agent'
                },
                {
                    'label': [{'value': '1969-'}],
                    'type': 'Date'
                }
            ],
            'startDate': 1969
        }
    ]


def test_marc21_to_provisionActivity_unknown_place_2_agents():
    """Test dojson publication statement.
    - unknown place and 2 agents from one field 264
    """
    marc21xml = """
      <record>
      <controlfield tag=
        "008">960525s1968    be |||||| ||||00|| |fre d</controlfield>
      <datafield tag="264" ind1=" " ind2="1">
        <subfield code="a">[Lieu de publication non identifié] :</subfield>
        <subfield code="b">Labor :</subfield>
        <subfield code="b">Nathan,</subfield>
        <subfield code="c">1968</subfield>
      </datafield>
      </record>
    """
    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)
    assert data.get('provisionActivity') == [
        {
            'type': 'bf:Publication',
            'place': [{
                'country': 'be',
                'type': 'bf:Place'
            }],
            'statement': [
                {
                    'label': [
                        {'value': '[Lieu de publication non identifié]'}
                    ],
                    'type': 'bf:Place'
                },
                {
                    'label': [{'value': 'Labor'}],
                    'type': 'bf:Agent'
                },
                {
                    'label': [{'value': 'Nathan'}],
                    'type': 'bf:Agent'
                },
                {
                    'label': [{'value': '1968'}],
                    'type': 'Date'
                }
            ],
            'startDate': 1968
        }
    ]
    assert create_publication_statement(data.get('provisionActivity')[0]) == [
        '[Lieu de publication non identifié] : Labor, Nathan, 1968'
    ]


def test_marc21_to_provisionActivity_3_places_dann_2_agents():
    """Test dojson publication statement.
    - 3 places and 2 agents from one field 264
    - 2 places with [dann] prefix
    """
    marc21xml = """
      <record>
      <controlfield tag=
        "008">000927m19759999gw |||||| ||||00|  |ger d</controlfield>
      <datafield tag="264" ind1=" " ind2="1">
        <subfield code="a">Hamm (Westf.) ;</subfield>
        <subfield code="a">[dann] Herzberg ;</subfield>
        <subfield code="a">[dann] Nordhausen :</subfield>
        <subfield code="b">T. Bautz,</subfield>
        <subfield code="c">1975-</subfield>
      </datafield>
      </record>
    """
    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)
    assert data.get('provisionActivity') == [
        {
            'type': 'bf:Publication',
            'place': [{
                 'country': 'gw',
                 'type': 'bf:Place'
            }],
            'statement': [
                {
                    'label': [{'value': 'Hamm (Westf.)'}],
                    'type': 'bf:Place'
                },
                {
                    'label': [{'value': '[dann] Herzberg'}],
                    'type': 'bf:Place'
                },
                {
                    'label': [{'value': '[dann] Nordhausen'}],
                    'type': 'bf:Place'
                },
                {
                    'label': [{'value': 'T. Bautz'}],
                    'type': 'bf:Agent'
                },
                {
                    'label': [{'value': '1975-'}],
                    'type': 'Date'
                }
            ],
            'startDate': 1975
        }
    ]
    assert create_publication_statement(data.get('provisionActivity')[0]) == [
        'Hamm (Westf.) ; [dann] Herzberg ; [dann] Nordhausen : T. Bautz, 1975-'
    ]


def test_marc21_to_provisionActivity_2_places_1_agent():
    """Test dojson publication statement.
    - 2 publication places and 1 agents from one field 264
    """

    marc21xml = """
      <record>
      <controlfield tag=
        "008">960525s1966    sz |||||| ||||00|| |fre d</controlfield>
      <datafield tag="264" ind1=" " ind2="1">
        <subfield code="a">[Louvain] ;</subfield>
        <subfield code="a">[Paris] :</subfield>
        <subfield code="b">[éditeur non identifié],</subfield>
        <subfield code="c">[1966]</subfield>
      </datafield>
      </record>
    """
    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)
    assert data.get('provisionActivity') == [
        {
            'type': 'bf:Publication',
            'place': [{
                'country': 'sz',
                'type': 'bf:Place'
            }],
            'statement': [
                {
                    'label': [{'value': '[Louvain]'}],
                    'type': 'bf:Place'
                },
                {
                    'label': [{'value': '[Paris]'}],
                    'type': 'bf:Place'
                },
                {
                    'label': [{'value': '[éditeur non identifié]'}],
                    'type': 'bf:Agent'
                },
                {
                    'label': [{'value': '[1966]'}],
                    'type': 'Date'
                }
            ],
            'startDate': 1966
        }
    ]
    assert create_publication_statement(data.get('provisionActivity')[0]) == [
        '[Louvain] ; [Paris] : [éditeur non identifié], [1966]'
    ]


def test_marc21_to_provisionActivity_1_place_1_agent_reprint_date():
    """Test dojson publication statement.
    - 1 place and 1 agent from one field 264
    - reprint date in 008
    """
    marc21xml = """
      <record>
      <controlfield tag=
        "008">000918r17581916xxu|||||| ||||00|| |eng d</controlfield>
      <datafield tag="041" ind1="0" ind2=" ">
        <subfield code="a">eng</subfield>
        <subfield code="a">fre</subfield>
      </datafield>
      <datafield tag="264" ind1=" " ind2="1">
        <subfield code="a">Washington :</subfield>
        <subfield code="b">Carnegie Institution of Washington,</subfield>
        <subfield code="c">1916</subfield>
      </datafield>
      </record>
    """
    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)
    assert data.get('provisionActivity') == [
        {
            'type': 'bf:Publication',
            'place': [{
                'country': 'xxu',
                'type': 'bf:Place'
            }],
            'statement': [
                {
                    'label': [{'value': 'Washington'}],
                    'type': 'bf:Place'
                },
                {
                    'label': [{'value': 'Carnegie Institution of Washington'}],
                    'type': 'bf:Agent'
                },
                {
                    'label': [{'value': '1916'}],
                    'type': 'Date'
                }
            ],
            'startDate': 1758,
            'endDate': 1916
        }
    ]


def test_marc21_to_provisionActivity_1_place_1_agent_uncertain_date():
    """Test dojson publication statement.
    - 1 place and 1 agent from one field 264
    - uncertain date
    """
    marc21xml = """
      <record>
      <controlfield tag=
        "008">160126q1941    fr ||| |  ||||00|  |fre d</controlfield>
      <datafield tag="264" ind1=" " ind2="1">
        <subfield code="a">Aurillac :</subfield>
        <subfield code="b">Impr. moderne,</subfield>
        <subfield code="c">[1941?]</subfield>
      </datafield>
      </record>
    """
    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)
    assert data.get('provisionActivity') == [
        {
            'type': 'bf:Publication',
            'place': [{
                'country': 'fr',
                'type': 'bf:Place'
            }],
            'statement': [
                {
                    'label': [{'value': 'Aurillac'}],
                    'type': 'bf:Place'
                },
                {
                    'label': [{'value': 'Impr. moderne'}],
                    'type': 'bf:Agent'
                },
                {
                    'label': [{'value': '[1941?]'}],
                    'type': 'Date'
                }
            ],
            'note': 'Date(s) uncertain or unknown',
            'startDate': 1941
        }
    ]
    assert create_publication_statement(data.get('provisionActivity')[0]) == [
        'Aurillac : Impr. moderne, [1941?]'
    ]


def test_marc21_to_provisionActivity_1_place_1_agent_chi_hani():
    """Test dojson publication statement.
    - 1 place and 1 agent from one field 264
    - extract data from the linked 880 from 3 fields 880
    """
    marc21xml = """
      <record>
      <controlfield tag=
        "008">180323s2017    cc ||| |  ||||00|  |chi d</controlfield>
      <datafield tag="264" ind1=" " ind2="1">
        <subfield code="6">880-04</subfield>
        <subfield code="a">Beijing :</subfield>
        <subfield code="b">Beijing da xue chu ban she,</subfield>
        <subfield code="c">2017</subfield>
      </datafield>
      <datafield tag="880" ind1=" " ind2="1">
        <subfield code="6">264-04/$1</subfield>
        <subfield code="a">北京 :</subfield>
        <subfield code="b">北京大学出版社,</subfield>
        <subfield code="c">2017</subfield>
      </datafield>
      <datafield tag="880" ind1="1" ind2=" ">
        <subfield code="6">100-01/$1</subfield>
        <subfield code="a">余锋</subfield>
      </datafield>
      <datafield tag="880" ind1="1" ind2="0">
        <subfield code="6">245-02/$1</subfield>
        <subfield code="a">中国娱乐法 /</subfield>
        <subfield code="c">余锋著</subfield>
      </datafield>
      </record>
    """
    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)
    assert data.get('provisionActivity') == [
        {
            'type': 'bf:Publication',
            'place': [{
                'country': 'cc',
                'type': 'bf:Place'
            }],
            'statement': [
                {
                    'label': [
                        {'value': 'Beijing'},
                        {'value': '北京', 'language': 'chi-hani'}
                    ],
                    'type': 'bf:Place'
                },
                {
                    'label': [
                          {'value': 'Beijing da xue chu ban she'},
                          {'value': '北京大学出版社', 'language': 'chi-hani'}
                    ],
                    'type': 'bf:Agent'
                },
                {
                    'label': [
                        {'value': '2017'},
                        {'language': 'chi-hani', 'value': '2017'}
                    ],
                    'type': 'Date'
                }
            ],
            'startDate': 2017
        }
    ]
    assert create_publication_statement(data.get('provisionActivity')[0]) == [
        '北京 : 北京大学出版社, 2017',
        'Beijing : Beijing da xue chu ban she, 2017'
    ]
    marc21xml = """
      <record>
      <controlfield tag=
        "008">180323s2017    cc ||| |  ||||00|  |chi d</controlfield>
      <datafield tag="264" ind1=" " ind2="1">
        <subfield code="6">880-04</subfield>
        <subfield code="a">Beijing :</subfield>
        <subfield code="b">Beijing da xue chu ban she,</subfield>
        <subfield code="c">2017</subfield>
      </datafield>
      <datafield tag="880" ind1=" " ind2="1">
        <subfield code="6">264-04/$1</subfield>
        <subfield code="a">北京 :</subfield>
        <subfield code="b">北京大学出版社,</subfield>
        <subfield code="c">2017</subfield>
      </datafield>
      <datafield tag="880" ind1="1" ind2=" ">
        <subfield code="6">100-01/$1</subfield>
        <subfield code="a">余锋</subfield>
      </datafield>
      <datafield tag="880" ind1="1" ind2="0">
        <subfield code="6">245-02/$1</subfield>
        <subfield code="a">中国娱乐法 /</subfield>
        <subfield code="c">余锋著</subfield>
      </datafield>
      </record>
    """
    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)
    assert data.get('provisionActivity') == [{
        'type': 'bf:Publication',
        'place': [{
            'country': 'cc',
            'type': 'bf:Place'
        }],
        'statement': [
            {
                'label': [
                    {'value': 'Beijing'},
                    {'value': '北京', 'language': 'chi-hani'}
                ],
                'type': 'bf:Place'
            },
            {
                'label': [
                    {'value': 'Beijing da xue chu ban she'},
                    {'value': '北京大学出版社',
                     'language': 'chi-hani'}
                ],
                'type': 'bf:Agent'
            },
            {
                'label': [
                    {'value': '2017'},
                    {'language': 'chi-hani', 'value': '2017'}
                ],
                'type': 'Date'
            }
        ],
        'startDate': 2017
    }]
    assert create_publication_statement(data.get('provisionActivity')[0]) == [
        '北京 : 北京大学出版社, 2017',
        'Beijing : Beijing da xue chu ban she, 2017'
    ]


def test_marc21_to_edition_statement_one_field_250():
    """Test dojson edition statement.
    - 1 edition designation and 1 responsibility from field 250
    - extract data from the linked 880 from field 880
    """
    marc21xml = """
      <record>
      <controlfield tag=
        "008">180323s2017    cc ||| |  ||||00|  |chi d</controlfield>
      <datafield  tag="250" ind1=" " ind2=" ">
        <subfield code="6">880-02</subfield>
        <subfield code="a">Di 3 ban /</subfield>
        <subfield code="b">Zeng Lingliang zhu bian</subfield>
      </datafield>
      <datafield tag="880" ind1=" " ind2=" ">
        <subfield code="6">250-02/$1</subfield>
        <subfield code="a">第3版 /</subfield>
        <subfield code="b">曾令良主编</subfield>
      </datafield>
      </record>
    """
    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)
    assert data.get('editionStatement') == [{
        'editionDesignation': [
            {
                'value': 'Di 3 ban'
            },
            {
                'value': '第3版',
                'language': 'chi-hani'
            }
        ],
        'responsibility': [
            {
                'value': 'Zeng Lingliang zhu bian'
            },
            {
                'value': '曾令良主编',
                'language': 'chi-hani'
                }
        ]
    }]


def test_marc21_to_edition_statement_two_fields_250():
    """Test dojson edition statement.
    - 2 edition designations and 2 responsibility from fields 250
    - extract data from the linked 880 from 1 field 880
    """
    marc21xml = """
      <record>
      <controlfield tag=
        "008">180323s2017    cc ||| |  ||||00|  |chi d</controlfield>
      <datafield  tag="250" ind1=" " ind2=" ">
        <subfield code="6">880-02</subfield>
        <subfield code="a">Di 3 ban /</subfield>
        <subfield code="b">Zeng Lingliang zhu bian</subfield>
      </datafield>
      <datafield  tag="250" ind1=" " ind2=" ">
        <subfield code="a">Edition /</subfield>
        <subfield code="b">Responsibility</subfield>
      </datafield>
      <datafield tag="880" ind1=" " ind2=" ">
        <subfield code="6">250-02/$1</subfield>
        <subfield code="a">第3版 /</subfield>
        <subfield code="b">曾令良主编</subfield>
      </datafield>
      </record>
    """
    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)
    assert data.get('editionStatement') == [{
        'editionDesignation': [
            {
                'value': 'Di 3 ban'
            },
            {
                'value': '第3版',
                'language': 'chi-hani'
            }
        ],
        'responsibility': [
            {
                'value': 'Zeng Lingliang zhu bian'
            },
            {
                'value': '曾令良主编',
                'language': 'chi-hani'
            }
        ]
    }, {
        'editionDesignation': [
            {
                'value': 'Edition'
            }
        ],
        'responsibility': [
            {
                'value': 'Responsibility'
            }
        ]
    }]


def test_marc21_to_edition_statement_with_two_subfield_a():
    """Test dojson edition statement.
    - 1 field 250 with 2 subfield_a
    - extract data from the linked 880 from 1 field 880
    """
    marc21xml = """
      <record>
      <controlfield tag=
        "008">180323s2017    cc ||| |  ||||00|  |chi d</controlfield>
      <datafield  tag="250" ind1=" " ind2=" ">
        <subfield code="6">880-02</subfield>
        <subfield code="a">Di 3 ban /</subfield>
        <subfield code="a">Di 4 ban /</subfield>
        <subfield code="b">Zeng Lingliang zhu bian</subfield>
      </datafield>
      <datafield tag="880" ind1=" " ind2=" ">
        <subfield code="6">250-02/$1</subfield>
        <subfield code="a">第3版 /</subfield>
        <subfield code="a">第4版 /</subfield>
        <subfield code="b">曾令良主编</subfield>
      </datafield>
      </record>
    """
    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)

    assert data.get('editionStatement') == [{
        'editionDesignation': [
            {
                'value': 'Di 3 ban'
            },
            {
                'value': '第3版',
                'language': 'chi-hani'
            }
        ],
        'responsibility': [
            {
                'value': 'Zeng Lingliang zhu bian'
            },
            {
                'value': '曾令良主编',
                'language': 'chi-hani'
            }
        ]
    }]


def test_marc21_to_edition_statement_with_one_bad_field_250():
    """Test dojson edition statement.
    - 3 fields 250, and one of them as bad subdields $x, $y
      and one as only $b
    - extract data from the linked 880 from 1 field 880
    """
    marc21xml = """
      <record>
      <controlfield tag=
        "008">180323s2017    cc ||| |  ||||00|  |chi d</controlfield>
      <datafield  tag="250" ind1=" " ind2=" ">
        <subfield code="6">880-02</subfield>
        <subfield code="a">Di 3 ban /</subfield>
        <subfield code="b">Zeng Lingliang zhu bian</subfield>
      </datafield>
      <datafield  tag="250" ind1=" " ind2=" ">
        <subfield code="x">Edition /</subfield>
        <subfield code="y">Responsibility</subfield>
      </datafield>
      <datafield  tag="250" ind1=" " ind2=" ">
        <subfield code="a">Edition</subfield>
        <subfield code="y">Responsibility</subfield>
      </datafield>
      <datafield tag="880" ind1=" " ind2=" ">
        <subfield code="6">250-02/$1</subfield>
        <subfield code="a">第3版 /</subfield>
        <subfield code="b">曾令良主编</subfield>
      </datafield>
      </record>
    """
    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)
    assert data.get('editionStatement') == [{
        'editionDesignation': [
            {
                'value': 'Di 3 ban'
            },
            {
                'value': '第3版',
                'language': 'chi-hani'
            }
        ],
        'responsibility': [
            {
                'value': 'Zeng Lingliang zhu bian'
            },
            {
                'value': '曾令良主编',
                'language': 'chi-hani'
            }
        ]
    }, {
        'editionDesignation': [
            {
                'value': 'Edition'
            }
        ]
     }]


def test_marc21_to_provisionActivity_1_place_1_agent_ara_arab():
    """Test dojson publication statement.
    - 1 place and 1 agent from one field 264
    - extract data from the linked 880
    """
    marc21xml = """
      <record>
      <controlfield tag=
        "008">150617s2014    ua ||| |  ||||00|  |ara d</controlfield>
      <datafield tag="264" ind1=" " ind2="1">
        <subfield code="6">880-01</subfield>
        <subfield code="a">al-Qāhirah :</subfield>
        <subfield code="b">Al-Hayʾat al-ʿāmmah li quṣūr al-thaqāfah,</subfield>
        <subfield code="c">2014</subfield>
      </datafield>
      <datafield tag="880" ind1=" " ind2="1">
        <subfield code="6">264-01/(3/r</subfield>
        <subfield code="a">القاهرة :</subfield>
        <subfield code="b">الهيئة العامة لقصور الثقافة,</subfield>
        <subfield code="c">2014</subfield>
      </datafield>
      </record>
    """
    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)
    assert data.get('provisionActivity') == [
        {
            'type': 'bf:Publication',
            'place': [{
                'country': 'ua',
                'type': 'bf:Place'
            }],
            'statement': [
                {
                    'label': [
                        {'value': 'al-Qāhirah'},
                        {'value': 'القاهرة',
                         'language': 'ara-arab'}
                    ],
                    'type': 'bf:Place'
                },
                {
                    'label': [
                        {'value': 'Al-Hayʾat al-ʿāmmah li quṣūr al-thaqāfah'},
                        {'value': 'الهيئة العامة لقصور الثقافة',
                         'language': 'ara-arab'}
                    ],
                    'type': 'bf:Agent'
                },
                {
                    'label': [
                        {'value': '2014'},
                        {'value': '2014', 'language': 'ara-arab'}
                    ],
                    'type': 'Date'
                }
            ],
            'startDate': 2014
        }
    ]
    assert create_publication_statement(data.get('provisionActivity')[0]) == [
        'القاهرة : الهيئة العامة لقصور الثقافة, 2014',
        'al-Qāhirah : Al-Hayʾat al-ʿāmmah li quṣūr al-thaqāfah, 2014'
    ]


def test_marc21_to_provisionActivity_2_places_2_agents_rus_cyrl():
    """Test dojson publication statement.
    - 2 places and 2 agents from one field 264
    - extract data from the linked 880 from 3 fields 880
    """
    marc21xml = """
      <record>
        <controlfield tag=
          "008">170626s2017    ru ||| |  ||||00|  |rus d</controlfield>
        <datafield tag="264" ind1=" " ind2="1">
          <subfield code="6">880-02</subfield>
          <subfield code="a">Ierusalim :</subfield>
          <subfield code="b">Gesharim ;</subfield>
          <subfield code="a">Moskva :</subfield>
          <subfield code="b">Mosty Kulʹtury,</subfield>
          <subfield code="c">2017</subfield>
        </datafield>
        <datafield tag="264" ind1=" " ind2="4">
          <subfield code="c">©2017</subfield>
        </datafield>
        <datafield tag="880" ind1=" " ind2="1">
          <subfield code="6">264-02/(N</subfield>
          <subfield code="a">Иерусалим :</subfield>
          <subfield code="b">Гешарим ;</subfield>
          <subfield code="a">Москва :</subfield>
          <subfield code="b">Мосты Культуры,</subfield>
          <subfield code="c">2017</subfield>
        </datafield>
        <datafield tag="880" ind1="1" ind2=" ">
          <subfield code="6">490-03/(N</subfield>
          <subfield code="a">Прошлый век. Воспоминания</subfield>
        </datafield>
        <datafield tag="880" ind1="1" ind2="0">
          <subfield code="6">245-01/(N</subfield>
          <subfield code="a">Воспоминания бабушки :</subfield>
          <subfield code=
              "b">очерки культурной истории евреев России в XIX в. /</subfield>
          <subfield code="c">Полина Венгерова</subfield>
        </datafield>
      </record>
    """
    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)
    assert data.get('provisionActivity') == [
        {
            'type': 'bf:Publication',
            'place': [{
                'country': 'ru',
                'type': 'bf:Place'
            }],
            'statement': [
                {
                    'label': [
                        {'value': 'Ierusalim'},
                        {'value': 'Иерусалим',
                         'language': 'rus-cyrl'}
                    ],
                    'type': 'bf:Place'
                },
                {
                    'label': [
                        {'value': 'Gesharim'},
                        {'value': 'Гешарим',
                         'language': 'rus-cyrl'}
                    ],
                    'type': 'bf:Agent'
                },
                {
                    'label': [
                        {'value': 'Moskva'},
                        {'value': 'Москва',
                         'language': 'rus-cyrl'}
                    ],
                    'type': 'bf:Place'
                },
                {
                    'label': [
                        {'value': 'Mosty Kulʹtury'},
                        {'value': 'Мосты Культуры',
                         'language': 'rus-cyrl'}
                    ],
                    'type': 'bf:Agent'
                },
                {
                    'label': [
                        {'value': '2017'},
                        {'language': 'rus-cyrl', 'value': '2017'}
                    ],
                    'type': 'Date'
                }
            ],
            'startDate': 2017
        }
    ]
    assert create_publication_statement(data.get('provisionActivity')[0]) == [
        'Иерусалим : Гешарим ; Москва : Мосты Культуры, 2017',
        'Ierusalim : Gesharim ; Moskva : Mosty Kulʹtury, 2017'
    ]


def test_marc21_to_provisionActivity_exceptions(capsys):
    """Test dojson publication statement.
    - exceptions
    """
    marc21xml = """
      <record>
        <controlfield tag=
          "008">170626s2017    ru ||| |  ||||00|  |</controlfield>
        <datafield tag="264" ind1=" " ind2="1">
          <subfield code="6">880-02</subfield>
          <subfield code="a">Ierusalim :</subfield>
        </datafield>
        <datafield tag="880" ind1=" " ind2="1">
          <subfield code="6">264-02/(N</subfield>
          <subfield code="a">Иерусалим :</subfield>
        </datafield>
      </record>
    """
    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)
    out, err = capsys.readouterr()
    assert data.get('provisionActivity') == [
        {
            'type': 'bf:Publication',
            'place': [{
                'country': 'ru',
                'type': 'bf:Place'
            }],
            'statement': [
                {
                    'label': [
                        {'value': 'Ierusalim'},
                        {'value': 'Иерусалим',
                         'language': 'und-cyrl'}
                    ],
                    'type': 'bf:Place'
                },
            ],
            'startDate': 2017
        }
    ]
    assert out.strip() == ('WARNING LANGUAGE SCRIPTS:\t???\t???\tcyrl\t008:'
                           '\t\t041$a:\t[]\t041$h:\t[]')

    marc21xml = """
      <record>
        <datafield tag="044" ind1=" " ind2=" ">
          <subfield code="c">chbe</subfield>
        </datafield>
      </record>
    """
    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)
    out, err = capsys.readouterr()
    assert out.strip() == ('WARNING INIT CANTONS:\t???\t???\tchbe\t\n'
                           'WARNING START DATE 264:\t???\t???\tNone')


# 300 [$a repetitive]: extent, duration:
# 300 [$a non repetitive]: colorContent, productionMethod,
#        illustrativeContent, note of type otherPhysicalDetails
# 300 [$c repetitive]: format
# 300 [$e non epetitive]: accompanying material note

def test_marc21_to_physical_description_plano():
    """Test dojson extent, productionMethod."""

    marc21xml = """
    <record>
      <datafield tag="300" ind1=" " ind2=" ">
        <subfield code="a">116 p.</subfield>
        <subfield code="b">litho photogravure gravure ;</subfield>
        <subfield code="c">plano 22 cm</subfield>
      </datafield>
    </record>
    """

    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)
    assert data.get('productionMethod') == \
        ['rdapm:1007', 'rdapm:1009']
    assert data.get('extent') == '116 p.'
    assert data.get('bookFormat') == ['in-plano']
    assert data.get('dimensions') == ['plano 22 cm']
    assert data.get('note') == [{
            'noteType': 'otherPhysicalDetails',
            'label': 'litho photogravure gravure'
        }]


def test_marc21_to_physical_description_with_material_note():
    """Test dojson extent, productionMethod, material note."""

    marc21xml = """
    <record>
      <datafield tag="300" ind1=" " ind2=" ">
        <subfield code="a">116 p.</subfield>
        <subfield code="b">litho photogravure gravure ;</subfield>
        <subfield code="c">plano 22 cm</subfield>
        <subfield code="e">1 atlas</subfield>
      </datafield>
    </record>
    """

    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)
    assert data.get('productionMethod') == \
        ['rdapm:1007', 'rdapm:1009']
    assert data.get('extent') == '116 p.'
    assert data.get('bookFormat') == ['in-plano']
    assert data.get('dimensions') == ['plano 22 cm']
    assert data.get('note') == [{
            'noteType': 'otherPhysicalDetails',
            'label': 'litho photogravure gravure'
        }, {
            'noteType': 'accompanyingMaterial',
            'label': '1 atlas'
        }
    ]


def test_marc21_to_physical_description_with_material_note_plus():
    """Test dojson extent, productionMethod, material note with +."""

    marc21xml = """
    <record>
      <datafield tag="300" ind1=" " ind2=" ">
        <subfield code="a">116 p.</subfield>
        <subfield code="b">litho photogravure gravure ;</subfield>
        <subfield code="c">plano 22 cm</subfield>
        <subfield code="e">1 atlas + 3 cartes + XXIX f. de pl.</subfield>
      </datafield>
    </record>
    """

    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)
    assert data.get('productionMethod') == \
        ['rdapm:1007', 'rdapm:1009']
    assert data.get('extent') == '116 p.'
    assert data.get('bookFormat') == ['in-plano']
    assert data.get('dimensions') == ['plano 22 cm']
    assert data.get('note') == [{
            'noteType': 'otherPhysicalDetails',
            'label': 'litho photogravure gravure'
        }, {
            'noteType': 'accompanyingMaterial',
            'label': '1 atlas'
        }, {
            'noteType': 'accompanyingMaterial',
            'label': '3 cartes'
        }, {
            'noteType': 'accompanyingMaterial',
            'label': 'XXIX f. de pl.'
        }
    ]


def test_marc21_to_physical_description_300_without_b():
    """Test dojson extent, productionMethod."""

    marc21xml = """
    <record>
      <datafield tag="300" ind1=" " ind2=" ">
        <subfield code="a">191 p. ;</subfield>
        <subfield code="c">21 cm</subfield>
      </datafield>
    </record>
    """
    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)
    assert data.get('extent') == '191 p.'
    assert data.get('dimensions') == ['21 cm']
    assert data.get('note') is None


def test_marc21_to_physical_description_ill_in_8():
    """Test dojson illustrativeContent: illustrations, dimensions: in-8."""
    marc21xml = """
    <record>
      <datafield tag="300" ind1=" " ind2=" ">
        <subfield code="a">1 DVD-R (50 min.)</subfield>
        <subfield code="b">litho Ill.en n. et bl. ;</subfield>
        <subfield code="c">in-8, 22 cm</subfield>
      </datafield>
    </record>
    """

    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)
    assert data.get('productionMethod') == ['rdapm:1007']
    assert data.get('extent') == '1 DVD-R (50 min.)'
    assert data.get('duration') == ['50 min.']
    assert data.get('illustrativeContent') == ['illustrations']
    assert data.get('colorContent') == ['rdacc:1002']
    assert data.get('bookFormat') == ['8º']
    assert data.get('dimensions') == ['in-8, 22 cm']
    assert data.get('note') == [{
        'noteType': 'otherPhysicalDetails',
        'label': 'litho Ill.en n. et bl.'
    }]


def test_marc21_to_physical_description_multiple_300():
    """Test dojson physical_description having multiple 300 fields."""
    marc21xml = """
    <record>
       <datafield tag="300" ind1=" " ind2=" ">
        <subfield code="a">116 p.</subfield>
        <subfield code="b">litho photogravure gravure n. et bl. ;</subfield>
        <subfield code="c">plano 22 cm</subfield>
      </datafield>
     <datafield tag="300" ind1=" " ind2=" ">
        <subfield code="a">1 DVD-R (50 min.)</subfield>
        <subfield code="b">litho Ill.en n. et bl. ;</subfield>
        <subfield code="c">in-8, 22 cm</subfield>
      </datafield>
    </record>
    """

    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)
    assert data.get('productionMethod') == \
        ['rdapm:1007', 'rdapm:1009']
    assert data.get('extent') == '1 DVD-R (50 min.)'
    assert data.get('duration') == ['50 min.']
    assert data.get('illustrativeContent') == ['illustrations', 'photographs']
    assert data.get('colorContent') == ['rdacc:1002']
    assert data.get('bookFormat') == ['8º', 'in-plano']
    assert data.get('dimensions') == ['in-8, 22 cm', 'plano 22 cm']
    assert data.get('note') == [{
            'noteType': 'otherPhysicalDetails',
            'label': 'litho photogravure gravure n. et bl.'
        }, {
            'noteType': 'otherPhysicalDetails',
            'label': 'litho Ill.en n. et bl.'
        }
    ]


# series.name: [490$a repetitive]
# series.number: [490$v repetitive]
def test_marc21_to_series_statement():
    """Test dojson seriesStatement."""

    marc21xml = """
    <record>
       <datafield tag="490" ind1="1" ind2=" ">
            <subfield code="a">Handbuch der Orientalistik</subfield>
            <subfield code="v">Abt. 7.</subfield>
            <subfield code="a">Kunst und Archäologie</subfield>
            <subfield code="v">Bd. 6.</subfield>
            <subfield code="a">Südostasien</subfield>
            <subfield code="v">Abschnitt 6</subfield>
        </datafield>
    </record>
    """
    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)
    assert data.get('seriesStatement') == [{
        'seriesTitle': [{'value': 'Handbuch der Orientalistik'}],
        'seriesEnumeration': [{'value': 'Abt. 7'}],
        'subseriesStatement': [{
                'subseriesTitle': [{'value': 'Kunst und Archäologie'}],
                'subseriesEnumeration': [{'value': 'Bd. 6'}]
            }, {
                'subseriesTitle': [{'value': 'Südostasien'}],
                'subseriesEnumeration': [{'value': 'Abschnitt 6'}]
            }
        ]
    }]


def test_marc21_to_series_statement_mutiple_490():
    """Test dojson seriesStatement."""

    marc21xml = """
    <record>
       <datafield tag="490" ind1="1" ind2=" ">
            <subfield code="a">Handbuch der Orientalistik 1</subfield>
            <subfield code="v">Abt. 7.</subfield>
            <subfield code="a">Kunst und Archäologie</subfield>
            <subfield code="v">Bd. 6.</subfield>
            <subfield code="a">Südostasien</subfield>
            <subfield code="v">Abschnitt 6</subfield>
        </datafield>
       <datafield tag="490" ind1="1" ind2=" ">
            <subfield code="a">Handbuch der Orientalistik 2</subfield>
            <subfield code="v">Abt. 7.</subfield>
            <subfield code="a">Kunst und Archäologie</subfield>
            <subfield code="v">Bd. 6.</subfield>
            <subfield code="a">Südostasien</subfield>
            <subfield code="v">Abschnitt 6</subfield>
        </datafield>
    </record>
    """
    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)
    assert data.get('seriesStatement') == [{
        'seriesTitle': [{'value': 'Handbuch der Orientalistik 1'}],
        'seriesEnumeration': [{'value': 'Abt. 7'}],
        'subseriesStatement': [{
                'subseriesTitle': [{'value': 'Kunst und Archäologie'}],
                'subseriesEnumeration': [{'value': 'Bd. 6'}]
            }, {
                'subseriesTitle': [{'value': 'Südostasien'}],
                'subseriesEnumeration': [{'value': 'Abschnitt 6'}]
            }
        ]
    }, {
        'seriesTitle': [{'value': 'Handbuch der Orientalistik 2'}],
        'seriesEnumeration': [{'value': 'Abt. 7'}],
        'subseriesStatement': [{
                'subseriesTitle': [{'value': 'Kunst und Archäologie'}],
                'subseriesEnumeration': [{'value': 'Bd. 6'}]
            }, {
                'subseriesTitle': [{'value': 'Südostasien'}],
                'subseriesEnumeration': [{'value': 'Abschnitt 6'}]
            }
        ]
    }]


# series.name: [490$a repetitive]
# series.number: [490$v repetitive]
def test_marc21_to_series_statement_with_alt_graphic():
    """Test dojson seriesStatement."""

    marc21xml = """
    <record>
        <controlfield tag=
            "008">960525s1962    ru |||||| ||||00|| |rus d</controlfield>
        <datafield tag="490" ind1="1" ind2=" ">
            <subfield code="6">880-04</subfield>
            <subfield code="a">Žizn&apos; zamečatel&apos;nych ljudej</subfield>
            <subfield code="v">vypusk 4, 357</subfield>
        </datafield>
        <datafield tag="880" ind1="1" ind2=" ">
            <subfield code="6">490-04/(N</subfield>
            <subfield code="a">Жизнь замечательных людей</subfield>
            <subfield code="v">выпуск 4, 357</subfield>
        </datafield>
    </record>
    """
    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)
    assert data.get('seriesStatement') == [{
        'seriesTitle': [
            {'value': "Žizn' zamečatel'nych ljudej"},
            {'value': 'Жизнь замечательных людей', 'language': 'rus-cyrl'}
        ],
        'seriesEnumeration': [
            {'value': 'vypusk 4, 357'},
            {'value': 'выпуск 4, 357', 'language': 'rus-cyrl'}
        ]
    }]


# series.name: [490$a repetitive]
# series.number: [490$v repetitive]
def test_marc21_to_series_statement_with_missig_subfield_v():
    """Test dojson seriesStatement."""

    marc21xml = """
    <record>
        <datafield tag="490" ind1="1" ind2=" ">
            <subfield code="a">Handbuch der Orientalistik</subfield>
            <subfield code="a">Kunst und Archäologie</subfield>
            <subfield code="a">Südostasien</subfield>
            <subfield code="v">Abschnitt 6</subfield>
        </datafield>
    </record>
    """
    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)
    assert data.get('seriesStatement') == [{
        'seriesTitle': [{'value': 'Handbuch der Orientalistik'}],
        'subseriesStatement': [{
                'subseriesTitle': [{'value': 'Kunst und Archäologie'}]
            }, {
                'subseriesTitle': [{'value': 'Südostasien'}],
                'subseriesEnumeration': [{'value': 'Abschnitt 6'}]
            }
        ]
    }]


# series.name: [490$a repetitive]
# series.number: [490$v repetitive]
def test_marc21_to_series_statement_with_missig_subfield_a():
    """Test dojson seriesStatement."""

    marc21xml = """
    <record>
       <controlfield tag="001">REROILS:123456789</controlfield>
       <datafield tag="490" ind1="1" ind2=" ">
            <subfield code="x">Handbuch der Orientalistik</subfield>
            <subfield code="v">Abt. 7.</subfield>
        </datafield>
    </record>
    """
    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)
    # should return None because of the bad formating of field 490
    assert data.get('seriesStatement') is None


# series.name: [490$a repetitive]
# series.number: [490$v repetitive]
def test_marc21_to_series_statement_with_succesive_subfield_v():
    """Test dojson seriesStatement."""

    marc21xml = """
    <record>
        <leader>00501nam a2200133 a 4500</leader>
        <datafield tag="490" ind1="1" ind2=" ">
            <subfield code="a">Handbuch der Orientalistik</subfield>
            <subfield code="v">Abt. 7.</subfield>
            <subfield code="v">Bd. 7.</subfield>
            <subfield code="a">Südostasien</subfield>
            <subfield code="v">Abschnitt 6</subfield>
            <subfield code="v">Bd. 6.</subfield>
        </datafield>
    </record>
    """
    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)
    assert data.get('seriesStatement') == [{
        'seriesTitle': [{'value': 'Handbuch der Orientalistik'}],
        'seriesEnumeration': [{'value': 'Abt. 7, Bd. 7'}],
        'subseriesStatement': [{
                'subseriesTitle': [{'value': 'Südostasien'}],
                'subseriesEnumeration': [{'value': 'Abschnitt 6, Bd. 6'}]
            }
        ]
    }]


# summary: [520$a repetitive]
def test_marc21_to_summary():
    """Test dojson summary (L27)."""

    marc21xml = """
    <record>
      <datafield tag="520" ind1=" " ind2=" ">
        <subfield code="a">This book is about</subfield>
        <subfield code="c">source</subfield>
      </datafield>
    </record>
    """
    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)
    assert data.get('summary') == [{
        "label": [{"value": "This book is about"}],
        "source": "source"
    }]

    marc21xml = """
    <record>
        <datafield tag="520" ind1="8" ind2=" ">
            <subfield code="6">880-05</subfield>
            <subfield code="a">Za wen fen wei si bu fen lu ru</subfield>
        </datafield>
        <datafield tag="880" ind1=" " ind2=" ">
            <subfield code="6">520-05/$1</subfield>
            <subfield code="a">杂文分为四部分录入</subfield>
        </datafield>
    </record>
    """
    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)
    assert data.get('summary') == [{
            'label': [{
                    'value': 'Za wen fen wei si bu fen lu ru',
                }, {
                    'value': '杂文分为四部分录入',
                    'language': 'und-hani'
                }]
    }]


def test_marc21_to_intended_audience():
    """Test dojson intendedAudience from field 521 (L27)."""

    marc21xml = """
    <record>
        <datafield tag="521" ind1=" " ind2=" ">
            <subfield code="a">jugendliche (12-15 Jahre):</subfield>
            <subfield code="9">vsbcvs/06.2003</subfield>
        </datafield>
        <datafield tag="521" ind1=" " ind2=" ">
            <subfield code="a">Ab 12 Jahre:</subfield>
            <subfield code="9">vsbcvs/06.2003</subfield>
        </datafield>
    </record>
    """
    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)
    assert data.get('intendedAudience') == [{
            'audienceType': 'understanding_level',
            'value': 'target_understanding_teenagers_12_15'
        }, {
            'audienceType': 'filmage_ch',
            'value': 'from the age of 12'
        }]

    marc21xml = """
    <record>
        <datafield tag="521" ind1=" " ind2=" ">
            <subfield code="a">Ado (12-15 ans)</subfield>
            <subfield code="9">vsbcvs/06.2003</subfield>
        </datafield>
    </record>
    """
    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)
    assert data.get('intendedAudience') == [{
            'audienceType': 'undefined',
            'value': 'Ado (12-15 ans)'
        }]


def test_marc21_to_original_title_from_500():
    """Test dojson original title from field 500, (L36)."""

    marc21xml = """
    <record>
      <datafield tag="500" ind1=" " ind2=" ">
        <subfield code="a">Traduit de: Harry Potter secrets</subfield>
      </datafield>
    </record>
    """
    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)
    assert data.get('originalTitle') == ['Harry Potter secrets']


def test_marc21_to_notes_from_500():
    """Test dojson notes from field 500 (L35)."""

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


def test_marc21_to_notes_from_510():
    """Test dojson notes from field 510 (L35)."""

    marc21xml = """
    <record>
      <datafield tag="510" ind1=" " ind2=" ">
        <subfield code="a">note 1</subfield>
        <subfield code="c">1c</subfield>
      </datafield>
      <datafield tag="510" ind1=" " ind2=" ">
        <subfield code="a">note 2</subfield>
        <subfield code="c">2c</subfield>
        <subfield code="x">2x</subfield>
      </datafield>
    </record>
    """
    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)
    assert data.get('note') == [{
            'noteType': 'cited_by',
            'label': 'note 1 1c'
        }, {
            'noteType': 'cited_by',
            'label': 'note 2 2c 2x'
        }
    ]


def test_marc21_to_notes_from_530_545_580():
    """Test dojson notes from field 530, 545 and 580 (L35)."""

    marc21xml = """
    <record>
      <datafield tag="530" ind1=" " ind2=" ">
        <subfield code="a">note 530</subfield>
      </datafield>
      <datafield tag="545" ind1=" " ind2=" ">
        <subfield code="a">note 545</subfield>
      </datafield>
      <datafield tag="580" ind1=" " ind2=" ">
        <subfield code="a">note 580</subfield>
      </datafield>
    </record>
    """
    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)
    assert data.get('note') == [{
            'noteType': 'general',
            'label': 'note 530'
        }, {
            'noteType': 'general',
            'label': 'note 545'
        }, {
            'noteType': 'general',
            'label': 'note 580'
        }
    ]


def test_marc21_to_classification_from_050():
    """Test dojson classification from 050 (L38)."""

    marc21xml = """
    <record>
      <datafield tag="035" ind1=" " ind2=" ">
        <subfield code="a">R008733390</subfield>
      </datafield>
      <datafield tag="050" ind1=" " ind2="0">
        <subfield code="a">JK468.I6</subfield>
        <subfield code="b">.J47 2018</subfield>
      </datafield>
      <datafield tag="050" ind1=" " ind2="4">
        <subfield code="a">JK500.I8</subfield>
        <subfield code="b">.J47 2019</subfield>
      </datafield>
    </record>
    """
    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)
    assert data.get('classification') == [{
          'type': 'bf:ClassificationLcc',
          'classificationPortion': 'JK468.I6',
          'assigner': 'LOC'
        }, {
          'type': 'bf:ClassificationLcc',
          'classificationPortion': 'JK500.I8'
        }
    ]


def test_marc21_to_classification_from_060():
    """Test dojson classification from 060 (L38)."""

    marc21xml = """
    <record>
      <datafield tag="035" ind1=" " ind2=" ">
        <subfield code="a">0364474</subfield>
      </datafield>
      <datafield tag="060" ind1=" " ind2="4">
        <subfield code="a">WM 460</subfield>
      </datafield>
      <datafield tag="060" ind1=" " ind2="0">
        <subfield code="a">WM 800</subfield>
      </datafield>
    </record>
    """
    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)
    assert data.get('classification') == [{
          'type': 'bf:ClassificationNlm',
          'classificationPortion': 'WM 460'
        }, {
          'type': 'bf:ClassificationNlm',
          'classificationPortion': 'WM 800',
          'assigner': 'NLM'
        }
    ]


def test_marc21_to_classification_from_080():
    """Test dojson classification from 080 (L38)."""

    marc21xml = """
    <record>
      <datafield tag="080" ind1="0" ind2=" ">
        <subfield code="a">821.134.2-31</subfield>
      </datafield>
      <datafield tag="080" ind1=" " ind2=" ">
        <subfield code="a">900.135.3-32</subfield>
      </datafield>
      <datafield tag="080" ind1="0" ind2=" ">
        <subfield code="a">700.138.1-45</subfield>
        <subfield code="2">dollar_2</subfield>
      </datafield>
      <datafield tag="080" ind1="1" ind2=" ">
        <subfield code="a">600.139.1-46</subfield>
        <subfield code="2">dollar_2</subfield>
      </datafield>
      <datafield tag="080" ind1="1" ind2=" ">
        <subfield code="a">500.156.1-47</subfield>
      </datafield>
    </record>
    """
    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)
    assert data.get('classification') == [{
          'type': 'bf:ClassificationUdc',
          'classificationPortion': '821.134.2-31',
          'edition': "Full edition"
        }, {
          'type': 'bf:ClassificationUdc',
          'classificationPortion': '900.135.3-32',
        }, {
          'type': 'bf:ClassificationUdc',
          'classificationPortion': '700.138.1-45',
          'edition': "Full edition, dollar_2"
        }, {
          'type': 'bf:ClassificationUdc',
          'classificationPortion': '600.139.1-46',
          'edition': "Abridged edition, dollar_2"
        }, {
          'type': 'bf:ClassificationUdc',
          'classificationPortion': '500.156.1-47',
          'edition': "Abridged edition"
        }
    ]


def test_marc21_to_classification_from_082():
    """Test dojson classification from 082 (L38)."""

    marc21xml = """
    <record>
      <datafield tag="035" ind1=" " ind2=" ">
        <subfield code="a">R008855729</subfield>
      </datafield>
      <datafield tag="082" ind1="1" ind2="4">
        <subfield code="a">820</subfield>
        <subfield code="2">15</subfield>
      </datafield>
      <datafield tag="082" ind1="1" ind2="4">
        <subfield code="a">821</subfield>
      </datafield>
      <datafield tag="082" ind1=" " ind2="0">
        <subfield code="a">822</subfield>
        <subfield code="2">15</subfield>
      </datafield>
      <datafield tag="082" ind1="1" ind2="4">
        <subfield code="a">823</subfield>
        <subfield code="2">15</subfield>
      </datafield>
    </record>
    """
    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)
    assert data.get('classification') == [{
          'type': 'bf:ClassificationDdc',
          'classificationPortion': '820',
          'edition': "Abridged edition, 15"
        }, {
          'type': 'bf:ClassificationDdc',
          'classificationPortion': '821',
          'edition': "Abridged edition"
        }, {
          'type': 'bf:ClassificationDdc',
          'classificationPortion': '822',
          'edition': "15",
          'assigner': 'LOC'
        }, {
          'type': 'bf:ClassificationDdc',
          'classificationPortion': '823',
          'edition': "Abridged edition, 15"
        }
    ]


def test_marc21_to_subjects_from_980_2_factum():
    """Test dojson subjects from 980 2$ factum (L50).
    - no classification to produce for $2 factum (38)
    """

    marc21xml = """
    <record>
      <datafield tag="980" ind1=" " ind2=" ">
        <subfield code="2">factum</subfield>
        <subfield code="a">Conti, Louis de Bourbon, prince de</subfield>
      </datafield>
      <datafield tag="980" ind1=" " ind2=" ">
        <subfield code="2">factum</subfield>
        <subfield code="a">Lesdiguières, Marie-Françoise de Gondi</subfield>
      </datafield>
    </record>
    """
    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)
    assert data.get('classification') is None
    assert data.get('subjects') == [{
            'type': 'bf:Person',
            'preferred_name': 'Conti, Louis de Bourbon, prince de',
            'source': 'factum',
        }, {
            'type': 'bf:Person',
            'preferred_name': 'Lesdiguières, Marie-Françoise de Gondi',
            'source': 'factum',
        }
    ]


def test_marc21_to_classification_from_980_2_musg_musi():
    """Test dojson classification from 980 2$ musg and $2 musi (L38)."""

    marc21xml = """
    <record>
      <datafield tag="035" ind1=" " ind2=" ">
        <subfield code="a">1673149</subfield>
      </datafield>
      <datafield tag="980" ind1=" " ind2=" ">
        <subfield code="2">musg</subfield>
        <subfield code="a">Opéra</subfield>
        <subfield code="d">soli, choeur, orchestre</subfield>
        <subfield code="e">1851-1900</subfield>
      </datafield>
      <datafield tag="980" ind1=" " ind2=" ">
        <subfield code="2">musi</subfield>
        <subfield code="a">soli, choeur, piano (adaptation)</subfield>
      </datafield>
    </record>
    """
    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)
    assert data.get('classification') == [{
          'type': 'classification_musicale_genres',
          'classificationPortion': 'Opéra',
          'subdivision': ['soli, choeur, orchestre', '1851-1900']
        }, {
          'type': 'classification_musicale_instruments',
          'classificationPortion': 'soli, choeur, piano (adaptation)'
        }
    ]


def test_marc21_to_classification_from_980_2_brp_and_dr_sys():
    """Test dojson classification from 980 2$ brp and $2 dr_sys (L38)."""

    marc21xml = """
    <record>
      <datafield tag="035" ind1=" " ind2=" ">
        <subfield code="a">1673149</subfield>
      </datafield>
      <datafield tag="980" ind1=" " ind2=" ">
        <subfield code="2">brp</subfield>
        <subfield code="a">brp_value</subfield>
        <subfield code="d">brp_subdivision</subfield>
        <subfield code="e">should_not_be_converted</subfield>
      </datafield>
      <datafield tag="980" ind1=" " ind2=" ">
        <subfield code="2">dr-sys</subfield>
        <subfield code="a">loi</subfield>
      </datafield>
    </record>
    """
    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)
    assert data.get('classification') == [{
          'type': 'classification_brunetparguez',
          'classificationPortion': 'brp_value',
          'subdivision': ['brp_subdivision']
        }, {
          'type': 'classification_droit',
          'classificationPortion': 'loi'
        }
    ]


def test_marc21_to_sequence_numbering_from_one_362():
    """Test dojson sequence_numbering from 362 (L39)."""

    marc21xml = """
    <record>
      <datafield tag="362" ind1="0" ind2=" ">
        <subfield code="a">1890-1891 ; 1892/1893 ; 1894-1896/1897</subfield>
      </datafield>
    </record>
    """
    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)
    assert data.get('sequence_numbering') == \
        '1890-1891 ; 1892/1893 ; 1894-1896/1897'


def test_marc21_to_sequence_numbering_from_two_362():
    """Test dojson sequence_numbering from 362 (L39)."""

    marc21xml = """
    <record>
      <datafield tag="362" ind1="0" ind2=" ">
        <subfield code="a">1890-1891 ; 1892/1893 ; 1894-1896/1897</subfield>
      </datafield>
      <datafield tag="362" ind1="0" ind2=" ">
        <subfield code="a">1915/1917-1918/1921 ; 1929</subfield>
      </datafield>
    </record>
    """
    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)
    assert data.get('sequence_numbering') == \
        '1890-1891 ; 1892/1893 ; 1894-1896/1897 ; 1915/1917-1918/1921 ; 1929'


def test_marc21_to_table_of_contents_from_505():
    """Test dojson tableOfContents from 505 (L44)."""

    marc21xml = """
    <record>
      <datafield tag="505" ind1="0" ind2=" ">
        <subfield code="a">Vol. 1: Le prisme noir</subfield>
        <subfield code="g">trad. de l'anglais</subfield>
      </datafield>
      <datafield tag="505" ind1="0" ind2=" ">
        <subfield code="a">Vol. 2 : Le couteau aveuglant</subfield>
      </datafield>

    </record>
    """
    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)
    assert data.get('tableOfContents') == [
        "Vol. 1: Le prisme noir trad. de l'anglais",
        'Vol. 2 : Le couteau aveuglant'
    ]


def test_marc21_to_credits_from_508():
    """Test dojson credits from 508 (L41)."""

    marc21xml = """
    <record>
      <datafield tag="035" ind1=" " ind2=" ">
        <subfield code="a">R008923090</subfield>
      </datafield>
      <datafield tag="508" ind1=" " ind2=" ">
        <subfield code="a">Ont également collaboré: Marco Praz</subfield>
      </datafield>

    </record>
    """
    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)
    assert data.get('credits') == ['Ont également collaboré: Marco Praz']


def test_marc21_to_credits_from_511():
    """Test dojson credits from 511 (L41)."""

    marc21xml = """
    <record>
      <datafield tag="035" ind1=" " ind2=" ">
        <subfield code="a">R009046495</subfield>
      </datafield>
      <datafield tag="511" ind1="0" ind2=" ">
        <subfield code="a">A. Kurmann</subfield>
      </datafield>
    </record>
    """
    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)
    assert data.get('credits') == ["Participants ou interprètes: A. Kurmann"]


# dissertation: [502$a repetitive]
def test_marc21_to_dissertation():
    """Test dojson dissertation (from filed 502 L40)."""
    marc21xml = """
    <record>
        <datafield tag="502" ind1="8" ind2=" ">
            <subfield code="6">880-05</subfield>
            <subfield code="a">Za wen fen wei si bu fen lu ru</subfield>
        </datafield>
        <datafield tag="880" ind1=" " ind2=" ">
            <subfield code="6">502-05/$1</subfield>
            <subfield code="a">杂文分为四部分录入</subfield>
        </datafield>
    </record>
    """
    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)
    assert data.get('dissertation') == [{
            'label': [{
                    'value': 'Za wen fen wei si bu fen lu ru',
                }, {
                    'value': '杂文分为四部分录入',
                    'language': 'und-hani'
                }]
    }]


def test_marc21_to_supplementary_content_from_504():
    """Test dojson supplementaryContent from 504 (L42)."""

    marc21xml = """
    <record>
      <datafield tag="504" ind1=" " ind2=" ">
        <subfield code="a">Bibliographie: p. 238-239</subfield>
      </datafield>
    </record>
    """
    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)
    assert data.get('supplementaryContent') == ['Bibliographie: p. 238-239']


# part_of 773, 800, 830
def test_marc21_to_part_of():
    """Test dojson partOf."""

    marc21xml = """
    <record>
      <datafield tag="773" ind1="1" ind2=" ">
        <subfield code="t">Stuart Hall : critical dialogues</subfield>
        <subfield code="g">411</subfield>
        <subfield code="w">123456</subfield>
      </datafield>
    </record>
    """
    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)
    assert data.get('partOf') == [{
            'document': {'$ref': 'https://ils.rero.ch/api/documents/123456'},
            'numbering': [{'pages': '411'}]
        }
    ]

    marc21xml = """
    <record>
      <datafield tag="773" ind1="1" ind2=" ">
        <subfield code="t">Stuart Hall : critical dialogues</subfield>
        <subfield code="g">411</subfield>
        <subfield code="g">2020/1/2/300</subfield>
        <subfield code="w">123456</subfield>
      </datafield>
    </record>
    """
    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)
    assert data.get('partOf') == [{
            'document': {'$ref': 'https://ils.rero.ch/api/documents/123456'},
            'numbering': [{
                    'pages': '411'
                },
                {
                    'year': '2020',
                    'volume': 1,
                    'issue': 2,
                    'pages': '300'
                }]
        }]

    marc21xml = """
    <record>
      <datafield tag="773" ind1="1" ind2=" ">
        <subfield code="t">Stuart Hall : critical dialogues</subfield>
        <subfield code="g">1/2/300</subfield>
        <subfield code="w">123456</subfield>
      </datafield>
    </record>
    """
    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)
    assert data.get('partOf') == [{
            'document': {'$ref': 'https://ils.rero.ch/api/documents/123456'},
            'numbering': [
                {
                    'volume': 1,
                    'issue': 2,
                    'pages': '300'
                }]
        }]

    marc21xml = """
    <record>
      <datafield tag="773" ind1="1" ind2=" ">
        <subfield code="t">Stuart Hall : critical dialogues</subfield>
        <subfield code="g">1/2/3/4</subfield>
        <subfield code="w">123456</subfield>
      </datafield>
    </record>
    """
    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)
    assert data.get('partOf') == [{
            'document': {'$ref': 'https://ils.rero.ch/api/documents/123456'}
        }]

    marc21xml = """
    <record>
      <datafield tag="773" ind1="1" ind2=" ">
        <subfield code="t">Stuart Hall : critical dialogues</subfield>
        <subfield code="g">2020/411</subfield>
        <subfield code="g">1/2</subfield>
        <subfield code="w">123456</subfield>
      </datafield>
    </record>
    """
    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)
    assert data.get('partOf') == [{
            'document': {'$ref': 'https://ils.rero.ch/api/documents/123456'},
            'numbering': [{
                    'year': '2020',
                    'pages': '411'
                },
                {
                    'volume': 1,
                    'issue': 2
                }]
        }]

    marc21xml = """
    <record>
      <datafield tag="773" ind1="1" ind2=" ">
        <subfield code="t">Stuart Hall : critical dialogues</subfield>
        <subfield code="g"> </subfield>
        <subfield code="w">123456</subfield>
      </datafield>
    </record>
    """
    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)
    assert data.get('partOf') == [{
            'document': {'$ref': 'https://ils.rero.ch/api/documents/123456'}
        }]

    marc21xml = """
    <record>
      <datafield tag="800" ind1="1" ind2=" ">
        <subfield code="t">Stuart Hall : critical dialogues</subfield>
        <subfield code="v">256</subfield>
        <subfield code="w">123456</subfield>
      </datafield>
    </record>
    """
    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)
    assert data.get('partOf') == [{
            'document': {'$ref': 'https://ils.rero.ch/api/documents/123456'},
            'numbering': [{
                    'volume': 256
                }]
        }]


def test_marc21_to_part_of_without_link():
    """Test dojson partOf when no link is specified.

    When a field 773, 800 or 830 has no link specified,
    then a seriesStatement must be generated instead of a partOf.
    But, in this case, a seriesStatement does not be generated
    for a field 773 if a field 580 exists
    and for the fields 800 and 830 if a field 490 exists
    """

    marc21xml = """
    <record>
      <datafield tag="773" ind1="1" ind2=" ">
        <subfield code="t">Stuart Hall : critical dialogues</subfield>
        <subfield code="g">411</subfield>
      </datafield>
    </record>
    """
    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)
    assert data.get('partOf') is None
    assert data.get('seriesStatement') == [{
        'seriesTitle': [{'value': 'Stuart Hall : critical dialogues'}],
        'seriesEnumeration': [{'value': '411'}],
        }
    ]

    # append author and reverse lastname, firstane
    marc21xml = """
    <record>
      <datafield tag="773" ind1="1" ind2=" ">
        <subfield code="a">Wehinger, Walter</subfield>
        <subfield code="t">Neuchâtel disparu</subfield>
        <subfield code="g">8</subfield>
      </datafield>
    </record>
    """
    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)
    assert data.get('partOf') is None
    assert data.get('seriesStatement') == [{
        'seriesTitle': [{'value': 'Neuchâtel disparu / Walter Wehinger'}],
        'seriesEnumeration': [{'value': '8'}],
        }
    ]

    # append author without comma
    marc21xml = """
    <record>
      <datafield tag="773" ind1="1" ind2=" ">
        <subfield code="a">Wehinger</subfield>
        <subfield code="t">Neuchâtel disparu</subfield>
        <subfield code="g">8</subfield>
      </datafield>
    </record>
    """
    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)
    assert data.get('partOf') is None
    assert data.get('seriesStatement') == [{
        'seriesTitle': [{'value': 'Neuchâtel disparu / Wehinger'}],
        'seriesEnumeration': [{'value': '8'}],
        }
    ]

    # append author
    marc21xml = """
    <record>
      <datafield tag="800" ind1="1" ind2=" ">
        <subfield code="a">Jacq, Christian. -</subfield>
        <subfield code="t">Ramsès</subfield>
        <subfield code="v">1</subfield>
      </datafield>
    </record>
    """
    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)
    assert data.get('partOf') is None
    assert data.get('seriesStatement') == [{
        'seriesTitle': [{'value': 'Ramsès / Christian Jacq'}],
        'seriesEnumeration': [{'value': '1'}],
        }
    ]

    marc21xml = """
    <record>
      <datafield tag="800" ind1="1" ind2=" ">
        <subfield code="t">Stuart Hall : critical dialogues</subfield>
        <subfield code="v">411</subfield>
      </datafield>
    </record>
    """
    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)
    assert data.get('partOf') is None
    assert data.get('seriesStatement') == [{
        'seriesTitle': [{'value': 'Stuart Hall : critical dialogues'}],
        'seriesEnumeration': [{'value': '411'}],
        }
    ]

    marc21xml = """
    <record>
      <datafield tag="830" ind1="1" ind2=" ">
        <subfield code="a">Stuart Hall : critical dialogues</subfield>
        <subfield code="v">411</subfield>
      </datafield>
    </record>
    """
    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)
    assert data.get('partOf') is None
    assert data.get('seriesStatement') == [{
        'seriesTitle': [{'value': 'Stuart Hall : critical dialogues'}],
        'seriesEnumeration': [{'value': '411'}],
        }
    ]

    # tests with field 490 and 580
    marc21xml = """
    <record>
       <datafield tag="580" ind1="1" ind2=" ">
            <subfield code="a">Stuart Hall : critical dialogues</subfield>
            <subfield code="v">411</subfield>
      </datafield>
      <datafield tag="773" ind1="1" ind2=" ">
        <subfield code="t">Stuart Hall : critical dialogues</subfield>
        <subfield code="g">411</subfield>
      </datafield>
    </record>
    """
    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)
    assert data.get('partOf') is None
    assert data.get('seriesStatement') is None

    marc21xml = """
    <record>
      <datafield tag="490" ind1="1" ind2=" ">
            <subfield code="a">Stuart Hall : all critical dialogues</subfield>
            <subfield code="v">512</subfield>
      </datafield>
      <datafield tag="800" ind1="1" ind2=" ">
        <subfield code="t">Stuart Hall : critical dialogues</subfield>
        <subfield code="v">411</subfield>
      </datafield>
    </record>
    """
    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)
    assert data.get('partOf') is None
    # the seriesStatement is generated form 490 and not from the 800
    assert data.get('seriesStatement') == [{
        'seriesTitle': [{'value': 'Stuart Hall : all critical dialogues'}],
        'seriesEnumeration': [{'value': '512'}],
        }
    ]

    marc21xml = """
    <record>
      <datafield tag="490" ind1="1" ind2=" ">
            <subfield code="a">Stuart Hall : all critical dialogues</subfield>
            <subfield code="v">512</subfield>
      </datafield>
      <datafield tag="830" ind1="1" ind2=" ">
        <subfield code="a">Stuart Hall : critical dialogues</subfield>
        <subfield code="v">411</subfield>
      </datafield>
    </record>
    """
    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)
    assert data.get('partOf') is None
    # the seriesStatement is generated form 490 and not from the 800
    assert data.get('seriesStatement') == [{
        'seriesTitle': [{'value': 'Stuart Hall : all critical dialogues'}],
        'seriesEnumeration': [{'value': '512'}],
        }
    ]


def test_marc21_to_part_of_with_multiple_800():
    """Test dojson partOf when multiple link specified.

    When multiple fields 800 having the same link exists
    """
    marc21xml = """
    <record>
      <datafield tag="245" ind1="1" ind2="0">
        <subfield code="a">Finis Africae /</subfield>
        <subfield code="c">dessins: Mirallès, scénario: Ruiz</subfield>
      </datafield>
      <datafield tag="490" ind1="1" ind2=" ">
        <subfield code="a">A la recherche de la Licorne / Mirallès</subfield>
        <subfield code="v">3</subfield>
      </datafield>
      <datafield tag="490" ind1="1" ind2=" ">
        <subfield code="a">Collection &quot;Vécu&quot;</subfield>
      </datafield>
      <datafield tag="800" ind1="1" ind2=" ">
        <subfield code="a">Mirallés, Ana. -</subfield>
        <subfield code="t">A la recherche de la Licorne</subfield>
        <subfield code="v">3</subfield>
        <subfield code="w">780067</subfield>
      </datafield>
      <datafield tag="800" ind1="1" ind2=" ">
        <subfield code="a">Ruiz, Emilio. -</subfield>
        <subfield code="t">A la recherche de la Licorne</subfield>
        <subfield code="v">3</subfield>
        <subfield code="w">780067</subfield>
      </datafield>
      <datafield tag="830" ind1=" " ind2="0">
        <subfield code="a">Collection &quot;Vécu&quot;.</subfield>
        <subfield code="p">Glénat</subfield>
      </datafield>
    </record>
    """
    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)
    assert data.get('partOf') == [{
            'document': {'$ref': 'https://ils.rero.ch/api/documents/780067'},
            'numbering': [{
                    'volume': 3
                }]
        }]
    # the seriesStatement is generated form 490 and not from the 800
    assert data.get('seriesStatement') == [{
        'seriesTitle': [{'value': 'A la recherche de la Licorne / Mirallès'}],
        'seriesEnumeration': [{'value': '3'}],
        }, {
        'seriesTitle': [{'value': 'Collection "Vécu"'}],
        }
    ]


def test_marc21_to_identifiedBy_from_020():
    """Test dojson identifiedBy from 020."""

    marc21xml = """
    <record>
      <datafield tag="020" ind1=" " ind2=" ">
        <subfield code="z">8124605254</subfield>
      </datafield>
      <datafield tag="020" ind1=" " ind2=" ">
        <subfield code="a">9788124605257 (broché)</subfield>
      </datafield>
      <datafield tag="020" ind1=" " ind2=" ">
        <subfield code="a">9788189997212</subfield>
        <subfield code="q">hbk.</subfield>
        <subfield code="c">£125.00</subfield>
      </datafield>
    </record>
    """
    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)
    assert data.get('identifiedBy') == [
        {
            'type': 'bf:Isbn',
            'status': 'invalid or cancelled',
            'value': '8124605254'
        },
        {
            'type': 'bf:Isbn',
            'qualifier': 'broché',
            'value': '9788124605257'
        },
        {
            'type': 'bf:Isbn',
            'qualifier': 'hbk.',
            'value': '9788189997212'
        }
    ]


def test_marc21_to_identifiedBy_from_022():
    """Test dojson identifiedBy from 022."""

    marc21xml = """
    <record>
      <datafield tag="022" ind1=" " ind2=" ">
        <subfield code="a">0264-2875</subfield>
        <subfield code="l">0264-2875</subfield>
      </datafield>
      <datafield tag="022" ind1=" " ind2=" ">
        <subfield code="a">0264-2875</subfield>
        <subfield code="y">0080-4649</subfield>
      </datafield>
      <datafield tag="022" ind1=" " ind2=" ">
        <subfield code="m">0080-4650</subfield>
      </datafield>
    </record>
    """
    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)
    assert data.get('identifiedBy') == [
        {
            'type': 'bf:Issn',
            'value': '0264-2875'
        },
        {
            'type': 'bf:IssnL',
            'value': '0264-2875'
        },
        {
            'type': 'bf:Issn',
            'value': '0264-2875'
        },
        {
            'type': 'bf:Issn',
            'status': 'invalid',
            'value': '0080-4649'
        },
        {
            'type': 'bf:IssnL',
            'status': 'cancelled',
            'value': '0080-4650'
        }
    ]


def test_marc21_to_identifiedBy_from_024_snl_bnf():
    """Test dojson identifiedBy from 024 field snl and bnf."""
    marc21xml = """
    <record>
      <datafield tag="024" ind1="7" ind2=" ">
        <subfield code="a">http://permalink.snl.ch/bib/chccsa86779</subfield>
        <subfield code="2">permalink</subfield>
      </datafield>
      <datafield tag="024" ind1="7" ind2=" ">
        <subfield code="a">http://catalogue.bnf.fr/ark:/12148/cb312v</subfield>
        <subfield code="2">uri</subfield>
      </datafield>
    </record>
    """
    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)
    assert data.get('identifiedBy') == [
        {
            'type': 'uri',
            'source': 'SNL',
            'value': 'http://permalink.snl.ch/bib/chccsa86779'
        },
        {
            'type': 'uri',
            'source': 'BNF',
            'value': 'http://catalogue.bnf.fr/ark:/12148/cb312v'
        }
    ]

    marc21xml = """
    <record>
      <datafield tag="024" ind1="7" ind2=" ">
        <subfield code="a">http://slsp.ch/12345</subfield>
        <subfield code="2">uri</subfield>
      </datafield>
    </record>
    """
    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)
    assert data.get('identifiedBy') == [
        {
            'type': 'bf:Identifier',
            'value': 'http://slsp.ch/12345'
        }
    ]


def test_marc21_to_identifiedBy_from_024_with_subfield_2():
    """Test dojson identifiedBy from 024 field with subfield 2."""

    marc21xml = """
    <record>
      <datafield tag="024" ind1="7" ind2=" ">
        <subfield code="a">10.1007/978-3-540-37973-7</subfield>
        <subfield code="c">£125.00</subfield>
        <subfield code="d">note</subfield>
        <subfield code="2">doi</subfield>
      </datafield>
      <datafield tag="024" ind1="7" ind2=" ">
        <subfield code="a">urn:nbn:de:101:1-201609052530</subfield>
        <subfield code="2">urn</subfield>
      </datafield>
      <datafield tag="024" ind1="7" ind2=" ">
        <subfield code="a">NIPO 035-16-060-7</subfield>
        <subfield code="2">nipo</subfield>
      </datafield>
      <datafield tag="024" ind1="7" ind2=" ">
        <subfield code="a">7290105422026</subfield>
        <subfield code="2">danacode</subfield>
      </datafield>
      <datafield tag="024" ind1="7" ind2=" ">
        <subfield code="a">VD18 10153438</subfield>
        <subfield code="2">vd18</subfield>
      </datafield>
      <datafield tag="024" ind1="7" ind2=" ">
        <subfield code="a">00028947969525</subfield>
        <subfield code="2">gtin-14</subfield>
      </datafield>
    </record>
    """
    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)
    assert data.get('identifiedBy') == [
        {
            'type': 'bf:Doi',
            'value': '10.1007/978-3-540-37973-7',
            'note': 'note'
        },
        {
            'type': 'bf:Urn',
            'value': 'urn:nbn:de:101:1-201609052530'
        },
        {
            'type': 'bf:Local',
            'source': 'NIPO',
            'value': 'NIPO 035-16-060-7'
        },
        {
            'type': 'bf:Local',
            'source': 'danacode',
            'value': '7290105422026'
        },
        {
            'type': 'bf:Local',
            'source': 'vd18',
            'value': 'VD18 10153438'
        },
        {
            'type': 'bf:Gtin14Number',
            'value': '00028947969525'
        }
    ]


def test_marc21_to_identifiedBy_from_024_without_subfield_2():
    """Test dojson identifiedBy from 024 field without subfield 2."""

    marc21xml = """
    <record>
      <datafield tag="024" ind1=" " ind2=" ">
        <subfield code="a">9782100745463</subfield>
      </datafield>
      <datafield tag="024" ind1="0" ind2="1">
        <subfield code="a">702391010582 (vol. 2) </subfield>
      </datafield>
      <datafield tag="024" ind1="0" ind2="2">
        <subfield code="a">Erato ECD 88030</subfield>
      </datafield>
      <datafield tag="024" ind1="1" ind2=" ">
        <subfield code="a">604907014223 (vol. 5)</subfield>
      </datafield>
      <datafield tag="024" ind1="1" ind2="2">
        <subfield code="a">EMI Classics 5 55585 2</subfield>
      </datafield>
      <datafield tag="024" ind1="2" ind2=" ">
        <subfield code="a">M006546565 (kritischer B., kartoniert)</subfield>
        <subfield code="q">vol. 1</subfield>
      </datafield>
      <datafield tag="024" ind1="2" ind2=" ">
        <subfield code="a">9790201858135</subfield>
        <subfield code="q">Kritischer Bericht</subfield>
      </datafield>
      <datafield tag="024" ind1="2" ind2=" ">
        <subfield code="a">4018262101065 (Bd. 1)</subfield>
      </datafield>
      <datafield tag="024" ind1="3" ind2=" ">
        <subfield code="a">309-5-56-196162-1</subfield>
        <subfield code="q">CD audio classe</subfield>
      </datafield>
      <datafield tag="024" ind1="3" ind2=" ">
        <subfield code="a">9783737407427</subfield>
        <subfield code="q">Bd 1</subfield>
        <subfield code="q">pbk.</subfield>
      </datafield>
      <datafield tag="024" ind1="3" ind2="2">
        <subfield code="a">EP 2305</subfield>
      </datafield>
      <datafield tag="024" ind1="3" ind2="2">
        <subfield code="a">97 EP 1234</subfield>
      </datafield>
     <datafield tag="024" ind1="8" ind2=" ">
        <subfield code="a">ELC1283925</subfield>
      </datafield>
      <datafield tag="024" ind1="8" ind2=" ">
        <subfield code="a">0000-0002-A3B1-0000-0-0000-0000-2</subfield>
      </datafield>
    </record>
    """
    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)
    assert data.get('identifiedBy') == [
        {
            'type': 'bf:Identifier',
            'value': '9782100745463'
        },
        {
            'type': 'bf:Isrc',
            'qualifier': 'vol. 2',
            'value': '702391010582'
        },
        {
            'type': 'bf:Isrc',
            'value': 'Erato ECD 88030'
        },
        {
            'type': 'bf:Upc',
            'qualifier': 'vol. 5',
            'value': '604907014223'
        },
        {
            'type': 'bf:Upc',
            'value': 'EMI Classics 5 55585 2'
        },
        {
            'type': 'bf:Ismn',
            'qualifier': 'kritischer B., kartoniert, vol. 1',
            'value': 'M006546565'
        },
        {
            'type': 'bf:Ismn',
            'qualifier': 'Kritischer Bericht',
            'value': '9790201858135'
        },
        {
            'type': 'bf:Identifier',
            'qualifier': 'Bd. 1',
            'value': '4018262101065'
        },
        {
            'type': 'bf:Identifier',
            'qualifier': 'CD audio classe',
            'value': '309-5-56-196162-1'
        },
        {
            'type': 'bf:Ean',
            'qualifier': 'Bd 1, pbk.',
            'value': '9783737407427'
        },
        {
            'type': 'bf:Identifier',
            'value': 'EP 2305'
        },
        {
            'type': 'bf:Ean',
            'value': '97 EP 1234'
        },
        {
            'type': 'bf:Identifier',
            'value': 'ELC1283925'
        },
        {
            'type': 'bf:Isan',
            'value': '0000-0002-A3B1-0000-0-0000-0000-2'
        }
    ]


def test_marc21_to_identifiedBy_from_028():
    """Test dojson identifiedBy from 035."""

    marc21xml = """
    <record>
      <datafield tag="028" ind1="3" ind2=" ">
        <subfield code="a">1234</subfield>
        <subfield code="b">SRC</subfield>
        <subfield code="q">Qualif1</subfield>
        <subfield code="q">Qualif2</subfield>
      </datafield>
    </record>
    """
    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)
    assert data.get('identifiedBy') == [
        {
            'type': 'bf:MusicPublisherNumber',
            'source': 'SRC',
            'qualifier': 'Qualif1, Qualif2',
            'value': '1234'
        }
    ]

    marc21xml = """
    <record>
      <datafield tag="028" ind1="9" ind2=" ">
        <subfield code="a">1234</subfield>
        <subfield code="b">SRC</subfield>
        <subfield code="q">Qualif1</subfield>
        <subfield code="q">Qualif2</subfield>
      </datafield>
    </record>
    """
    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)
    assert data.get('identifiedBy') == [
        {
            'type': 'bf:Identifier',
            'source': 'SRC',
            'qualifier': 'Qualif1, Qualif2',
            'value': '1234'
        }
    ]


def test_marc21_to_acquisition_terms():
    """Test dojson acquisition terms from 020, 024 et 037."""

    marc21xml = """
    <record>
      <datafield tag="020" ind1=" " ind2=" ">
        <subfield code="a">3727201525</subfield>
        <subfield code="c">CHF 68</subfield>
      </datafield>
      <datafield tag="024" ind1="7" ind2=" ">
        <subfield code="a">10.1007/978-3-540-37973-7</subfield>
        <subfield code="c">£125.00</subfield>
        <subfield code="d">note</subfield>
        <subfield code="2">doi</subfield>
      </datafield>
      <datafield ind1=" " ind2=" " tag="037">
        <subfield code="c">Fr. 147.20</subfield>
        <subfield code="c">€133.14</subfield>
      </datafield>
      <datafield ind1=" " ind2=" " tag="037">
        <subfield code="c">gratuit</subfield>
      </datafield>
    """
    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)
    assert data.get('acquisitionTerms') == [
        'CHF 68',
        '£125.00',
        'Fr. 147.20',
        '€133.14',
        'gratuit'
    ]


def test_marc21_to_subjects():
    """Test dojson subjects from 6xx (L49, L50)."""
    # field 600 without $t
    marc21xml = """
    <record>
    <datafield ind1="0" ind2="7" tag="600">
        <subfield code="a">Athenagoras</subfield>
        <subfield code="c">(patriarche oecuménique ;</subfield>
        <subfield code="b">1)</subfield>
        <subfield code="2">rero</subfield>
        <subfield code="0">(RERO)A009963344</subfield>
    </datafield>
    </record>
    """
    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)
    assert data.get('subjects') == [{
          'type': 'bf:Person',
          'preferred_name': 'Athenagoras (patriarche oecuménique ; 1)',
          'source': 'rero',
          'identifiedBy': {
              'value': 'A009963344',
              'source': 'rero',
              'type': 'bf:Local'
          }
    }]

    # field 611 without $t
    marc21xml = """
    <record>
        <datafield ind1="2" ind2="7" tag="611">
        <subfield code="a">Belalp Hexe</subfield>
        <subfield code="c">(Blatten)</subfield>
        <subfield code="2">rero</subfield>
        <subfield code="0">(RERO)A017827554</subfield>
    </datafield>
    </record>
    """
    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)
    assert data.get('subjects') == [{
          'type': 'bf:Organization',
          'conference': True,
          'preferred_name': 'Belalp Hexe (Blatten)',
          'source': 'rero',
          'identifiedBy': {
              'value': 'A017827554',
              'source': 'rero',
              'type': 'bf:Local'
          }
    }]

    # field 600 with $t
    marc21xml = """
    <record>
    <datafield ind1="1" ind2="7" tag="600">
        <subfield code="a">Giraudoux, Jean.</subfield>
        <subfield code="t">Electre</subfield>
        <subfield code="2">rero</subfield>
        <subfield code="0">(IDREF)027538303</subfield>
    </datafield>
    </record>
    """
    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)
    assert data.get('subjects') == [{
          'type': 'bf:Work',
          'creator': 'Giraudoux, Jean',
          'title': 'Electre',
          'source': 'rero',
          'identifiedBy': {
              'value': '027538303',
              'source': 'idref',
              'type': 'bf:Local'
          }
    }]

    # field 611 with $t
    marc21xml = """
    <record>
    <datafield ind1="2" ind2="7" tag="611">
        <subfield code="a">Concile de Vatican 2</subfield>
        <subfield code="t">Influence reçue</subfield>
        <subfield code="2">rero</subfield>
        <subfield code="0">(RERO)A010067471</subfield>
    </datafield>
    </record>
    """
    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)
    assert data.get('subjects') == [{
          'type': 'bf:Work',
          'creator': 'Concile de Vatican 2',
          'title': 'Influence reçue',
          'source': 'rero',
          'identifiedBy': {
              'value': 'A010067471',
              'source': 'rero',
              'type': 'bf:Local'
          }
    }]

    # field 650 topic
    marc21xml = """
    <record>
    <datafield ind1=" " ind2="7" tag="650">
        <subfield code="a">Vie</subfield>
        <subfield code="2">rero</subfield>
        <subfield code="0">(RERO)A021002965</subfield>
    </datafield>
    </record>
    """
    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)
    assert data.get('subjects') == [{
          'type': 'bf:Topic',
          'term': 'Vie',
          'source': 'rero',
          'identifiedBy': {
              'value': 'A021002965',
              'source': 'rero',
              'type': 'bf:Local'
          }
    }]

    # field 650 temporal
    marc21xml = """
    <record>
    <datafield ind1=" " ind2="7" tag="650">
        <subfield code="a">1961</subfield>
        <subfield code="2">rero</subfield>
        <subfield code="0">(RERO)G021002965</subfield>
    </datafield>
    </record>
    """
    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)
    assert data.get('subjects') == [{
          'type': 'bf:Temporal',
          'term': '1961',
          'source': 'rero',
          'identifiedBy': {
              'value': 'G021002965',
              'source': 'rero',
              'type': 'bf:Local'
          }
    }]

    # field 651
    marc21xml = """
    <record>
    <datafield ind1=" " ind2="7" tag="651">
        <subfield code="a">Europe occidentale</subfield>
        <subfield code="2">rero</subfield>
        <subfield code="0">(RERO)A009975209</subfield>
    </datafield>
    </record>
    """
    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)
    assert data.get('subjects') == [{
          'type': 'bf:Place',
          'preferred_name': 'Europe occidentale',
          'source': 'rero',
          'identifiedBy': {
              'value': 'A009975209',
              'source': 'rero',
              'type': 'bf:Local'
          }
    }]

    # field 655 with $0
    marc21xml = """
    <record>
    <datafield ind1=" " ind2="7" tag="655">
        <subfield code="a">[Bases de données]</subfield>
        <subfield code="2">rero</subfield>
        <subfield code="0">(RERO)A001234567</subfield>
    </datafield>
    </record>
    """
    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)
    assert data.get('genreForm') == [{
          'type': 'bf:Topic',
          'term': 'Bases de données',
          'source': 'rero',
          'identifiedBy': {
              'value': 'A001234567',
              'source': 'rero',
              'type': 'bf:Local'
          }
    }]

    # field 655 without $0
    marc21xml = """
    <record>
    <datafield ind1=" " ind2="7" tag="655">
        <subfield code="a">[Bases de données]</subfield>
        <subfield code="2">rero</subfield>
    </datafield>
    </record>
    """
    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)
    assert data.get('genreForm') == [{
          'type': 'bf:Topic',
          'term': 'Bases de données',
          'source': 'rero'
    }]


def test_marc21_to_subjects_imported():
    """Test dojson subjects imported from 6xx/919 (L53)."""
    # field 919 without $2
    marc21xml = """
    <record>
    <datafield tag="919" ind1=" " ind2="0">
      <subfield code="a">Pollution</subfield>
      <subfield code="a">Government policy</subfield>
      <subfield code="a">Germany (West)</subfield>
      </datafield>
    </record>
    """
    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)
    assert data.get('subjects_imported') == [{
          'type': 'bf:Topic',
          'term': 'Pollution - Government policy - Germany (West)'
    }]

    # field 919 with $2 chrero and $v
    marc21xml = """
    <record>
      <datafield tag="919" ind1=" " ind2=" ">
        <subfield code="9">651 _7</subfield>
        <subfield code="a">Zermatt (Suisse, VS)</subfield>
        <subfield code="y">19e s. (fin)</subfield>
        <subfield code="v">[carte postale]</subfield>
        <subfield code="2">chrero</subfield>
    </datafield>
    </record>
    """
    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)
    assert data.get('subjects_imported') == [{
          'type': 'bf:Topic',
          'term': 'Zermatt (Suisse, VS) - 19e s. (fin) - [carte postale]',
          'source': 'chrero'
    }]

    # field 919 with $2 chrero and without $v
    marc21xml = """
    <record>
      <datafield tag="919" ind1=" " ind2=" ">
        <subfield code="9">651 _7</subfield>
        <subfield code="a">Zermatt (Suisse, VS)</subfield>
        <subfield code="y">19e s. (fin)</subfield>
        <subfield code="2">chrero</subfield>
    </datafield>
    </record>
    """
    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)
    assert data == {}

    # field 919 with $2 chrero and without $v
    marc21xml = """
    <record>
        <datafield ind1=" " ind2=" " tag="919">
          <subfield code="9">650 _7</subfield>
          <subfield code="a">chemin de fer</subfield>
          <subfield code="z">Suisse</subfield>
         <subfield code="2">chrero</subfield>
        </datafield>
    </record>
    """
    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)
    assert data == {}

    # field 919 with $2 ram|rameau|gnd|rerovoc
    marc21xml = """
    <record>
      <datafield tag="919" ind1=" " ind2=" ">
        <subfield code="a">Sekundarstufe</subfield>
        <subfield code="0">(DE-588)4077347-4</subfield>
        <subfield code="2">gnd</subfield>
      </datafield>
    </record>
    """
    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)
    assert data.get('subjects_imported') == [{
          'type': 'bf:Topic',
          'term': 'Sekundarstufe',
          'source': 'gnd'
    }]

    # field 650 _0
    marc21xml = """
    <record>
      <datafield tag="610" ind1="2" ind2="0">
        <subfield code="a">Conference of European Churches</subfield>
      </datafield>
    </record>
    """
    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)
    assert data.get('subjects_imported') == [{
          'type': 'bf:Organization',
          'conference': False,
          'preferred_name': 'Conference of European Churches',
          'source': 'LCSH'
    }]

    # field 650 _2
    marc21xml = """
    <record>
      <datafield tag="650" ind1=" " ind2="2">
        <subfield code="a">Philosophy, Medical</subfield>
      </datafield>
    </record>
    """
    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)
    assert data.get('subjects_imported') == [{
          'type': 'bf:Topic',
          'term': 'Philosophy, Medical',
          'source': 'MeSH'
    }]

    # field 650 with $2 rerovoc
    marc21xml = """
    <record>
      <datafield tag="650" ind1=" " ind2="7">
      <subfield code="a">société (milieu humain)</subfield>
      <subfield code="2">rerovoc</subfield>
    </datafield>
    </record>
    """
    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)
    assert data.get('subjects_imported') == [{
          'type': 'bf:Topic',
          'term': 'société (milieu humain)',
          'source': 'rerovoc'
    }]

    # field 650 with $2 rerovoc
    marc21xml = """
    <record>
        <datafield ind1="2" ind2="0" tag="610">
            <subfield code="a">Catholic Church</subfield>
            <subfield code="x">Relations</subfield>
            <subfield code="x">Eastern churches</subfield>
        </datafield>
    </record>
    """
    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)
    assert data.get('subjects_imported') == [{
          'type': 'bf:Organization',
          'preferred_name': 'Catholic Church - Relations - Eastern churches',
          'source': 'LCSH',
          'conference': False
    }]


def test_marc21_to_genreForm_imported():
    """Test dojson genreForm imported from 655/919 (L54)."""
    # field 919 with $2 gatbegr|gnd-content
    marc21xml = """
    <record>
      <datafield tag="919" ind1=" " ind2=" ">
        <subfield code="0">(DE-588)4133254-4</subfield>
        <subfield code="0">(DE-101)041332547</subfield>
        <subfield code="a">Erlebnisbericht</subfield>
        <subfield code="2">gnd-content</subfield>
      </datafield>
    </record>
    """
    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)
    assert data.get('genreForm_imported') == [{
          'type': 'bf:Topic',
          'term': 'Erlebnisbericht',
          'source': 'gnd-content'
    }]

    # field 919 with $2 chrero and $v
    marc21xml = """
    <record>
      <datafield tag="919" ind1=" " ind2=" ">
        <subfield code="9">655 _7</subfield>
        <subfield code="a">Zermatt (Suisse, VS)</subfield>
        <subfield code="y">19e s. (fin)</subfield>
        <subfield code="v">[carte postale]</subfield>
        <subfield code="2">gnd-content</subfield>
      </datafield>
    </record>
    """
    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)
    assert data.get('genreForm_imported') == [{
          'type': 'bf:Topic',
          'term': 'Zermatt (Suisse, VS) - 19e s. (fin) - [carte postale]',
          'source': 'gnd-content'
    }]


def test_marc21_to_identifiedBy_from_035():
    """Test dojson identifiedBy from 035."""

    marc21xml = """
    <record>
      <datafield tag="035" ind1=" " ind2=" ">
        <subfield code="a">R008945501</subfield>
      </datafield>
    </record>
    """
    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)
    assert data.get('identifiedBy') == [
        {
            'type': 'bf:Local',
            'source': 'RERO',
            'value': 'R008945501'
        }
    ]


@mock.patch('requests.get')
def test_marc21_to_electronicLocator_from_856(mock_cover_get):
    """Test dojson electronicLocator from 856."""

    marc21xml = """
    <record>
      <datafield tag="856" ind1="4" ind2="1">
        <subfield code="3">fullText</subfield>
        <subfield code="u">http://reader.digitale-s.de/r/d/XXX.html</subfield>
        <subfield code="z">Vol. 1</subfield>
      </datafield>
    </record>
    """
    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)
    assert data.get('electronicLocator') == [
        {
            'url': 'http://reader.digitale-s.de/r/d/XXX.html',
            'type': 'versionOfResource',
            'content': 'fullText',
            'publicNote': ['Vol. 1']
        }
    ]
    assert get_cover_art(data) is None
    assert get_other_accesses(data) == []

    marc21xml = """
    <record>
      <datafield tag="856" ind1="4" ind2="2">
        <subfield code="3">Inhaltsverzeichnis</subfield>
        <subfield code="u">http://d-nb.info/1071856731/04</subfield>
        <subfield code="q">application/pdf</subfield>
        <subfield code="z">Bd. 1</subfield>
      </datafield>
    </record>
    """
    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)
    assert data.get('electronicLocator') == [
        {
            'url': 'http://d-nb.info/1071856731/04',
            'type': 'relatedResource',
            'publicNote': ['Inhaltsverzeichnis', 'Bd. 1']
        }
    ]
    assert get_cover_art(data) is None
    assert get_other_accesses(data) == [
        {
            'content': 'http://d-nb.info/1071856731/04',
            'public_note': 'Inhaltsverzeichnis, Bd. 1',
            'type': 'relatedResource',
            'url': 'http://d-nb.info/1071856731/04'
        }
    ]

    marc21xml = """
    <record>
      <datafield tag="856" ind1="4" ind2="2">
        <subfield code="3">Inhaltsverzeichnis</subfield>
        <subfield code="u">http://d-nb.info/1071856731/04</subfield>
        <subfield code="q">application/pdf</subfield>
        <subfield code="z">Bd. 1</subfield>
      </datafield>
      <datafield tag="856" ind1="4" ind2="2">
        <subfield code="3">coverImage</subfield>
        <subfield code="u">http://d-nb.info/image.png</subfield>
      </datafield>
      <datafield tag="856" ind1="4" ind2="1">
        <subfield code="3">coverImage</subfield>
        <subfield code="u">http://d-nb.info/image2.png</subfield>
      </datafield>
    </record>
    """
    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)
    assert data.get('electronicLocator') == [
        {
            'url': 'http://d-nb.info/1071856731/04',
            'type': 'relatedResource',
            'publicNote': ['Inhaltsverzeichnis', 'Bd. 1']
        },
        {
            'content': 'coverImage',
            'type': 'relatedResource',
            'url': 'http://d-nb.info/image.png'
        },
        {
            'content': 'coverImage',
            'type': 'versionOfResource',
            'url': 'http://d-nb.info/image2.png'
        }
    ]
    mock_cover_get.return_value = mock_response(json_data={})
    assert get_cover_art(data) == 'http://d-nb.info/image.png'
    assert get_other_accesses(data) == [
        {
            'content': 'http://d-nb.info/1071856731/04',
            'public_note': 'Inhaltsverzeichnis, Bd. 1',
            'type': 'relatedResource',
            'url': 'http://d-nb.info/1071856731/04'
        }
    ]


def test_marc21_to_identifiedBy_from_930():
    """Test dojson identifiedBy from 930."""

    # identifier with source in parenthesis
    marc21xml = """
    <record>
      <datafield tag="930" ind1=" " ind2=" ">
        <subfield code="a">(OCoLC) ocm11113722</subfield>
      </datafield>
    </record>
    """
    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)
    assert data.get('identifiedBy') == [
        {
            'type': 'bf:Local',
            'source': 'OCoLC',
            'value': 'ocm11113722'
        }
    ]
    # identifier without source in parenthesis
    marc21xml = """
    <record>
      <datafield tag="930" ind1=" " ind2=" ">
        <subfield code="a">ocm11113722</subfield>
      </datafield>
    </record>
    """
    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)
    assert data.get('identifiedBy') == [
        {
            'type': 'bf:Local',
            'value': 'ocm11113722'
        }
    ]


@mock.patch('requests.get')
def test_get_contribution_link(mock_get, capsys):
    """Test get mef contribution link"""
    os.environ['RERO_ILS_MEF_HOST'] = 'mef.xxx.rero.ch'

    mock_get.return_value = mock_response(json_data={})
    mef_url = get_contribution_link(
        bibid='1',
        reroid='1',
        id='(IDREF)003945843',
        key='100..',
        value={'0': '(IDREF)003945843'}
    )
    assert mef_url == 'https://mef.rero.ch/api/idref/003945843'

    mock_get.return_value = mock_response(status=404)
    mef_url = get_contribution_link(
        bibid='1',
        reroid='1',
        id='(IDREF)123456789',
        key='100..',
        value={'0': '(IDREF)123456789'}
    )
    assert not mef_url
    out, err = capsys.readouterr()
    assert out == "WARNING MEF CONTRIBUTION IDREF NOT FOUND:\t1\t1\t" + \
        '100.. $0 (IDREF)123456789\t' + \
        'https://mef.xxx.rero.ch/api/idref/123456789\t404\t\n'

    mock_get.return_value = mock_response(status=400)
    mef_url = get_contribution_link(
        bibid='1',
        reroid='1',
        id='X123456789',
        key='100..',
        value={'0': 'X123456789'}
    )
    assert not mef_url


def test_marc21_to_masked():
    """Test record masking.

    Test masking fields 099.
    """
    marc21xml = """
    <record>
      <leader>00501nam a2200133 a 4500</leader>
      <datafield tag="099" ind1=" " ind2=" ">
        <subfield code="a">masked</subfield>
      </datafield>
    </record>
    """
    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)
    assert data.get('_masked')

    marc21xml = """
    <record>
      <leader>00501nam a2200133 a 4500</leader>
      <datafield tag="099" ind1=" " ind2=" ">
        <subfield code="a">toto</subfield>
      </datafield>
    </record>
    """
    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)
    assert not data.get('_masked')

    marc21xml = """
    <record>
      <leader>00501nam a2200133 a 4500</leader>
    </record>
    """
    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)
    assert not data.get('_masked')


def test_marc21_to_content_media_carrier():
    """Test dojson contentMediaCarrier (L30)."""

    marc21xml = """
    <record>
      <leader>00501nam a2200133 a 4500</leader>
      <datafield tag="035" ind1=" " ind2=" ">
        <subfield code="a">R006143240</subfield>
      </datafield>
      <datafield tag="336" ind1=" " ind2=" ">
        <subfield code="b">txt</subfield>
        <subfield code="2">rdacontent</subfield>
      </datafield>
      <datafield tag="336" ind1=" " ind2=" ">
        <subfield code="b">sti</subfield>
        <subfield code="2">rdacontent</subfield>
      </datafield>
      <datafield tag="337" ind1=" " ind2=" ">
        <subfield code="b">n</subfield>
        <subfield code="2">rdamedia</subfield>
      </datafield>
      <datafield tag="338" ind1=" " ind2=" ">
        <subfield code="b">nc</subfield>
        <subfield code="2">rdacarrier</subfield>
      </datafield>
    </record>
    """
    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)
    assert data.get('contentMediaCarrier') == [{
        "contentType": ["rdaco:1020", "rdaco:1014"],
        "mediaType": "rdamt:1007",
        "carrierType": "rdact:1049"
    }]

    # missing 338
    marc21xml = """
    <record>
      <leader>00501nam a2200133 a 4500</leader>
      <datafield tag="035" ind1=" " ind2=" ">
        <subfield code="a">R003453868</subfield>
      </datafield>
      <datafield tag="336" ind1=" " ind2=" ">
        <subfield code="b">txt</subfield>
        <subfield code="2">rdacontent</subfield>
      </datafield>
      <datafield tag="337" ind1=" " ind2=" ">
        <subfield code="b">h</subfield>
        <subfield code="2">rdamedia</subfield>
      </datafield>
    </record>
    """
    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)
    assert data.get('contentMediaCarrier') == [{
        "contentType": ["rdaco:1020"],
        "mediaType": "rdamt:1002"
    }]


def test_marc21_to_content_media_carrier_with_linked_fields():
    """Test dojson contentMediaCarrier (L30)."""

    marc21xml = """
    <record>
      <leader>00501nam a2200133 a 4500</leader>
      <datafield tag="035" ind1=" " ind2=" ">
        <subfield code="a">R006143240</subfield>
      </datafield>
      <datafield tag="336" ind1=" " ind2=" ">
        <subfield code="8">01</subfield>
        <subfield code="b">txt</subfield>
        <subfield code="2">rdacontent</subfield>
      </datafield>
      <datafield tag="336" ind1=" " ind2=" ">
        <subfield code="8">01</subfield>
        <subfield code="b">sti</subfield>
        <subfield code="2">rdacontent</subfield>
      </datafield>
      <datafield tag="336" ind1=" " ind2=" ">
        <subfield code="8">02</subfield>
        <subfield code="b">tci</subfield>
        <subfield code="2">rdacontent</subfield>
      </datafield>
      <datafield tag="337" ind1=" " ind2=" ">
       <subfield code="8">01</subfield>
       <subfield code="b">n</subfield>
        <subfield code="2">rdamedia</subfield>
      </datafield>
      <datafield tag="338" ind1=" " ind2=" ">
        <subfield code="8">01</subfield>
        <subfield code="b">nc</subfield>
        <subfield code="2">rdacarrier</subfield>
      </datafield>
      <datafield tag="338" ind1=" " ind2=" ">
        <subfield code="8">02</subfield>
        <subfield code="b">ck</subfield>
        <subfield code="2">rdacarrier</subfield>
      </datafield>
    </record>
    """
    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)
    assert data.get('contentMediaCarrier') == [{
        "contentType": ["rdaco:1020", "rdaco:1014"],
        "mediaType": "rdamt:1007",
        "carrierType": "rdact:1049"
    }, {
        "contentType": ["rdaco:1015"],
        "mediaType": "rdamt:1003",
        "carrierType": "rdact:1011"
    }]

    # unlinked 337
    marc21xml = """
    <record>
        <leader>00501nam a2200133 a 4500</leader>
        <datafield ind1=" " ind2=" " tag="336">
            <subfield code="8">01</subfield>
            <subfield code="b">txt</subfield>
            <subfield code="2">rdacontent</subfield>
        </datafield>
        <datafield ind1=" " ind2=" " tag="336">
            <subfield code="8">02</subfield>
            <subfield code="b">tcf</subfield>
            <subfield code="2">rdacontent</subfield>
        </datafield>
        <datafield ind1=" " ind2=" " tag="337">
            <subfield code="b">n</subfield>
            <subfield code="2">rdamedia</subfield>
        </datafield>
        <datafield ind1=" " ind2=" " tag="338">
            <subfield code="8">01</subfield>
            <subfield code="b">nc</subfield>
            <subfield code="2">rdacarrier</subfield>
        </datafield>
    </record>
    """
    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)
    assert data.get('contentMediaCarrier') == [{
            "contentType": ["rdaco:1020"],
            "mediaType": "rdamt:1007",
            "carrierType": "rdact:1049"
        }, {
            "contentType": ["rdaco:1019"],
            "mediaType": "rdamt:1007"
        }]


def test_marc21_to_original_language():
    """Test dojson original_language (L31)."""

    marc21xml = """
    <record>
      <leader>00501nam a2200133 a 4500</leader>
      <controlfield tag=
        "008">071114s2007    fr ||| |  ||||00|  |fre d</controlfield>
      <datafield tag="035" ind1=" " ind2=" ">
        <subfield code="a">R004578243</subfield>
      </datafield>
      <datafield tag="041" ind1="1" ind2=" ">
        <subfield code="a">fre</subfield>
        <subfield code="h">eng</subfield>
      </datafield>
    </record>
    """
    marc21json = create_record(marc21xml)
    data = marc21.do(marc21json)
    assert data.get('originalLanguage') == ['eng']
