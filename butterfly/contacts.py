# telepathy-butterfly - an MSN connection manager for Telepathy
#
# Copyright (C) 2009 Olivier Le Thanh Duong <olivier@lethanh.be>
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
import time

import telepathy
import telepathy.constants
import telepathy.errors
import pymsn

from butterfly.handle import ButterflyHandleFactory
from butterfly.util.decorator import async

__all__ = ['ButterflyContacts']

logger = logging.getLogger('Butterfly.Contacts')



class ButterflyContacts(
        telepathy.server.ConnectionInterfaceContacts,
        pymsn.event.ContactEventInterface,
        pymsn.event.ProfileEventInterface):

    attributes = {
        'org.freedesktop.Telepathy.Connection' : 'org.freedesktop.Telepathy.Connection/contact-id',
        'org.freedesktop.Telepathy.Connection.Interface.SimplePresence' : 'org.freedesktop.Telepathy.Connection.Interface.SimplePresence/presence',
        'org.freedesktop.Telepathy.Connection.Interface.Aliasing' : 'org.freedesktop.Telepathy.Connection.Interface.Aliasing/alias',
        'org.freedesktop.Telepathy.Connection.Interface.Avatars' : 'org.freedesktop.Telepathy.Connection.Interface.Avatars/token'
        }

    def __init__(self):
        telepathy.server.ConnectionInterfaceContacts.__init__(self)
        pymsn.event.ContactEventInterface.__init__(self, self.msn_client)
        pymsn.event.ProfileEventInterface.__init__(self, self.msn_client)

        dbus_interface = 'org.freedesktop.Telepathy.Connection.Interface.Contacts'

        self._implement_property_get(dbus_interface, \
                {'ContactAttributeInterfaces' : self.get_contact_attribute_interfaces})

    def GetContactAttributes(self, handles, interfaces, hold):
        for interface in interfaces:
            if interface not in self.attributes.keys():
                raise telepathy.errors.InvalidArgument
        ret = {}

        self.check_connected()
        handle_type = telepathy.HANDLE_TYPE_CONTACT
        self.check_handle_type(handle_type)

        for handle in handles:
            self.check_handle(handle_type, handle)

        # Attributes from the interface org.freedesktop.Telepathy.Connection
        # are always returned, and need not be requested explicitly.
        interface = 'org.freedesktop.Telepathy.Connection'
        if interface in interfaces :
            interfaces.remove(interface)
        interface_attribute = self.attributes[interface]

        for handle in handles:
            ret[handle] = {}
            ret[handle][interface_attribute] = self._handles[handle_type, handle].get_name()

            # Hold handle if needed
            # FIXME : We need the sender argument
            #if hold:
                #self.add_client_handle(handle, sender)

        interface = 'org.freedesktop.Telepathy.Connection.Interface.SimplePresence'
        if interface in interfaces :
            interface_attribute = self.attributes[interface]
            presences = self.get_simple_presences(handles)

            for handle, presence in presences.items():
                ret[handle.id][interface_attribute] = presence

        interface = 'org.freedesktop.Telepathy.Connection.Interface.Aliasing'
        if interface in interfaces :
            interface_attribute = self.attributes[interface]
            for handle in handles:
                ret[handle][interface_attribute] = self._get_alias(handle)

        interface = 'org.freedesktop.Telepathy.Connection.Interface.Avatars'
        if interface in interfaces :
            interface_attribute = self.attributes[interface]
            tokens = self.GetKnownAvatarTokens(handles)

            for handle, token in tokens.items():
                ret[handle.id][interface_attribute] = token

        return ret

    def get_contact_attribute_interfaces(self):
        return self.attributes.keys()
