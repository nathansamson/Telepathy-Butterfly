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

from butterfly.Channel_Interface_Conference import *

__all__ = ['ButterflyTextChannel']

logger = logging.getLogger('Butterfly.TextChannel')


class ButterflyTextChannel(
        telepathy.server.ChannelTypeText,
        telepathy.server.ChannelInterfaceGroup,
        telepathy.server.ChannelInterfaceChatState,
        papyon.event.ContactEventInterface,
        papyon.event.ConversationEventInterface,
        ChannelInterfaceConference):

    def __init__(self, conn, manager, conversation, props, object_path=None):
        _, surpress_handler, handle = manager._get_type_requested_handle(props)
        self._recv_id = 0
        self._conn_ref = weakref.ref(conn)
        self.__is_group = False

        telepathy.server.ChannelTypeText.__init__(self, conn, manager, props,
            object_path=object_path)
        telepathy.server.ChannelInterfaceChatState.__init__(self)

        if handle.get_type() == telepathy.HANDLE_TYPE_NONE \
                and CHANNEL_INTERFACE_CONFERENCE + '.InitialChannels' in props:
            logger.info('Getting channels from InitialChannels')
            ic_paths = props[CHANNEL_INTERFACE_CONFERENCE + '.InitialChannels']
            ic = set()

            for channel in conn._channels:
                if channel._object_path in ic_paths:
                    ic.add(channel)

            if not ic:
                raise telepathy.Error("Couldn't find any channels referred to in InitialChannels")

            if len(ic) != len(ic_paths):
                raise telepathy.Error("Couldn't find all channels referred to in InitialChannels")

            self._conference_initial_channels = ic.copy()
            self._conference_channels = ic.copy()

            # Steal the first channel's conversation
            steal_channel = ic.pop()
            logger.info('Stealing switchboard from channel %s' % steal_channel._object_path)
            self._conversation = steal_channel._steal_conversation()

            self._offline_contact = None
            self._offline_handle = None
            papyon.event.ConversationEventInterface.__init__(self, self._conversation)

            while ic:
                channel = ic.pop()
                if channel._conversation is None:
                    continue

                for contact in channel._conversation.participants:
                    if contact not in self._conversation.participants:
                        logger.info('Inviting %s into channel' % contact.id)
                        self._conversation.invite_user(contact)

            self._conference_initial_invitees = []

            for invitee_handle in props.get(CHANNEL_INTERFACE_CONFERENCE + '.InitialInviteeHandles', []):
                handle = conn.handle(telepathy.HANDLE_TYPE_CONTACT, invitee_handle)
                if handle is not None and handle not in self._conference_initial_invitees:
                    self._conference_initial_invitees.append(handle)

            for invitee_id in props.get(CHANNEL_INTERFACE_CONFERENCE + '.InitialInviteeIDs', []):
                handle = None
                for h in conn._handles.itervalues():
                    if h.get_name() == invitee_id:
                        handle = h
                        break

                if handle is not None and handle not in self._conference_initial_invitees:
                    self._conference_initial_invitees.append(handle)

            for handle in self._conference_initial_invitees:
                logger.info('Inviting initial invitee, %s into channel' % handle.account)
                self._conversation.invite_user(handle.contact)

            self._add_immutables({
                    'InitialChannels': CHANNEL_INTERFACE_CONFERENCE,
                    'InitialInviteeIDs': CHANNEL_INTERFACE_CONFERENCE,
                    'InitialInviteeHandles': CHANNEL_INTERFACE_CONFERENCE,
                    'InvitationMessage': CHANNEL_INTERFACE_CONFERENCE,
                    'SupportsNonMerges': CHANNEL_INTERFACE_CONFERENCE
                    })

            self._implement_property_get(CHANNEL_INTERFACE_CONFERENCE, {
                'Channels':
                    lambda: dbus.Array(self._conference_channels, signature='o'),
                'InitialChannels':
                    lambda: dbus.Array(self._conference_initial_channels,
                                       signature='o'),
                'InitialInviteeHandles':
                    lambda: dbus.Array(
                        [h.get_id() for h in self._conference_initial_invitees],
                        signature='u'),
                'InitialInviteeIDs':
                    lambda: dbus.Array(
                        [h.get_name() for h in self._conference_initial_invitees],
                        signature='s'),
                'InvitationMessage':
                    lambda: dbus.String(''),
                'SupportsNonMerges':
                    lambda: dbus.Boolean(True)
                })

            ChannelInterfaceConference.__init__(self)
            telepathy.server.ChannelInterfaceGroup.__init__(self)

            self.__add_initial_participants()
            self.__is_group = True
        elif conversation and handle.get_type() == telepathy.HANDLE_TYPE_NONE \
                and CHANNEL_INTERFACE_CONFERENCE + '.InitialChannels' not in props:
            self._offline_contact = None
            self._offline_handle = None

            self._conversation = conversation
            papyon.event.ConversationEventInterface.__init__(self, self._conversation)
            telepathy.server.ChannelInterfaceGroup.__init__(self)

            self.__add_initial_participants()
            self.__is_group = True
        else:
            self._pending_offline_messages = {}
            contact = handle.contact
            if conversation is None:
                if contact.presence != papyon.Presence.OFFLINE:
                    client = conn.msn_client
                    conversation = papyon.Conversation(client, [contact])
            self._conversation = conversation

            if self._conversation:
                self._offline_contact = None
                self._offline_handle = None
                papyon.event.ConversationEventInterface.__init__(self, self._conversation)
            else:
                self._offline_handle = handle
                self._offline_contact = contact

            self._initial_id = handle.get_id()

        papyon.event.ConversationEventInterface.__init__(self, conn.msn_client)

        self._oim_box_ref = weakref.ref(conn.msn_client.oim_box)

    def _steal_conversation(self):
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
        if self._conversation is None and self._offline_contact.presence != papyon.Presence.OFFLINE:
            contact = self._offline_contact
            logger.info('Contact %s still connected, inviting him to the text channel before sending message' % unicode(contact))
            client = self._conn_ref().msn_client
            self._conversation = papyon.Conversation(client, [contact])
            papyon.event.ConversationEventInterface.__init__(self, self._conversation)
            self._offline_contact = None
            self._offline_handle = None

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
            if message_type == telepathy.CHANNEL_TEXT_MESSAGE_TYPE_NORMAL:
                logger.info("Sending offline message : %s" % unicode(text))
                self._oim_box_ref().send_message(self._offline_contact, text.encode("utf-8"))
                #FIXME : Check if the message was sent correctly?
            else:
                raise telepathy.NotImplemented("Unhandled message type for offline contact")
            self.Sent(int(time.time()), message_type, text)

    def Close(self):
        if self._conversation is not None:
            self._conversation.leave()
        telepathy.server.ChannelTypeText.Close(self)
        self.remove_from_connection()

    # Redefine GetSelfHandle since we use our own handle
    #  as Butterfly doesn't have channel specific handles
    def GetSelfHandle(self):
        return self._conn.GetSelfHandle()

    # Rededefine AcknowledgePendingMessages to remove offline messages
    # from the oim box.
    def AcknowledgePendingMessages(self, ids):
        telepathy.server.ChannelTypeText.AcknowledgePendingMessages(self, ids)

        if not self.__is_group:
            messages = []
            for id in ids:
                if id in self._pending_offline_messages.keys():
                    messages.append(self._pending_offline_messages[id])
                    del self._pending_offline_messages[id]
            self._oim_box_ref().delete_messages(messages)

    # Rededefine ListPendingMessages to remove offline messages
    # from the oim box.
    def ListPendingMessages(self, clear):
        if clear:
            messages = self._pending_offline_messages.values()
            self._oim_box_ref().delete_messages(messages)
        return telepathy.server.ChannelTypeText.ListPendingMessages(self, clear)

    # Group interface, only removing ourself is supported
    def RemoveMembers(self, contacts, message):
        if int(self.GetSelfHandle()) in contacts:
            self.Close()
        else :
            raise telepathy.PermissionDenied

    # papyon.event.ConversationEventInterface
    def on_conversation_user_joined(self, contact):
        handle = ButterflyHandleFactory(self._conn_ref(), 'contact',
                contact.account, contact.network_id)
        logger.info("User %s joined" % unicode(handle))

        if not self.__is_group and self._initial_id == handle.get_id():
            return

        if self.__is_group and handle not in self._members:
            self.MembersChanged('', [handle], [], [], [],
                    handle, telepathy.CHANNEL_GROUP_CHANGE_REASON_INVITED)
            return

        if self.__is_group:
            return

        props = {
            telepathy.CHANNEL + '.ChannelType': dbus.String(telepathy.CHANNEL_TYPE_TEXT),
            telepathy.CHANNEL + '.TargetHandleType': dbus.UInt32(telepathy.HANDLE_TYPE_NONE),
            CHANNEL_INTERFACE_CONFERENCE + '.InitialChannels': dbus.Array([self._object_path], signature='o'),
            CHANNEL_INTERFACE_CONFERENCE + '.InitialInviteeIDs': dbus.String(handle.get_name()),
            telepathy.CHANNEL + '.Requested': dbus.Boolean(False)
            }

        new_channel = self._conn_ref()._channel_manager.channel_for_props(props,
            signal=True, conversation=None)

        logger.info('Created new MUC channel to replace this 1-1 one: %s' % \
            new_channel._object_path)

    # papyon.event.ConversationEventInterface
    def on_conversation_user_left(self, contact):
        handle = ButterflyHandleFactory(self._conn_ref(), 'contact',
                contact.account, contact.network_id)
        logger.info("User %s left" % unicode(handle))

        if not self.__is_group:
            return

        self.MembersChanged('', [], [handle], [], [],
                handle, telepathy.CHANNEL_GROUP_CHANGE_REASON_NONE)

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

    # papyon.event.ContactEventInterface
    def on_contact_presence_changed(self, contact):
        handle = ButterflyHandleFactory(self._conn_ref(), 'contact',
                contact.account, contact.network_id)
        # Recreate a conversation if our contact join
        if self._offline_contact == contact and contact.presence != papyon.Presence.OFFLINE:
            logger.info('Contact %s connected, inviting him to the text channel' % unicode(contact))
            client = self._conn_ref().msn_client
            self._conversation = papyon.Conversation(client, [contact])
            papyon.event.ConversationEventInterface.__init__(self, self._conversation)
            self._offline_contact = None
            self._offline_handle = None
        #FIXME : I really hope there is no race condition between the time
        # the contact accept the invitation and the time we send him a message
        # Can a user refuse an invitation? what happens then?

    def AddMembers(self, contacts, message):
        for handle_id in contacts:
            handle = self._conn_ref().handle(telepathy.HANDLE_TYPE_CONTACT, handle_id)
            logger.info('Inviting new contact, %s, to chat' % handle.account)
            self._conversation.invite_user(handle.contact)

    # Public API
    def offline_message_received(self, message):
        # @message a papyon.OfflineIM.OfflineMessage
        id = self._recv_id
        sender = message.sender
        timestamp = time.mktime(message.date.timetuple())
        text = message.text

        # Map the id to the offline message so we can remove it
        # when acked by the client
        self._pending_offline_messages[id] = message

        handle = ButterflyHandleFactory(self._conn_ref(), 'contact',
                sender.account, sender.network_id)
        type = telepathy.CHANNEL_TEXT_MESSAGE_TYPE_NORMAL
        logger.info("User %r sent a offline message" % handle)
        self.Received(id, timestamp, handle, type, 0, text)

        self._recv_id += 1

    def attach_conversation(self, conversation):
        # @conversation a papyon.ConversationInterface
        if self._conversation:
            if self._conversation is conversation:
                logger.warning("Trying to reattach the same switchboard to a channel, do nothing")
                return
            else:
                logger.warning("Attaching to a channel which already have a switchboard, leaving previous one")
                self._conversation.leave()
        else:
            self._offline_contact = None
            self._offline_handle = None
        self._conversation = conversation
        papyon.event.ConversationEventInterface.__init__(self, self._conversation)

    @async
    def __add_initial_participants(self):
        handles = []
        handles.append(self._conn.GetSelfHandle())
        if self._conversation:
            for participant in self._conversation.participants:
                handle = ButterflyHandleFactory(self._conn_ref(), 'contact',
                        participant.account, participant.network_id)
                handles.append(handle)
        elif self._offline_handle:
            handles.append(self._offline_handle)

        if handles:
            self.MembersChanged('', handles, [], [], [],
                    0, telepathy.CHANNEL_GROUP_CHANGE_REASON_NONE)
