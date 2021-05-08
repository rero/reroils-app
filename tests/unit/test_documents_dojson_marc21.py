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

"""DOJSON transformation for RERO MARC21 module tests."""

from __future__ import absolute_import, print_function

from copy import deepcopy

import mock
from flask_babelex import gettext as _

from rero_ils.modules.documents.dojson.contrib.jsontomarc21 import to_marc21


def test_pid_to_marc21(app, marc21_record):
    """Test PID to MARC21 transformation."""
    record = {
        'pid': '12345678',
        'language': [{
            "type": "bf:Language",
            "value": "fre"
        }],
        'provisionActivity': [{
            '_text': [{
                    'language': 'default',
                    'value': 'Paris : Ed. Cornélius, 2007-'
            }],
            'place': [{
                    'country': 'fr',
                    'type': 'bf:Place'
            }],
            'startDate': 2007,
            'endDate': 2020,
            'statement': [{
                    'label': [{'value': 'Paris'}],
                    'type': 'bf:Place'
                }, {
                    'label': [{'value': 'Ed. Cornélius'}],
                    'type': 'bf:Agent'
                }, {
                    'label': [{'value': '2007-2020'}],
                    'type': 'Date'
            }],
            'type': 'bf:Publication'
        }]
    }
    result = to_marc21.do(record)
    record = deepcopy(marc21_record)
    record.update({
        '__order__': ('leader', '001', '008'),
        '001': '12345678',
        '008': '000000|20072020xx#|||||||||||||||||fre|c',
    })
    assert result == record


def test_title_to_marc21(app, marc21_record):
    """Test title to MARC21 transformation."""
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
    result = to_marc21.do(record)
    record = deepcopy(marc21_record)
    record.update({
        '__order__': ('leader', '008', '2450_'),
        '2450_': {
            '__order__': ('a', 'b', 'c'),
            'a': 'Kunst der Farbe',
            'b': 'Studienausgabe',
            'c': "Johannes Itten ; traduit de l'allemand par Valérie Bourgeois"
        }
    })
    assert result == record

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
    result = to_marc21.do(record)
    record = deepcopy(marc21_record)
    record.update({
        '__order__': ('leader', '008', '2450_'),
        '2450_': {
            '__order__': ('a', 'b', 'c', 'n', 'p', 'n', 'p'),
            'a': 'Statistique',
            'b': 'exercices corrigés avec rappels de cours',
            'c': 'Edmond Berrebi',
            'n': ('T. 1', 'Section 2'),
            'p': ('Licence ès sciences économiques, 1ère année, étudiants de '
                  'Grandes écoles',
                  'Grandes écoles')
        }
    })
    assert result == record

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
    result = to_marc21.do(record)
    record = deepcopy(marc21_record)
    record.update({
        '__order__': ('leader', '008', '2450_'),
        '2450_': {
            '__order__': ('a', 'b'),
            'a': 'Suisse',
            'b': 'Schweiz. Svizzera : Le guide Michelin 2020'
        }
    })
    assert result == record


