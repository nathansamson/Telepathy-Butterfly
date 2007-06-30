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
import dbus
import logging
import weakref

import telepathy_butterfly.handler as event
from telepathy_butterfly.channel import *
from telepathy_butterfly.presence import ButterflyConnectionPresence
from telepathy_butterfly.aliasing import ButterflyConnectionAliasing

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
        self._connection = connection
        self._contacts_handles = weakref.WeakValueDictionary()
        self._list_handles = weakref.WeakValueDictionary()

    def handle_for_handle_id(self, handle_type, handle_id):
        self._connection.check_handle(handle_type, handle_id)
        return self._connection._handles[handle_type, handle_id]

    def handle_for_contact(self, account):
        if account in self._contacts_handles:
            handle = self._contacts_handles[account]
        else:
            handle = telepathy.server.Handle(self._connection.get_handle_id(),
                    telepathy.CONNECTION_HANDLE_TYPE_CONTACT,
                    account)
            self._contacts_handles[account] = handle
            self._connection._handles[handle.get_type(), handle.get_id()] = \
                    handle
            logger.debug("New contact handle %u %s" % \
                    (handle.get_id(), handle.get_name()))
        return handle
    
    def handle_for_list(self, lst):
        if lst in self._list_handles:
            handle = self._list_handles[lst]
        else:
            handle = telepathy.server.Handle(self._connection.get_handle_id(),
                    telepathy.CONNECTION_HANDLE_TYPE_LIST,
                    lst)
            self._list_handles[lst] = handle
            self._connection._handles[handle.get_type(), handle.get_id()] = \
                    handle
            logger.debug("New list handle %u %s" % \
                    (handle.get_id(), handle.get_name()))
        return handle

class ChannelManager(object):
    def __init__(self, connection):
        self._connection = connection
        self._list_channels = weakref.WeakValueDictionary()
        self._text_channels = weakref.WeakValueDictionary()

    def channel_for_list(self, list_type, handle, suppress_handler=False):
        if handle in self._list_channels:
            channel = self._list_channels[handle]
        else:
            if list_type == 'subscribe':
                channel_class = ButterflySubscribeListChannel
            elif list_type == 'publish':
                channel_class = ButterflyPublishListChannel
            #elif list_type == 'hide':
            #    channel_class = ButterflyHideListChannel
            #elif list_type == 'allow':
            #    channel_class = ButterflyAllowListChannel
            #elif list_type == 'deny':
            #    channel_class = ButterflyDenyListChannel
            else:
                raise AssertionError("Unknown list type : " + list_type)
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
            account = handle.get_name()
            contact = self._connection._pymsn_client.address_book.contacts.\
                    search_by_account(account).get_first()
            if contact.presence == pymsn.Presence.OFFLINE:
                    raise telepathy.NotAvailable('Contact not available')
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
        ButterflyConnectionAliasing):

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
        try: 
            account = unicode(parameters['account'])
            server = (parameters['server'], parameters['port'])

            proxies = {}

            proxy = build_proxy_infos(parameters, 'http')
            if proxy is not None:
                proxies['http'] = proxy

            proxy = build_proxy_infos(parameters, 'https')
            if proxy is not None:
                proxies['https'] = proxy
            
            try:
                telepathy.server.Connection.__init__(self, 'msn', account, 'butterfly')
            except TypeError: # handle old versions of tp-python
                telepathy.server.Connection.__init__(self, 'msn', account)

            ButterflyConnectionPresence.__init__(self)
            ButterflyConnectionAliasing.__init__(self)
            self._handle_manager = HandleManager(self)
            self._channel_manager = ChannelManager(self)
            
            self._account = (parameters['account'], parameters['password'])
            self._initial_presence = pymsn.Presence.ONLINE
            self._initial_personal_message = ""

            self._manager = manager
            self._pymsn_client = pymsn.Client(server, proxies)
            event.ButterflyClientEventsHandler(self._pymsn_client, self)
            event.ButterflyContactEventsHandler(self._pymsn_client, self)
            event.ButterflyInviteEventsHandler(self._pymsn_client, self)

            self_handle = self._handle_manager.handle_for_contact(self._account[0])
            self.set_self_handle(self_handle)
            logger.info("Connection to the account %s created" % account)
        except Exception, e:
            print e

    
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
        if handle_type == telepathy.CONNECTION_HANDLE_TYPE_CONTACT:
            get_handle = self._handle_manager.handle_for_contact
        elif handle_type == telepathy.CONNECTION_HANDLE_TYPE_LIST:
            get_handle = self._handle_manager.handle_for_list
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
            if handle_type != telepathy.CONNECTION_HANDLE_TYPE_CONTACT:
                raise telepathy.NotImplemented("Only Contacts are allowed currently")

            handle = self._handle_manager.\
                    handle_for_handle_id(handle_type, handle_id)
            channel = self._channel_manager.\
                    channel_for_text(handle, None, suppress_handler)
        else:
            raise telepathy.NotImplemented("unknown channel type %s" % type)

        return channel._object_path

    #
    def _connect(self):
        self._pymsn_client.login(*self._account)
        return False

    def _disconnect(self):
        self._manager.disconnected(self)
        self._pymsn_client.logout()
        return False

    def _create_contact_list(self):
        handle = self._handle_manager.handle_for_list('subscribe')
        self._channel_manager.channel_for_list('subscribe', handle)
        handle = self._handle_manager.handle_for_list('publish')
        self._channel_manager.channel_for_list('publish', handle)

