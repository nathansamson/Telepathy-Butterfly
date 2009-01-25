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
import telepathy.errors
import pymsn
import dbus

__all__ = ['ButterflyContacts']

logger = logging.getLogger('Butterfly.Contacts')

class ButterflyContacts(
        telepathy.server.ConnectionInterfaceContacts,
        pymsn.event.ContactEventInterface,
        pymsn.event.ProfileEventInterface):

    attributes = {
        telepathy.CONNECTION : 'contact-id',
        telepathy.CONNECTION_INTERFACE_SIMPLE_PRESENCE : 'presence',
        telepathy.CONNECTION_INTERFACE_ALIASING : 'alias',
        telepathy.CONNECTION_INTERFACE_AVATARS : 'token'
        }

    def __init__(self):
        telepathy.server.ConnectionInterfaceContacts.__init__(self)
        pymsn.event.ContactEventInterface.__init__(self, self.msn_client)
        pymsn.event.ProfileEventInterface.__init__(self, self.msn_client)

        dbus_interface = telepathy.CONNECTION_INTERFACE_CONTACTS

        self._implement_property_get(dbus_interface, \
                {'ContactAttributeInterfaces' : self.get_contact_attribute_interfaces})

    # Overwrite the dbus attribute to get the sender argument
    @dbus.service.method(telepathy.CONNECTION_INTERFACE_CONTACTS, in_signature='auasb',
                            out_signature='a{ua{sv}}', sender_keyword='sender')
    def GetContactAttributes(self, handles, interfaces, hold, sender):
        for interface in interfaces:
            if interface not in self.attributes:
                raise telepathy.errors.InvalidArgument(
                    'Interface %s is not supported by GetContactAttributes' % (interface))

        handle_type = telepathy.HANDLE_TYPE_CONTACT
        ret = {}
        for handle in handles:
            ret[handle] = {}

        #InspectHandle already checks we're connected, the handles and handle type.

        #Hold handles if needed
        if hold:
            self.HoldHandles(handle_type, handles, sender)

        # Attributes from the interface org.freedesktop.Telepathy.Connection
        # are always returned, and need not be requested explicitly.
        interface = telepathy.CONNECTION
        interface_attribute = interface + '/' + self.attributes[interface]
        ids = self.InspectHandles(handle_type, handles)
        for handle, id in zip(handles, ids):
            ret[handle][interface_attribute] = id

        interface = telepathy.CONNECTION_INTERFACE_SIMPLE_PRESENCE
        if interface in interfaces:
            interface_attribute = interface + '/' + self.attributes[interface]
            presences = self.GetPresences(handles)
            for handle, presence in presences.items():
                ret[handle.id][interface_attribute] = presence

        interface = telepathy.CONNECTION_INTERFACE_ALIASING
        if interface in interfaces:
            interface_attribute = interface + '/' + self.attributes[interface]
            aliases = self.GetAliases(handles)
            for handle, alias in zip(handles, aliases):
                ret[handle][interface_attribute] = alias

        interface = telepathy.CONNECTION_INTERFACE_AVATARS
        if interface in interfaces:
            interface_attribute = interface + '/' + self.attributes[interface]
            tokens = self.GetKnownAvatarTokens(handles)
            for handle, token in tokens.items():
                ret[handle.id][interface_attribute] = token

        return ret

    def get_contact_attribute_interfaces(self):
        return self.attributes.keys()
