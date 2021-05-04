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

"""Document JSON schema tests."""

from __future__ import absolute_import, print_function

import pytest
from jsonschema import validate
from jsonschema.exceptions import ValidationError


def test_required(app, document_schema, document_data_tmp):
    """Test required for jsonschemas."""
    validate(document_data_tmp, document_schema)

    with pytest.raises(ValidationError):
        validate({}, document_schema)


def test_pid(document_schema, document_data_tmp):
    """Test pid for jsonschemas."""
    validate(document_data_tmp, document_schema)

    with pytest.raises(ValidationError):
        document_data_tmp['pid'] = 25
        validate(document_data_tmp, document_schema)


def test_title(document_schema, document_data_tmp):
    """Test title for jsonschemas."""
    validate(document_data_tmp, document_schema)

    with pytest.raises(ValidationError):
        document_data_tmp['title'] = 2
        validate(document_data_tmp, document_schema)


def test_titlesProper(document_schema, document_data_tmp):
    """Test titlesProper for jsonschemas."""
    document_data_tmp['titlesProper'] = ['RERO21 pour les nuls']

    validate(document_data_tmp, document_schema)

    with pytest.raises(ValidationError):
        document_data_tmp['titlesProper'] = 'string is a bad type'
        validate(document_data_tmp, document_schema)


def test_type(document_schema, document_data_tmp):
    """Test type for document jsonschemas."""
    validate(document_data_tmp, document_schema)

    with pytest.raises(ValidationError):
        document_data_tmp['type'] = 2
        validate(document_data_tmp, document_schema)

    with pytest.raises(ValidationError):
        document_data_tmp['type'] = 'CD-ROM'
        validate(document_data_tmp, document_schema)


def test_part_of(document_schema, document_data_tmp):
    """Test type for document jsonschemas."""
    validate(document_data_tmp, document_schema)

    with pytest.raises(ValidationError):
        document_data_tmp['partOf'] = 2
        validate(document_data_tmp, document_schema)


def test_languages(document_schema, document_data_tmp):
    """Test languages for jsonschemas."""
    validate(document_data_tmp, document_schema)

    with pytest.raises(ValidationError):
        document_data_tmp['language'][0]['value'] = [2]
        validate(document_data_tmp, document_schema)

    with pytest.raises(ValidationError):
        document_data_tmp['language'][0]['value'] = ['gre']
        validate(document_data_tmp, document_schema)


def test_translatedFrom(document_schema, document_data_tmp):
    """Test translatedFrom for jsonschemas."""
    document_data_tmp['translatedFrom'] = ['eng']

    validate(document_data_tmp, document_schema)

    with pytest.raises(ValidationError):
        document_data_tmp['translatedFrom'] = [2]
        validate(document_data_tmp, document_schema)


def test_contribution(document_schema, document_data_tmp):
    """Test contribution for jsonschemas."""
    document_data_tmp['contribution'] = [
        {
            'agent': {
                'type': 'bf:Person',
                'preferred_name': 'Dumont, Jean',
                'date_of_birth': '1954',
                'qualifier': 'Développeur'
            },
            'role': ['aut']
        },
        {
            'agent': {
                'type': 'bf:Organisation',
                'preferred_name': 'RERO'
            },
            'role': ['aut']
        }
    ]
    validate(document_data_tmp, document_schema)

    with pytest.raises(ValidationError):
        document_data_tmp['contribution'][0]['agent']['type'] = [2]
        validate(document_data_tmp, document_schema)

    with pytest.raises(ValidationError):
        document_data_tmp['contribution'][0]['agent']['preferred_name'] = [2]
        validate(document_data_tmp, document_schema)

    with pytest.raises(ValidationError):
        document_data_tmp['contribution'][1]['agent']['type'] = [2]
        validate(document_data_tmp, document_schema)

    with pytest.raises(ValidationError):
        document_data_tmp['contribution'][1]['agent']['preferred_name'] = [2]
        validate(document_data_tmp, document_schema)


