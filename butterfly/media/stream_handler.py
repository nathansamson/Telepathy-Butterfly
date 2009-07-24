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
        self._direction = 3
        self._pending_send = 1
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

    def Ready(self, Codecs):
        if self._remote_candidates is not None:
            self.SetRemoteCandidateList(self._remote_candidates)
        if self._remote_codecs is not None:
            self.SetRemoteCodecs(self._remote_codecs)
        self.SetLocalCodecs(codecs)
        #if self._session is None:
        #    self._session = ButterflyWebcamSession(self._conn, self._handle.contact)

    def StreamState(self, State):
        print "StreamState : ", State

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
        self._stream.new_active_candidate_pair(native_id, remote_id)

    def SetLocalCodecs(self, Codecs):
        list = self.convert_tp_codecs(codecs)
        self._stream.set_local_codecs(list)

    def SupportedCodecs(self, Codecs):
        print "SupportedCodecs: ", Codecs

    def CodecChoice(self, Codec_ID):
        print "CodecChoice :", Codec_ID

    def CodecsUpdated(self, Codecs):
        print "CodecsUpdated: ", Codecs

    #papyon.event.MediaStreamEventInterface
    def on_remote_candidates_received(self, candidates):
        print "REMOTE CANDIDATES"
        list = self.convert_ice_candidates(candidates)
        self._remote_candidates = list

    #papyon.event.MediaStreamEventInterface
    def on_remote_codecs_received(self, codecs):
        list = []
        for codec in codecs:
            list.append(self.convert_sdp_codec(codec))
        self._remote_codecs = list

    #papyon.event.MediaStreamEventInterface
    def on_stream_direction_changed(self):
        self._session.StreamDirectionChanged(self.id, self.direction,
                self.flag_send)

    #papyon.event.MediaStreamEventInterface
    def on_stream_closed(self):
        self.Close()

    def convert_sdp_codec(self, codec):
        return (codec.payload, codec.encoding, self._type, codec.bitrate, 1, {})

    def convert_tp_codecs(self, codecs):
        list = []
        for codec in codecs:
            c = papyon.sip.sdp.SDPCodec(codec[0], codec[1], codec[3])
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
        type = "host"
        return papyon.sip.ice.ICECandidate(19, id, int(transport[0]), proto, priority,
                transport[8], transport[9], type, transport[1],
                int(transport[2]))
