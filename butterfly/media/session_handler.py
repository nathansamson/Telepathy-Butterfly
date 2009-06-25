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
from papyon.sip.media import MediaSessionType

__all__ = ['ButterflySessionHandler']

class ButterflySessionHandler (telepathy.server.MediaSessionHandler):
    def __init__(self, connection, channel, session):
        self._conn = connection
        self._session = session
        self._stream_handlers = {}
        self._next_stream_id = 0
        self._type = session.type
        self._subtype = self._type is MediaSessionType.WEBCAM and "msn" or "rtp"
        self._ready = False
        self._pending_handlers = []

        path = channel._object_path + "/sessionhandler1"
        telepathy.server.MediaSessionHandler.__init__(self, connection._name, path)

    @property
    def next_stream_id(self):
        self._next_stream_id += 1
        return self._next_stream_id

    @property
    def subtype(self):
        return self._subtype

    @property
    def type(self):
        return self._type

    def get_stream_path(self, id):
        return "%s/stream%d" % (self._object_path, id)

    def Ready(self):
        print "Session ready", self._pending_handlers
        self._ready = True
        for handler in self._pending_handlers:
            self.NewStream(handler=handler)
        self._pending_handlers = []

    def Error(self, code, message):
        print "Session error", code, message

    def GetStream(self, id):
        return self._stream_handlers[id]

    def FindStream(self, stream):
        ret = None
        for handler in self.ListStreams():
            if handler.stream == stream:
                ret = handler
        return ret

    def HasStreams(self):
        return bool(self._stream_handlers)

    def ListStreams(self):
        return self._stream_handlers.values()

    def CreateStream(self, type, direction):
        if type == telepathy.MEDIA_STREAM_TYPE_AUDIO:
            media_type = "audio"
        else:
            media_type = "video"
        stream = self._session.create_stream(media_type, direction, True)
        handler = self.HandleStream(stream)
        self._session.add_pending_stream(stream)
        return handler

    def HandleStream(self, stream):
        handler = ButterflyStreamHandler(self._conn, self, stream)
        print "Session add stream handler", handler.id
        self._stream_handlers[handler.id] = handler
        return handler

    def NewStream(self, stream=None, handler=None):
        if handler is None:
            handler = self.FindStream(stream)
        if not self._ready:
            self._pending_handlers.append(handler)
            return handler
        print "Session new stream handler", handler.id
        path = self.get_stream_path(handler.id)
        self.NewStreamHandler(path, handler.id, handler.type, handler.direction)
        return handler

    def RemoveStream(self, id):
        print "Session remove stream handler", id
        if id in self._stream_handlers:
            handler = self._stream_handlers[id]
            handler.remove_from_connection()
            del self._stream_handlers[id]
