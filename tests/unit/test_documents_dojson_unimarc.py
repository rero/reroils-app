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

from dojson.contrib.marc21.utils import create_record

from rero_ils.modules.documents.dojson.contrib.unimarctojson import unimarc


# type: leader
def test_unimarc_to_type():
    """
    Test dojson unimarc_to_type.

    Books: LDR/6-7: am
    Journals: LDR/6-7: as
    Articles: LDR/6-7: aa + add field 773 (journal title)
    Scores: LDR/6: c|d
    Videos: LDR/6: g + 007/0: m|v
    Sounds: LDR/6: i|j
    E-books (imported from Cantook)
    """

    unimarcxml = """
    <record>
        <leader>00501nam a2200133 a 4500</leader>
    </record>
    """
    unimarcjson = create_record(unimarcxml)
    data = unimarc.do(unimarcjson)
    assert data.get('type') == [{
        "main_type": "docmaintype_book",
        "subtype": "docsubtype_other_book"
    }]

    unimarcxml = """
    <record>
        <leader>00501nas a2200133 a 4500</leader>
    </record>
    """
    unimarcjson = create_record(unimarcxml)
    data = unimarc.do(unimarcjson)
    assert data.get('type') == [{
        "main_type": "docmaintype_serial"
    }]

    unimarcxml = """
    <record>
        <leader>00501naa a2200133 a 4500</leader>
    </record>
    """
    unimarcjson = create_record(unimarcxml)
    data = unimarc.do(unimarcjson)
    assert data.get('type') == [{
        "main_type": "docmaintype_article",
    }]

    unimarcxml = """
    <record>
        <leader>00501nca a2200133 a 4500</leader>
    </record>
    """
    unimarcjson = create_record(unimarcxml)
    data = unimarc.do(unimarcjson)
    assert data.get('type') == [{
        "main_type": "docmaintype_score",
        "subtype": "docsubtype_printed_score"
    }]

    unimarcxml = """
    <record>
        <leader>00501nda a2200133 a 4500</leader>
    </record>
    """
    unimarcjson = create_record(unimarcxml)
    data = unimarc.do(unimarcjson)
    assert data.get('type') == [{
        "main_type": "docmaintype_score",
        "subtype": "docsubtype_printed_score"
    }]

    unimarcxml = """
    <record>
        <leader>00501nia a2200133 a 4500</leader>
    </record>
    """
    unimarcjson = create_record(unimarcxml)
    data = unimarc.do(unimarcjson)
    assert data.get('type') == [{
        "main_type": "docmaintype_audio",
        "subtype": "docsubtype_music"
    }]

    unimarcxml = """
    <record>
        <leader>00501nja a2200133 a 4500</leader>
    </record>
    """
    unimarcjson = create_record(unimarcxml)
    data = unimarc.do(unimarcjson)
    assert data.get('type') == [{
        "main_type": "docmaintype_audio",
        "subtype": "docsubtype_music"
    }]

    unimarcxml = """
    <record>
        <leader>00501nga a2200133 a 4500</leader>
    </record>
    """
    unimarcjson = create_record(unimarcxml)
    data = unimarc.do(unimarcjson)
    assert data.get('type') == [{
        "main_type": "docmaintype_movie_series",
        "subtype": "docsubtype_movie"
    }]


