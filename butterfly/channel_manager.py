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

import telepathy
import pymsn

from butterfly.channel.contact_list import ButterflyContactListChannelFactory
from butterfly.channel.group import ButterflyGroupChannel
from butterfly.channel.text import ButterflyTextChannel
from butterfly.handle import ButterflyHandleFactory

__all__ = ['ChannelManager']

logger = logging.getLogger('Butterfly.ChannelManager')


class ChannelManager(object):
    def __init__(self, connection):
        self._conn_ref = weakref.ref(connection)
        self._list_channels = weakref.WeakValueDictionary()
        self._text_channels = weakref.WeakValueDictionary()

    def close(self):
        for channel in self._list_channels.values():
            channel.remove_from_connection()# so that dbus lets it die.
        for channel in self._text_channels.values():
            channel.Close()

    def channel_for_list(self, handle, suppress_handler=False):
        if handle in self._list_channels:
            channel = self._list_channels[handle]
        else:
            if handle.get_type() == telepathy.HANDLE_TYPE_GROUP:
                channel = ButterflyGroupChannel(self._conn_ref(), handle)
            else:
                channel = ButterflyContactListChannelFactory(self._conn_ref(), handle)
            self._list_channels[handle] = channel
            self._conn_ref().add_channel(channel, handle, suppress_handler)
        return channel

    def channel_for_text(self, handle, conversation=None, suppress_handler=False):
        if handle in self._text_channels:
            channel = self._text_channels[handle]
        else:
            logger.debug("Requesting new text channel")
            contact = handle.contact

            if conversation is None:
                client = self._conn_ref().msn_client
                conversation = pymsn.Conversation(client, [contact])
            channel = ButterflyTextChannel(self._conn_ref(), conversation, self)
            self._text_channels[handle] = channel
            self._conn_ref().add_channel(channel, handle, suppress_handler)
        return channel

    def remove_text_channel(self, text_channel):
        logger.debug("Removing channel %s" % text_channel)
        for handle, chan in self._text_channels.items():
            if chan == text_channel:
                del self._text_channels[handle]

