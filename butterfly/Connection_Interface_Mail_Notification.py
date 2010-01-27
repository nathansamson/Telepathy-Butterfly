# -*- coding: utf-8 -*-
# Generated from the Telepathy spec
""" Copyright (C) 2007 Collabora Limited 

    This library is free software; you can redistribute it and/or
modify it under the terms of the GNU Lesser General Public
License as published by the Free Software Foundation; either
version 2.1 of the License, or (at your option) any later version.

This library is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
Library General Public License for more details.

You should have received a copy of the GNU Lesser General Public
License along with this library; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
  
"""

import dbus.service


class ConnectionInterfaceMailNotification(dbus.service.Interface):
    """\
      An interface to support receiving notifications about a e-mail
        account associated with this connection. It is intended that the
        connection manager has the means to provide necessary information
        so that the client is always able to open a web based mail client
        without having to re-authenticate.
      
      
        To use this interface, a client MUST first subscribe using the
        Subscribe method. The subscription
        mechanic aims at reducing network traffic and memory footprint in the
        situation where nobody is currently interesting in provided
        information.
      
      
        Protocol often have different level of Mail Notification support. To
        make it more explicit, the interface provides a property called
        Capabilities. Possible value are
        described by Mail_Notification_Flags. Not all
        combinations are valid. We can regroup the mail notification in four
        different combinations.
      
      
        1) Supports_Unread_Mail_Count only:
        
        This flag is generally combined with other flags, but provides
        sufficient information to be usefull. The mail count is supported
        by most protocols including MSN, Yahoo and Google Talk. It allows 
        a UI to permanantly display messages like 'GMail: 4 unread messages'.
      
      
        2) Emist_Mails_Received only:
        
        In this case, the CM does not keep track of any mails. It simply emits
        information whenever they arrived to it. Those events may be used for
        short term display (like notification popup) to inform the user. No
        protocol is known to only supported this single feature, but it is
        useful for certain library integration that does not implement
        tracking of count or have a buggy counter implementation.
        
          It's always better to remove a feature then enabling one that does
          not behave properly.
        
      
      
        3) Supports_Unread_Mail_Count and Supports_Unread_Mails:
        
        This allow full state recovery of unread mail status. It is provided
        by Google XMPP Mail Notification Extension. With this set of flag,
        a client could have same display has case 1, and have let's say a
        plus button to show more detailed information. Refer to
        Mail documentation for the list of details that
        MAY be provided.
      
      
        4) Supports_Unread_Mail_Count and Emits_Mails_Received
        
        This is the most common level of support, it is provided by protocols
        like MSN and Yahoo. This would result in a combination of case 1 and 2
        where the client could display a counter and real-time notification.
      
      
        In case 1, 3 and 4, client SHOULD connect to signal
        UnreadMailsChanged to get updated with
        latest value of UnreadMailCount. In
        case 3, this signal also provides updates of
        UnreadMails property.
      
      
        In case 2 and 4, client MAY connect to signal
        MailsReceived to get real-time
        notification about newly arrived e-mails.
      
      
        Other independant features promoted within the
        Capabilities are the RequestSomethingURL
        methods. Those requests are used to obtain authentication free URL that
        will allow client to open web base mail client. Those capabilities
        are all optional, but flag Supports_Request_Inbox_URL is
        recommanded for case 1, 3 and 4. Flag 
        Supports_Request_Mail_URL is mostly usefull for case 1, 3
        and 4, but client SHOULD fallback to Inbox URL if missing. Finally,
        flag Supports_Request_Compose_URL is a special feature that
        allow accessing the mail creation web interface with a single click.
        This feature is simply optional.
      
      
        When done with this interface, client SHOULD call
        Unsubscribe. If no more clients are
        subscribed, the CM will then be able to free any uneeded memory and
        reduce network traffic.
      
    """

    def __init__(self):
        self._interfaces.add('org.freedesktop.Telepathy.Connection.Interface.MailNotification.DRAFT')

    @dbus.service.method('org.freedesktop.Telepathy.Connection.Interface.MailNotification.DRAFT', in_signature='', out_signature='')
    def Subscribe(self):
        """
        This method subscribes a client to the notification interface. This
          MUST be called by clients before using this interface.

        The CM tracks a subscription count (like a refcount) for each
          unique bus name that has called Subscribe(). When a client calls
          Unsubscribe(), it releases one "reference". If a client exits
          (or crash), it releases all of its "references".

        
            The reference count imposed on the subscription SHOULD simplify
            implementation of client running in the same process
            (e.g. plug-ins). Two plug-ins interested in mail notification can
            call Subscribe independently without relying on the CM to handle
            this particular action.
        

        
            This method exists to initiate real time messages in the case
            at least one client is subscribed. This may also be used to reduce
            memory and network overhead when there is no active subscription.
            An example of protocol that benifits from this method is the
            Google XMPP Mail Notification extension. In this protocol, the CM
            receives a notification telling that something has changed. To get
            more information, the CM must request this information. Knowing
            that nobody is currently interested in this information, the CM
            can avoid generating useless network traffic. In the same situation,
            the CM may free the list of unread messages and reduce memory
            overhead.
        

      
        """
        raise NotImplementedError
  
    @dbus.service.method('org.freedesktop.Telepathy.Connection.Interface.MailNotification.DRAFT', in_signature='', out_signature='')
    def Unsubscribe(self):
        """
        This method unsubscribes a client from the notification interface.
        This SHOULD be called when a client no longer need the mail
        notification interface.
        
          When the last client unsubscribe from this interface, the CM may
          free any uneeded data and reduce network traffic. See
          Unsubscribe for more rationale on
          this topic.
        
      
        """
        raise NotImplementedError
  
    @dbus.service.method('org.freedesktop.Telepathy.Connection.Interface.MailNotification.DRAFT', in_signature='', out_signature='(sua(ss))')
    def RequestInboxURL(self):
        """
        This method creates and returns an URL and an optionnal POST data that
        allow openning the Inbox folder of your Web mail account. This URL may
        contains token with short lifetime. Thus, a client SHOULD NOT reuse it
        and request a new URL whenever it is needed. This method is implemented
        only if Supports_Request_Inbox_URL flag is set in
        Capabilities.
        
          We are NOT using properties here because the tokens MAY NOT be shared
          between clients and that network may be required to obtain the
          information that leads to authentication free Web access.
        
      
        """
        raise NotImplementedError
  
    @dbus.service.method('org.freedesktop.Telepathy.Connection.Interface.MailNotification.DRAFT', in_signature='ss', out_signature='(sua(ss))')
    def RequestMailURL(self, ID, URL_Data):
        """
        This method creates and return a URL and optionnal POST data that
        allow openning specific mail of your Web mail account. Refer to
        RequestInboxURL for rationale. This
        method is implemented only if Supports_Request_Mail_URL flag
        is set in Capabilities.
      
        """
        raise NotImplementedError
  
    @dbus.service.method('org.freedesktop.Telepathy.Connection.Interface.MailNotification.DRAFT', in_signature='', out_signature='(sua(ss))')
    def RequestComposeURL(self):
        """
        This method assembles and returns an URL and optional POST data that
        allow openning the mail compositer page of your Web mail account.
        This method is implemented only if Supports_Request_Compose_URL
        flag is set in Capabilities.
        
          The goal is to allow a Web mail user to have the same level of
          integration as if he were using a native mail client.
        
      
        """
        raise NotImplementedError
  
    @dbus.service.signal('org.freedesktop.Telepathy.Connection.Interface.MailNotification.DRAFT', signature='aa{sv}')
    def MailsReceived(self, Mails):
        """
        Emitted when new e-mails messages arrive to the inbox associated with
        this connection. This signal is used for protocol that are NOT able
        to maintained UnreadMails list but
        receives real-time notification about newly arrived e-mails. It MAY be
        emited only if Emits_Mails_Received flag is set in
        Capabilities.
      
        """
        pass
  
    @dbus.service.signal('org.freedesktop.Telepathy.Connection.Interface.MailNotification.DRAFT', signature='uaa{sv}as')
    def UnreadMailsChanged(self, Count, Mails_Added, Mails_Removed):
        """
        Emitted when UnreadMails or
        UnreadMailCount have changed. It MAY be
        emited only if Supports_Unread_Mail_Count flag is set in
        Capabilities. mails_added and
        mails_removed MAY NOT be empty list if 
        Supports_Unread_Mails flag is set.
      
        """
        pass
  