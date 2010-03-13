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

import dbus
import telepathy
import papyon
import papyon.event

from butterfly.presence import ButterflyPresence
from butterfly.aliasing import ButterflyAliasing
from butterfly.avatars import ButterflyAvatars
from butterfly.handle import ButterflyHandleFactory
from butterfly.capabilities import ButterflyCapabilities
from butterfly.contacts import ButterflyContacts
from butterfly.channel_manager import ButterflyChannelManager
from butterfly.mail_notification import ButterflyMailNotification

__all__ = ['ButterflyConnection']

logger = logging.getLogger('Butterfly.Connection')


class ButterflyConnection(telepathy.server.Connection,
        telepathy.server.ConnectionInterfaceRequests,
        ButterflyPresence,
        ButterflyAliasing,
        ButterflyAvatars,
        ButterflyCapabilities,
        ButterflyContacts,
        ButterflyMailNotification,
        papyon.event.ClientEventInterface,
        papyon.event.InviteEventInterface,
        papyon.event.OfflineMessagesEventInterface):

    _secret_parameters = set([
            'password',
            'http-proxy-password',
            'https-proxy-password'
            ])
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
            self._msn_client = papyon.Client(server, proxies)
            self._account = (parameters['account'].encode('utf-8'),
                    parameters['password'].encode('utf-8'))
            self._channel_manager = ButterflyChannelManager(self)

            # Call parent initializers
            telepathy.server.Connection.__init__(self, 'msn', account, 'butterfly')
            telepathy.server.ConnectionInterfaceRequests.__init__(self)
            ButterflyPresence.__init__(self)
            ButterflyAliasing.__init__(self)
            ButterflyAvatars.__init__(self)
            ButterflyCapabilities.__init__(self)
            ButterflyContacts.__init__(self)
            ButterflyMailNotification.__init__(self)
            papyon.event.ClientEventInterface.__init__(self, self._msn_client)
            papyon.event.InviteEventInterface.__init__(self, self._msn_client)
            papyon.event.OfflineMessagesEventInterface.__init__(self, self._msn_client)


            self.set_self_handle(ButterflyHandleFactory(self, 'self'))

            self.__disconnect_reason = telepathy.CONNECTION_STATUS_REASON_NONE_SPECIFIED
            self._initial_presence = papyon.Presence.INVISIBLE
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
        if self._status == telepathy.CONNECTION_STATUS_DISCONNECTED:
            logger.info("Connecting")
            self.__disconnect_reason = telepathy.CONNECTION_STATUS_REASON_NONE_SPECIFIED
            self._msn_client.login(*self._account)

    def Disconnect(self):
        logger.info("Disconnecting")
        self.__disconnect_reason = telepathy.CONNECTION_STATUS_REASON_REQUESTED
        self._msn_client.logout()

    def GetInterfaces(self):
        # The self._interfaces set is only ever touched in ButterflyConnection.__init__,
        # where connection interfaces are added.

        # The mail notification interface is added then too, but also removed in its
        # ButterflyMailNotification.__init__ because it might not actually be available.
        # It is added before the connection status turns to connected, if available.

        # The spec denotes that this method can return a subset of the actually
        # available interfaces before connected. As the only possible change will
        # be adding the mail notification interface before connecting, this is fine.

        return self._interfaces

    def RequestHandles(self, handle_type, names, sender):
        self.check_connected()
        self.check_handle_type(handle_type)

        handles = []
        for name in names:
            if handle_type == telepathy.HANDLE_TYPE_CONTACT:
                name = name.rsplit('#', 1)
                contact_name = name[0]
                if len(name) > 1:
                    network_id = int(name[1])
                else:
                    network_id = papyon.NetworkID.MSN
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

    def _generate_props(self, channel_type, handle, suppress_handler, initiator_handle=None):
        props = {
            telepathy.CHANNEL_INTERFACE + '.ChannelType': channel_type,
            telepathy.CHANNEL_INTERFACE + '.TargetHandle': handle.get_id(),
            telepathy.CHANNEL_INTERFACE + '.TargetHandleType': handle.get_type(),
            telepathy.CHANNEL_INTERFACE + '.Requested': suppress_handler
            }

        if initiator_handle is not None:
            if initiator_handle.get_type() is not telepathy.HANDLE_TYPE_NONE:
                props[telepathy.CHANNEL_INTERFACE + '.InitiatorHandle'] = \
                        initiator_handle.get_id()

        return props


    @dbus.service.method(telepathy.CONNECTION, in_signature='suub',
        out_signature='o', async_callbacks=('_success', '_error'))
    def RequestChannel(self, type, handle_type, handle_id, suppress_handler,
            _success, _error):
        self.check_connected()
        channel_manager = self._channel_manager

        if handle_id == telepathy.HANDLE_TYPE_NONE:
            handle = telepathy.server.handle.NoneHandle()
        else:
            handle = self.handle(handle_type, handle_id)
        props = self._generate_props(type, handle, suppress_handler)
        self._validate_handle(props)

        channel = channel_manager.channel_for_props(props, signal=False)

        _success(channel._object_path)
        self.signal_new_channels([channel])

    # papyon.event.ClientEventInterface
    def on_client_state_changed(self, state):
        if state == papyon.event.ClientState.CONNECTING:
            self.StatusChanged(telepathy.CONNECTION_STATUS_CONNECTING,
                    telepathy.CONNECTION_STATUS_REASON_REQUESTED)
        elif state == papyon.event.ClientState.SYNCHRONIZED:
            handle = ButterflyHandleFactory(self, 'list', 'subscribe')
            props = self._generate_props(telepathy.CHANNEL_TYPE_CONTACT_LIST,
                handle, False)
            self._channel_manager.channel_for_props(props, signal=True)

            handle = ButterflyHandleFactory(self, 'list', 'publish')
            props = self._generate_props(telepathy.CHANNEL_TYPE_CONTACT_LIST,
                handle, False)
            self._channel_manager.channel_for_props(props, signal=True)

            #handle = ButterflyHandleFactory(self, 'list', 'hide')
            #props = self._generate_props(telepathy.CHANNEL_TYPE_CONTACT_LIST,
            #    handle, False)
            #self._channel_manager.channel_for_props(props, signal=True)

            #handle = ButterflyHandleFactory(self, 'list', 'allow')
            #props = self._generate_propstelepathy.CHANNEL_TYPE_CONTACT_LIST,
            #    handle, False)
            #self._channel_manager.channel_for_props(props, signal=True)

            #handle = ButterflyHandleFactory(self, 'list', 'deny')
            #props = self._generate_props(telepathy.CHANNEL_TYPE_CONTACT_LIST,
            #    handle, False)
            #self._channel_manager.channel_for_props(props, signal=True)

            for group in self.msn_client.address_book.groups:
                handle = ButterflyHandleFactory(self, 'group',
                        group.name.decode("utf-8"))
                props = self._generate_props(
                    telepathy.CHANNEL_TYPE_CONTACT_LIST, handle, False)
                self._channel_manager.channel_for_props(props, signal=True)
        elif state == papyon.event.ClientState.OPEN:
            self._populate_capabilities()
            if self._client.profile.profile['EmailEnabled'] == '1':
                self.enable_mail_notification_interface()
            self.StatusChanged(telepathy.CONNECTION_STATUS_CONNECTED,
                    telepathy.CONNECTION_STATUS_REASON_REQUESTED)
            presence = self._initial_presence
            message = self._initial_personal_message
            if presence is not None:
                self._client.profile.presence = presence
            if message is not None:
                self._client.profile.personal_message = message
            self._client.profile.end_point_name = "PAPYON"

            if (presence is not None) or (message is not None):
                self._presence_changed(ButterflyHandleFactory(self, 'self'),
                        self._client.profile.presence,
                        self._client.profile.personal_message)
        elif state == papyon.event.ClientState.CLOSED:
            self.StatusChanged(telepathy.CONNECTION_STATUS_DISCONNECTED,
                    self.__disconnect_reason)
            #FIXME
            self._channel_manager.close()
            self._advertise_disconnected()

    # papyon.event.ClientEventInterface
    def on_client_error(self, type, error):
        if type == papyon.event.ClientErrorType.NETWORK:
            self.__disconnect_reason = telepathy.CONNECTION_STATUS_REASON_NETWORK_ERROR
        elif type == papyon.event.ClientErrorType.AUTHENTICATION:
            self.__disconnect_reason = telepathy.CONNECTION_STATUS_REASON_AUTHENTICATION_FAILED
        elif type == papyon.event.ClientErrorType.PROTOCOL and \
             error == papyon.event.ProtocolError.OTHER_CLIENT:
            self.__disconnect_reason = telepathy.CONNECTION_STATUS_REASON_NAME_IN_USE
        else:
            self.__disconnect_reason = telepathy.CONNECTION_STATUS_REASON_NONE_SPECIFIED

    # papyon.event.InviteEventInterface
    def on_invite_conversation(self, conversation):
        logger.debug("Conversation invite")

        if len(conversation.participants) == 1:
            p = list(conversation.participants)[0]
            handle = ButterflyHandleFactory(self, 'contact',
                    p.account, p.network_id)
        else:
            handle = telepathy.server.handle.NoneHandle()

        props = self._generate_props(telepathy.CHANNEL_TYPE_TEXT,
            handle, False, initiator_handle=handle)

        channel = self._channel_manager.channel_for_props(props,
            signal=True, conversation=conversation)

        if channel._conversation is not conversation:
            # If we get an existing channel, attach the conversation object to it
            channel.attach_conversation(conversation)

    # papyon.event.InviteEventInterface
    def on_invite_conference(self, call):
        logger.debug("Call invite, ignoring it")
        #logger.debug("Call invite")
        #handle = ButterflyHandleFactory(self, 'contact', call.peer.account,
                #call.peer.network_id)

        #props = self._generate_props(telepathy.CHANNEL_TYPE_STREAMED_MEDIA,
                #handle, False, initiator_handle=handle)

        #channel = self._channel_manager.channel_for_props(props,
                #signal=True, call=call)

    # papyon.event.InviteEventInterface
    def on_invite_webcam(self, session, producer):
        direction = (producer and "send") or "receive"
        logger.debug("Invitation to %s webcam, ignoring it" % direction)
        #logger.debug("Invitation to %s webcam" % direction)

        #handle = ButterflyHandleFactory(self, 'contact', session.peer.account,
                #session.peer.network_id)
        #props = self._generate_props(telepathy.CHANNEL_TYPE_STREAMED_MEDIA,
                #handle, False, initiator_handle=handle)
        #channel = self._channel_manager.channel_for_props(props, signal=True,
                #call=session)

    # papyon.event.OfflineMessagesEventInterface
    def on_oim_messages_received(self, messages):
        # We got notified we received some offlines messages so we
        #are going to fetch them
        self.msn_client.oim_box.fetch_messages(messages)

    # papyon.event.OfflineMessagesEventInterface
    def on_oim_messages_fetched(self, messages):
        for message in messages:
            # Request butterfly text channel (creation, what happen when it exist)
            sender = message.sender
            logger.info('received offline message from %s : %s' % (sender.account, message.text))
            handle = ButterflyHandleFactory(self, 'contact',
                    sender.account, sender.network_id)
            props = self._generate_props(telepathy.CHANNEL_TYPE_TEXT,
                handle, False)
            channel = self._channel_manager.channel_for_props(props,
                signal=True)
            # Notify it of the message
            channel.offline_message_received(message)

    def _advertise_disconnected(self):
        self._manager.disconnected(self)


def build_proxy_infos(self, parameters, proxy_type='http'):
    server_key = proxy_type + '-proxy-server'
    port_key = proxy_type + '-proxy-port'
    username_key = proxy_type + '-proxy-username'
    password_key = proxy_type + '-proxy-password'
    if server_key in parameters and port_key in parameters:
        return papyon.ProxyInfos(host = parameters[server_key],
                port = parameters[port_key],
                type = proxy_type,
                user = parameters.get(username_key, None),
                password = parameters.get(password_key, None) )
    else:
        return None