def test_marc21_to_mode_of_issuance():
    """
    Test dojson marc21_to_mode_issuance.
    """

    #  rdami:1001 (single unit)
    #    materialUnit > LDR07=m
    #    article > LDR07=a
    #    privateFile > LDR07=c
    #    privateSubfile > no equivalence
    unimarcxml = """
    <record>
        <leader>00501naa a2200133 a 4500</leader>
    </record>
    """
    unimarcjson = create_record(unimarcxml)
    data = unimarc.do(unimarcjson)
    assert data.get('issuance') == {
        'main_type': 'rdami:1001',
        'subtype': 'article'
    }

    unimarcxml = """
    <record>
        <leader>00501nam a2200133 a 4500</leader>
    </record>
    """
    unimarcjson = create_record(unimarcxml)
    data = unimarc.do(unimarcjson)
    assert data.get('issuance') == {
        'main_type': 'rdami:1001',
        'subtype': 'materialUnit'
    }

    unimarcxml = """
    <record>
        <leader>00501nac a2200133 a 4500</leader>
    </record>
    """
    unimarcjson = create_record(unimarcxml)
    data = unimarc.do(unimarcjson)
    assert data.get('issuance') == {
        'main_type': 'rdami:1001',
        'subtype': 'privateFile'
    }

    #  rdami:1003 (serial)
    #    serialInSerial > no equivalence
    #    monographicSeries > LDR07=s AND 110$a/0=b
    #    periodical > LDR07=s AND 110$a/0=a
    unimarcxml = """
    <record>
        <leader>00501nas a2200133 a 4500</leader>
        <datafield tag="110" ind1=" " ind2=" ">
          <subfield code="a">a</subfield>
        </datafield>
    </record>
    """
    unimarcjson = create_record(unimarcxml)
    data = unimarc.do(unimarcjson)
    assert data.get('issuance') == {
        'main_type': 'rdami:1003',
        'subtype': 'periodical'
    }

    unimarcxml = """
    <record>
        <leader>00501nas a2200133 a 4500</leader>
        <datafield tag="110" ind1=" " ind2=" ">
          <subfield code="a">b</subfield>
        </datafield>
    </record>
    """
    unimarcjson = create_record(unimarcxml)
    data = unimarc.do(unimarcjson)
    assert data.get('issuance') == {
        'main_type': 'rdami:1003',
        'subtype': 'monographicSeries'
    }

    # rdami:1004 (integrating resource)
    #    updatingWebsite > LDR07=i AND 110$a/0=f|g|h
    #    updatingLoose-leaf > LDR07=i AND 110$a/0=e
    unimarcxml = """
    <record>
        <leader>00501nai a2200133 a 4500</leader>
        <datafield tag="110" ind1=" " ind2=" ">
          <subfield code="a">f</subfield>
        </datafield>
    </record>
    """
    unimarcjson = create_record(unimarcxml)
    data = unimarc.do(unimarcjson)
    assert data.get('issuance') == {
        'main_type': 'rdami:1004',
        'subtype': 'updatingWebsite'
    }

    unimarcxml = """
    <record>
        <leader>00501nai a2200133 a 4500</leader>
        <datafield tag="110" ind1=" " ind2=" ">
          <subfield code="a">g</subfield>
        </datafield>
    </record>
    """
    unimarcjson = create_record(unimarcxml)
    data = unimarc.do(unimarcjson)
    assert data.get('issuance') == {
        'main_type': 'rdami:1004',
        'subtype': 'updatingWebsite'
    }

    unimarcxml = """
    <record>
        <leader>00501nai a2200133 a 4500</leader>
        <datafield tag="110" ind1=" " ind2=" ">
          <subfield code="a">h</subfield>
        </datafield>
    </record>
    """
    unimarcjson = create_record(unimarcxml)
    data = unimarc.do(unimarcjson)
    assert data.get('issuance') == {
        'main_type': 'rdami:1004',
        'subtype': 'updatingWebsite'
    }

    unimarcxml = """
    <record>
        <leader>00501nai a2200133 a 4500</leader>
        <datafield tag="110" ind1=" " ind2=" ">
          <subfield code="a">e</subfield>
        </datafield>
    </record>
    """
    unimarcjson = create_record(unimarcxml)
    data = unimarc.do(unimarcjson)
    assert data.get('issuance') == {
        'main_type': 'rdami:1004',
        'subtype': 'updatingLoose-leaf'
    }


def test_unimarc_to_title():
    """Test dojson unimarc to title."""

    # field 200 to bf:Title
    # field 200 with $a, $e, $f, $h, $i, $i
    unimarcxml = """
    <record>
      <datafield tag="200" ind1="1" ind2="0">
        <subfield code="a">main title</subfield>
        <subfield code="e">subtitle</subfield>
        <subfield code="f">responsibility</subfield>
        <subfield code="h">Part Number</subfield>
        <subfield code="i">Part Name</subfield>
        <subfield code="i">Part Name 2</subfield>
      </datafield>
    </record>
    """
    unimarcjson = create_record(unimarcxml)
    data = unimarc.do(unimarcjson)
    assert data.get('title') == [
        {
            'mainTitle': [
                {
                    'value': 'main title'
                }
            ],
            'subtitle': [
                {
                    'value': 'subtitle'
                }
            ],
            'part': [
                {
                    'partNumber': [
                        {
                            'value': 'Part Number'
                        }
                    ],
                    'partName': [
                        {
                            'value': 'Part Name'
                        }
                    ]
                },
                {
                    'partName': [
                        {
                            'value': 'Part Name 2'
                        }
                    ]
                }

            ],
            'type': 'bf:Title'
        }
    ]
    assert data.get('responsibilityStatement') == [
        [
            {
                'value': 'responsibility'
            }
        ]
    ]

    # field 200 to bf:Title
    # field 200 with $a, $f
    unimarcxml = """
    <record>
      <datafield tag="200" ind1="1" ind2="0">
        <subfield code="a">main title</subfield>
        <subfield code="f">responsibility</subfield>
      </datafield>
    </record>
    """
    unimarcjson = create_record(unimarcxml)
    data = unimarc.do(unimarcjson)
    assert data.get('title') == [
        {
            'mainTitle': [
                {
                    'value': 'main title'
                }
            ],
            'type': 'bf:Title'
        }
    ]
    assert data.get('responsibilityStatement') == [
        [
            {
                'value': 'responsibility'
            }
        ]
    ]

    # field 200 to bf:Title
    # field 200 with $a
    unimarcxml = """
    <record>
      <datafield tag="200" ind1="1" ind2="0">
        <subfield code="a">main title</subfield>
      </datafield>
    </record>
    """
    unimarcjson = create_record(unimarcxml)
    data = unimarc.do(unimarcjson)
    assert data.get('title') == [
        {
            'mainTitle': [
                {
                    'value': 'main title'
                }
            ],
            'type': 'bf:Title'
        }
    ]
    assert data.get('responsibilityStatement') is None


