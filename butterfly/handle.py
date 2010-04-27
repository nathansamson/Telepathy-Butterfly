# telepathy-butterfly - an MSN connection manager for Telepathy
#
# Copyright (C) 2007 Ali Sabil <ali.sabil@gmail.com>
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
import papyon

__all__ = ['ButterflyHandleFactory', 'network_to_extension']

logger = logging.getLogger('Butterfly.Handle')

network_to_extension = {papyon.NetworkID.EXTERNAL: "#yahoo"}


def ButterflyHandleFactory(connection, type, *args):
    mapping = {'self': ButterflySelfHandle,
               'contact': ButterflyContactHandle,
               'list': ButterflyListHandle,
               'group': ButterflyGroupHandle}
    handle = mapping[type](connection, *args)
    connection._handles[handle.get_type(), handle.get_id()] = handle
    return handle


class ButterflyHandleMeta(type):
    def __call__(cls, connection, *args):
        obj, newly_created = cls.__new__(cls, connection, *args)
        if newly_created:
            obj.__init__(connection, connection.get_handle_id(), *args)
            logger.info("New Handle %s" % unicode(obj))
        return obj 


class ButterflyHandle(telepathy.server.Handle):
    __metaclass__ = ButterflyHandleMeta

    instances = weakref.WeakValueDictionary()
    def __new__(cls, connection, *args):
        key = (cls, connection._account[0], args)
        if key not in cls.instances.keys():
            instance = object.__new__(cls)
            cls.instances[key] = instance # TRICKY: instances is a weakdict
            return instance, True
        return cls.instances[key], False

    def __init__(self, connection, id, handle_type, name):
        telepathy.server.Handle.__init__(self, id, handle_type, name)
        self._conn = weakref.proxy(connection)

    def __unicode__(self):
        type_mapping = {telepathy.HANDLE_TYPE_CONTACT : 'Contact',
                telepathy.HANDLE_TYPE_ROOM : 'Room',
                telepathy.HANDLE_TYPE_LIST : 'List',
                telepathy.HANDLE_TYPE_GROUP : 'Group'}
        type_str = type_mapping.get(self.type, '')
        return "<Butterfly%sHandle id=%u name='%s'>" % \
            (type_str, self.id, self.name)

    id = property(telepathy.server.Handle.get_id)
    type = property(telepathy.server.Handle.get_type)
    name = property(telepathy.server.Handle.get_name)


class ButterflySelfHandle(ButterflyHandle):
    instance = None

    def __init__(self, connection, id):
        handle_type = telepathy.HANDLE_TYPE_CONTACT
        handle_name = connection._account[0]
        self._connection = connection
        ButterflyHandle.__init__(self, connection, id, handle_type, handle_name)

    @property
    def profile(self):
        return self._connection.msn_client.profile


class ButterflyContactHandle(ButterflyHandle):
    def __init__(self, connection, id, contact_account, contact_network):
        extension = network_to_extension.get(contact_network, "")
        handle_type = telepathy.HANDLE_TYPE_CONTACT
        handle_name = contact_account + extension
        self.account = contact_account
        self.network = contact_network
        self.pending_groups = set()
        self.pending_alias = None
        ButterflyHandle.__init__(self, connection, id, handle_type, handle_name)

    @property
    def contact(self):
        return self._conn.msn_client.address_book.search_contact(self.account,
                self.network)


class ButterflyListHandle(ButterflyHandle):
    def __init__(self, connection, id, list_name):
        handle_type = telepathy.HANDLE_TYPE_LIST
        handle_name = list_name
        ButterflyHandle.__init__(self, connection, id, handle_type, handle_name)


class ButterflyGroupHandle(ButterflyHandle):
    def __init__(self, connection, id, group_name):
        handle_type = telepathy.HANDLE_TYPE_GROUP
        handle_name = group_name
        ButterflyHandle.__init__(self, connection, id, handle_type, handle_name)

    @property
    def group(self):
        for group in self._conn.msn_client.address_book.groups:
            # Microsoft seems to like case insensitive stuff
            if group.name.decode("utf-8").lower() == self.name.lower():
                return group
        return None

