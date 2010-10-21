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

import telepathy
import gobject
import dbus
import logging

from butterfly.connection import ButterflyConnection

__all__ = ['ButterflyConnectionManager']

logger = logging.getLogger('Butterfly.ConnectionManager')


class ButterflyConnectionManager(telepathy.server.ConnectionManager):
    """Butterfly connection manager
    
    Implements the org.freedesktop.Telepathy.ConnectionManager interface"""

    def __init__(self, shutdown_func=None):
        "Initializer"
        telepathy.server.ConnectionManager.__init__(self, 'butterfly')

        self._protos['msn'] = ButterflyConnection
        self._shutdown = shutdown_func
        logger.info("Connection manager created")

    def GetParameters(self, proto):
        "Returns the mandatory and optional parameters for the given proto."
        if proto not in self._protos:
            raise telepathy.NotImplemented('unknown protocol %s' % proto)

        result = []
        connection_class = self._protos[proto]
        secret_parameters = connection_class._secret_parameters
        mandatory_parameters = connection_class._mandatory_parameters
        optional_parameters = connection_class._optional_parameters
        default_parameters = connection_class._parameter_defaults

        for parameter_name, parameter_type in mandatory_parameters.iteritems():
            flags = telepathy.CONN_MGR_PARAM_FLAG_REQUIRED
            if parameter_name in secret_parameters:
                flags |= telepathy.CONN_MGR_PARAM_FLAG_SECRET
            param = (parameter_name, flags,  parameter_type, '')
            result.append(param)

        for parameter_name, parameter_type in optional_parameters.iteritems():
            flags = 0
            default = ''
            if parameter_name in secret_parameters:
                flags |= telepathy.CONN_MGR_PARAM_FLAG_SECRET
            if parameter_name in default_parameters:
                flags |= telepathy.CONN_MGR_PARAM_FLAG_HAS_DEFAULT
                default = default_parameters[parameter_name]
            param = (parameter_name, flags, parameter_type, default)
            result.append(param)

        return result

    def disconnected(self, conn):
        def shutdown():
            if self._shutdown is not None and \
                    len(self._connections) == 0:
                self._shutdown()
            return False
        result = telepathy.server.ConnectionManager.disconnected(self, conn)
        gobject.timeout_add_seconds(5, shutdown)

    def quit(self):
        "Terminates all connections. Must be called upon quit"
        conns = self._connections.copy()
        for connection in conns:
            connection.Disconnect()
        logger.info("Connection manager quitting")