def test_unimarc_to_title_with_alt_graphic_with_bad_lang():
    """Test dojson unimarc to title with alternate graphic."""

    unimarcxml = """
    <record>
      <datafield tag="101" ind1=" " ind2=" ">
        <subfield code="a">fre</subfield>
        <subfield code="c">fre</subfield>
        <subfield code="g">rus</subfield>
      </datafield>
      <datafield tag="200" ind1="1" ind2="0">
        <subfield code="6">a01</subfield>
        <subfield code="7">ba</subfield>
        <subfield code="a">Aẖbār min Marrākuš</subfield>
        <subfield code="f">al-Ṭāhir ibn Ǧullūn</subfield>
      </datafield>
      <datafield tag="200" ind1="1" ind2="0">
        <subfield code="6">a01</subfield>
        <subfield code="7">fa</subfield>
        <subfield code="a">أخبار من مراكش</subfield>
        <subfield code="f">لمبرون</subfield>
      </datafield>
    </record>
    """

    unimarcjson = create_record(unimarcxml)
    data = unimarc.do(unimarcjson)
    assert data.get('title') == [
        {
            'mainTitle': [
                {
                    'value': 'Aẖbār min Marrākuš'
                },
                {
                     'value': 'أخبار من مراكش',
                     'language': 'und-arab'
                }

            ],
            'type': 'bf:Title'
        }
    ]

    assert data.get('responsibilityStatement') == [
        [
            {
                'value': 'al-Ṭāhir ibn Ǧullūn'
            },
            {
                'value': 'لمبرون',
                'language': 'und-arab'
            }
        ]
    ]


def test_unimarc_to_title_with_alt_graphic():
    """Test dojson unimarc to title with alternate graphic."""

    unimarcxml = """
    <record>
      <datafield tag="101" ind1=" " ind2=" ">
        <subfield code="a">fre</subfield>
        <subfield code="c">fre</subfield>
        <subfield code="g">ara</subfield>
      </datafield>
      <datafield tag="200" ind1="1" ind2="0">
        <subfield code="6">a01</subfield>
        <subfield code="7">ba</subfield>
        <subfield code="a">Aẖbār min Marrākuš</subfield>
        <subfield code="f">al-Ṭāhir ibn Ǧullūn</subfield>
      </datafield>
      <datafield tag="200" ind1="1" ind2="0">
        <subfield code="6">a01</subfield>
        <subfield code="7">fa</subfield>
        <subfield code="a">أخبار من مراكش</subfield>
        <subfield code="f">لمبرون</subfield>
      </datafield>
    </record>
    """

    unimarcjson = create_record(unimarcxml)
    data = unimarc.do(unimarcjson)
    assert data.get('title') == [
        {
            'mainTitle': [
                {
                    'value': 'Aẖbār min Marrākuš'
                },
                {
                     'value': 'أخبار من مراكش',
                     'language': 'ara-arab'
                }
            ],
            'type': 'bf:Title'
        }
    ]

    assert data.get('responsibilityStatement') == [
        [
            {
                'value': 'al-Ṭāhir ibn Ǧullūn'
            },
            {
                'value': 'لمبرون',
                'language': 'ara-arab'
            }
        ]
    ]


def test_unimarctotitle_with_parallel_title():
    """Test dojson unimarc to title and parallel title."""

    # field 200 to bf:Title
    # field 200 with $a, $e, $f, $g $h, $i
    # field 510 to bf:ParallelTitle
    # field 510 with $a, $e, $h, $i

    unimarcxml = """
    <record>
      <datafield tag="200" ind1="1" ind2="0">
        <subfield code="a">main title</subfield>
        <subfield code="e">subtitle</subfield>
        <subfield code="f">responsibility f</subfield>
        <subfield code="g">responsibility g</subfield>
        <subfield code="h">Part Number</subfield>
        <subfield code="i">Part Name</subfield>
      </datafield>
        <datafield tag="510" ind1="1" ind2="0">
        <subfield code="a">main parallel title</subfield>
        <subfield code="e">parallel subtitle</subfield>
        <subfield code="h">Part Number parallel</subfield>
        <subfield code="i">Part Name parallel</subfield>
      </datafield>
    </record>
    """
    unimarcjson = create_record(unimarcxml)
    data = unimarc.do(unimarcjson)
    assert data.get('title') == [
        {
            'mainTitle': [
                {
                    'value': 'main title'
                }
            ],
            'subtitle': [
                {
                    'value': 'subtitle'
                }
            ],
            'part': [
                {
                    'partNumber': [
                        {
                            'value': 'Part Number'
                        }
                    ],
                    'partName': [
                        {
                            'value': 'Part Name'
                        }
                    ]
                }
            ],
            'type': 'bf:Title'
        },
        {
            'mainTitle': [
                {
                    'value': 'main parallel title'
                }
            ],
            'subtitle': [
                {
                    'value': 'parallel subtitle'
                }
            ],
            'part': [
                {
                    'partNumber': [
                        {
                            'value': 'Part Number parallel'
                        }
                    ],
                    'partName': [
                        {
                            'value': 'Part Name parallel'
                        }
                    ]
                }
            ],
            'type': 'bf:ParallelTitle'
        }
    ]
    assert data.get('responsibilityStatement') == [
        [
            {
                'value': 'responsibility f'
            }
        ],
        [
            {
                'value': 'responsibility g'
            }
        ]
    ]


