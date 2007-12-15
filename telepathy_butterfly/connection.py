# telepathy-butterfly - an MSN connection manager for Telepathy
#
# Copyright (C) 2006-2007 Ali Sabil <ali.sabil@gmail.com>
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

import telepathy
import pymsn
import gobject
import dbus
import logging
import weakref

import telepathy_butterfly.handler as event
from telepathy_butterfly.channel import *
from telepathy_butterfly.presence import ButterflyConnectionPresence
from telepathy_butterfly.aliasing import ButterflyConnectionAliasing
from telepathy_butterfly.avatars import ButterflyConnectionAvatars

__all__ = ['ButterflyConnection']

logger = logging.getLogger('telepathy-butterfly:connection')

def build_proxy_infos(self, parameters, proxy_type='http'):
    server_key = proxy_type + '-proxy-server'
    port_key = proxy_type + '-proxy-port'
    username_key = proxy_type + '-proxy-username'
    password_key = proxy_type + '-proxy-password'
    if server_key in parameters and port_key in parameters:
        return pymsn.ProxyInfos(host = parameters[server_key],
                port = parameters[port_key],
                type = proxy_type,
                user = parameters.get(username_key, None),
                password = parameters.get(password_key, None) )
    else:
        return None

class HandleManager(object):
    def __init__(self, connection):
        self._connection = weakref.proxy(connection)
        self._self_handle = None
        self._contacts_handles = weakref.WeakValueDictionary()
        self._list_handles = weakref.WeakValueDictionary()
        self._group_handles = weakref.WeakValueDictionary()

    def handle_for_handle_id(self, handle_type, handle_id):
        self._connection.check_handle(handle_type, handle_id)
        return self._connection._handles[handle_type, handle_id]

    def handle_for_self(self, account):
        if self._self_handle is None:
            handle = telepathy.server.Handle(
                    self._connection.get_handle_id(),
                    telepathy.HANDLE_TYPE_CONTACT,
                    account + "#" + str(pymsn.NetworkID.MSN))
            self._connection._handles[handle.get_type(), handle.get_id()] = \
                    handle
            logger.debug("New self handle %u %s" % \
                    (handle.get_id(), handle.get_name()))
            self._self_handle = weakref.proxy(handle)
        else:
            handle = self._self_handle
        return handle

    def handle_for_contact(self, contact):
        if contact in self._contacts_handles:
            handle = self._contacts_handles[contact]
        else:
            account = "#".join([contact.account, str(contact.network_id)])
            handle = telepathy.server.Handle(self._connection.get_handle_id(),
                    telepathy.HANDLE_TYPE_CONTACT,
                    account)
            self._contacts_handles[contact] = handle
            self._connection._handles[handle.get_type(), handle.get_id()] = \
                    handle
            logger.debug("New contact handle %u %s" % \
                    (handle.get_id(), handle.get_name()))
        return handle

    def handle_for_contact_name(self, handle_name):
        for contact, handle in self._contacts_handles.iteritems():
            if handle_name == handle.get_name():
                return handle
            account, network_id = handle.get_name().rsplit('#', 1)
            if handle_name == account:
                return account
        return None
    
    def handle_for_list(self, list_name):
        if list_name in self._list_handles:
            handle = self._list_handles[list_name]
        else:
            handle = telepathy.server.Handle(self._connection.get_handle_id(),
                    telepathy.HANDLE_TYPE_LIST,
                    list_name)
            self._list_handles[list_name] = handle
            self._connection._handles[handle.get_type(), handle.get_id()] = \
                    handle
            logger.debug("New list handle %u %s" % \
                    (handle.get_id(), handle.get_name()))
        return handle

    def handle_for_group(self, group_name):
        if group_name in self._group_handles:
            handle = self._group_handles[group_name]
        else:
            group = self._connection._group_for_name(group_name)
            if group is None:
                self._connection._pymsn_client.address_book.\
                    add_group(group_name)
            # FIXME : something better should be done with dbus contexts

            handle = telepathy.server.Handle(self._connection.get_handle_id(),
                    telepathy.HANDLE_TYPE_GROUP,
                    group_name)
            self._group_handles[group_name] = handle
            self._connection._handles[handle.get_type(), handle.get_id()] = \
                    handle
            logger.debug("New group handle %u %s" % \
                    (handle.get_id(), handle.get_name()))
        return handle


