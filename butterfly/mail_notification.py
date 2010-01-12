# telepathy-butterfly - an MSN connection manager for Telepathy
#
# Copyright (C) 2010 Collabora Ltd.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

from base64 import b64encode, b64decode
from butterfly.Connection_Interface_Mail_Notification import ConnectionInterfaceMailNotification
from string import join
import dbus.service
import logging
import papyon
import telepathy
import telepathy.constants


__all__ = ['ButterflyMailNotification']

logger = logging.getLogger('Butterfly.MailNotification')


# Interface name
CONN_IFACE_MAIL_NOTIFICATION = \
    'org.freedesktop.Telepathy.Connection.Interface.MailNotification.DRAFT'

# Mail_Notification_Flags (bitfield/set of flags, 0 for none)
MAIL_NOTIFICATION_HAS_PROP_UNREADMAILCOUNT = 1
MAIL_NOTIFICATION_HAS_PROP_UNREADMAILS = 2
MAIL_NOTIFICATION_HAS_SIGNAL_MAILSRECEIVED = 4

# HTTP_Method
HTTP_METHOD_GET = 0
HTTP_METHOD_POST = 1
LAST_HTTP_METHOD = 1

# Mail_Type
MAIL_TYPE_SINGLE = 0
MAIL_TYPE_THREAD = 1
LAST_MAIL_TYPE = 1


class ButterflyMailNotification(
        telepathy.server.DBusProperties,
        ConnectionInterfaceMailNotification,
        papyon.event.MailboxEventInterface):

    def __init__(self):
        logger.debug("Initialized")
        telepathy.server.DBusProperties.__init__(self)
        ConnectionInterfaceMailNotification.__init__(self)
        papyon.event.MailboxEventInterface.__init__(self, self.msn_client)

        self._implement_property_get(CONN_IFACE_MAIL_NOTIFICATION,
            {'Capabilities': lambda: self.capabilities,
             'UnreadMailCount': lambda: self.unread_mail_count,})


    @property
    def capabilities(self):
        return MAIL_NOTIFICATION_HAS_PROP_UNREADMAILCOUNT \
                | MAIL_NOTIFICATION_HAS_SIGNAL_MAILSRECEIVED


    @property
    def unread_mail_count(self):
        return self.msn_client.mailbox.unread_mail_count


    def Subscribe(self):
        pass


    def Unsubscribe(self):
        pass


    @dbus.service.method(CONN_IFACE_MAIL_NOTIFICATION,
            in_signature='', out_signature='(sua(ss))',
            async_callbacks=('_success', '_error'))
    def RequestInboxURL(self, _success, _error):
        def got_url(post_url, form_dict):
            post_data = []
            for key in form_dict:
                post_data += ((key, form_dict[key]),)
            _success((post_url, HTTP_METHOD_POST, post_data))

        self.msn_client.mailbox.request_inbox_url(got_url)

    def RequestMailURL(self, id, url_data):
        # Unserialize POST Data from base64 making sure it's good data.
        # Data is of the form <key>:<value>[&<key>:<value>]* where key
        # and value are base64 encoded.
        post_data = []
        for data in url_data.split('&'):
            tmp_data = data.split(':')
            if len(tmp_data) is not 2:
                raise telepathy.errors.InvalidArgument
            try:
                final_data = (b64decode(tmp_data[0]), b64decode(tmp_data[1]))
            except Exception, e:
                raise telepathy.errors.InvalidArgument
            post_data += [final_data]
        return (id, HTTP_METHOD_POST, post_data)


    def on_mailbox_new_mail_received(self, mail_message):
        logger.debug("New Mail " + str(mail_message))

        # Serialize with POST data in base64 as decribed in previous function.
        url_data = []
        for key, value in mail_message.form_data.items():
            url_data += [b64encode(key) + ':' + b64encode(value)]

        mail = {'id': mail_message.post_url,
                'type': MAIL_TYPE_SINGLE,
                'url_data': join(url_data,'&'),
                'senders': [(mail_message.name, mail_message.address)],
                'subject':  mail_message._subject}

        self.MailsReceived([mail])


    def on_mailbox_unread_mail_count_changed(self, unread_mail_count,
            initial=False):
        logger.debug("Unread Mail Count Changed " + str(unread_mail_count))
        self.UnreadMailsChanged(unread_mail_count, [], [])
