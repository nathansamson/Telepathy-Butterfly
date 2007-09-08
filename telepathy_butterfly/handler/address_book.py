# telepathy-butterfly - an MSN connection manager for Telepathy
#
# Copyright (C) 2007 Johann Prieur <johann.prieur@gmail.com>
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

import weakref
import logging

import pymsn
import pymsn.event
import telepathy
import gobject

__all__ = ['ButterflyAddressBookEventsHandler']

logger = logging.getLogger('telepathy-butterfly:address_book')

class ButterflyAddressBookEventsHandler(pymsn.event.AddressBookEventInterface):
    def __init__(self, client, telepathy_connection):
        self._telepathy_connection = weakref.proxy(telepathy_connection)
        pymsn.event.AddressBookEventInterface.__init__(self, client)

    def on_addressbook_new_pending_contact(self, pending_contact):
        pass

    def on_addressbook_messenger_contact_added(self, contact):
        pass

    def on_addressbook_contact_deleted(self, contact):
        pass

    def on_addressbook_contact_blocked(self, contact):
        pass

    def on_addressbook_contact_unblocked(self, contact):
        pass

    def on_addressbook_group_added(self, group):
        channel = self._telepathy_connection._channel_manager.\
            channel_for_list(self._telepathy_connection._handle_manager.\
                                 handle_for_group(group.name))
        channel._release_pendings()

    def on_addressbook_group_deleted(self, group):
        channel = self._telepathy_connection._channel_manager.\
            channel_for_list(self._telepathy_connection._handle_manager.\
                                 handle_for_group(group.name))
        channel._close()

    def on_addressbook_group_renamed(self, group):
        pass

    def on_addressbook_group_contact_added(self, group, contact):
        added = set()

        full_account = "/".join([contact.account, str(contact.network_id)])
        handle = self._telepathy_connection._handle_manager.\
            handle_for_contact(full_account)
        added.add(handle)
        
        channel = self._telepathy_connection._channel_manager.\
            channel_for_list(self._telepathy_connection._handle_manager.\
                                 handle_for_group(group.name))

        channel.MembersChanged('', added, (), (), (), 0,
                               telepathy.CHANNEL_GROUP_CHANGE_REASON_NONE)
        
        logger.debug("contact %s added to group %s" % (full_account,
                                                            group.name))

    def on_addressbook_group_contact_deleted(self, group, contact):
        removed = set()

        full_account = "/".join([contact.account, str(contact.network_id)])
        handle = self._telepathy_connection._handle_manager.\
            handle_for_contact(full_account)
        removed.add(handle)
        
        channel = self._telepathy_connection._channel_manager.\
            channel_for_list(self._telepathy_connection._handle_manager.\
                                 handle_for_group(group.name))

        channel.MembersChanged('', (), removed, (), (), 0,
                               telepathy.CHANNEL_GROUP_CHANGE_REASON_NONE)
        
        logger.debug("contact %s removed from group %s" % (full_account,
                                                                group.name))