def test_unimarctotitle_with_parallel_and_variant_title():
    """Test dojson unimarc to title, parallel and variant title."""

    # field 200 to bf:Title
    # field 200 with $a, $e, $f, $g $h, $i
    # field 510 to bf:ParallelTitle
    # field 510 with $a, $e, $h, $i
    # field 512 to bf:VariantlTitle
    # field 512 with $a, $e, $h, $i
    # field 514 to bf:VariantlTitle
    # field 514 with $a, $e, $h, $

    unimarcxml = """
    <record>
      <datafield tag="200" ind1="1" ind2="0">
        <subfield code="a">main title</subfield>
        <subfield code="e">subtitle</subfield>
        <subfield code="f">responsibility f</subfield>
        <subfield code="g">responsibility g</subfield>
        <subfield code="h">Part Number</subfield>
        <subfield code="i">Part Name</subfield>
      </datafield>
      <datafield tag="510" ind1="1" ind2="0">
        <subfield code="a">main parallel title</subfield>
        <subfield code="e">parallel subtitle</subfield>
        <subfield code="h">Part Number parallel</subfield>
        <subfield code="i">Part Name parallel</subfield>
      </datafield>
      <datafield>
        <datafield tag="512" ind1="1" ind2="0">
        <subfield code="a">main variant title 512</subfield>
        <subfield code="e">variant subtitle 512</subfield>
        <subfield code="h">Part Number variant 512</subfield>
        <subfield code="i">Part Name variant 512</subfield>
      </datafield>
      <datafield>
        <datafield tag="514" ind1="1" ind2="0">
        <subfield code="a">main variant title 514</subfield>
        <subfield code="e">variant subtitle 514</subfield>
        <subfield code="h">Part Number variant 514</subfield>
        <subfield code="i">Part Name variant 514</subfield>
      </datafield>
    </record>
    """
    unimarcjson = create_record(unimarcxml)
    data = unimarc.do(unimarcjson)
    assert data.get('title') == [
        {
            'mainTitle': [
                {
                    'value': 'main title'
                }
            ],
            'subtitle': [
                {
                    'value': 'subtitle'
                }
            ],
            'part': [
                {
                    'partNumber': [
                        {
                            'value': 'Part Number'
                        }
                    ],
                    'partName': [
                        {
                            'value': 'Part Name'
                        }
                    ]
                }
            ],
            'type': 'bf:Title'
        },
        {
            'mainTitle': [
                {
                    'value': 'main parallel title'
                }
            ],
            'subtitle': [
                {
                    'value': 'parallel subtitle'
                }
            ],
            'part': [
                {
                    'partNumber': [
                        {
                            'value': 'Part Number parallel'
                        }
                    ],
                    'partName': [
                        {
                            'value': 'Part Name parallel'
                        }
                    ]
                }
            ],
            'type': 'bf:ParallelTitle'
        },
        {
            'mainTitle': [
                {
                    'value': 'main variant title 512'
                }
            ],
            'subtitle': [
                {
                    'value': 'variant subtitle 512'
                }
            ],
            'part': [
                {
                    'partNumber': [
                        {
                            'value': 'Part Number variant 512'
                        }
                    ],
                    'partName': [
                        {
                            'value': 'Part Name variant 512'
                        }
                    ]
                }
            ],
            'type': 'bf:VariantTitle'
        },
        {
            'mainTitle': [
                {
                    'value': 'main variant title 514'
                }
            ],
            'subtitle': [
                {
                    'value': 'variant subtitle 514'
                }
            ],
            'part': [
                {
                    'partNumber': [
                        {
                            'value': 'Part Number variant 514'
                        }
                    ],
                    'partName': [
                        {
                            'value': 'Part Name variant 514'
                        }
                    ]
                }
            ],
            'type': 'bf:VariantTitle'
        }
    ]
    assert data.get('responsibilityStatement') == [
        [
            {
                'value': 'responsibility f'
            }
        ],
        [
            {
                'value': 'responsibility g'
            }
        ]
    ]


# titleProper: [500$a repetitive]
def test_unimarctotitlesProper():
    """Test dojson unimarc_titlesProper."""

    unimarcxml = """
    <record>
      <datafield tag="500" ind1="1" ind2="0">
        <subfield code="a">proper title</subfield>
      </datafield>
    </record>
    """
    unimarcjson = create_record(unimarcxml)
    data = unimarc.do(unimarcjson)
    assert data.get('titlesProper') == ['proper title']

    unimarcxml = """
    <record>
      <datafield tag="500" ind1=" " ind2=" ">
        <subfield code="a">proper title</subfield>
      </datafield>
      <datafield tag="500" ind1=" " ind2=" ">
         <subfield code="a">other proper title</subfield>
       </datafield>
    </record>
    """
    unimarcjson = create_record(unimarcxml)
    data = unimarc.do(unimarcjson)
    assert data.get('titlesProper') == ['proper title', 'other proper title']


