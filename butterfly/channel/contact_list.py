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

import logging
import weakref

import telepathy
import pymsn
import pymsn.event

from butterfly.util.decorator import async
from butterfly.handle import ButterflyHandleFactory

__all__ = ['ButterflyContactListChannelFactory']


def ButterflyContactListChannelFactory(connection, handle):
    if handle.get_name() == 'subscribe':
        channel_class = ButterflySubscribeListChannel
    elif handle.get_name() == 'publish':
        channel_class = ButterflyPublishListChannel
    elif handle.get_name() == 'hide':
        channel_class = ButterflyHideListChannel
    elif handle.get_name() == 'allow':
        channel_class = ButterflyAllowListChannel
    elif handle.get_name() == 'deny':
        channel_class = ButterflyDenyListChannel
    else:
        raise TypeError("Unknown list type : " + handle.get_name())
    return channel_class(connection, handle)


class ButterflyListChannel(
        telepathy.server.ChannelTypeContactList,
        telepathy.server.ChannelInterfaceGroup,
        pymsn.event.AddressBookEventInterface):
    "Abstract Contact List channels"

    def __init__(self, connection, handle):
        self._conn_ref = weakref.ref(connection)
        telepathy.server.ChannelTypeContactList.__init__(self, connection, handle)
        telepathy.server.ChannelInterfaceGroup.__init__(self)
        pymsn.event.AddressBookEventInterface.__init__(self, connection.msn_client)
        self._populate(connection)

    def GetLocalPendingMembersWithInfo(self):
        return []

    # pymsn.event.AddressBookEventInterface
    def on_addressbook_messenger_contact_added(self, contact):
        added = set()
        local_pending = set()
        remote_pending = set()

        handle = ButterflyHandleFactory(self._conn_ref(), 'contact', contact)
        ad, lp, rp = self._filter_contact(contact)
        if ad: added.add(handle)
        if lp: local_pending.add(handle)
        if rp: remote_pending.add(handle)
        self.MembersChanged('', added, (), local_pending, remote_pending, 0,
                telepathy.CHANNEL_GROUP_CHANGE_REASON_NONE)

    # pymsn.event.AddressBookEventInterface
    def on_addressbook_contact_deleted(self, contact):
        handle = ButterflyHandleFactory(self._conn_ref(), 'contact', contact)
        members, local_pending, remote_pending = self.GetAllMembers()
        if (handle in members) or (handle in local_pending) or (handle in remote_pending):
            self.MembersChanged('', (), [handle], (), remote_pending, 0,
                    telepathy.CHANNEL_GROUP_CHANGE_REASON_NONE)

    # pymsn.event.AddressBookEventInterface
    def on_addressbook_contact_blocked(self, contact):
        pass

    # pymsn.event.AddressBookEventInterface
    def on_addressbook_contact_unblocked(self, contact):
        pass

    @async
    def _populate(self, connection):
        added = set()
        local_pending = set()
        remote_pending = set()

        for contact in connection.msn_client.address_book.contacts:
            handle = ButterflyHandleFactory(self._conn_ref(), 'contact', contact)
            ad, lp, rp = self._filter_contact(contact)
            if ad: added.add(handle)
            if lp: local_pending.add(handle)
            if rp: remote_pending.add(handle)
        self.MembersChanged('', added, (), local_pending, remote_pending, 0,
                telepathy.CHANNEL_GROUP_CHANGE_REASON_NONE)

    def _filter_contact(self, contact):
        return (False, False, False)


class ButterflySubscribeListChannel(ButterflyListChannel):
    """Subscribe List channel.

    This channel contains the list of contact to whom the current used is
    'subscribed', basically this list contains the contact for whom you are
    supposed to receive presence notification."""

    def __init__(self, connection, handle):
        ButterflyListChannel.__init__(self, connection, handle)
        self.GroupFlagsChanged(telepathy.CHANNEL_GROUP_FLAG_CAN_ADD |
                telepathy.CHANNEL_GROUP_FLAG_CAN_REMOVE, 0)

    def RemoveMembers(self, contacts, message):
        ab = self._conn.msn_client.address_book
        for h in contacts:
            handle = self._conn.handle(telepathy.HANDLE_TYPE_CONTACT, h)
            contact = handle.contact
            ab.delete_contact(contact)

    def _filter_contact(self, contact):
        return (contact.is_member(pymsn.Membership.FORWARD), False, False)


class ButterflyPublishListChannel(ButterflyListChannel):

    def __init__(self, connection, handle):
        ButterflyListChannel.__init__(self, connection, handle)
        self.GroupFlagsChanged(0, 0)

    def _filter_contact(self, contact):
        return (contact.is_member(pymsn.Membership.REVERSE),
                contact.is_member(pymsn.Membership.PENDING),
                False)

    def GetLocalPendingMembersWithInfo(self):
        result = []
        for contact in self._conn.msn_client.address_book.contacts:
            if not contact.is_member(pymsn.Membership.PENDING):
                continue
            handle = ButterflyHandleFactory(self._conn_ref(), 'contact', contact)
            result.append((handle, handle,
                    telepathy.CHANNEL_GROUP_CHANGE_REASON_INVITED,
                    contact.attributes.get('invite_message', '')))
        return result

