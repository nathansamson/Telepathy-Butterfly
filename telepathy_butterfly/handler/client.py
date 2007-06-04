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

import pymsn
import pymsn.event
import telepathy

__all__ = ['ButterflyClientEventsHandler']

class ButterflyClientEventsHandler(pymsn.event.ClientEventInterface):
    def __init__(self, client, telepathy_connection):
        self._telepathy_connection = telepathy_connection
        pymsn.event.ClientEventInterface.__init__(self, client)

    def on_client_state_changed(self, state):
        if state == pymsn.event.ClientState.CONNECTING:
            self._telepathy_connection.StatusChanged(
                    telepathy.CONNECTION_STATUS_CONNECTING,
                    telepathy.CONNECTION_STATUS_REASON_REQUESTED)
        elif state == pymsn.event.ClientState.SYNCHRONIZED:
            self._telepathy_connection._create_contact_list()
        elif state == pymsn.event.ClientState.OPEN:
            self._telepathy_connection.StatusChanged(
                    telepathy.CONNECTION_STATUS_CONNECTED,
                    telepathy.CONNECTION_STATUS_REASON_REQUESTED)
            self._client.profile.presence = \
                    self._telepathy_connection._initial_presence
            self._client.profile.personal_message = \
                    self._telepathy_connection._initial_personal_message
        elif state == pymsn.event.ClientState.CLOSED:
            self._telepathy_connection.StatusChanged(
                    telepathy.CONNECTION_STATUS_DISCONNECTED,
                    telepathy.CONNECTION_STATUS_REASON_REQUESTED)

    def on_client_error(self, type, error):
        if type == pymsn.event.ClientErrorType.NETWORK:
            self._telepathy_connection.StatusChanged(
                    telepathy.CONNECTION_STATUS_DISCONNECTED,
                    telepathy.CONNECTION_STATUS_REASON_NETWORK_ERROR)
        elif type == pymsn.event.ClientErrorType.AUTHENTICATION:
            self._telepathy_connection.StatusChanged(
                    telepathy.CONNECTION_STATUS_DISCONNECTED,
                    telepathy.CONNECTION_STATUS_REASON_AUTHENTICATION_FAILED)
        else:
            self._telepathy_connection.StatusChanged(
                    telepathy.CONNECTION_STATUS_DISCONNECTED,
                    telepathy.CONNECTION_STATUS_REASON_NONE_SPECIFIED)