# languages: 101 [$a]
def test_unimarc_languages():
    """Test dojson unimarc_languages."""

    unimarcxml = """
    <record>
      <datafield tag="101" ind1=" " ind2=" ">
        <subfield code="a">eng</subfield>
      </datafield>
    </record>
    """
    unimarcjson = create_record(unimarcxml)
    data = unimarc.do(unimarcjson)
    assert data.get('language') == [{'value': 'eng', 'type': 'bf:Language'}]

    unimarcxml = """
    <record>
      <datafield tag="101" ind1=" " ind2=" ">
        <subfield code="a">eng</subfield>
        <subfield code="a">fre</subfield>
        <subfield code="c">ita</subfield>
      </datafield>
    </record>
    """
    unimarcjson = create_record(unimarcxml)
    data = unimarc.do(unimarcjson)
    assert data.get('language') == [
        {'value': 'eng', 'type': 'bf:Language'},
        {'value': 'fre', 'type': 'bf:Language'}
    ]
    assert data.get('translatedFrom') == ['ita']

    unimarcxml = """
    <record>
      <datafield tag="101" ind1=" " ind2=" ">
        <subfield code="a">eng</subfield>
        <subfield code="a">???</subfield>
        <subfield code="c">ita</subfield>
      </datafield>
    </record>
    """
    unimarcjson = create_record(unimarcxml)
    data = unimarc.do(unimarcjson)
    assert data.get('language') == [
        {'value': 'eng', 'type': 'bf:Language'},
    ]
    assert data.get('translatedFrom') == ['ita']


def test_unimarc_contribution():
    """Test dojson unimarctocontribution."""

    unimarcxml = """
    <record>
      <datafield tag="700" ind1=" " ind2=" ">
        <subfield code="a">Jean-Paul</subfield>
        <subfield code="d">II</subfield>
        <subfield code="c">Pape</subfield>
        <subfield code="f">1954 -</subfield>
         <subfield code="4">aut</subfield>
      </datafield>
      <datafield tag="701" ind1=" " ind2=" ">
        <subfield code="a">Dumont</subfield>
        <subfield code="b">Jean</subfield>
        <subfield code="c">Historien</subfield>
        <subfield code="f">1921 - 2014</subfield>
         <subfield code="4">aut</subfield>
      </datafield>
      <datafield tag="702" ind1=" " ind2=" ">
        <subfield code="a">Dicker</subfield>
        <subfield code="b">J.</subfield>
        <subfield code="f">1921 -</subfield>
      </datafield>
      <datafield tag="710" ind1=" " ind2=" ">
        <subfield code="a">RERO</subfield>
         <subfield code="4">edt</subfield>
      </datafield>
      <datafield tag="711" ind1=" " ind2=" ">
        <subfield code="a">LOC</subfield>
        <subfield code="d">1</subfield>
        <subfield code="e">London</subfield>
        <subfield code="f">2020-02-02</subfield>
      </datafield>
      <datafield tag="712" ind1="1" ind2=" ">
        <subfield code="a">BNF</subfield>
      </datafield>
    </record>
    """
    unimarcjson = create_record(unimarcxml)
    data = unimarc.do(unimarcjson)
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
            'role': ['aut']
        },
        {
            'agent': {
                'type': 'bf:Person',
                'preferred_name': 'Dicker, J.',
                'date_of_birth': '1921'
            },
            'role': ['aut']
        },
        {
            'agent': {
                'type': 'bf:Organisation',
                'preferred_name': 'RERO',
                'conference': False
            },
            'role': ['aut']
        },
        {
            'agent': {
                'type': 'bf:Organisation',
                'preferred_name': 'LOC',
                'conference': False,
                'numbering': '1',
                'place': 'London',
                'conference_date': '2020-02-02'
            },
            'role': ['aut']
        },
        {
            'agent': {
                'type': 'bf:Organisation',
                'preferred_name': 'BNF',
                'conference': True
            },
            'role': ['aut']
        }
    ]


def test_unimarc_edition():
    """Test dojson edition statement.
    - 1 edition designation and 1 responsibility from field 205
    """
    unimarcxml = """
    <record>
      <datafield tag="205" ind1=" " ind2=" ">
        <subfield code="a">2e ed.</subfield>
        <subfield code="f">avec un avant-propos par Jean Faret</subfield>
      </datafield>
    </record>
    """
    unimarcjson = create_record(unimarcxml)
    data = unimarc.do(unimarcjson)
    assert data.get('editionStatement') == [
      {
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
      }
    ]


