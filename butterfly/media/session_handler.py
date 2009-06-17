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
    def __init__(self, connection, channel, call):
        self._conn = connection
        self._channel = channel
        self._call = call
        self._stream_handlers = {}
        self._next_stream_id = 0
        self._type = call.media_session.type
        self._subtype = self._type is MediaSessionType.WEBCAM and "msn" or "rtp"

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
        print "Session ready"
        for handler in self._stream_handlers.values():
            path = self.get_stream_path(handler.id)
            self.NewStreamHandler(path, handler.id, handler.type,
                    handler.direction)
        #self._call.invite()

    def Error(self, code, message):
        print "Session error", code, message

    def GetStream(self, id):
        return self._stream_handlers[id]

    def FindStream(self, stream):
        id = None
        for handler in self.ListStreams():
            if handler._stream == stream:
                id = handler.id
        return id

    def HasStreams(self):
        return bool(self._stream_handlers)

    def ListStreams(self):
        return self._stream_handlers.values()

    def AddStream(self, stream):
        handler = ButterflyStreamHandler(self._conn, self, stream)
        self._stream_handlers[handler.id] = handler
        path = self.get_stream_path(handler.id)
        self.NewStreamHandler(path, handler.id, handler.type, handler.direction)
        return handler

    def CreateStream(self, type, direction):
        if type == telepathy.MEDIA_STREAM_TYPE_AUDIO:
            media_type = "audio"
        else:
            media_type = "video"
        stream = self._call.media_session.add_stream(media_type, direction, True)
        handler = ButterflyStreamHandler(self._conn, self, stream)
        return handler

    def RemoveStream(self, id):
        del self._stream_handlers[id]

    def on_stream_state_changed(self, id, state):
        self._channel.on_stream_state_changed(id, state)