def test_contribution_to_marc21(app, marc21_record,
                                mef_record_1, mef_record_2, mef_record_3):
    """Test contribution to MARC21 transformation."""
    record = {
        'contribution': [{
            'agent': {
                'date_of_birth': '1923',
                'date_of_death': '1999',
                'preferred_name': 'Fujimoto, Satoko',
                'type': 'bf:Person'
            },
            'role': ['ctb', 'aut']
        }, {
            'agent': {
                '$ref': 'https://mef.rero.ch/api/idref/mef_record_1',
                'type': 'bf:Person'
            },
            'role': ['trl']
        }, {
            'agent': {
                'conference': False,
                'preferred_name': 'Université de Genève',
                'type': 'bf:Organisation'
            },
            'role': ['ctb']
        }, {
            'agent': {
                '$ref': 'https://mef.rero.ch/api/gnd/mef_record_2',
                'type': 'bf:Organisation'
            },
            'role': ['aut']
        }, {
            'agent': {
                'conference': True,
                'conference_date': '1989',
                'numbering': '4',
                'place': 'Lausanne',
                'preferred_name': 'Congrès des animaux volants',
                'type': 'bf:Organisation'
            },
            'role': ['aut']
        }, {
            'agent': {
                '$ref': 'https://mef.rero.ch/api/idref/mef_record_3',
                'type': 'bf:Organisation'
            },
            'role': ['aut']
        }]
    }
    with mock.patch(
        'rero_ils.modules.contributions.api.Contribution.get_contribution',
        side_effect=[mef_record_1, mef_record_2, mef_record_3]
    ):
        result = to_marc21.do(record)

    record = deepcopy(marc21_record)
    record.update({
        '__order__': ('leader', '008', '7001_', '7001_', '710__', '710__',
                      '711__', '711__'),

        '7001_': ({
            '__order__': ('a', 'd', '4', '4'),
            'a': 'Fujimoto, Satoko',
            'd': '1923 - 1999',
            '4': ('ctb', 'aut')
        }, {
            '__order__': ('a', '4', '0', '0'),
            'a': 'Honnoré, Patrick',
            '4': 'trl',
            '0': ('(idref)072277742', '(rero)A009220673'),
        }),
        '710__': ({
            '__order__': ('a', '4'),
            'a': 'Université de Genève',
            '4': 'ctb'
        }, {
            '__order__': ('a', '4', '0', '0'),
            'a': 'Université de Genève',
            '4': 'aut',
            '0': ('(idref)02643136X', '(gnd)004058518'),
        }),
        '711__': ({
            '__order__': ('a', 'd', '4'),
            'a': 'Congrès des animaux volants',
            'd': '1989',
            '4': 'aut',
        }, {
            '__order__': ('a', '4', '0', '0', '0'),
            'a': 'Congrès ouvrier français',
            '4': 'aut',
            '0': ('(idref)03255608X', '(rero)A005462931', '(gnd)050343211')
        })
    })
    assert result == record


def test_type_to_marc21(app, marc21_record):
    """Test type to MARC21 transformation."""
    record = {
        'type': [{
            'main_type': 'docmaintype_comic',
            'subtype': 'docsubtype_manga'
        }, {
            'main_type': 'docmaintype_map',
            'subtype': 'docsubtype_atlas'
        }]
    }
    result = to_marc21.do(record)
    record = deepcopy(marc21_record)
    record.update({
        '__order__': ('leader', '008', '900__', '900__'),
        '900__': ({
            '__order__': ('a', 'b'),
            'a': _('docmaintype_comic'),
            'b': _('docsubtype_manga')
        }, {
            '__order__': ('a', 'b'),
            'a': _('docmaintype_map'),
            'b': _('docsubtype_atlas')
        })
    })
    assert result == record


def test_holdings_items_to_marc21(app, marc21_record, document,
                                  holding_lib_martigny, item_lib_martigny,
                                  ebook_5, holding_lib_martiny_electronic):
    """Test holding items to MARC21 transformation."""
    record = {'pid': document.pid}
    result = to_marc21.do(record, with_holdings_items=False)
    record = deepcopy(marc21_record)
    record.update({
        '__order__': ('leader', '001', '008'),
        '001': document.pid,
    })
    assert result == record

    record = {'pid': document.pid}
    result = to_marc21.do(record, with_holdings_items=True)
    record = deepcopy(marc21_record)
    record.update({
        '__order__': ('leader', '001', '008', '949__'),
        '001': 'doc1',
        '949__': ({
            '__order__': ('0', '1', '2', '3', '4', '5', 'B', 'a', 'e'),
            '0': 'org1',
            '1': 'The district of Martigny Libraries',
            '2': 'lib1',
            '3': 'Library of Martigny-ville',
            '4': 'loc1',
            '5': 'Martigny Library Public Space',
            'B': 'h00001',
            'a': '1234',
            'e': 'https://lipda.mediatheque.ch/CH-000019-X:223156.file'
        })
    })
    assert result == record

    record = {'pid': ebook_5.pid}
    result = to_marc21.do(record, with_holdings_items=True)
    record = deepcopy(marc21_record)
    record.update({
        '__order__': ('leader', '001', '008', '949__'),
        '001': 'ebook5',
        '949__': {
            '__order__': ('0', '1', '2', '3', '4', '5', 'E'),
            '0': 'org1',
            '1': 'The district of Martigny Libraries',
            '2': 'lib1',
            '3': 'Library of Martigny-ville',
            '4': 'loc1',
            '5': 'Martigny Library Public Space',
            'E':
                'https://bm.ebibliomedia.ch/resources/5f780fc22357943b9a83ca3d'
        }
    })
    assert result == record