def test_unimarc_publishers_provision_activity():
    """Test dojson publishers publicationDate."""

    unimarcxml = """
    <record>
      <datafield tag="100" ind1=" " ind2=" ">
        <subfield code="a">xxxxxxxxx2015????xxxxxxxxx</subfield>
      </datafield>
      <datafield tag="210" ind1=" " ind2=" ">
        <subfield code="a">Lausanne</subfield>
        <subfield code="c">Payot</subfield>
        <subfield code="d">2015</subfield>
      </datafield>
    </record>
    """
    unimarcjson = create_record(unimarcxml)
    data = unimarc.do(unimarcjson)
    assert data.get('provisionActivity') == [{
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
                    {'value': '2015'}
                ],
                'type': 'Date'
            }
        ],
        'startDate': 2015,
    }]

    unimarcxml = """
    <record>
      <datafield tag="100" ind1=" " ind2=" ">
        <subfield code="a">xxxxxxxxx2015????xxxxxxxxx</subfield>
      </datafield>
      <datafield tag="210" ind1=" " ind2=" ">
        <subfield code="a">Lausanne</subfield>
        <subfield code="c">Payot</subfield>
        <subfield code="d">2015</subfield>
      </datafield>
      <datafield tag="210" ind1=" " ind2=" ">
        <subfield code="e">Lausanne</subfield>
      </datafield>
    </record>
    """
    unimarcjson = create_record(unimarcxml)
    data = unimarc.do(unimarcjson)
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
                        {'value': '2015'}
                    ],
                    'type': 'Date'
                }
            ],
            'startDate': 2015,
        },
        {
            'statement': [
                {
                    'label': [
                        {'value': 'Lausanne'}
                    ],
                    'type': 'bf:Place'
                }
            ],
            'type': 'bf:Manufacture'
        }
    ]

    unimarcxml = """
    <record>
      <datafield tag="102" ind1=" " ind2=" ">
        <subfield code="a">FR</subfield>
      </datafield>
      <datafield tag="210" ind1=" " ind2=" ">
        <subfield code="a">[Paris] :</subfield>
        <subfield code="c">Desclée de Brouwer [puis] </subfield>
        <subfield code="c">Etudes augustiniennes,</subfield>
        <subfield code="d">[1969-1999]</subfield>
      </datafield>
    </record>
    """
    unimarcjson = create_record(unimarcxml)
    data = unimarc.do(unimarcjson)
    assert data.get('provisionActivity') == [{
        'type': 'bf:Publication',
        'place': [
            {
                'country': 'fr',
                'type': 'bf:Place'
            },
        ],
        'statement': [
            {
                'label': [
                    {'value': '[Paris]'}
                ],
                'type': 'bf:Place'
            },
            {
                'label': [
                    {'value': 'Desclée de Brouwer [puis]'}
                ],
                'type': 'bf:Agent'
            },
            {
                'label': [
                    {'value': 'Etudes augustiniennes'}
                ],
                'type': 'bf:Agent'
            },
            {
                'label': [
                    {'value': '[1969-1999]'}
                ],
                'type': 'Date'
            }
        ]
    }]

    unimarcxml = """
    <record>
      <datafield tag="214" ind1=" " ind2="0">
        <subfield code="a">Paris</subfield>
        <subfield code="c">Champion</subfield>
        <subfield code="a">Genève</subfield>
        <subfield code="c">Droz</subfield>
        <subfield code="d">1912-1955</subfield>
      </datafield>
    </record>
    """
    unimarcjson = create_record(unimarcxml)
    data = unimarc.do(unimarcjson)
    assert data.get('provisionActivity') == [{
        'type': 'bf:Publication',
        'statement': [
            {
                'label': [
                    {'value': 'Paris'}
                ],
                'type': 'bf:Place'
            },
            {
                'label': [
                    {'value': 'Champion'}
                ],
                'type': 'bf:Agent'
            },
            {
                'label': [
                    {'value': 'Genève'}
                ],
                'type': 'bf:Place'
            },
            {
                'label': [
                    {'value': 'Droz'}
                ],
                'type': 'bf:Agent'
            },
            {
                'label': [
                    {'value': '1912-1955'}
                ],
                'type': 'Date'
            }
        ]
    }]

    unimarcxml = """
    <record>
      <datafield tag="214" ind1=" " ind2="1">
        <subfield code="a">Lausanne</subfield>
      </datafield>
    </record>
    """
    unimarcjson = create_record(unimarcxml)
    data = unimarc.do(unimarcjson)
    assert data.get('provisionActivity') == [{
        'type': 'bf:Production',
        'statement': [
            {
                'label': [
                    {'value': 'Lausanne'}
                ],
                'type': 'bf:Place'
            }
        ],
    }]

    unimarcxml = """
    <record>
      <datafield tag="214" ind1=" " ind2="2">
        <subfield code="a">Lausanne</subfield>
      </datafield>
    </record>
    """
    unimarcjson = create_record(unimarcxml)
    data = unimarc.do(unimarcjson)
    assert data.get('provisionActivity') == [{
        'type': 'bf:Distribution',
        'statement': [
            {
                'label': [
                    {'value': 'Lausanne'}
                ],
                'type': 'bf:Place'
            }
        ],
    }]

    unimarcxml = """
    <record>
      <datafield tag="214" ind1=" " ind2="3">
        <subfield code="a">Lausanne</subfield>
      </datafield>
    </record>
    """
    unimarcjson = create_record(unimarcxml)
    data = unimarc.do(unimarcjson)
    assert data.get('provisionActivity') == [{
        'type': 'bf:Manufacture',
        'statement': [
            {
                'label': [
                    {'value': 'Lausanne'}
                ],
                'type': 'bf:Place'
            }
        ],
    }]


def test_unimarc_copyright_date():
    """Test copyright date."""
    unimarcxml = """
    <record>
      <datafield tag="214" ind1=" " ind2="4">
        <subfield code="d">1919</subfield>
      </datafield>
    </record>
    """
    unimarcjson = create_record(unimarcxml)
    data = unimarc.do(unimarcjson)
    assert data.get('copyrightDate') == ['© 1919']

    unimarcxml = """
    <record>
      <datafield tag="214" ind1=" " ind2="4">
        <subfield code="d">P 1919</subfield>
      </datafield>
    </record>
    """
    unimarcjson = create_record(unimarcxml)
    data = unimarc.do(unimarcjson)
    assert data.get('copyrightDate') == ['℗ 1919']


