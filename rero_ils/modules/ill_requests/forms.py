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

"""Forms definitions about ILLrequest in public view."""

from datetime import datetime

from flask_babelex import gettext as _
from flask_wtf import FlaskForm
from wtforms import FormField, IntegerField, RadioField, SelectField, \
    StringField, TextAreaField, validators
from wtforms.fields.html5 import URLField

from rero_ils.modules.utils import get_ref_for_pid
from rero_ils.utils import remove_empties_from_dict


class ILLRequestDocumentSource(FlaskForm):
    """Form for 'published in' information about an ILL Request."""

    class Meta:
        """Meta class for ILLRequestDocumentSource."""

        csrf = False

    journal_title = StringField(
        validators=[
            validators.Optional(),
            validators.Length(min=3)
        ],
        description=_('Journal or book title')
    )
    volume = StringField(
        description=_('Volume'),
        render_kw={'placeholder': '1, 2, …'}
    )
    number = StringField(
        description=_('Issue'),
        render_kw={'placeholder': '1, January, …'}
    )


class ILLRequestDocumentForm(FlaskForm):
    """Form for document about an ILL Request."""

    class Meta:
        """Meta class for ILLRequestDocumentForm."""

        csrf = False

    current_year = datetime.now().year

    title = StringField(
        label=_('Title'),
        validators=[
            validators.DataRequired(),
            validators.Length(min=3)
        ]
    )
    authors = StringField(
        label=_('Authors'),
        validators=[
            validators.Optional(),
            validators.Length(min=3)
        ],
        render_kw={'placeholder': _('author#1; author#2')}
    )
    year = IntegerField(
        label=_('Year'),
        validators=[
          validators.Optional(),
          validators.NumberRange(min=1348, max=current_year+1)
        ],
        render_kw={'placeholder': '2020'}
    )
    publisher = StringField(
        label=_('Publisher'),
        validators=[
            validators.Optional(),
            validators.Length(min=3)
        ]
    )
    identifier = StringField(
        label=_('Identifier'),
        description=_('Example: 978-0-901690-54-6 (ISBN), '
                      '2049-3630 (ISSN), …'),
        render_kw={'placeholder': _('ISBN, ISSN')}
    )
    source = FormField(
        ILLRequestDocumentSource,
        label=_('Published in')
    )


class ILLRequestSourceForm(FlaskForm):
    """Form for source about an ILL Request."""

    class Meta:
        """Meta class for ILLRequestSourceForm."""

        csrf = False

    origin = StringField(
        description=_('Library catalog name')
    )
    url = URLField(
        description=_('Link of the document'),
        render_kw={'placeholder': 'https://…'}
    )

    def validate(self):
        """Custom validation for this form."""
        if self.url.data:
            self.origin.validators = [
                validators.DataRequired()
            ]
        if self.origin.data:
            self.url.validators = [
                validators.DataRequired(),
                validators.URL()
            ]
        return super().validate()


class ILLRequestForm(FlaskForm):
    """Form to create an ILL request."""

    document = FormField(ILLRequestDocumentForm)
    request_copy = RadioField(
        label=_('Scope'),
        choices=[(0, _('Loan')), (1, _('Copy'))],
        default=0,
        description=_('Define if the request is for a copy or an actual document.')
    )
    pages = StringField(
        label=_('Pages')
    )
    source = FormField(
        ILLRequestSourceForm,
        label=_('Found in')
    )
    note = TextAreaField(
        label='Note',
        render_kw={'rows': 5}
    )
    pickup_location = SelectField(
        label=_('Pickup location'),
        choices=[],  # Choices will be loaded dynamically because they should
                     # be given inside app_context
        validate_choice=False,
        description=_('Select the location where this request will be '
                      'operated.')
    )

    def validate(self):
        """Add custom validation on the form."""
        form_validate = super().validate()

        # if 'request_copy' is set to True, then 'pages' is required field
        custom_validate = True
        if self.request_copy.data == '1' and len(self.pages.data.strip()) == 0:
            custom_validate = False
            self.pages.errors.append(
                _('As you request a document part, you need to specify '
                  'requested pages.')
            )

        return form_validate and custom_validate

    def get_data(self):
        """Return the form as a valid ILLRequest data structure."""
        data = remove_empties_from_dict({
            'document': {
                'title': self.document.title.data,
                'authors': self.document.authors.data,
                'publisher': self.document.publisher.data,
                'year': str(self.document.year.data or ''),
                'identifier': self.document.identifier.data,
                'source': {
                    'journal_title': self.document.source.journal_title.data,
                    'volume': self.document.source.volume.data,
                    'number': self.document.source.number.data,
                }
            },
            'pickup_location': {
                '$ref': get_ref_for_pid('locations', self.pickup_location.data)
            },
            'pages': self.pages.data,
            'found_in': {
                'source': self.source.origin.data,
                'url': self.source.url.data
            }
        })
        if self.note.data:
            data['notes'] = [{
                'type': 'public_note',
                'content': self.note.data
            }]

        # if we put 'copy' in the dict before the dict cleaning and if 'copy'
        # is set to 'No', then it will be removed by `remove_empties_from_dict`
        # So we need to add it after the cleaning
        data['copy'] = self.request_copy.data == 1

        # if user select 'not specified' into the ILL request form, this value
        # must be removed from the dict.
        if data.get('document', {}).get('year') == 'n/a':
            del data['document']['year']

        return data
