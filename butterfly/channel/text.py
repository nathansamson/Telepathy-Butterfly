# telepathy-butterfly - an MSN connection manager for Telepathy
#
# Copyright (C) 2006-2007 Ali Sabil <ali.sabil@gmail.com>
# Copyright (C) 2007 Johann Prieur <johann.prieur@gmail.com>
# Copyright (C) 2009-2010 Collabora, Ltd.
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

import logging
import weakref
import time

import telepathy
import papyon
import papyon.event

from butterfly.handle import ButterflyHandleFactory

__all__ = ['ButterflyTextChannel']

logger = logging.getLogger('Butterfly.TextChannel')

class ButterflyTextChannel(
        telepathy.server.ChannelTypeText,
        telepathy.server.ChannelInterfaceChatState,
        papyon.event.ContactEventInterface,
        papyon.event.ConversationEventInterface):

    def __init__(self, conn, manager, conversation, props, object_path=None):
        self._recv_id = 0
        self._conn_ref = weakref.ref(conn)

        self._conversation = None

        telepathy.server.ChannelTypeText.__init__(self, conn, manager, props,
            object_path=object_path)
        telepathy.server.ChannelInterfaceChatState.__init__(self)
        papyon.event.ConversationEventInterface.__init__(self, conn.msn_client)

    def steal_conversation(self):
        # This assumes there is only one participant in this text chat,
        # which is fair.
        participants = list(self._conversation.participants)
        contact = participants[0]

        handle = ButterflyHandleFactory(self._conn_ref(), 'contact',
                contact.account, contact.network_id)

        self._offline_handle = handle
        self._offline_contact = contact

        ret = self._conversation
        self._conversation = None

        # We don't want this object to receive events regarding the conversation
        # that has been stolen. It would be nice if papyon had an API to do this,
        # as opposed to having to access the _events_handlers weak set of the
        # conversation we're losing.
        self._client = None
        ret._events_handlers.remove(self)

        return ret

    def SetChatState(self, state):
        # Not useful if we dont have a conversation.
        if self._conversation is not None:
            if state == telepathy.CHANNEL_CHAT_STATE_COMPOSING:
                self._conversation.send_typing_notification()
        handle = ButterflyHandleFactory(self._conn_ref(), 'self')
        self.ChatStateChanged(handle, state)

    def Send(self, message_type, text):
        if self._conversation is not None:
            if message_type == telepathy.CHANNEL_TEXT_MESSAGE_TYPE_NORMAL:
                logger.info("Sending message : %s" % unicode(text))
                self._conversation.send_text_message(papyon.ConversationMessage(text))
            elif message_type == telepathy.CHANNEL_TEXT_MESSAGE_TYPE_ACTION and \
                    text == u"nudge":
                self._conversation.send_nudge()
            else:
                raise telepathy.NotImplemented("Unhandled message type")
            self.Sent(int(time.time()), message_type, text)
        else:
            logger.warning('Tried sending a message with no conversation')

    def Close(self):
        if self._conversation is not None:
            self._conversation.leave()
        telepathy.server.ChannelTypeText.Close(self)
        self.remove_from_connection()

    # Redefine GetSelfHandle since we use our own handle
    #  as Butterfly doesn't have channel specific handles
    def GetSelfHandle(self):
        return self._conn_ref().GetSelfHandle()

    # papyon.event.ConversationEventInterface
    def on_conversation_user_typing(self, contact):
        handle = ButterflyHandleFactory(self._conn_ref(), 'contact',
                contact.account, contact.network_id)
        logger.info("User %s is typing" % unicode(handle))
        self.ChatStateChanged(handle, telepathy.CHANNEL_CHAT_STATE_COMPOSING)

    # papyon.event.ConversationEventInterface
    def on_conversation_message_received(self, sender, message):
        id = self._recv_id
        timestamp = int(time.time())
        handle = ButterflyHandleFactory(self._conn_ref(), 'contact',
                sender.account, sender.network_id)
        type = telepathy.CHANNEL_TEXT_MESSAGE_TYPE_NORMAL
        message = message.content
        logger.info("User %s sent a message" % unicode(handle))
        self.Received(id, timestamp, handle, type, 0, message)
        self._recv_id += 1

    # papyon.event.ConversationEventInterface
    def on_conversation_nudge_received(self, sender):
        id = self._recv_id
        timestamp = int(time.time())
        handle = ButterflyHandleFactory(self._conn_ref(), 'contact',
                sender.account, sender.network_id)
        type = telepathy.CHANNEL_TEXT_MESSAGE_TYPE_ACTION
        text = unicode("sends you a nudge", "utf-8")
        logger.info("User %s sent a nudge" % unicode(handle))
        self.Received(id, timestamp, handle, type, 0, text)
        self._recv_id += 1
