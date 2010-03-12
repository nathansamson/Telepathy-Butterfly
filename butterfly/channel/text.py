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

import gobject
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
        self._send_typing_notification_timeout = 0
        self._typing_notifications = dict()

        self._conversation = None

        telepathy.server.ChannelTypeText.__init__(self, conn, manager, props,
            object_path=object_path)
        telepathy.server.ChannelInterfaceChatState.__init__(self)
        papyon.event.ConversationEventInterface.__init__(self, conn.msn_client)

    def __del__(self):
        self._remove_typing_timeouts()

    def _remove_typing_timeouts(self):
        # Remove any timeouts we had running.
        handle = ButterflyHandleFactory(self._conn_ref(), 'self')

        if self._send_typing_notification_timeout != 0:
            gobject.source_remove(self._send_typing_notification_timeout)
            self._send_typing_notification_timeout = 0
            self.ChatStateChanged(handle, telepathy.CHANNEL_CHAT_STATE_ACTIVE)

        for handle, tag in self._typing_notifications.items():
            gobject.source_remove(tag)
            self.ChatStateChanged(handle, telepathy.CHANNEL_CHAT_STATE_ACTIVE)
        self._typing_notifications = dict()

    def steal_conversation(self):
        if self._conversation is None:
            return None

        ret = self._conversation
        self._conversation = None

        self._remove_typing_timeouts()

        # We don't want this object to receive events regarding the conversation
        # that has been stolen. It would be nice if papyon had an API to do this,
        # as opposed to having to access the _events_handlers weak set of the
        # conversation we're losing.
        self._client = None
        ret._events_handlers.remove(self)

        return ret

    def get_participants(self):
        if self._conversation:
            return self._conversation.participants
        else:
            return set()

    def _send_typing_notification(self):
        # No need to emit ChatStateChanged in this method becuase it will not
        # have changed from composing otherwise this source will have been
        # removed.

        if self._conversation is not None:
            # Send this notification and keep sending them.
            self._conversation.send_typing_notification()
            return True
        else:
            # Don't bother sending anymore as we have no conversation.
            self._send_typing_notification_timeout = 0
            return False

    def SetChatState(self, state):
        # Not useful if we dont have a conversation.
        if self._conversation is not None:
            if state == telepathy.CHANNEL_CHAT_STATE_COMPOSING:
                # User has started typing.
                self._conversation.send_typing_notification()

                # If we haven't already set a timeout, add one for every 5s.
                if self._send_typing_notification_timeout == 0:
                    self._send_typing_notification_timeout = \
                        gobject.timeout_add_seconds(5, self._send_typing_notification)

            elif state == telepathy.CHANNEL_CHAT_STATE_ACTIVE:
                # User has stopped typing.
                # If we have a timeout for sending typing notifications, remove it.
                if self._send_typing_notification_timeout != 0:
                    gobject.source_remove(self._send_typing_notification_timeout)
                    self._send_typing_notification_timeout = 0

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
        self._remove_typing_timeouts()
        telepathy.server.ChannelTypeText.Close(self)
        self.remove_from_connection()

    # Redefine GetSelfHandle since we use our own handle
    #  as Butterfly doesn't have channel specific handles
    def GetSelfHandle(self):
        return self._conn_ref().GetSelfHandle()

    def _contact_typing_notification_timeout(self, handle):
        # Contact hasn't sent a typing notification for ten seconds. He or she
        # has probably stopped typing.
        del self._typing_notifications[handle]
        self.ChatStateChanged(handle, telepathy.CHANNEL_CHAT_STATE_ACTIVE)
        return False

    # papyon.event.ConversationEventInterface
    def on_conversation_user_typing(self, contact):
        handle = ButterflyHandleFactory(self._conn_ref(), 'contact',
                contact.account, contact.network_id)
        logger.info("User %s is typing" % unicode(handle))

        # Remove any previous timeout.
        if handle in self._typing_notifications:
            gobject.source_remove(self._typing_notifications[handle])
            del self._typing_notifications[handle]

        # Add a new timeout of 10 seconds. If we don't receive another typing
        # notification in that time, the contact has probably stopped typing,
        # so we should set the chat state back to active for that handle.
        self._typing_notifications[handle] = \
            gobject.timeout_add_seconds(10, self._contact_typing_notification_timeout, handle)

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
