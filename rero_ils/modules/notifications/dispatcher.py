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

"""API for dispatch Notifications."""

from __future__ import absolute_import, print_function

import pycountry
from flask import current_app
from invenio_mail.api import TemplatedMessage
from invenio_mail.tasks import send_email as task_send_email
from num2words import num2words

from ..libraries.api import email_notification_type


class Dispatcher:
    """Dispatcher notifications class."""

    @classmethod
    def dispatch_notifications(cls, notification_pids=[], resend=False,
                               verbose=False):
        """Dispatch the notification.

        :param notification_pids: Notification pids to send notification.
        :param resend: Resend notification if already send.
        :param verbose: Verbose output.
        :returns: dictionary with proccessed and send count
        """
        from .api import Notification, get_communication_channel_to_use, \
            get_template_to_use

        def not_yet_implemented(*args):
            """Do nothing placeholder for a notification."""
            return

        sent = not_sent = count = 0
        aggregated = {}
        for notification_pid in notification_pids:
            count += 1
            notification = Notification.get_record_by_pid(notification_pid)
            if notification:
                process_date = notification.get('process_date')
                if process_date:
                    current_app.logger.warning(
                        f'Notification: {notification.pid} already processed '
                        f'on: {process_date}'
                    )
                    if not resend:
                        continue
                communication_switcher = {
                    'email': Dispatcher.send_mail_to_patron,
                    'mail': Dispatcher.send_mail_for_printing,
                    #  'sms': not_yet_implemented
                    #  'telepathy': self.madness_mind
                    #  ...
                }
                data = notification.replace_pids_and_refs()
                loan = data['loan']
                patron = loan['patron']
                communication_channel = get_communication_channel_to_use(
                    loan, notification, patron
                )
                dispatcher_function = communication_switcher.get(
                    communication_channel,
                    not_yet_implemented
                )
                reminder_counter = data.get('reminder_counter', 0)
                reminder = reminder_counter + 1
                communication_lang = patron['patron']["communication_language"]
                try:
                    language = pycountry.languages.get(
                        bibliographic=communication_lang)
                    reminder = num2words(
                        reminder,
                        to='ordinal_num',
                        lang=language.alpha_2
                    )
                except Exception:
                    pass
                if dispatcher_function == not_yet_implemented:
                    current_app.logger.warning(
                        'The communication channel of the patron'
                        f' (pid: {patron["pid"]}) is not yet implemented')
                # loan = Loan.get_record_by_pid(loan['pid'])
                notification_type = notification['notification_type']
                tpl_path = get_template_to_use(
                    loan, notification_type, reminder_counter).rstrip('/')
                template = f'{tpl_path}/{communication_lang}.txt'
                # Add all information used in the templates here:
                ctx_data = {
                    'template': template,
                    'profile_url': loan['profile_url'],
                    'patron': patron,
                    'library': {
                        'pid': loan['library']['pid'],
                        'notification_email': email_notification_type(
                            loan['library'], notification_type),
                        'email': loan['library'].get('email'),
                        'name': loan['library']['name'],
                        'address': loan['library']['address'],
                        'notification_settings': loan['library'][
                            'notification_settings']
                    },
                    'pickup_name': loan['pickup_name'],
                    'documents': [],
                    'notifications': []
                }

                # aggregate notifications
                n_type = notification_type
                l_pid = loan['library']['pid']
                p_pid = patron['pid']
                aggregated.setdefault(n_type, {})
                aggregated[n_type].setdefault(l_pid, {})
                aggregated[n_type][l_pid].setdefault(p_pid, ctx_data)
                documents_data = {
                    'title_text': loan['document']['title_text'],
                    'responsibility_statement':
                        loan['document']['responsibility_statement'],
                    'reminder': reminder
                }
                end_date = loan.get('end_date')
                if end_date:
                    documents_data['end_date'] = end_date
                aggregated[n_type][l_pid][p_pid]['documents'].append(
                    documents_data
                )
                aggregated[n_type][l_pid][p_pid]['notifications'].append(
                    notification
                )

        for notification_type, notification_values in aggregated.items():
            for library_pid, library_values in notification_values.items():
                for patron_pid, ctx_data in library_values.items():
                    if verbose:
                        current_app.logger.info(
                            f'Dispatch notifications: {notification_type} '
                            f'library: {library_pid} '
                            f'patron: {patron_pid} '
                            f'documents: {len(ctx_data["documents"])}'
                        )
                    sent = dispatcher_function(ctx_data)
                    for notification in ctx_data['notifications']:
                        notification.update_process_date(sent=sent)
                    if sent:
                        sent += len(ctx_data['notifications'])
                    else:
                        not_sent += len(ctx_data['notifications'])
        return {'processed': count, 'sent': sent, 'not_sent': not_sent}

    @staticmethod
    def _create_email(recipients, reply_to, ctx_data, template):
        """Create email message from template.

        :param recipients: List of emails to send the message too.
        :param reply_to: Reply to email address.
        :param ctx_data: Dictionary with informations used in template.
        :param template: Template to use to create TemplatedMessage.
        :returns: Message created.
        """
        msg = TemplatedMessage(
            template_body=template,
            sender=current_app.config.get('DEFAULT_SENDER_EMAIL',
                                          'noreply@rero.ch'),
            reply_to=reply_to,
            recipients=recipients,
            ctx=ctx_data
        )
        text = msg.body.split('\n')
        # subject is the first line
        msg.subject = text[0]
        # body
        msg.body = '\n'.join(text[1:])
        return msg

    @staticmethod
    def send_mail_for_printing(ctx_data):
        """Send the notification by email to the library.

        :param ctx_data: Dictionary with informations used in template.
        """
        # get the recipient email from the library
        notification_email = ctx_data['library'].get('notification_email')
        error_reason = ''
        if not notification_email:
            error_reason = '(Missing notification email)'
        reply_to = ctx_data['library'].get('email')
        if not reply_to:
            error_reason = '(Missing reply_to email)'
        if error_reason:
            current_app.logger.warning(
                'Notification for printing is lost for patron: '
                f'{ctx_data["patron"]["pid"]} '
                f'send to library: {ctx_data["library"]["pid"]} '
                f'{error_reason}')
            return False
        msg = Dispatcher._create_email(
            recipients=[notification_email],
            reply_to=reply_to,
            ctx_data=ctx_data,
            template=ctx_data['template']
        )
        task_send_email.apply_async((msg.__dict__,))
        return True

    @staticmethod
    def send_mail_to_patron(ctx_data):
        """Send the notification by email to the patron.

        :param ctx_data: Dictionary with informations used in template.
        """
        # get the recipient email from loan.patron.patron.email
        error_reason = ''
        recipients = [ctx_data['patron'].get('email')]
        # additional recipient
        add_recipient = ctx_data['patron'].get(
            'additional_communication_email')
        if add_recipient:
            recipients.append(add_recipient)
        if not recipients:
            error_reason = '(Missing notification recipients)'
        reply_to = ctx_data['library'].get('email')
        if not reply_to:
            error_reason = '(Missing reply_to email)'
        if error_reason:
            current_app.logger.warning(
                'Notification is lost for patron: '
                f'{ctx_data["patron"]["pid"]} '
                f'send to library: {ctx_data["library"]["pid"]} '
                f'{error_reason}')
            return False
        # delay
        delay_availability = 0
        # get notification settings for notification type
        for setting in ctx_data['library']['notification_settings']:
            if setting['type'] == 'availability':
                delay_availability = setting.get('delay', 0)
        msg = Dispatcher._create_email(
            recipients=recipients,
            reply_to=reply_to,
            ctx_data=ctx_data,
            template=ctx_data['template']
        )
        task_send_email.apply_async(
            (msg.__dict__,),
            countdown=delay_availability
        )
        return True
