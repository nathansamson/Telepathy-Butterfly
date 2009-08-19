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

import dbus
import gobject
import telepathy
import papyon
import papyon.event
import socket

from butterfly.util.decorator import async
from butterfly.handle import ButterflyHandleFactory

__all__ = ['ButterflyFileTransferChannel']

logger = logging.getLogger('Butterfly.FileTransferChannel')


class ButterflyFileTransferChannel(
        telepathy.server.ChannelTypeFileTransfer,
        telepathy.server.ChannelInterfaceGroup):

    def __init__(self, conn, manager, session, handle, props):
        self._session = session
        self._handle = handle
        self._conn_ref = weakref.ref(conn)
        self._state = 0
        self._filename = session.filename
        self._size = session.size
        self._transferred = 0

        telepathy.server.ChannelTypeFileTransfer.__init__(self, conn, manager, props)
        telepathy.server.ChannelInterfaceGroup.__init__(self)

        session.connect("accepted", self.on_transfer_accepted)
        session.connect("progressed", self.on_transfer_progressed)
        session.connect("completed", self.on_transfer_completed)

        dbus_interface = telepathy.CHANNEL_TYPE_FILE_TRANSFER
        self._implement_property_get(dbus_interface, \
                {'State' : lambda: dbus.UInt32(self.state),
                 'ContentType': lambda: self.content_type,
                 'Filename': lambda: self.filename,
                 'Size': lambda: dbus.UInt64(self.size),
                 'Description': lambda: self.description,
                 'AvailableSocketTypes': lambda: self.socket_types,
                 'TransferredBytes': lambda: self.transferred,
                 'InitialOffset': lambda: self.offset
                 })

        self.__add_initial_participants()

    @property
    def state(self):
        return self._state

    @property
    def content_type(self):
        return "plain/text"

    @property
    def filename(self):
        return self._filename

    @property
    def size(self):
        return self._size

    @property
    def description(self):
        return ""

    @property
    def socket_types(self):
        return {
            telepathy.SOCKET_ADDRESS_TYPE_IPV4:
                [telepathy.SOCKET_ACCESS_CONTROL_LOCALHOST,
                 telepathy.SOCKET_ACCESS_CONTROL_PORT,
                 telepathy.SOCKET_ACCESS_CONTROL_NETMASK],
            telepathy.SOCKET_ADDRESS_TYPE_UNIX:
                [telepathy.SOCKET_ACCESS_CONTROL_LOCALHOST,
                 telepathy.SOCKET_ACCESS_CONTROL_CREDENTIALS]}

    @property
    def transferred(self):
        return self._transferred

    @property
    def offset(self):
        return 0

    def set_state(self, state, reason):
        if self._state == state:
            return
        self._state = state
        self.FileTransferStateChanged(state, reason)

    def AcceptFile(self, address_type, access_control, param, offset):
        self._receiving = True
        logger.debug("Accept file")
        self.socket = self.add_listener()
        self.channel = self.add_io_channel(self.socket)
        self.set_state(telepathy.FILE_TRANSFER_STATE_PENDING,
                       telepathy.FILE_TRANSFER_STATE_CHANGE_REASON_REQUESTED)
        self.InitialOffsetDefined(0)
        self.set_state(telepathy.FILE_TRANSFER_STATE_OPEN,
                       telepathy.FILE_TRANSFER_STATE_CHANGE_REASON_NONE)
        return self.socket.getsockname()

    def ProvideFile(self, address_type, access_control, param):
        self._receiving = False
        logger.debug("Provide file")
        self.socket = self.add_listener()
        self.channel = self.add_io_channel(self.socket)
        return self.socket.getsockname()

    def Close(self):
        logger.debug("Close")
        telepathy.server.ChannelTypeFileTransfer.Close(self)
        self.remove_from_connection()

    def GetSelfHandle(self):
        return self._conn.GetSelfHandle()

    def add_listener(self):
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM, 0)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, True)
        sock.bind("/tmp/patatepoil%i.txt" % int(time.time()))
        sock.listen(1)
        return sock

    def add_io_channel(self, sock):
        sock.setblocking(False)
        channel = gobject.IOChannel(sock.fileno())
        channel.set_flags(channel.get_flags() | gobject.IO_FLAG_NONBLOCK)
        channel.add_watch(gobject.IO_IN, self.on_socket_connected)
        return channel

    def on_socket_connected(self, channel, condition):
        logger.debug("Telepathy socket connected")
        sock = self.socket.accept()[0]
        if self._receiving:
            buffer = DataBuffer(sock)
            self._session.set_receive_data_buffer(buffer, self.size)
            self._session.accept()
        else:
            buffer = DataBuffer(sock, self.size)
            self._session.send(buffer)
        self.socket = sock

    def on_transfer_complete(self, session, data):
        self.set_state(telepathy.FILE_TRANSFER_STATE_COMPLETED,
                       telepathy.FILE_TRANSFER_STATE_CHANGE_REASON_NONE)

    def on_transfer_accepted(self, session):
        self.set_state(telepathy.FILE_TRANSFER_STATE_ACCEPTED,
                       telepathy.FILE_TRANSFER_STATE_CHANGE_REASON_REQUESTED)
        self.set_state(telepathy.FILE_TRANSFER_STATE_OPEN,
                       telepathy.FILE_TRANSFER_STATE_CHANGE_REASON_NONE)

    def on_transfer_progressed(self, session, size):
        self._transferred += size
        self.TransferredBytesChanged(self._transferred)

    def on_transfer_completed(self, session, data):
        self.set_state(telepathy.FILE_TRANSFER_STATE_COMPLETED,
                       telepathy.FILE_TRANSFER_STATE_CHANGE_REASON_NONE)

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

    @async
    def __add_initial_participants(self):
        pending = [self._conn.GetSelfHandle()]
        handles = [self._handle]
        self.MembersChanged('', handles, pending, [], [],
                0, telepathy.CHANNEL_GROUP_CHANGE_REASON_NONE)


class DataBuffer(object):

    def __init__(self, socket, size=0):
        self._socket = socket
        self._size = size
        self._offset = 0
        self._buffer = ""

    def seek(self, offset, position):
        if position == 0:
            self._offset = offset
        elif position == 2:
            self._offset = self._size

    def tell(self):
        return self._offset

    def read(self, max_size=None):
        if max_size is None:
            # we can't read all the data;
            # let's just return the last chunk
            return self._buffer
        max_size = min(max_size, self._size - self._offset)
        data = self._socket.recv(max_size)
        self._buffer = data
        self._offset += len(data)
        return data

    def write(self, data):
        self._buffer = data
        self._size += len(data)
        self._offset += len(data)
        self._socket.send(data)

    def add_channel(self):
        sock.setblocking(False)
        channel = gobject.IOChannel(sock.fileno())
        channel.set_encoding(None)
        channel.set_buffered(False)
        channel.set_flags(channel.get_flags() | gobject.IO_FLAG_NONBLOCK)
        channel.add_watch(gobject.IO_IN | gobject.IO_PRI, self.on_stream_received)
        self.channel = channel

    def on_stream_received(self, channel, condition):
        data = channel.read(1024)
        self._session.send_chunk(data)
