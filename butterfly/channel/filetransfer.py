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

from telepathy.interfaces import CHANNEL_TYPE_FILE_TRANSFER

__all__ = ['ButterflyFileTransferChannel']

logger = logging.getLogger('Butterfly.FileTransferChannel')


class ButterflyFileTransferChannel(telepathy.server.ChannelTypeFileTransfer):

    def __init__(self, conn, manager, session, handle, props):
        self._handle = handle
        self._conn_ref = weakref.ref(conn)
        self._state = 0
        self._transferred = 0

        self._receiving = not props[telepathy.CHANNEL + '.Requested']

        telepathy.server.ChannelTypeFileTransfer.__init__(self, conn, manager, props)

        # Incoming.
        if session is None:
            type = telepathy.CHANNEL_TYPE_FILE_TRANSFER
            filename = props.get(type + ".Filename", None)
            size = props.get(type + ".Size", None)

            if filename is None or size is None:
                raise telepathy.InvalidArgument(
                    "New file transfer channel requires Filename and Size properties")

            client = conn.msn_client
            session = client.ft_manager.send(handle.contact, filename, size)

        self._session = session
        self._filename = session.filename
        self._size = session.size

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

        self._add_immutables({
                'Filename': CHANNEL_TYPE_FILE_TRANSFER,
                'Size': CHANNEL_TYPE_FILE_TRANSFER,
                })

        self.set_state(telepathy.FILE_TRANSFER_STATE_PENDING,
                       telepathy.FILE_TRANSFER_STATE_CHANGE_REASON_REQUESTED)

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
        logger.debug("State change: %u -> %u (reason: %u)" % (self._state, state, reason))
        self._state = state
        self.FileTransferStateChanged(state, reason)

    def AcceptFile(self, address_type, access_control, param, offset):
        logger.debug("Accept file")

        if address_type not in self.socket_types.keys():
            raise telepathy.NotImplemented("Socket type %u is unsupported" % address_type)

        self.socket = self.add_listener()
        self.channel = self.add_io_channel(self.socket)
        self.set_state(telepathy.FILE_TRANSFER_STATE_PENDING,
                       telepathy.FILE_TRANSFER_STATE_CHANGE_REASON_REQUESTED)
        self.InitialOffsetDefined(0)
        self.set_state(telepathy.FILE_TRANSFER_STATE_OPEN,
                       telepathy.FILE_TRANSFER_STATE_CHANGE_REASON_NONE)
        return self.socket.getsockname()

    def ProvideFile(self, address_type, access_control, param):
        logger.debug("Provide file")

        if address_type not in self.socket_types.keys():
            raise telepathy.NotImplemented("Socket type %u is unsupported" % address_type)

        self.socket = self.add_listener()
        self.channel = self.add_io_channel(self.socket)
        return self.socket.getsockname()

    def Close(self):
        logger.debug("Close")
        if self.state not in (telepathy.FILE_TRANSFER_STATE_CANCELLED,
                                 telepathy.FILE_TRANSFER_STATE_COMPLETED):
            self._session.cancel()
            self.set_state(telepathy.FILE_TRANSFER_STATE_CANCELLED,
                           telepathy.FILE_TRANSFER_STATE_CHANGE_REASON_LOCAL_CANCELLED)
        telepathy.server.ChannelTypeFileTransfer.Close(self)
        self.remove_from_connection()

    def GetSelfHandle(self):
        return self._conn.GetSelfHandle()

    def add_listener(self):
        """Create a listener socket"""
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM, 0)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, True)
        sock.bind("/tmp/butterfly-%i" % int(time.time()))
        sock.listen(1)
        return sock

    def add_io_channel(self, sock):
        """Set up notification on the socket via a giochannel"""
        sock.setblocking(False)
        channel = gobject.IOChannel(sock.fileno())
        channel.set_flags(channel.get_flags() | gobject.IO_FLAG_NONBLOCK)
        channel.add_watch(gobject.IO_IN, self.on_socket_connected)
        channel.add_watch(gobject.IO_HUP | gobject.IO_ERR,
                self.on_socket_disconnected)
        return channel

    def on_socket_connected(self, channel, condition):
        logger.debug("Client socket connected")
        sock = self.socket.accept()[0]
        if self._receiving:
            buffer = DataBuffer(sock)
            self._session.set_receive_data_buffer(buffer, self.size)
            # Notify the other end we accepted the FT
            self._session.accept()
        else:
            buffer = DataBuffer(sock, self.size)
            self._session.send(buffer)
        self.socket = sock

    def on_socket_disconnected(self, channel, condition):
        logger.debug("Client socket disconnected")
        #TODO only cancel if the socket is disconnected while listening
        #self._session.cancel()
        #self.set_state(telepathy.FILE_TRANSFER_STATE_CANCELLED,
        #               telepathy.FILE_TRANSFER_STATE_CHANGE_REASON_LOCAL_ERROR)

    def on_transfer_accepted(self, session):
        logger.debug("Transfer has been accepted")
        self.set_state(telepathy.FILE_TRANSFER_STATE_ACCEPTED,
                       telepathy.FILE_TRANSFER_STATE_CHANGE_REASON_REQUESTED)
        self.set_state(telepathy.FILE_TRANSFER_STATE_OPEN,
                       telepathy.FILE_TRANSFER_STATE_CHANGE_REASON_NONE)

    def on_transfer_progressed(self, session, size):
        self._transferred += size
        self.TransferredBytesChanged(self._transferred)

    def on_transfer_completed(self, session, data):
        logger.debug("Transfer completed")
        self.set_state(telepathy.FILE_TRANSFER_STATE_COMPLETED,
                       telepathy.FILE_TRANSFER_STATE_CHANGE_REASON_NONE)

class DataBuffer(object):

    def __init__(self, socket, size=0):
        self._socket = socket
        self._size = size
        self._offset = 0
        self._buffer = ""
        #self.add_channel()

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
        sock = self._socket
        sock.setblocking(False)
        channel = gobject.IOChannel(sock.fileno())
        channel.set_encoding(None)
        channel.set_buffered(False)
        channel.set_flags(channel.get_flags() | gobject.IO_FLAG_NONBLOCK)
        channel.add_watch(gobject.IO_HUP | gobject.IO_ERR, self.on_error)
        channel.add_watch(gobject.IO_IN | gobject.IO_PRI, self.on_stream_received)
        self.channel = channel

    def on_error(self, channel, condition):
        logger.error("DataBuffer %s" % condition)

    def on_stream_disconnected(self, channel, condition):
        pass


    def on_stream_received(self, channel, condition):
        logger.info("Received data to send")
        data = channel.read(1024)
        print data
        #self._session.send_chunk(data)