class ChannelManager(object):
    def __init__(self, connection):
        self._connection = weakref.proxy(connection)
        self._list_channels = {}
        self._text_channels = {}
    
    def close(self):
        for channel in self._list_channels.values():
            channel.remove_from_connection()# so that dbus lets it die.
        for channel in self._text_channels.values():
            channel.Close()

    def channel_for_list(self, handle, suppress_handler=False):
        if handle in self._list_channels:
            channel = self._list_channels[handle]
        else:
            if handle.get_type() == telepathy.HANDLE_TYPE_GROUP:
                channel_class = ButterflyGroupChannel
            elif handle.get_name() == 'subscribe':
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
                raise AssertionError("Unknown list type : " + handle.get_name())
            channel = channel_class(self._connection, handle)
            self._list_channels[handle] = channel
            self._connection.add_channel(channel, handle,
                    suppress_handler=suppress_handler)
        return channel

    def channel_for_text(self, handle, conversation=None, suppress_handler=False):
        if handle in self._text_channels:
            logger.debug("Requesting already available text channel")
            channel = self._text_channels[handle]
        else:
            logger.debug("Requesting new text channel")
            contact = self._connection._contact_for_handle(handle)

            if conversation is None:
                contacts = [contact]
            else:
                contacts = []
            channel = ButterflyTextChannel(self._connection,
                                           conversation, contacts)
            self._text_channels[handle] = channel
            self._connection.add_channel(channel, handle, suppress_handler)
        return channel

