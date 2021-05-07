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

"""Items Record utils tests."""
import pytest

from rero_ils.modules.items.utils import exists_available_item


def test_exists_available_item(item_lib_martigny):
    """Test exists_available_items function."""
    assert not exists_available_item([])
    assert exists_available_item([item_lib_martigny])
    assert exists_available_item([item_lib_martigny.pid])

    with pytest.raises(ValueError):
        assert exists_available_item([0, item_lib_martigny.pid])
