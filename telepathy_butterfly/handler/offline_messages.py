# telepathy-butterfly - an MSN connection manager for Telepathy
#
# Copyright (C) 2007 Johann Prieur <johann.prieur@gmail.com>
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

import weakref
import logging

import pymsn
import pymsn.event
import telepathy
import gobject

from pymsn.service.OfflineIM import OfflineMessagesBoxState

__all__ = ['ButterflyOfflineMessagesEventsHandler']

logger = logging.getLogger('telepathy-butterfly:offline_messages')

class ButterflyOfflineMessagesEventsHandler(
    pymsn.event.OfflineMessagesEventInterface):
    def __init__(self, client, telepathy_connection):
        self._telepathy_connection = weakref.proxy(telepathy_connection)
        pymsn.event.OfflineMessagesEventInterface.__init__(self, client)
    
    def on_oim_messages_received(self, messages):
        self._client.oim_box.fetch_messages(messages)

    def on_oim_messages_fetched(self, messages):
        conversations = messages.group_by_sender()
        for sender in conversations.keys():
            handle = self._telepathy_connection._handle_for_contact(sender)
            channel = self._telepathy_connection._channel_manager.\
                channel_for_text(handle)
            
            convo = list(conversations[sender])
            convo.sort()

            for message in convo:
                channel.on_conversation_message_received(sender, message.text,
                            None, int(message.date.strftime('%s')))
        # FIXME : do this in the channel AcknowledgePendingMessages method
        # gobject.idle_add(self._client.oim_box.delete_messages, messages)

    def on_oim_messages_deleted(self):
        pass

    def on_oim_message_sent(self, recipient, message):
        pass

