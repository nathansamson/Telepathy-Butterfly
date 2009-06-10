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

import base64

import dbus

import telepathy
import papyon
import papyon.event

__all__ = ['ButterflyStreamHandler']

StreamTypes = {
    "audio": 0,
    "video": 1
}

class ButterflyStreamHandler (
        telepathy.server.DBusProperties,
        telepathy.server.MediaStreamHandler,
        papyon.event.MediaStreamEventInterface):

    def __init__(self, connection, session, stream):
        self._id = session.next_stream_id
        path = session.get_stream_path(self._id)

        self._conn = connection
        self._session = session
        self._stream = stream
        self._interfaces = set()

        self._state = 1
        self._direction = telepathy.MEDIA_STREAM_DIRECTION_BIDIRECTIONAL
        if self._stream.controlling:
            self._pending_send = telepathy.MEDIA_STREAM_PENDING_REMOTE_SEND
        else:
            self._pending_send = telepathy.MEDIA_STREAM_PENDING_LOCAL_SEND
        self._type = StreamTypes[stream.name]

        self._remote_candidates = None
        self._remote_codecs = None

        telepathy.server.DBusProperties.__init__(self)
        telepathy.server.MediaStreamHandler.__init__(self, connection._name, path)
        papyon.event.MediaStreamEventInterface.__init__(self, stream)

        self._implement_property_get(telepathy.interfaces.MEDIA_STREAM_HANDLER,
            {'CreatedLocally': lambda: self._stream.controlling,
             'NATTraversal': lambda: self.nat_traversal,
             'STUNServers': lambda: self.stun_servers,
             'RelayInfo': lambda: self.relay_info})

    @property
    def id(self):
        return self._id

    @property
    def type(self):
        return self._type

    @property
    def direction(self):
        return self._direction

    @property
    def pending_send(self):
        return self._pending_send

    @property
    def state(self):
        return self._state

    @property
    def nat_traversal(self):
        return "wlm-2009"

    @property
    def relay_info(self):
        return dbus.Array([], signature="aa{sv}")

    @property
    def stun_servers(self):
        return [("64.14.48.28", dbus.UInt32(3478))]

    def set_direction(self, direction, pending_send):
        self._direction = direction
        self._pending_send = pending_send

    def Ready(self, codecs):
        print "StreamReady : ", codecs
        if self._remote_candidates is not None:
            self.SetRemoteCandidateList(self._remote_candidates)
        if self._remote_codecs is not None:
            self.SetRemoteCodecs(self._remote_codecs)
        self.SetStreamPlaying(True)
        self.SetStreamSending(True)
        if self._stream.controlling:
            self.SetLocalCodecs(codecs)
        #if self._session is None:
        #    self._session = ButterflyWebcamSession(self._conn, self._handle.contact)

    def StreamState(self, state):
        print "StreamState : ", state
        self._state = state
        self._session.on_stream_state_changed(self.id, state)

    def Error(self, code, message):
        print "StreamError - %i - %s" % (code, message)

    def NewNativeCandidate(self, id, transports):
        candidates = []
        for transport in transports:
            candidates.append(self.convert_tp_candidate(id, transport))
        for candidate in candidates:
            self._stream.new_local_candidate(candidate)

    def NativeCandidatesPrepared(self):
        self._stream.local_candidates_prepared()

    def NewActiveCandidatePair(self, native_id, remote_id):
        print "New active candidate pair %s %s" % (native_id, remote_id)
        self._stream.new_active_candidate_pair(native_id, remote_id)

    def SetLocalCodecs(self, codecs):
        print "Set Local Codecs"
        list = self.convert_tp_codecs(codecs)
        self._stream.set_local_codecs(list)

    def SupportedCodecs(self, codecs):
        print "SupportedCodecs: ", codecs
        list = self.convert_tp_codecs(codecs)
        self._stream.set_local_codecs(list)

    def CodecChoice(self, codec_id):
        print "CodecChoice :", codec_id

    def CodecsUpdated(self, codecs):
        print "CodecsUpdated: ", codecs

    #papyon.event.MediaStreamEventInterface
    def on_remote_candidates_received(self, candidates):
        list = self.convert_ice_candidates(candidates)
        self._remote_candidates = list
        if self._stream.controlling:
            self.SetRemoteCandidateList(list)

    #papyon.event.MediaStreamEventInterface
    def on_remote_codecs_received(self, codecs):
        list = self.convert_sdp_codecs(codecs)
        self._remote_codecs = list
        if self._stream.controlling:
            self.SetRemoteCodecs(list)

    #papyon.event.MediaStreamEventInterface
    def on_stream_closed(self):
        print "Stream Closed"
        self.Close()

    def convert_sdp_codecs(self, codecs):
        list = []
        for codec in codecs:
            list.append(self.convert_sdp_codec(codec))
        return list

    def convert_sdp_codec(self, codec):
        return (codec.payload, codec.encoding, self._type, codec.clockrate, 0,
                codec.params)

    def convert_tp_codecs(self, codecs):
        list = []
        for codec in codecs:
            c = papyon.sip.sdp.SDPCodec(codec[0], codec[1], codec[3], codec[5])
            list.append(c)
        return list

    def convert_ice_candidates(self, candidates):
        array = {}
        for c in candidates:
            if c.transport.lower() == "udp":
                proto = 0
            else:
                proto = 1
            if c.type == "host":
                type = 0
            elif c.type == "srflx" or c.type == "prflx":
                type = 1
            elif c.type == "relay":
                type = 2
            else:
                print "TYPE", c.type
                type = 0
            while True:
                try:
                    base64.b64decode(c.username)
                    break
                except:
                    c.username += "="
            while True:
                try:
                    base64.b64decode(c.password)
                    break
                except:
                    c.password += "="
            preference = float(c.priority) / 65536.0
            transport = (c.component_id, c.ip, c.port, proto, "RTP", "AVP",
                    preference, type, c.username, c.password)
            array.setdefault(c.foundation, []).append(transport)
        return array.items()

    def convert_tp_candidate(self, id, transport):
        proto = "UDP"
        priority = int(transport[6] * 65536)
        if transport[7] == 0:
            type = "host"
            addr = None
            port = None
        elif transport[7] == 1:
            type = "srflx"
            addr = "192.168.1.102"
            port = int(transport[2])
        elif transport[7] == 2:
            type = "relay"
            addr = None
            port = None
        return papyon.sip.ice.ICECandidate(19, id, int(transport[0]), proto, priority,
                transport[8], transport[9], type, transport[1],
                int(transport[2]), addr, port)