def test_unimarc_description():
    """Test dojson physical description.

    215 [$a repetitive (the first one if many)]: extent, duration:
    215 [$c non repetitive]: colorContent, productionMethod,
        illustrativeContent, note of type otherPhysicalDetails
    215 [$d repetitive]: dimensions, book_formats
    215 [$e repetitive]: note of type accompanyingMaterial
    """
    unimarcxml = """
    <record>
      <datafield tag="215" ind1=" " ind2=" ">
        <subfield code="a">116 p.</subfield>
        <subfield code="c">ill.</subfield>
        <subfield code="d">22 cm</subfield>
        <subfield code="e">1 volume (200 pages)</subfield>
      </datafield>
    </record>
    """
    unimarcjson = create_record(unimarcxml)
    data = unimarc.do(unimarcjson)
    assert data.get('extent') == '116 p.'
    assert data.get('illustrativeContent') == ['illustrations']
    assert data.get('dimensions') == ['22 cm']
    assert data.get('note') == [{
            'noteType': 'otherPhysicalDetails',
            'label': 'ill.'
        }, {
            'noteType': 'accompanyingMaterial',
            'label': '1 volume (200 pages)'
        }]

    unimarcxml = """
    <record>
      <datafield tag="215" ind1=" " ind2=" ">
        <subfield code="a">116 p.</subfield>
        <subfield code="c">ill.</subfield>
        <subfield code="d">22 cm</subfield>
        <subfield code="e">1 volume (200 pages)</subfield>
        <subfield code="e">une brochure (12 pages)</subfield>
        <subfield code="e">une disquette</subfield>
      </datafield>
    </record>
    """
    unimarcjson = create_record(unimarcxml)
    data = unimarc.do(unimarcjson)
    assert data.get('extent') == '116 p.'
    assert data.get('illustrativeContent') == ['illustrations']
    assert data.get('dimensions') == ['22 cm']
    assert data.get('note') == [{
            'noteType': 'otherPhysicalDetails',
            'label': 'ill.'
        }, {
            'noteType': 'accompanyingMaterial',
            'label': '1 volume (200 pages)'
        }, {
            'noteType': 'accompanyingMaterial',
            'label': 'une brochure (12 pages)'
        }, {
            'noteType': 'accompanyingMaterial',
            'label': 'une disquette'
        }]

    unimarcxml = """
    <record>
      <datafield tag="215" ind1=" " ind2=" ">
        <subfield code="a">116 p.</subfield>
        <subfield code="c">ill.</subfield>
        <subfield code="d">22 cm</subfield>
        <subfield code="d">12 x 15</subfield>
      </datafield>
      <datafield tag="215" ind1=" " ind2=" ">
        <subfield code="a">200 p.</subfield>
        <subfield code="c">ill.</subfield>
        <subfield code="d">19 cm</subfield>
      </datafield>
    </record>
    """
    unimarcjson = create_record(unimarcxml)
    data = unimarc.do(unimarcjson)
    assert data.get('illustrativeContent') == ['illustrations']
    assert data.get('dimensions') == ['12 x 15', '19 cm', '22 cm']
    assert data.get('note') == [{
            'noteType': 'otherPhysicalDetails',
            'label': 'ill.'
        }]
    unimarcxml = """
    <record>
      <datafield tag="215" ind1=" " ind2=" ">
        <subfield code="a">232 p.</subfield>
        <subfield code="c">couv. ill. en coul.</subfield>
        <subfield code="d">24 cm</subfield>
      </datafield>
    </record>
    """
    unimarcjson = create_record(unimarcxml)
    data = unimarc.do(unimarcjson)
    assert data.get('dimensions') == ['24 cm']
    assert data.get('colorContent') == ['rdacc:1003']
    assert data.get('note') == [{
            'noteType': 'otherPhysicalDetails',
            'label': 'couv. ill. en coul.'
        }]


# seriesStatement: [225 repetitive]
def test_unimarc_series_statement():
    """Test dojson seriesStatement."""

    unimarcxml = """
    <record>
      <datafield tag="225" ind1=" " ind2=" ">
        <subfield code="a">Collection formation</subfield>
        <subfield code="e">Mucchielli</subfield>
        <subfield code="v">5</subfield>
        <subfield code="i">Développement personnel</subfield>
        <subfield code="v">6</subfield>
      </datafield>
      <datafield tag="225" ind1=" " ind2=" ">
        <subfield code="a">Collection Two</subfield>
        <subfield code="v">123</subfield>
      </datafield>
    </record>
    """
    unimarcjson = create_record(unimarcxml)
    data = unimarc.do(unimarcjson)
    assert data.get('seriesStatement') == [{
            'seriesTitle': [{'value': 'Collection formation: Mucchielli'}],
            'seriesEnumeration': [{'value': '5'}],
            'subseriesStatement': [{
                'subseriesTitle': [{'value': 'Développement personnel'}],
                'subseriesEnumeration': [{'value': '6'}]
                }]
            }, {
            'seriesTitle': [{'value': 'Collection Two'}],
            'seriesEnumeration': [{'value': '123'}],
        }
    ]


def test_unimarc_partOf_without_link(document):
    """Test dojson partOf when no linked record found."""

    unimarcxml = """
    <record>
      <datafield tag="410" ind1=" " ind2="0">
        <subfield code="t">Formation permanente en sciences humaines</subfield>
        <subfield code="x">0768-2026</subfield>
        <subfield code="v">41</subfield>
      </datafield>
    </record>
    """
    unimarcjson = create_record(unimarcxml)
    data = unimarc.do(unimarcjson)
    assert data == {}

    unimarcxml = """
    <record>
      <datafield tag="463" ind1=" " ind2="|">
        <subfield code="t">Acupuncture & moxibustion</subfield>
        <subfield code="x">1633-3454</subfield>
        <subfield code="v">17</subfield>
      </datafield>
    </record>
    """
    unimarcjson = create_record(unimarcxml)
    data = unimarc.do(unimarcjson)
    assert data == {}


