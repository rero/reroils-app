# -*- coding: utf-8 -*-
#
# RERO ILS
# Copyright (C) 2019 RERO
# Copyright (C) 2020 UCLouvain
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

"""API for manipulating libraries."""

from datetime import datetime, timedelta
from functools import partial

import pytz
from dateutil import parser
from dateutil.rrule import FREQNAMES, rrule

from .models import LibraryIdentifier, LibraryMetadata
from ..api import IlsRecord, IlsRecordsIndexer, IlsRecordsSearch
from ..fetchers import id_fetcher
from ..locations.api import LocationsSearch
from ..minters import id_minter
from ..providers import Provider
from ..utils import date_string_to_utc, strtotime

# provider
LibraryProvider = type(
    'LibraryProvider',
    (Provider,),
    dict(identifier=LibraryIdentifier, pid_type='lib')
)
# minter
library_id_minter = partial(id_minter, provider=LibraryProvider)
# fetcher
library_id_fetcher = partial(id_fetcher, provider=LibraryProvider)


# define Python user-defined exceptions
class LibraryNeverOpen(Exception):
    """Raised when the library has no open days."""


class LibrariesSearch(IlsRecordsSearch):
    """Libraries search."""

    class Meta():
        """Meta class."""

        index = 'libraries'
        doc_types = None
        fields = ('*', )
        facets = {}

        default_filter = None


