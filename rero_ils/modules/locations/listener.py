# -*- coding: utf-8 -*-
#
# This file is part of RERO ILS.
# Copyright (C) 2017 RERO.
#
# RERO ILS is free software; you can redistribute it
# and/or modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 2 of the
# License, or (at your option) any later version.
#
# RERO ILS is distributed in the hope that it will be
# useful, but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with RERO ILS; if not, write to the
# Free Software Foundation, Inc., 59 Temple Place, Suite 330, Boston,
# MA 02111-1307, USA.
#
# In applying this license, RERO does not
# waive the privileges and immunities granted to it by virtue of its status
# as an Intergovernmental Organization or submit itself to any jurisdiction.

"""Signals connector for Location."""

from .api import Location, LocationsSearch


def enrich_location_data(sender, json=None, record=None, index=None,
                         **dummy_kwargs):
    """Signal sent before a record is indexed.

    Arguments:
    - ``json``: The dumped record dictionary which can be modified.
    - ``record``: The record being indexed.
    - ``index``: The index in which the record will be indexed.
    - ``doc_type``: The doc_type for the record.
    """
    location_index_name = LocationsSearch.Meta.index
    if index.startswith(location_index_name):
        location = record
        if not isinstance(record, Location):
            location = Location.get_record_by_pid(record.get('pid'))
        org_pid = location.get_library().replace_refs()['organisation']['pid']
        json['organisation'] = {
            'pid': org_pid
        }
