# telepathy-butterfly - an MSN connection manager for Telepathy
#
# Copyright (C) 2006-2007 Ali Sabil <ali.sabil@gmail.com>
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


import telepathy
import pymsn
import pymsn.event
import gobject
import time
import logging
from gettext import gettext as _

__all__ = ['ButterflySubscribeListChannel', 'ButterflyPublishListChannel',
        'ButterflyTextChannel']

class ButterflyListChannel(
        telepathy.server.ChannelTypeContactList,
        telepathy.server.ChannelInterfaceGroup):

    def __init__(self, connection, handle):
        telepathy.server.ChannelTypeContactList.__init__(self,
                connection, handle)
        telepathy.server.ChannelInterfaceGroup.__init__(self)
        gobject.idle_add(self.__populate, connection)

    def __populate(self, connection):
        for contact in connection._pymsn_client.address_book.contacts:
            account = contact.account
            handle = connection._handle_manager.handle_for_contact(account)
            self.contact_added(handle, contact)
        return False

    def contact_added(self, handle, contact):
        pass



class ButterflySubscribeListChannel(ButterflyListChannel):

    def __init__(self, connection, handle):
        ButterflyListChannel.__init__(self, connection, handle)
        self.GroupFlagsChanged(0, 0) # no contact Management for now

    def contact_added(self, handle, contact):
        added = set()
        if contact.is_member(pymsn.Membership.FORWARD):
            added.add(handle)

        if added:
            self.MembersChanged('', added, (), (), (), 0,
                                telepathy.CHANNEL_GROUP_CHANGE_REASON_NONE)

class ButterflyPublishListChannel(ButterflyListChannel):

    def __init__(self, connection, handle):
        ButterflyListChannel.__init__(self, connection, handle)
        self.GroupFlagsChanged(0, 0) # no contact Management for now

    def contact_added(self, handle, contact):
        added = set()
        local_pending = set()

        if contact.is_member(pymsn.Membership.REVERSE):
            added.add(handle)

        if contact.is_member(pymsn.Membership.PENDING):
            local_pending.add(handle)

        if added:
            self.MembersChanged('', added, (), local_pending, (), 0,
                                telepathy.CHANNEL_GROUP_CHANGE_REASON_NONE)


class ButterflyTextChannel(
        telepathy.server.ChannelTypeText,
        telepathy.server.ChannelInterfaceGroup,
        pymsn.event.ConversationEventInterface):
    
    logger = logging.getLogger('telepathy-butterfly:text-channel')

    def __init__(self, connection, conversation=None, contacts=[]):
        self._recv_id = 0
        telepathy.server.ChannelTypeText.__init__(self, connection, None)
        telepathy.server.ChannelInterfaceGroup.__init__(self)
        self.GroupFlagsChanged(telepathy.CHANNEL_GROUP_FLAG_CAN_ADD, 0)
        if conversation is None:
            self._conversation = pymsn.Conversation(connection._pymsn_client,
                    contacts)
        else:
            self._conversation = conversation
            gobject.idle_add(self.__add_initial_participants)
        pymsn.event.ConversationEventInterface.__init__(self,
                self._conversation)

    def __add_initial_participants(self):
        handles = []
        for participant in self._conversation.participants:
            handle = self._conn._handle_manager.\
                    handle_for_contact(participant.account)
            handles.append(handle)
        self.MembersChanged('', handles, [], [], [],
                0, telepathy.CHANNEL_GROUP_CHANGE_REASON_INVITED)
        return False

    def on_conversation_user_joined(self, contact):
        self.logger.debug("user joined : %s" % contact.account)
        handle = self._conn._handle_manager.handle_for_contact(contact.account)
        self.MembersChanged('', [handle], [], [], [],
                handle, telepathy.CHANNEL_GROUP_CHANGE_REASON_INVITED)

    def on_conversation_user_left(self, contact):
        self.logger.debug("user left : %s" % contact.account)
        handle = self._conn._handle_manager.handle_for_contact(contact.account)
        self.MembersChanged('', [], [handle], [], [],
                handle, telepathy.CHANNEL_GROUP_CHANGE_REASON_NONE)

    def on_conversation_message_received(self, sender, message, formatting):
        id = self._recv_id
        timestamp = int(time.time())
        sender = self._conn._handle_manager.handle_for_contact(sender.account)
        type = telepathy.CHANNEL_TEXT_MESSAGE_TYPE_NORMAL

        self.Received(id, timestamp, sender, type, 0, message)
        self._recv_id += 1
    
    def on_conversation_nudge_received(self, sender):
        id = self._recv_id
        timestamp = int(time.time())
        sender = self._conn._handle_manager.handle_for_contact(sender.account)
        type = telepathy.CHANNEL_TEXT_MESSAGE_TYPE_ACTION
        text = unicode(_("sends you a nudge"), "utf-8")

        self.Received(id, timestamp, sender, type, 0, text)
        self._recv_id += 1
    
    def Send(self, message_type, text):
        if message_type == telepathy.CHANNEL_TEXT_MESSAGE_TYPE_NORMAL:
            self._conversation.send_text_message(text)
        elif message_type == telepathy.CHANNEL_TEXT_MESSAGE_TYPE_ACTION and \
                text == u"nudge":
            self._conversation.send_nudge()
        else:
            raise telepathy.NotImplemented("Unhandled message type")
        self.Sent(int(time.time()), message_type, text) 

    def Close(self):
        # FIXME: figure out why we leak a reference
        for handle, channel in self._conn._channel_manager.\
                _text_channels.items():
            if channel is self:
                del self._conn._channel_manager._text_channels[handle]

        self._conversation.leave()
        telepathy.server.ChannelTypeText.Close(self)
