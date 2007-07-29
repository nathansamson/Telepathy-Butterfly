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

__all__ = ['ButterflyConnectionAliasing']

logger = logging.getLogger('telepathy-butterfly:aliasing')

class ButterflyConnectionAliasing(
        telepathy.server.ConnectionInterfaceAliasing):

    def RequestAliases(self, contacts):
        result = []
        for handle_id in contacts:
            handle = self._handle_manager.handle_for_handle_id(
                    telepathy.CONNECTION_HANDLE_TYPE_CONTACT, handle_id)
            if handle == self.GetSelfHandle():
                display_name = self._pymsn_client.profile.display_name
                if display_name == "":
                    display_name = handle.get_name().split('@', 1)[0]
                    display_name = display_name.replace("_", " ")
                result.append(unicode(display_name, 'utf-8'))
            else:
                contact = self._pymsn_client.address_book.contacts.\
                        search_by_account(handle.get_name())[0]
                result.append(unicode(contact.display_name, 'utf-8'))
        return result
            
    def SetAliases(self, aliases):
        for handle_id, alias in aliases.iteritems():
            handle = self._handle_manager.handle_for_handle_id(
                    telepathy.CONNECTION_HANDLE_TYPE_CONTACT, handle_id)
            if handle != self.GetSelfHandle():
                raise telepathy.PermissionDenied("MSN doesn't allow setting"\
                        "aliases for contacts")
            self._pymsn_client.profile.display_name = alias.encode('utf-8')

    def contact_alias_changed(self, contact):
        handle = self._handle_manager.handle_for_contact(contact.account)
        alias = unicode(contact.display_name, 'utf-8')
        self.AliasesChanged(((handle, alias), ))