def test_unimarc_partOf_with_link(document_with_issn):
    """Test dojson partOf when linked record found."""

    unimarcxml = """
    <record>
      <datafield tag="410" ind1=" " ind2="0">
        <subfield code="t">Formation permanente en sciences humaines</subfield>
        <subfield code="x">0768-2026</subfield>
        <subfield code="v">41</subfield>
      </datafield>
    </record>
    """
    unimarcjson = create_record(unimarcxml)
    data = unimarc.do(unimarcjson)
    assert data['partOf'] == [{
            'document': {'$ref': 'https://ils.rero.ch/api/documents/doc5'},
            'numbering': '41'
        }
    ]


# abstract: [330$a repetitive]
def test_unimarc_summary():
    """Test dojson summary."""

    unimarcxml = """
    <record>
      <datafield tag="330" ind1=" " ind2=" ">
        <subfield code="a">This book is about</subfield>
      </datafield>
    </record>
    """
    unimarcjson = create_record(unimarcxml)
    data = unimarc.do(unimarcjson)
    assert data.get('summary') == [
        {'label': [{'value': 'This book is about'}]}]


# identifiers:isbn: 010$a
def test_unimarc_identifiers():
    """Test dojson identifiers."""

    unimarcxml = """
    <record>
      <controlfield
        tag="003">http://catalogue.bnf.fr/ark:/12148/cb350330441</controlfield>
      <datafield tag="073" ind1=" " ind2=" ">
        <subfield code="a">9782370550163</subfield>
      </datafield>
    </record>
    """
    unimarcjson = create_record(unimarcxml)
    data = unimarc.do(unimarcjson)
    assert data.get('identifiedBy') == [
      {
        "type": "bf:Local",
        "value": "ark:/12148/cb350330441",
        "source": "BNF"
      },
      {
        "type": "bf:Ean",
        "value": "9782370550163"
      }
    ]

    unimarcxml = """
    <record>
      <datafield tag="073" ind1=" " ind2=" ">
        <subfield code="a">978237055016x</subfield>
      </datafield>
    </record>
    """
    unimarcjson = create_record(unimarcxml)
    data = unimarc.do(unimarcjson)
    assert data.get('identifiedBy') == [
      {
        "type": "bf:Ean",
        "value": "978237055016x",
        "status": "invalid"
      }
    ]


# notes: [300$a repetitive]
def test_unimarc_notes():
    """Test dojson notes."""

    unimarcxml = """
    <record>
      <datafield tag="300" ind1=" " ind2=" ">
        <subfield code="a">note</subfield>
      </datafield>
    </record>
    """
    unimarcjson = create_record(unimarcxml)
    data = unimarc.do(unimarcjson)
    assert data.get('note') == [{
        'noteType': 'general',
        'label': 'note'
    }]

    unimarcxml = """
    <record>
      <datafield tag="300" ind1=" " ind2=" ">
        <subfield code="a">note 1</subfield>
      </datafield>
      <datafield tag="300" ind1=" " ind2=" ">
        <subfield code="a">note 2</subfield>
      </datafield>
    </record>
    """
    unimarcjson = create_record(unimarcxml)
    data = unimarc.do(unimarcjson)
    assert data.get('note') == [{
            'noteType': 'general',
            'label': 'note 1'
        }, {
            'noteType': 'general',
            'label': 'note 2'
        }
    ]


# subjects: 600..617 $a,$b,$c,$d,$f
# [duplicates could exist between several vocabularies,
# if possible deduplicate]
def test_unimarc_subjects():
    """Test dojson subjects."""

    unimarcxml = """
    <record>
      <datafield tag="600" ind1=" " ind2=" ">
        <subfield code="a">subjects 600</subfield>
      </datafield>
      <datafield tag="616" ind1=" " ind2=" ">
        <subfield code="a">Capet</subfield>
        <subfield code="b">Louis</subfield>
        <subfield code="c">Jr.</subfield>
        <subfield code="d">III</subfield>
        <subfield code="f">1700-1780</subfield>
      </datafield>
    </record>
    """
    unimarcjson = create_record(unimarcxml)
    data = unimarc.do(unimarcjson)
    assert data.get('subjects') == [
        {'term': 'subjects 600', 'type': 'bf:Topic'},
        {'term': 'Capet, Louis III, Jr., 1700-1780', 'type': 'bf:Topic'}
    ]


def test_unimarc_to_electronicLocator_from_856():
    """Test dojson electronicLocator from 856."""

    unimarcxml = """
    <record>
      <datafield tag="856" ind1="4" ind2=" ">
        <subfield
            code="u">http://gallica.bnf.fr/ark:/12148/btv1b550017355</subfield>
      </datafield>

    </record>
    """
    unimarcjson = create_record(unimarcxml)
    data = unimarc.do(unimarcjson)
    assert data.get('electronicLocator') == [{
        'url': 'http://gallica.bnf.fr/ark:/12148/btv1b550017355',
        'type': 'resource',
    }]
