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

import weakref
import logging

import telepathy
import pymsn
import pymsn.event

from butterfly.presence import ButterflyPresence
from butterfly.simple_presence import ButterflySimplePresence
from butterfly.aliasing import ButterflyAliasing
from butterfly.avatars import ButterflyAvatars
from butterfly.handle import ButterflyHandleFactory
from butterfly.contacts import ButterflyContacts
from butterfly.channel_manager import ChannelManager

__all__ = ['ButterflyConnection']

logger = logging.getLogger('Butterfly.Connection')


class ButterflyConnection(telepathy.server.Connection,
        ButterflyPresence,
        ButterflySimplePresence,
        ButterflyAliasing,
        ButterflyAvatars,
        ButterflyContacts,
        pymsn.event.ClientEventInterface,
        pymsn.event.InviteEventInterface):

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
            server = (parameters['server'].encode('utf-8'), parameters['port'])

            # Build the proxies configurations
            proxies = {}
            proxy = build_proxy_infos(parameters, 'http')
            if proxy is not None:
                proxies['http'] = proxy
            proxy = build_proxy_infos(parameters, 'https')
            if proxy is not None:
                proxies['https'] = proxy

            self._manager = weakref.proxy(manager)
            self._msn_client = pymsn.Client(server, proxies)
            self._account = (parameters['account'].encode('utf-8'),
                    parameters['password'].encode('utf-8'))
            self._channel_manager = ChannelManager(self)

            # Call parent initializers
            try:
                telepathy.server.Connection.__init__(self, 'msn', account, 'butterfly')
            except TypeError: # handle old versions of tp-python
                telepathy.server.Connection.__init__(self, 'msn', account)
            ButterflyPresence.__init__(self)
            ButterflySimplePresence.__init__(self)
            ButterflyAliasing.__init__(self)
            ButterflyAvatars.__init__(self)
            ButterflyContacts.__init__(self)
            pymsn.event.ClientEventInterface.__init__(self, self._msn_client)
            pymsn.event.InviteEventInterface.__init__(self, self._msn_client)

            self.set_self_handle(ButterflyHandleFactory(self, 'self'))

            self.__disconnect_reason = telepathy.CONNECTION_STATUS_REASON_NONE_SPECIFIED
            self._initial_presence = None
            self._initial_personal_message = None

            logger.info("Connection to the account %s created" % account)
        except Exception, e:
            import traceback
            logger.exception("Failed to create Connection")
            raise

    @property
    def manager(self):
        return self._manager

    @property
    def msn_client(self):
        return self._msn_client

    def handle(self, handle_type, handle_id):
        self.check_handle(handle_type, handle_id)
        return self._handles[handle_type, handle_id]

    def Connect(self):
        logger.info("Connecting")
        self.__disconnect_reason = telepathy.CONNECTION_STATUS_REASON_NONE_SPECIFIED
        self._msn_client.login(*self._account)

    def Disconnect(self):
        logger.info("Disconnecting")
        self.__disconnect_reason = telepathy.CONNECTION_STATUS_REASON_REQUESTED
        self._msn_client.logout()

    def RequestHandles(self, handle_type, names, sender):
        self.check_connected()
        self.check_handle_type(handle_type)

        handles = []
        for name in names:
            name = name.encode('utf-8')
            if handle_type == telepathy.HANDLE_TYPE_CONTACT:
                name = name.rsplit('#', 1)
                contact_name = name[0]
                if len(name) > 1:
                    network_id = int(contact_name[1])
                else:
                    network_id = pymsn.NetworkID.MSN
                contacts = self.msn_client.address_book.contacts.\
                        search_by_account(contact_name).\
                        search_by_network_id(network_id)

                if len(contacts) > 0:
                    contact = contacts[0]
                    handle = ButterflyHandleFactory(self, 'contact',
                            contact.account, contact.network_id)
                else:
                    handle = ButterflyHandleFactory(self, 'contact',
                            contact_name, network_id)
            elif handle_type == telepathy.HANDLE_TYPE_LIST:
                handle = ButterflyHandleFactory(self, 'list', name)
            elif handle_type == telepathy.HANDLE_TYPE_GROUP:
                handle = ButterflyHandleFactory(self, 'group', name)
            else:
                raise telepathy.NotAvailable('Handle type unsupported %d' % handle_type)
            handles.append(handle.id)
            self.add_client_handle(handle, sender)
        return handles

    def RequestChannel(self, type, handle_type, handle_id, suppress_handler):
        self.check_connected()

        channel = None
        channel_manager = self._channel_manager
        handle = self.handle(handle_type, handle_id)

        if type == telepathy.CHANNEL_TYPE_CONTACT_LIST:
            channel = channel_manager.channel_for_list(handle, suppress_handler)
        elif type == telepathy.CHANNEL_TYPE_TEXT:
            if handle_type != telepathy.HANDLE_TYPE_CONTACT:
                raise telepathy.NotImplemented("Only Contacts are allowed")
            contact = handle.contact
            if contact.presence == pymsn.Presence.OFFLINE:
                raise telepathy.NotAvailable('Contact not available')
            channel = channel_manager.channel_for_text(handle, None, suppress_handler)
        else:
            raise telepathy.NotImplemented("unknown channel type %s" % type)

        return channel._object_path

    # pymsn.event.ClientEventInterface
    def on_client_state_changed(self, state):
        if state == pymsn.event.ClientState.CONNECTING:
            self.StatusChanged(telepathy.CONNECTION_STATUS_CONNECTING,
                    telepathy.CONNECTION_STATUS_REASON_REQUESTED)
        elif state == pymsn.event.ClientState.SYNCHRONIZED:
            handle = ButterflyHandleFactory(self, 'list', 'subscribe')
            self._channel_manager.channel_for_list(handle)
            handle = ButterflyHandleFactory(self, 'list', 'publish')
            self._channel_manager.channel_for_list(handle)
            #handle = ButterflyHandleFactory(self, 'list', 'hide')
            #self._channel_manager.channel_for_list(handle)
            #handle = ButterflyHandleFactory(self, 'list', 'allow')
            #self._channel_manager.channel_for_list(handle)
            #handle = ButterflyHandleFactory(self, 'list', 'deny')
            #self._channel_manager.channel_for_list(handle)

            for group in self.msn_client.address_book.groups:
                handle = ButterflyHandleFactory(self, 'group', group.name)
                self._channel_manager.channel_for_list(handle)
        elif state == pymsn.event.ClientState.OPEN:
            self.StatusChanged(telepathy.CONNECTION_STATUS_CONNECTED,
                    telepathy.CONNECTION_STATUS_REASON_REQUESTED)
            presence = self._initial_presence
            message = self._initial_personal_message
            if presence is not None:
                self._client.profile.presence = presence
            if message is not None:
                self._client.profile.personal_message = message

            if (presence is not None) or (message is not None):
                self._presence_changed(ButterflyHandleFactory(self, 'self'),
                        self._client.profile.presence,
                        self._client.profile.personal_message)
        elif state == pymsn.event.ClientState.CLOSED:
            self.StatusChanged(telepathy.CONNECTION_STATUS_DISCONNECTED,
                    self.__disconnect_reason)
            #FIXME
            self._channel_manager.close()
            self._advertise_disconnected()

    # pymsn.event.ClientEventInterface
    def on_client_error(self, type, error):
        if type == pymsn.event.ClientErrorType.NETWORK:
            self.__disconnect_reason = telepathy.CONNECTION_STATUS_REASON_NETWORK_ERROR
        elif type == pymsn.event.ClientErrorType.AUTHENTICATION:
            self.__disconnect_reason = telepathy.CONNECTION_STATUS_REASON_AUTHENTICATION_FAILED
        else:
            self.__disconnect_reason = telepathy.CONNECTION_STATUS_REASON_NONE_SPECIFIED

    # pymsn.event.InviteEventInterface
    def on_invite_conversation(self, conversation):
        logger.debug("Conversation invite")
        #FIXME: get rid of this crap and implement group support
        participants = conversation.participants 
        for p in participants:
            participant = p
            break
        handle = ButterflyHandleFactory(self, 'contact',
                participant.account, participant.network_id)
        channel = self._channel_manager.channel_for_text(handle, conversation)

    def _advertise_disconnected(self):
        self._manager.disconnected(self)


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