def test_copyrightDate(document_schema, document_data_tmp):
    """Test copyright date for jsonschemas."""
    document_data_tmp['copyrightDate'] = ['© 1971']

    validate(document_data_tmp, document_schema)

    with pytest.raises(ValidationError):
        document_data_tmp['copyrightDate'] = 1971
        validate(document_data_tmp, document_schema)


def test_edition_statement(document_schema, document_data_tmp):
    """Test edition statement for jsonschemas."""
    document_data_tmp['editionStatement'] = [{
        'editionDesignation': [{
            'value': 'Di 3 ban'
        }, {
            'value': '第3版',
            'language': 'chi-hani'
        }],
        'responsibility': [{
            'value': 'Zeng Lingliang zhu bian'
        }, {
            'value': '曾令良主编',
            'language': 'chi-hani'
        }]
    }]

    validate(document_data_tmp, document_schema)

    with pytest.raises(ValidationError):
        document_data_tmp['editionStatement'] = [{'bad_key': 'bad_value'}]
        validate(document_data_tmp, document_schema)
    with pytest.raises(ValidationError):
        document_data_tmp['editionStatement'] = 'string is a bad type'
        validate(document_data_tmp, document_schema)


def test_provisionActivity(document_schema, document_data_tmp):
    """Test publishers for jsonschemas."""
    document_data_tmp['provisionActivity'] = [{
        'type': 'bf:Publication',
        'place': [
            {
                'country': 'fr',
                'type': 'bf:Place'
            }
        ],
        'statement': [
            {
                'label': [
                    {'value': 'Paris'}
                ],
                'type': 'bf:Place'
            },
            {
                'label': [
                    {'value': 'Desclée de Brouwer'}
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
                    {'value': '1969'}
                ],
                'type': 'Date'
            }

        ],
        'startDate': 1969
    }]

    validate(document_data_tmp, document_schema)

    with pytest.raises(ValidationError):
        document_data_tmp['provisionActivity'][0]['type'] = [2]
        validate(document_data_tmp, document_schema)

    with pytest.raises(ValidationError):
        document_data_tmp['provisionActivity'][0]['startDate'] = [2]
        validate(document_data_tmp, document_schema)


def test_extent(document_schema, document_data_tmp):
    """Test extent for jsonschemas."""
    document_data_tmp['extent'] = '1 DVD-R (50 min.)'

    validate(document_data_tmp, document_schema)

    with pytest.raises(ValidationError):
        document_data_tmp['extent'] = [2]
        validate(document_data_tmp, document_schema)


def test_duration(document_schema, document_data_tmp):
    """Test duration for jsonschemas."""
    document_data_tmp['duration'] = ['(50 min.)']

    validate(document_data_tmp, document_schema)

    with pytest.raises(ValidationError):
        document_data_tmp['duration'] = [2]
        validate(document_data_tmp, document_schema)


def test_production_method(document_schema, document_data_tmp):
    """Test productionMethod for jsonschemas."""
    document_data_tmp['productionMethod'] = ['rdapm:1007']

    validate(document_data_tmp, document_schema)

    with pytest.raises(ValidationError):
        document_data_tmp['productionMethod'] = [2]
        validate(document_data_tmp, document_schema)


def test_illustrative_content(document_schema, document_data_tmp):
    """Test illustrativeContent for jsonschemas."""
    document_data_tmp['illustrativeContent'] = ['illustrations']

    validate(document_data_tmp, document_schema)

    with pytest.raises(ValidationError):
        document_data_tmp['illustrativeContent'] = [2]
        validate(document_data_tmp, document_schema)


def test_color_content(document_schema, document_data_tmp):
    """Test colorContent for jsonschemas."""
    document_data_tmp['colorContent'] = ['rdacc:1002']

    validate(document_data_tmp, document_schema)

    with pytest.raises(ValidationError):
        document_data_tmp['colorContent'] = [2]
        validate(document_data_tmp, document_schema)


