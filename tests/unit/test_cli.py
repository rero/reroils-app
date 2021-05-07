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

"""Test cli."""

from os.path import dirname, join

from click.testing import CliRunner

from rero_ils.modules.cli import check_validate, extract_from_xml, \
    reindex_missing, tokens_create
from rero_ils.modules.organisations.api import Organisation


def test_cli_validate(app, script_info):
    """Test validate cli."""
    runner = CliRunner()
    file_name = join(dirname(__file__), '../data/documents.json')

    res = runner.invoke(
        check_validate,
        [file_name, 'doc', '-v'],
        obj=script_info
    )
    assert res.output.strip().split('\n') == [
        'Testing json schema for file',
        '\tTest record: 1',
        '\tTest record: 2'
    ]


def test_cli_access_token(app, script_info, patron_martigny):
    """Test access token cli."""
    runner = CliRunner()
    res = runner.invoke(
        tokens_create,
        ['-n', 'test', '-u', patron_martigny.dumps().get('email'),
         '-t', 'my_token'],
        obj=script_info
    )
    assert res.output.strip().split('\n') == ['my_token']


def test_cli_reindex_missing(app, script_info, org_sion_data):
    """Test reindex missing cli."""
    org = Organisation.create(
        data=org_sion_data,
        delete_pid=False,
        dbcommit=True,
    )
    print(org)

    runner = CliRunner()
    res = runner.invoke(
        reindex_missing,
        ['-t', 'xxx', '-t', 'org', '-v'],
        obj=script_info
    )
    assert res.output.strip().split('\n') == [
        'Indexing missing xxx: ERROR pid type does not exist!',
        'Indexing missing org: 1',
        '1\torg\torg2'
    ]


def test_cli_extract_from_xml(app, tmpdir, document_marcxml, script_info):
    """Test extract from xml cli."""
    pids_file_name = join(dirname(__file__), '..', 'data', '001.pids')
    xml_file_name = join(dirname(__file__), '..', 'data', 'documents.xml')
    temp_file_name = join(tmpdir, 'temp.xml')
    runner = CliRunner()
    result = runner.invoke(
        extract_from_xml,
        [pids_file_name, xml_file_name, temp_file_name, '-v'],
        obj=script_info
    )
    assert result.exit_code == 0
    results_output = result.output.split('\n')
    assert results_output[0] == 'Extract pids from xml: '
    assert results_output[4] == 'Search pids count: 1'
