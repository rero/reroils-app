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

"""DOJSON transformation for Doublin Core module tests."""

from __future__ import absolute_import, print_function

from flask_babelex import gettext as _

from rero_ils.modules.documents.dojson.contrib.jsontodc import dublincore


def test_title_to_dc():
    """Test title transformation to Dublin Core."""
    record = {
        'title': [{
            'type': 'bf:Title',
            'mainTitle': [{'value': 'Kunst der Farbe'}],
            'subtitle': [{'value': 'Studienausgabe'}]
        }],
        'responsibilityStatement': [
            [{'value': 'Johannes Itten'}],
            [{'value': "traduit de l'allemand par Valérie Bourgeois"}]
        ]
    }
    result = dublincore.do(record)
    assert result == {'titles': [
        'Kunst der Farbe : Studienausgabe / Johannes Itten / '
        "traduit de l'allemand par Valérie Bourgeois"
    ]}

    record = {
        'title': [{
            'type': 'bf:Title',
            'mainTitle': [{'value': 'Statistique'}],
            'subtitle': [{
                'value': 'exercices corrigés avec rappels de cours'}],
            'part': [{
                'partNumber': [{'value': 'T. 1'}],
                'partName': [{
                    'value': 'Licence ès sciences économiques, 1ère année, '
                    'étudiants de Grandes écoles'
                    }]
            }, {
                'partNumber': [{'value': 'Section 2'}],
                'partName': [{'value': 'Grandes écoles'}]
            }]
        }],
        'responsibilityStatement': [
            [{'value': 'Edmond Berrebi'}]
        ]
    }
    result = dublincore.do(record)
    assert result == {'titles': [
        'Statistique : exercices corrigés avec rappels de cours. Section '
        '2, Grandes écoles / Edmond Berrebi'
    ]}

    record = {
        'title': [{
            'mainTitle': [{'value': 'Suisse'}],
            'type': 'bf:Title'
        }, {
            'mainTitle': [{'value': 'Schweiz'}],
            'type': 'bf:ParallelTitle'
        }, {
            'mainTitle': [{'value': 'Svizzera'}],
            'subtitle': [{'value': 'Le guide Michelin 2020'}],
            'type': 'bf:ParallelTitle'
        }]
    }
    result = dublincore.do(record)
    assert result == {'titles': ['Suisse']}


# def test_contribution_to_dc():
#     """Test contribution to dublincore transformation."""
#     pass


def test_summary_note_dissertation_supplementarycontent_to_dc():
    """Test description transformation to Dublin Core."""
    record = {
        'summary': [
            {'label': [{
                'value': 'Fictions jeunesse: roman, jeux vid\u00e9o, '
                         'imagination'
            }]}
        ],
        'note': [{
            'noteType': 'general',
            'label': 'In : Edinburgh medical and surgical journal. - '
                     'Edinburgh. - No. 55(1818), 64 p.'
        }],
        'supplementaryContent': ['Bibliogr.: p. 52'],
        'dissertation': [{'label': 'Th. Sc. techn. Lausanne'}]
    }
    result = dublincore.do(record)
    assert result == {'descriptions': [
        'Fictions jeunesse: roman, jeux vidéo, imagination',
        'In : Edinburgh medical and surgical journal. - Edinburgh. - '
        'No. 55(1818), 64 p.',
        'Bibliogr.: p. 52',
        'Th. Sc. techn. Lausanne',
    ]}


def test_language_to_dc():
    """Test language transformation to Dublin Core."""
    record = {'language': [
        {
            'type': 'bf:Language',
            'value': 'ain'
        }
    ]}
    result = dublincore.do(record)
    assert result == {'languages': ['ain']}


def test_provision_activity_to_dc():
    """Test provisionActivity transformation to Dublin Core."""
    record = {'provisionActivity': [{
        'type': 'bf:Publication',
        'statement': [{
            'type': 'bf:Place',
            'label': [{'value': 'New York'}]
        }, {
            'type': 'bf:Agent',
            'label': [{'value': 'Listening Library'}]
        }, {
            'type': 'Date',
            'label': [{'value': '2006'}]
        }],
        'startDate': 2006,
        'place': [{
            'type': 'bf:Place',
            'country': 'xxu'
        }]
        }
    ]}
    result = dublincore.do(record)
    assert result == {
        'dates': ['2006'],
        'publishers': ['Listening Library']
    }
    record = {'provisionActivity': [{
        'type': 'bf:Publication',
        'statement': [{
            'label': [{'value': '1978'}],
            'type': 'Date'
        }],
        'startDate': 1978,
        'place': [{
            'country': 'xx',
            'type': 'bf:Place'
         }]
    }]}
    result = dublincore.do(record)
    assert result == {'dates': ['1978']}


def test_type_to_dc():
    """Test type transformation to Dublin Core."""
    record = {'type': [
        {
            'main_type': 'docmaintype_book',
            'subtype': 'docsubtype_other_book'
        }
    ]}
    result = dublincore.do(record)
    assert result == {'types': [
        f"{_('docmaintype_book')} / {_('docsubtype_other_book')}"
    ]}


def test_identified_by_to_dc():
    """Test identifiedBy transformation to Dublin Core."""
    record = {"identifiedBy": [
      {
        "value": "R003461120",
        "type": "bf:Local",
        "source": "RERO"
      }
    ]}
    result = dublincore.do(record)
    assert result == {'identifiers': ['bf:Local|R003461120(RERO)']}
    record = {"identifiedBy": [
        {
            "qualifier": "vol. 5",
            "value": "604907014223",
            "type": "bf:Upc"
        },
        {
            "value": "Arbiter 142",
            "type": "bf:AudioIssueNumber"
        },
        {
            "value": "R005918723",
            "type": "bf:Local",
            "source": "RERO"
        }
    ]}
    result = dublincore.do(record)
    assert result == {'identifiers': [
        'bf:Upc|604907014223',
        'bf:AudioIssueNumber|Arbiter 142',
        'bf:Local|R005918723(RERO)'
    ]}


# def test_relations():
#     """Test relations transformation."""
#     pass
