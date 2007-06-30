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

from telepathy_butterfly.connection import ButterflyConnection

__all__ = ['ButterflyConnectionManager']

logger = logging.getLogger('telepathy-butterfly:connection_manager')


class ButterflyConnectionManager(telepathy.server.ConnectionManager):
    """Butterfly connection manager
    
    Implements the org.freedesktop.Telepathy.ConnectionManager interface"""

    def __init__(self):
        "Initializer"
        try:
            telepathy.server.ConnectionManager.__init__(self, 'butterfly')
        except TypeError: # old versions of tp-python
            telepathy.server.ConnectionManager.__init__(self)

        self._protos['msn'] = ButterflyConnection
        logger.info("Connection manager created")

    def GetParameters(self, proto):
        "Returns the mandatory and optional parameters for the given proto."
        if proto not in self._protos:
            raise telepathy.NotImplemented('unknown protocol %s' % proto)
        
        result = []
        connection_class = self._protos[proto]
        mandatory_parameters = connection_class._mandatory_parameters
        optional_parameters = connection_class._optional_parameters
        default_parameters = connection_class._parameter_defaults

        for parameter_name, parameter_type in mandatory_parameters.iteritems():
            param = (parameter_name,
                    telepathy.CONN_MGR_PARAM_FLAG_REQUIRED,
                    parameter_type,
                    '')
            result.append(param)

        for parameter_name, parameter_type in optional_parameters.iteritems():
            if parameter_name in default_parameters:
                param = (parameter_name,
                        telepathy.CONN_MGR_PARAM_FLAG_HAS_DEFAULT,
                        parameter_name,
                        default_parameters[parameter_name])
            else:
                param = (parameter_name, 0, parameter_name, '')
            result.append(param)

        return result

    def quit(self):
        """
        Terminates all connections. Must be called upon quit
        """
        for connection in self._connections:
            connection.Disconnect()