class ButterflyConnection(telepathy.server.Connection,
        ButterflyConnectionPresence,
        ButterflyConnectionAliasing,
        ButterflyConnectionAvatars):

    _mandatory_parameters = {
            'account' : 's',
            'password' : 's'
            }
    _optional_parameters = {
            'server' : 's',
            'port' : 'q',
            'http-proxy-server' : 's',
            'http-proxy-port' : 'q',
            'http-proxy-username' : 's',
            'http-proxy-password' : 's',
            'https-proxy-server' : 's',
            'https-proxy-port' : 'q',
            'https-proxy-username' : 's',
            'https-proxy-password' : 's'
            }
    _parameter_defaults = {
            'server' : 'messenger.hotmail.com',
            'port' : 1863
            }

    def __init__(self, manager, parameters):
        self.check_parameters(parameters)
        
        account = unicode(parameters['account'])
        server = (parameters['server'].encode('utf-8'), parameters['port'])
        
        proxies = {}
        
        proxy = build_proxy_infos(parameters, 'http')
        if proxy is not None:
            proxies['http'] = proxy
        
        proxy = build_proxy_infos(parameters, 'https')
        if proxy is not None:
            proxies['https'] = proxy
        
        try:
            telepathy.server.Connection.__init__(self, 'msn', account, 'butterfly')
        except TypeError, e: # handle old versions of tp-python
            print e
            telepathy.server.Connection.__init__(self, 'msn', account)
        
        ButterflyConnectionPresence.__init__(self)
        ButterflyConnectionAliasing.__init__(self)
        ButterflyConnectionAvatars.__init__(self)
        self._handle_manager = HandleManager(self)
        self._channel_manager = ChannelManager(self)
        
        self._account = (parameters['account'].encode('utf-8'),
                parameters['password'].encode('utf-8'))
        self._initial_presence = pymsn.Presence.ONLINE
        self._initial_personal_message = ""
        
        self._manager = weakref.proxy(manager)
        self._pymsn_client = pymsn.Client(server, proxies)
        self._event_handlers = [] 
        self._event_handlers.append(event.ButterflyClientEventsHandler(self._pymsn_client, self))
        self._event_handlers.append(event.ButterflyContactEventsHandler(self._pymsn_client, self))
        self._event_handlers.append(event.ButterflyInviteEventsHandler(self._pymsn_client, self))
        self._event_handlers.append(event.ButterflyAddressBookEventsHandler(self._pymsn_client, self))

        full_account = "#".join([self._account[0], str(pymsn.profile.NetworkID.MSN)])
        self_handle = self._handle_manager.handle_for_self(full_account)
        self.set_self_handle(self_handle)
        logger.info("Connection to the account %s created" % account)
    
    def Connect(self):
        logger.info("Connecting")
        gobject.idle_add(self._connect)

    def Disconnect(self):
        logger.info("Disconnecting")
        gobject.idle_add(self._disconnect)

    def RequestHandles(self, handle_type, names, sender):
        self.check_connected()
        self.check_handle_type(handle_type)
        handles = []
        if handle_type == telepathy.HANDLE_TYPE_CONTACT:
            get_handle = self._handle_manager.handle_for_contact_name
        elif handle_type == telepathy.HANDLE_TYPE_LIST:
            get_handle = self._handle_manager.handle_for_list
        elif handle_type == telepathy.HANDLE_TYPE_GROUP:
            get_handle = self._handle_manager.handle_for_group
        else:
            raise telepathy.NotAvailable('Handle type unsupported %d' % 
                    handle_type)
        
        for name in names:
            handle = get_handle(name)
            handles.append(handle.get_id())
            self.add_client_handle(handle, sender)
        
        return handles

    def RequestChannel(self, type, handle_type, handle_id, suppress_handler):
        self.check_connected()

        channel = None
        if type == telepathy.CHANNEL_TYPE_CONTACT_LIST:
            self.check_handle_type(handle_type)
            handle = self._handle_manager.\
                    handle_for_handle_id(handle_type, handle_id)
            channel = self._channel_manager.\
                    channel_for_list(handle, suppress_handler)
        elif type == telepathy.CHANNEL_TYPE_TEXT:
            # FIXME: Also accept Group Handles
            if handle_type != telepathy.HANDLE_TYPE_CONTACT:
                raise telepathy.NotImplemented("Only Contacts are allowed currently")

            handle = self._handle_manager.\
                    handle_for_handle_id(handle_type, handle_id)
            contact = self._contact_for_handle(handle)
            if contact.presence == pymsn.Presence.OFFLINE:
                raise telepathy.NotAvailable('Contact not available')
            channel = self._channel_manager.\
                    channel_for_text(handle, None, suppress_handler)
        else:
            raise telepathy.NotImplemented("unknown channel type %s" % type)

        return channel._object_path

    def _connect(self):
        self._pymsn_client.login(*self._account)
        return False

    def _disconnect(self):
        self._pymsn_client.logout()
        return False

    def _advertise_disconnected(self):
        self._manager.disconnected(self)

    def _create_contact_list(self):
        handle = self._handle_manager.handle_for_list('subscribe')
        self._channel_manager.channel_for_list(handle)
        handle = self._handle_manager.handle_for_list('publish')
        self._channel_manager.channel_for_list(handle)
        handle = self._handle_manager.handle_for_list('hide')
        self._channel_manager.channel_for_list(handle)
        handle = self._handle_manager.handle_for_list('allow')
        self._channel_manager.channel_for_list(handle)
        handle = self._handle_manager.handle_for_list('deny')
        self._channel_manager.channel_for_list(handle)
        
        for group in self._pymsn_client.address_book.groups:
            handle = self._handle_manager.handle_for_group(group.name)
            self._channel_manager.channel_for_list(handle)

    # Utility methods
    def _group_for_handle(self, handle):
        return self._group_for_name(handle.get_name())

    def _group_for_name(self, group_name):
        for group in self._pymsn_client.address_book.groups:
            if group.name == group_name:
                return group
        return None

    def _contact_for_handle(self, handle):
        if handle == self.GetSelfHandle():
            return self._pymsn_client.profile

        account, network = handle.get_name().split("#")
        return self._pymsn_client.address_book.contacts.\
            search_by_account(account).search_by_network_id(int(network))[0]
    
