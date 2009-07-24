# telepathy-butterfly - an MSN connection manager for Telepathy
#
# Copyright (C) 2009 Collabora Ltd.
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
import papyon.event

from butterfly.util.decorator import async
from butterfly.handle import ButterflyHandleFactory
from butterfly.media import ButterflyStreamHandler

__all__ = ['ButterflySessionHandler']

class ButterflySessionHandler (telepathy.server.MediaSessionHandler):
    def __init__(self, connection, channel, session, handle):
        self._conn = connection
        self._session = session
        self._handle = handle
        self._stream_handlers = {}
        self._next_stream_id = 0

        path = channel._object_path + "/sessionhandler1"
        telepathy.server.MediaSessionHandler.__init__(self, connection._name, path)

    @property
    def next_stream_id(self):
        self._next_stream_id += 1
        return self._next_stream_id

    @property
    def type(self):
        return "rtp"

    def get_stream_path(self, id):
        return "%s/stream%d" % (self._object_path, id)

    def Ready(self):
        print "Session ready"
        for handler in self._stream_handlers.values():
            path = self.get_stream_path(handler.id)
            self.NewStreamHandler(path, handler.id, handler.type,
                    handler.direction)

    def Error(self, code, message):
        print "Session error", code, message

    def GetStream(self, id):
        return self._stream_handlers[id]

    def ListStreams(self):
        return self._stream_handlers.values()

    def AddStream(self, stream):
        handler = ButterflyStreamHandler(self._conn, self, stream)
        self._stream_handlers[handler.id] = handler
        path = self.get_stream_path(handler.id)
        self.NewStreamHandler(path, handler.id, handler.type, handler.direction)
        return handler

    def CreateStream(self, type):
        if type == 0:
            media_type = "audio"
        else:
            media_type = "video"
        stream = self._session.create_stream(media_type)
        handler = ButterflyStreamHandler(self._conn, self, stream)
        return handler

    def RemoveStream(self, id):
        pass