class Library(IlsRecord):
    """Library class."""

    minter = library_id_minter
    fetcher = library_id_fetcher
    provider = LibraryProvider
    model_cls = LibraryMetadata
    pids_exist_check = {
        'required': {
            'org': 'organisation'
        }
    }

    @property
    def online_location(self):
        """Get the online location."""
        result = LocationsSearch()\
            .filter('term', is_online=True)\
            .filter('term', library__pid=self.pid)\
            .source(['pid']).scan()
        try:
            return next(result).pid
        except StopIteration:
            return None

    def get_organisation(self):
        """Get Organisation."""
        from ..organisations.api import Organisation
        return Organisation.get_record_by_pid(self.organisation_pid)

    def pickup_location_query(self):
        """Search the location index for pickup locations."""
        return LocationsSearch().filter(
            'term', library__pid=self.pid).filter(
                'term', is_pickup=True).source(['pid']).scan()

    def get_pickup_locations_pids(self):
        """Returns libraries all pickup locations pids."""
        for location in self.pickup_location_query():
            yield location.pid

    def get_pickup_location_pid(self):
        """Returns libraries first pickup location pid."""
        try:
            return next(self.pickup_location_query()).pid
        except StopIteration:
            return None

    def _is_betweentimes(self, time_to_test, times):
        """Test if time is between times."""
        times_open = False
        for time_given in times:
            start_time = strtotime(time_given['start_time'])
            end_time = strtotime(time_given['end_time'])

            if time_to_test.hour == time_to_test.minute == \
                    time_to_test.second == 0:
                # case when library is open or close few hours per day
                times_open = times_open or end_time > start_time
            else:
                times_open = times_open or ((time_to_test >= start_time) and
                                            (time_to_test <= end_time))
        return times_open

    def _has_is_open(self):
        """Test if library has opening days."""
        opening_hours = self.get('opening_hours')
        if opening_hours:
            for opening_hour in opening_hours:
                if opening_hour['is_open']:
                    return True
        exception_dates = self.get('exception_dates')
        if exception_dates:
            for exception_date in exception_dates:
                if exception_date['is_open']:
                    return True
        return False

    def _get_exceptions_matching_date(self, date_to_check, day_only=False):
        """Get all exception matching a given date."""
        for exception in self.get('exception_dates', []):
            # Get the start date and the gap (in days) between start date and
            # end date. If no end_date are supplied, the gap will be 0.
            start_date = date_string_to_utc(exception['start_date'])
            end_date = start_date
            day_gap = 0
            if exception.get('end_date'):
                end_date = date_string_to_utc(exception.get('end_date'))
                day_gap = (end_date - start_date).days

            # If the exception is repeatable, then the start_date should be the
            # nearest date (lower or equal than date_to_check) related to the
            # repeat period/interval definition. To know that, we need to know
            # all exception dates possible (form exception start_date to
            # date_to_check) and get only the last one.
            if exception.get('repeat'):
                period = exception['repeat']['period'].upper()
                exception_dates = rrule(
                    freq=FREQNAMES.index(period),
                    until=date_to_check,
                    interval=exception['repeat']['interval'],
                    dtstart=start_date
                )
                for start_date in exception_dates:
                    pass
                end_date = start_date + timedelta(days=day_gap)

            # Now, check if exception is matching for the date_to_check
            # If exception defined times, we need to check if the date_to_check
            # is includes into theses time intervals (only if `day_only` method
            # argument is set)
            if start_date.date() <= date_to_check.date() <= end_date.date():
                if exception.get('times') and not day_only:
                    times = exception.get('times')
                    if self._is_betweentimes(date_to_check.time(), times):
                        yield exception
                else:
                    yield exception

    def is_open(self, date=datetime.now(pytz.utc), day_only=False):
        """Test library is open."""
        is_open = False
        rule_hours = []

        # First of all, change date to be aware and with timezone.
        if isinstance(date, str):
            date = date_string_to_utc(date)
        if isinstance(date, datetime) and date.tzinfo is None:
            date = date.replace(tzinfo=pytz.utc)

        # STEP 1 :: check about regular rules
        #   Each library could defined if a specific weekday is open or closed.
        #   Check into this weekday array if the day is open/closed. If the
        #   searched weekday isn't defined the default value is closed
        #
        #   If the find rule defined open time periods, check if date_to_check
        #   is into this periods (depending of `day_only` method argument).
        day_name = date.strftime("%A").lower()
        regular_rule = [
            rule for rule in self['opening_hours']
            if rule['day'] == day_name
        ]
        if regular_rule:
            is_open = regular_rule[0].get('is_open', False)
            rule_hours = regular_rule[0].get('times', [])

        if is_open and not day_only:
            is_open = self._is_betweentimes(date.time(), rule_hours)

        # STEP 2 :: test each exceptions
        #   Each library can defined a set of exception dates. These exceptions
        #   could be repeatable for a specific interval. Check is some
        #   exceptions are relevant related to date_to_check and if these
        #   exception changed the behavior of regular rules.
        #
        #   Each exception can defined open time periods, check if
        #   date_to_check is into this periods (depending of `day_only`
        #   method argument)
        for exception in self._get_exceptions_matching_date(date, day_only):
            if is_open != exception['is_open']:
                is_open = not is_open

        return is_open

    def _get_opening_hour_by_day(self, day_name):
        """Get the library opening hour for a specific day."""
        day_name = day_name.lower()
        days = [
            day for day in self.get('opening_hours', [])
            if day['day'] == day_name and day['is_open']
        ]
        if days and days[0]['times']:
            return days[0]['times'][0]['start_time']

    def next_open(self, date=datetime.now(pytz.utc), previous=False,
                  ensure=False):
        """Get next open day."""
        if not self._has_is_open():
            raise LibraryNeverOpen
        if isinstance(date, str):
            date = parser.parse(date)
        add_day = 1
        if previous:
            add_day = -1
        date += timedelta(days=add_day)
        while not self.is_open(date=date, day_only=True):
            date += timedelta(days=add_day)
        if not ensure:
            return date
        opening_hour = self._get_opening_hour_by_day(date.strftime('%A'))
        time = [int(part) for part in opening_hour.split(':')]
        return date.replace(
            hour=time[0],
            minute=time[1],
            second=0,
            microsecond=0
        )

    def get_open_days(self, start_date=datetime.now(pytz.utc),
                      end_date=datetime.now(pytz.utc)):
        """Get all open days between date interval."""
        if isinstance(start_date, str):
            start_date = date_string_to_utc(start_date)
        if isinstance(end_date, str):
            end_date = date_string_to_utc(end_date)

        dates = []
        end_date += timedelta(days=1)
        while end_date > start_date:
            if self.is_open(date=start_date, day_only=True):
                dates.append(start_date)
            start_date += timedelta(days=1)
        return dates

    def count_open(self, start_date=datetime.now(pytz.utc),
                   end_date=datetime.now(pytz.utc)):
        """Get number of open day between date interval."""
        return len(self.get_open_days(start_date, end_date))

    def in_working_days(self, count, date=datetime.now(pytz.utc)):
        """Get date for given working days."""
        counting = 1
        if isinstance(date, str):
            date = date_string_to_utc(date)
        while counting <= count:
            counting += 1
            date = self.next_open(date=date)
        return date

    def get_number_of_librarians(self):
        """Get number of librarians."""
        from ..patrons.api import PatronsSearch
        results = PatronsSearch().filter(
            'term', libraries__pid=self.pid).filter(
                'term', roles='librarian').source().count()
        return results

    def get_number_of_locations(self):
        """Get number of locations."""
        results = LocationsSearch().filter(
            'term', library__pid=self.pid).source().count()
        return results

    def get_links_to_me(self):
        """Get number of links."""
        links = {}
        locations = self.get_number_of_locations()
        if locations:
            links['locations'] = locations
        librarians = self.get_number_of_librarians()
        if librarians:
            links['patrons'] = librarians
        return links

    def reasons_not_to_delete(self):
        """Get reasons not to delete record."""
        cannot_delete = {}
        links = self.get_links_to_me()
        if links:
            cannot_delete['links'] = links
        return cannot_delete

    def get_timezone(self):
        """Get library timezone."""
        # TODO: get timezone regarding Library address.
        # TODO: Use BABEL_DEFAULT_TIMEZONE by default
        default = pytz.timezone('Europe/Zurich')
        return default


class LibrariesIndexer(IlsRecordsIndexer):
    """Holdings indexing class."""

    record_cls = Library

    def bulk_index(self, record_id_iterator):
        """Bulk index records.

        :param record_id_iterator: Iterator yielding record UUIDs.
        """
        super().bulk_index(record_id_iterator, doc_type='lib')


def email_notification_type(libray, notification_type):
    """Get the email corresponding to the given notification type.

    :param notification_type: the notification type.
    :return: the email corresponding to the notification type.
    :rtype: string
    """
    for setting in libray['notification_settings']:
        if setting['type'] == notification_type:
            return setting['email']