def test_book_format(document_schema, document_data_tmp):
    """Test bookFormat for jsonschemas."""
    document_data_tmp['bookFormat'] = ['8º']

    validate(document_data_tmp, document_schema)

    with pytest.raises(ValidationError):
        document_data_tmp['bookFormat'] = [2]
        validate(document_data_tmp, document_schema)


def test_dimensions(document_schema, document_data_tmp):
    """Test dimensions for jsonschemas."""
    document_data_tmp['dimensions'] = ['in-8, 22 cm']

    validate(document_data_tmp, document_schema)

    with pytest.raises(ValidationError):
        document_data_tmp['dimensions'] = [2]
        validate(document_data_tmp, document_schema)


def test_series(document_schema, document_data_tmp):
    """Test series for jsonschemas."""
    document_data_tmp['seriesStatement'] = [{
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

    validate(document_data_tmp, document_schema)

    with pytest.raises(ValidationError):
        document_data_tmp['seriesStatement'][0]['seriesTitle'] = 2
        validate(document_data_tmp, document_schema)

    with pytest.raises(ValidationError):
        document_data_tmp['seriesStatement'][0]['seriesEnumeration'] = 2
        validate(document_data_tmp, document_schema)

    with pytest.raises(ValidationError):
        document_data_tmp['seriesStatement'][0]['subseriesStatement'] is None
        validate(document_data_tmp, document_schema)


def test_note(document_schema, document_data_tmp):
    """Test note for jsonschemas."""
    document_data_tmp['note'] = [{
        'noteType': 'otherPhysicalDetails',
        'label': 'litho Ill.en n. et bl.'
    }]

    validate(document_data_tmp, document_schema)

    with pytest.raises(ValidationError):
        document_data_tmp['note'][0] = 2
        validate(document_data_tmp, document_schema)


def test_identifiedby(document_schema, document_data_tmp):
    """Test identifiers for jsonschemas."""
    document_data_tmp['identifiedBy'] = [
        {
            "type": "bf:Local",
            "source": "RERO",
            "value": "R008745599"
        },
        {
            "type": "bf:Isbn",
            "value": "9782844267788"
        },
        {
            "type": "bf:Local",
            "source": "BNF",
            "value": "FRBNF452959040000002"
        },
        {
            "type": "uri",
            "value": "http://catalogue.bnf.fr/ark:/12148/cb45295904f"
        }
    ]
    validate(document_data_tmp, document_schema)

    with pytest.raises(ValidationError):
        for identifier in document_data_tmp['identifiedBy']:
            identifier['value'] = 2
            validate(document_data_tmp, document_schema)

    with pytest.raises(ValidationError):
        document_data_tmp['identifiedBy'] = {}
        validate(document_data_tmp, document_schema)


def test_subjects(document_schema, document_data_tmp):
    """Test subjects for jsonschemas."""
    document_data_tmp['subjects'] = [
        {
            'type': "bf:Topic",
            'term': 'ILS'
        },
        {
            'type': "bf:Topic",
            'term': 'informatique'
        },
        {
            'type': "bf:Topic",
            'term': 'bibliothèque'
        }
    ]

    validate(document_data_tmp, document_schema)

    with pytest.raises(ValidationError):
        document_data_tmp['subjects'] = 2
        validate(document_data_tmp, document_schema)


def test_harvested(document_schema, document_data_tmp):
    """Test harvested for jsonschemas."""
    validate(document_data_tmp, document_schema)

    with pytest.raises(ValidationError):
        document_data_tmp['harvested'] = 2
        validate(document_data_tmp, document_schema)


def test_draft(document_schema, document_data_tmp):
    """Test draft for jsonschemas."""
    validate(document_data_tmp, document_schema)

    with pytest.raises(ValidationError):
        document_data_tmp['_draft'] = 2
        validate(document_data_tmp, document_schema)
