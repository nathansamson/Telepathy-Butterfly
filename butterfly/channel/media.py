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
from butterfly.media import ButterflySessionHandler

__all__ = ['ButterflyMediaChannel']

logger = logging.getLogger('Butterfly.MediaChannel')


class ButterflyMediaChannel(
        telepathy.server.ChannelTypeStreamedMedia,
        telepathy.server.ChannelInterfaceCallState,
        telepathy.server.ChannelInterfaceGroup,
        telepathy.server.ChannelInterfaceMediaSignalling,
        papyon.event.CallEventInterface,
        papyon.event.MediaSessionEventInterface):

    def __init__(self, conn, manager, call, handle, props):
        telepathy.server.ChannelTypeStreamedMedia.__init__(self, conn, manager, props)
        telepathy.server.ChannelInterfaceCallState.__init__(self)
        telepathy.server.ChannelInterfaceGroup.__init__(self)
        telepathy.server.ChannelInterfaceMediaSignalling.__init__(self)
        papyon.event.CallEventInterface.__init__(self, call)
        papyon.event.MediaSessionEventInterface.__init__(self, call.media_session)

        self._call = call
        self._handle = handle

        self._session_handler = ButterflySessionHandler(self._conn, self, call)
        self.NewSessionHandler(self._session_handler, self._session_handler.type)

        self.GroupFlagsChanged(telepathy.CHANNEL_GROUP_FLAG_CAN_REMOVE, 0)
        self.GroupFlagsChanged(telepathy.CHANNEL_GROUP_FLAG_MESSAGE_REMOVE, 0)
        self.GroupFlagsChanged(telepathy.CHANNEL_GROUP_FLAG_MESSAGE_REJECT, 0)
        self.__add_initial_participants()

    def Close(self):
        print "Channel closed by client"
        self._call.end()

    def GetSessionHandlers(self):
        return [(self._session_handler, self._session_handler.type)]

    def ListStreams(self):
        print "ListStreams"
        streams = dbus.Array([], signature="a(uuuuuu)")
        for handler in self._session_handler.ListStreams():
            streams.append((handler.id, self._handle, handler.type,
                handler.state, handler.direction, handler.pending_send))
        return streams

    def RequestStreams(self, handle, types):
        print "RequestStreams %r %r %r" % (handle, self._handle, types)
        if self._handle.get_id() == 0:
            self._handle = self._conn.handle(telepathy.HANDLE_TYPE_CONTACT, handle)

        streams = dbus.Array([], signature="a(uuuuuu)")
        for type in types:
            handler = self._session_handler.CreateStream(type)
            streams.append((handler.id, self._handle, handler.type,
                handler.state, handler.direction, handler.pending_send))
        return streams

    def RequestStreamDirection(self, id, direction):
        print "RequestStreamDirection %r %r" % (id, direction)
        self._session_handler.GetStream(id).direction = direction

    def RemoveStreams(self, streams):
        print "RemoveStreams %r" % streams
        for id in streams:
            self._session_handler.RemoveStream(id)
        if not self._session_handler.HasStreams():
            self.Close()

    def GetSelfHandle(self):
        return self._conn.GetSelfHandle()

    def GetLocalPendingMembersWithInfo(self):
        info = []
        for member in self._local_pending:
            info.append((member, self._handle, 0, ''))
        return info

    def AddMembers(self, handles, message):
        print "Add members", handles, message
        for handle in handles:
            print handle, self.GetSelfHandle()
            if handle == int(self.GetSelfHandle()):
                print "That's me"
                if self.GetSelfHandle() in self._local_pending:
                    print "Is local pending"
                    self._call.accept()
            else:
                print "Not me", self.GetSelfHandle()

    def RemoveMembers(self, handles, message):
        print "Remove members", handles, message

    def RemoveMembersWithReason(self, handles, message, reason):
        print "Remove members", handles, message, reason

    #papyon.event.call.CallEventInterface
    def on_call_incoming(self):
        self._call.accept()

    #papyon.event.call.CallEventInterface
    def on_call_ringing(self):
        pass

    #papyon.event.call.CallEventInterface
    def on_call_accepted(self):
        self.on_call_answered(3, 0)

    #papyon.event.call.CallEventInterface
    def on_call_rejected(self, response):
        self.on_call_answered(0, 0)

    def on_call_answered(self, direction, pending_send):
        for handler in self._session_handler.ListStreams():
            handler.set_direction(direction, pending_send)
            self.StreamDirectionChanged(handler.id, direction, pending_send)

    #papyon.event.call.CallEventInterface
    def on_call_ended(self):
        print "Call ended"
        telepathy.server.ChannelTypeStreamedMedia.Close(self)
        self.remove_from_connection()

    #papyon.event.media.MediaSessionEventInterface
    def on_stream_created(self, stream):
        print "Media Stream created"
        handler = self._session_handler.AddStream(stream)
        self.StreamAdded(handler.id, self._handle, handler.type)
        self.StreamDirectionChanged(handler.id, handler.direction,
                handler.pending_send)

    #papyon.event.media.MediaSessionEventInterface
    def on_stream_removed(self, stream):
        print "Media Stream removed"
        id = self._session_handler.FindStream(stream)
        self._session_handler.RemoveStream(id)

    def on_stream_state_changed(self, id, state):
        self.StreamStateChanged(id, state)

    @async
    def __add_initial_participants(self):
        added = []
        local_pending = []
        remote_pending = []

        if False:
            remote_pending.append(self._handle)
            added.append(self._conn.GetSelfHandle())
        else:
            local_pending.append(self._conn.GetSelfHandle())
            added.append(self._handle)

        self.MembersChanged('', added, [], local_pending, remote_pending,
                0, telepathy.CHANNEL_GROUP_CHANGE_REASON_NONE)
