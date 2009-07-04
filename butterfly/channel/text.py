# telepathy-butterfly - an MSN connection manager for Telepathy
#
# Copyright (C) 2006-2007 Ali Sabil <ali.sabil@gmail.com>
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

import logging
import weakref
import time

import telepathy
import papyon
import papyon.event

from butterfly.util.decorator import async
from butterfly.handle import ButterflyHandleFactory

__all__ = ['ButterflyTextChannel']

logger = logging.getLogger('Butterfly.TextChannel')


class ButterflyTextChannel(
        telepathy.server.ChannelTypeText,
        telepathy.server.ChannelInterfaceGroup,
        telepathy.server.ChannelInterfaceChatState,
        papyon.event.ConversationEventInterface):

    def __init__(self, connection, conversation, chan_manager):
        self._recv_id = 0
        self._conversation = conversation
        self._conn_ref = weakref.ref(connection)
        self._chan_manager_ref = weakref.ref(chan_manager)

        telepathy.server.ChannelTypeText.__init__(self, connection, None)
        telepathy.server.ChannelInterfaceGroup.__init__(self)
        telepathy.server.ChannelInterfaceChatState.__init__(self)
        papyon.event.ConversationEventInterface.__init__(self, self._conversation)

        self.GroupFlagsChanged(telepathy.CHANNEL_GROUP_FLAG_CAN_ADD, 0)
        self.__add_initial_participants()

    def SetChatState(self, state):
        if state == telepathy.CHANNEL_CHAT_STATE_COMPOSING:
            self._conversation.send_typing_notification()
        handle = ButterflyHandleFactory(self._conn_ref(), 'self')
        self.ChatStateChanged(handle, state)

    def Send(self, message_type, text):
        if message_type == telepathy.CHANNEL_TEXT_MESSAGE_TYPE_NORMAL:
            self._conversation.send_text_message(papyon.ConversationMessage(text))
        elif message_type == telepathy.CHANNEL_TEXT_MESSAGE_TYPE_ACTION and \
                text == u"nudge":
            self._conversation.send_nudge()
        else:
            raise telepathy.NotImplemented("Unhandled message type")
        self.Sent(int(time.time()), message_type, text)

    def Close(self):
        self._conversation.leave()
        self._chan_manager_ref().remove_text_channel(self)
        telepathy.server.ChannelTypeText.Close(self)
        self.remove_from_connection()

    # Redefine GetSelfHandle since we use our own handle
    #  as Butterfly doesn't have channel specific handles
    def GetSelfHandle(self):
        return self._conn.GetSelfHandle()

    # papyon.event.ConversationEventInterface
    def on_conversation_user_joined(self, contact):
        handle = ButterflyHandleFactory(self._conn_ref(), 'contact',
                contact.account, contact.network_id)
        logger.info("User %r joined" % handle)
        self.MembersChanged('', [handle], [], [], [],
                handle, telepathy.CHANNEL_GROUP_CHANGE_REASON_INVITED)

    # papyon.event.ConversationEventInterface
    def on_conversation_user_left(self, contact):
        handle = ButterflyHandleFactory(self._conn_ref(), 'contact',
                contact.account, contact.network_id)
        logger.info("User %r left" % handle)
        if len(self._members) == 1:
            self.ChatStateChanged(handle, telepathy.CHANNEL_CHAT_STATE_GONE)
        else:
            self.MembersChanged('', [], [handle], [], [],
                    handle, telepathy.CHANNEL_GROUP_CHANGE_REASON_NONE)

    # papyon.event.ConversationEventInterface
    def on_conversation_user_typing(self, contact):
        handle = ButterflyHandleFactory(self._conn_ref(), 'contact',
                contact.account, contact.network_id)
        logger.info("User %r is typing" % handle)
        self.ChatStateChanged(handle, telepathy.CHANNEL_CHAT_STATE_COMPOSING)

    # papyon.event.ConversationEventInterface
    def on_conversation_message_received(self, sender, message):
        id = self._recv_id
        timestamp = int(time.time())
        handle = ButterflyHandleFactory(self._conn_ref(), 'contact',
                sender.account, sender.network_id)
        type = telepathy.CHANNEL_TEXT_MESSAGE_TYPE_NORMAL
        message = message.content
        logger.info("User %r sent a message" % handle)
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
        logger.info("User %r sent a nudge" % handle)
        self.Received(id, timestamp, handle, type, 0, text)
        self._recv_id += 1

    @async
    def __add_initial_participants(self):
        handles = []
        handles.append(self._conn.GetSelfHandle())
        for participant in self._conversation.participants:
            handle = ButterflyHandleFactory(self._conn_ref(), 'contact',
                    participant.account, participant.network_id)
            handles.append(handle)
        self.MembersChanged('', handles, [], [], [],
                0, telepathy.CHANNEL_GROUP_CHANGE_REASON_NONE)
