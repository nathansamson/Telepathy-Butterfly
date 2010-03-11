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

import logging
import weakref

import dbus
import telepathy
import papyon

from butterfly.channel.contact_list import ButterflyContactListChannelFactory
from butterfly.channel.group import ButterflyGroupChannel
from butterfly.channel.text import ButterflyTextChannel
from butterfly.channel.media import ButterflyMediaChannel
from butterfly.handle import ButterflyHandleFactory

from butterfly.Channel_Interface_Conference import CHANNEL_INTERFACE_CONFERENCE

__all__ = ['ButterflyChannelManager']

logger = logging.getLogger('Butterfly.ChannelManager')

class ButterflyChannelManager(telepathy.server.ChannelManager):
    __text_channel_id = 1
    __media_channel_id = 1

    def __init__(self, connection):
        telepathy.server.ChannelManager.__init__(self, connection)

        classes = [
            ({telepathy.CHANNEL_INTERFACE + '.ChannelType': telepathy.CHANNEL_TYPE_TEXT,
              telepathy.CHANNEL_INTERFACE + '.TargetHandleType': dbus.UInt32(telepathy.HANDLE_TYPE_CONTACT)},
             []),

            ({telepathy.CHANNEL_INTERFACE + '.ChannelType': telepathy.CHANNEL_TYPE_TEXT,
              telepathy.CHANNEL_INTERFACE + '.TargetHandleType': dbus.UInt32(telepathy.HANDLE_TYPE_NONE)},
             [CHANNEL_INTERFACE_CONFERENCE + '.InitialChannels',
              CHANNEL_INTERFACE_CONFERENCE + '.InitialInviteeHandles',
              CHANNEL_INTERFACE_CONFERENCE + '.InitialInviteeIDs',
              CHANNEL_INTERFACE_CONFERENCE + '.SupportsNonMerges'])
            ]
        self.implement_channel_classes(telepathy.CHANNEL_TYPE_TEXT, self._get_text_channel, classes)

        classes = [
            ({telepathy.CHANNEL_INTERFACE + '.ChannelType': telepathy.CHANNEL_TYPE_CONTACT_LIST},
             [])
            ]
        self.implement_channel_classes(telepathy.CHANNEL_TYPE_CONTACT_LIST, self._get_list_channel, classes)

        classes = [
            ({telepathy.CHANNEL_INTERFACE + '.ChannelType': telepathy.CHANNEL_TYPE_STREAMED_MEDIA,
              telepathy.CHANNEL_INTERFACE + '.TargetHandleType': dbus.UInt32(telepathy.HANDLE_TYPE_CONTACT)},
             [telepathy.CHANNEL_INTERFACE + '.TargetHandle'])
            ]
        self.implement_channel_classes(telepathy.CHANNEL_TYPE_STREAMED_MEDIA, self._get_media_channel, classes)

    def _get_list_channel(self, props):
        _, surpress_handler, handle = self._get_type_requested_handle(props)

        logger.debug('New contact list channel')

        if handle.get_type() == telepathy.HANDLE_TYPE_GROUP:
            # This mangling the handle name technique could possibly be better. We
            # want tp_escape_as_identifier, really.
            path = "RosterChannel/Group/%s" % unicode(handle.get_name()).encode('ascii', 'ignore')
            channel = ButterflyGroupChannel(self._conn, self, props, object_path=path)
        else:
            channel = ButterflyContactListChannelFactory(self._conn,
                self, handle, props)
        return channel

    def _get_text_channel(self, props, conversation=None):
        _, surpress_handler, handle = self._get_type_requested_handle(props)

        logger.debug('New text channel')

        if handle.get_type() not in (telepathy.HANDLE_TYPE_CONTACT, telepathy.HANDLE_TYPE_NONE):
            raise telepathy.NotImplemented('Only contacts are allowed')

        path = "ImChannel%d" % self.__text_channel_id
        self.__text_channel_id += 1

        channel = ButterflyTextChannel(self._conn, self, conversation, props,
            object_path=path)
        return channel

    def _get_media_channel(self, props, call=None):
        _, surpress_handler, handle = self._get_type_requested_handle(props)

        if handle.get_type() != telepathy.HANDLE_TYPE_CONTACT:
            raise telepathy.NotImplemented('Only contacts are allowed')

        contact = handle.contact

        if contact.presence == papyon.Presence.OFFLINE:
            raise telepathy.NotAvailable('Contact not available')

        logger.debug('New media channel')

        if call is None:
            client = self._conn.msn_client
            call = client.call_manager.create_call(contact)


        path = "MediaChannel/%d" % self.__media_channel_id
        self.__media_channel_id += 1

        return ButterflyMediaChannel(self._conn, self, call, handle, props,
            object_path=path)
