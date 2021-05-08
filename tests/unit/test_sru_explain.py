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

"""Test explain."""

import mock
from utils import mock_response

from rero_ils.modules.sru.explaine import Explain


@mock.patch('requests.get')
def test_explain(mock_get, app):
    """Test Explain."""

    mock_get.return_value = mock_response(
        json_data={
            "documents-document-v0.0.1-1616965132": {
                "mappings": {
                    "date_detection": False,
                    "numeric_detection": False,
                    "properties": {
                        "$schema": {
                            "type": "keyword"
                        },
                        "_created": {
                            "type": "date"
                        },
                        "_draft": {
                            "type": "boolean"
                        },
                        "_masked": {
                            "type": "boolean"
                        },
                        "_updated": {
                            "type": "date"
                        },
                        "authorized_access_point": {
                            "type": "text",
                            "fields": {
                                "keyword": {
                                    "type": "keyword",
                                    "ignore_above": 256
                                }
                            }
                        },
                        "available": {
                            "type": "boolean"
                        },
                        "electronicLocator": {
                            "properties": {
                                "content": {
                                    "type": "keyword"
                                },
                                "publicNote": {
                                    "type": "text"
                                },
                                "type": {
                                    "type": "keyword"
                                },
                                "url": {
                                    "type": "keyword"
                                }
                            }
                        },
                        "identifiedBy": {
                            "properties": {
                                "acquisitionTerms": {
                                    "type": "text"
                                },
                                "note": {
                                    "type": "text"
                                },
                                "qualifier": {
                                    "type": "keyword"
                                },
                                "source": {
                                    "type": "keyword"
                                },
                                "status": {
                                    "type": "text"
                                },
                                "type": {
                                    "type": "keyword"
                                },
                                "value": {
                                    "type": "keyword"
                                }
                            }
                        },
                        "language": {
                            "properties": {
                                "type": {
                                    "type": "keyword"
                                },
                                "value": {
                                    "type": "keyword"
                                }
                            }
                        },
                        "pid": {
                            "type": "keyword"
                        },
                        "title": {
                            "properties": {
                                "_text": {
                                    "type": "text",
                                    "index": False,
                                    "fields": {
                                        "eng": {
                                            "type": "text",
                                            "analyzer": "english"
                                        },
                                        "fre": {
                                            "type": "text",
                                            "analyzer": "french"
                                        },
                                        "ger": {
                                            "type": "text",
                                            "analyzer": "german"
                                        },
                                        "ita": {
                                            "type": "text",
                                            "analyzer": "italian"
                                        }
                                    }
                                },
                                "mainTitle": {
                                    "properties": {
                                        "language": {
                                            "type": "keyword",
                                            "index": False
                                        },
                                        "value": {
                                            "type": "text",
                                            "index": False,
                                            "copy_to": [
                                                "autocomplete_title"
                                            ]
                                        }
                                    }
                                },
                                "type": {
                                    "type": "keyword"
                                }
                            }
                        },
                        "type": {
                            "properties": {
                                "main_type": {
                                    "type": "keyword"
                                },
                                "subtype": {
                                    "type": "keyword"
                                }
                            }
                        }
                     }
                }
            }
        }
    )
    explain = Explain('api/sru')
    assert explain.indexes == [
        '_created',
        '_draft',
        '_masked',
        '_updated',
        'authorized_access_point',
        'available',
        'electronicLocator.content',
        'electronicLocator.publicNote',
        'electronicLocator.type',
        'electronicLocator.url',
        'identifiedBy.acquisitionTerms',
        'identifiedBy.note',
        'identifiedBy.qualifier',
        'identifiedBy.source',
        'identifiedBy.status',
        'identifiedBy.type',
        'identifiedBy.value',
        'language.type',
        'language.value',
        'pid',
        'title.type',
        'type.main_type',
        'type.subtype',
    ]
    explain_strings = str(explain).split('\n')
    assert explain_strings[0] == \
        '<sru:explainResponse xmlns:sru="http://www.loc.gov/standards/sru/">'
