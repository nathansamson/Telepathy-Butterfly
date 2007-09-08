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
import pymsn
import logging

from pymsn.service.description.AB.constants import \
    ContactGeneral, ContactAnnotations

__all__ = ['ButterflyConnectionAliasing']

logger = logging.getLogger('telepathy-butterfly:aliasing')

class ButterflyConnectionAliasing(
        telepathy.server.ConnectionInterfaceAliasing):

    def RequestAliases(self, contacts):
        result = []
        for handle_id in contacts:
            handle = self._handle_manager.handle_for_handle_id(
                    telepathy.HANDLE_TYPE_CONTACT, handle_id)
            if handle == self.GetSelfHandle():
                display_name = self._pymsn_client.profile.display_name
                if display_name == "":
                    display_name = handle.get_name().split('@', 1)[0]
                    display_name = display_name.replace("_", " ")
                result.append(display_name.encode('utf-8'))
            else:
                contact = self._contact_for_handle(handle)
                alias = contact.infos.get(ContactGeneral.ANNOTATIONS, {}).\
                    get(ContactAnnotations.NICKNAME, "").encode('utf-8')
                if alias == "":
                    alias = contact.display_name.encode('utf-8')
                result.append(alias)
        return result
            
    def SetAliases(self, aliases):
        for handle_id, alias in aliases.iteritems():
            handle = self._handle_manager.handle_for_handle_id(
                    telepathy.HANDLE_TYPE_CONTACT, handle_id)
            if handle != self.GetSelfHandle():
                contact = self._contact_for_handle(handle)
                infos = { ContactGeneral.ANNOTATIONS : \
                     { ContactAnnotations.NICKNAME : alias.encode('utf-8')}}
                self._pymsn_client.address_book.\
                    update_contact_infos(contact, infos)
            else:
                self._pymsn_client.profile.display_name = alias.encode('utf-8')

    def contact_alias_changed(self, contact):
        handle = self._handle_for_contact(contact)

        alias = contact.infos.get(ContactGeneral.ANNOTATIONS, {}).\
            get(ContactAnnotations.NICKNAME, "").encode('utf-8')
        if alias == "":
            alias = contact.display_name.encode('utf-8')

        self.AliasesChanged(((handle, alias), ))

