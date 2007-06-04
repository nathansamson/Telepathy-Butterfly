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
import gobject

__all__ = ['ButterflySubscribeListChannel', 'ButterflyPublishListChannel']

class ButterflyListChannel(
        telepathy.server.ChannelTypeContactList,
        telepathy.server.ChannelInterfaceGroup):

    def __init__(self, connection, handle):
        telepathy.server.ChannelTypeContactList.__init__(self,
                connection, handle)
        telepathy.server.ChannelInterfaceGroup.__init__(self)
        gobject.idle_add(self.__populate, connection)

    def __populate(self, connection):
        for contact in connection._pymsn_client.address_book.contacts:
            account = contact.account
            handle = connection._handle_manager.handle_for_contact(account)
            self.contact_added(handle, contact)
        return False

    def contact_added(self, handle, contact):
        pass



class ButterflySubscribeListChannel(ButterflyListChannel):

    def __init__(self, connection, handle):
        ButterflyListChannel.__init__(self, connection, handle)
        self.GroupFlagsChanged(0, 0) # no contact Management for now

    def contact_added(self, handle, contact):
        added = set()
        if contact.is_member(pymsn.Membership.FORWARD):
            added.add(handle)

        if added:
            self.MembersChanged('', added, (), (), (), 0,
                                telepathy.CHANNEL_GROUP_CHANGE_REASON_NONE)

class ButterflyPublishListChannel(ButterflyListChannel):

    def __init__(self, connection, handle):
        ButterflyListChannel.__init__(self, connection, handle)
        self.GroupFlagsChanged(0, 0) # no contact Management for now

    def contact_added(self, handle, contact):
        added = set()
        local_pending = set()

        if contact.is_member(pymsn.Membership.REVERSE):
            added.add(handle)

        if contact.is_member(pymsn.Membership.PENDING):
            local_pending.add(handle)

        if added:
            self.MembersChanged('', added, (), local_pending, (), 0,
                                telepathy.CHANNEL_GROUP_CHANGE_REASON_NONE)
