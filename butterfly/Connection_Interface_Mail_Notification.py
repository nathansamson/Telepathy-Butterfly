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
        account associated with this connection.

      In protocols where this is possible, this interface also allows the
        connection manager to provide the necessary information for clients
        to open a web-based mail client without having to re-authenticate.

      To use this interface, a client MUST first subscribe using the
        Subscribe method. The subscription
        mechanic aims at reducing network traffic and memory footprint in the
        situation where nobody is currently interesting in provided
        information. When done with this interface, clients SHOULD call
        Unsubscribe to release resources in
        the CM.

      Protocols have various different levels of Mail Notification support.
        To describe the level of support, the interface provides a property
        called MailNotificationFlags.
        Not all combinations are valid; protocols can be divided into four
        categories as follows.

      Connections to the most capable protocols, such as Google's XMPP Mail
        Notification extension, have the Supports_Unread_Mails flag (this
        implies that they must also have Supports_Unread_Mail_Count, but not
        Emits_Mails_Received). On these connections, clients
        requiring change notification MUST monitor the
        UnreadMailsChanged signal, and
        either recover the initial state from the
        UnreadMails property (if they require
        details other than the number of mails) or the
        UnreadMailCount property (if they
        are only interested in the number of unread mails). The
        MailsReceived signal is never emitted
        on these connections, so clients that will display a short-term
        notification for each new mail MUST do so in response to emission of
        the UnreadMailsChanged signal.

      The most common situation, seen in protocols like MSN and Yahoo, is
        that the number of unread mails is provided and kept up-to-date,
        and a separate notification is emitted with some details of each new
        mail. This is a combination of the following two features, and clients
        SHOULD implement one or both as appropriate for their requirements.

      On protocols that have the Emits_Mails_Received flag (which implies
        that they do not have Supports_Unread_Mails), the CM does not keep
        track of any mails; it simply emits a notification whenever new mail
        arrives. Those events may be used for short term display (like a
        notification popup) to inform the user. No protocol is known to support
        only this feature, but it is useful for integration with libraries that
        that do not implement tracking of the number of mails. Clients
        requiring these notifications MUST monitor the
        MailsReceived signal on any connections
        with this flag.

      On protocols that have the Supports_Unread_Mail_Count flag but not
        the Supports_Unread_Mails flag, clients cannot display complete
        details of unread email, but can display an up-to-date count of the
        number of unread mails. To do this, they must monitor the
        UnreadMailsChanged signal, and
        retrieve the initial state from the
        UnreadMailCount property.

      
        Orthogonal features described by the
        MailNotificationFlags property include the
        RequestSomethingURL methods, which are used to obtain URLs allowing
        clients to open a webmail client. Connections SHOULD support as many
        of these methods as possible.
    """

    def __init__(self):
        self._interfaces.add('org.freedesktop.Telepathy.Connection.Interface.MailNotification.DRAFT')

    @dbus.service.method('org.freedesktop.Telepathy.Connection.Interface.MailNotification.DRAFT', in_signature='', out_signature='')
    def Subscribe(self):
        """
        This method subscribes a client to the notification interface. This
          MUST be called by clients before using this interface.

        The Connection tracks a subscription count (like a refcount) for
          each unique bus name that has called Subscribe(). When a client calls
          Unsubscribe(), it releases one "reference". If a client exits
          (or crashes), the Connection releases all "references" held on its
          behalf.

        
          The reference count imposed on the subscription simplifies
            implementation of client running in the same process
            (e.g. plug-ins): two plug-ins interested in mail notification can
            call Subscribe and Unsubscribe independently without interfering
            with each other.

          This method exists to reduce memory and network overhead when
            there is no active subscription. An example of a protocol that
            benefits from this method is the Google XMPP Mail Notification
            extension: in this protocol, the CM receives a notification
            that something has changed, but to get more information, the CM
            must request this information. Knowing that nobody is currently
            interested in this information, the CM can avoid generating
            useless network traffic. Similarly, the CM may free
            the list of unread messages to reduce memory overhead.
        

      
        """
        raise NotImplementedError
  
    @dbus.service.method('org.freedesktop.Telepathy.Connection.Interface.MailNotification.DRAFT', in_signature='', out_signature='')
    def Unsubscribe(self):
        """
        This method unsubscribes a client from the notification interface.
        This SHOULD be called by each client that has successfully called
        Subscribe when it no longer needs the mail notification interface.

        
          See Subscribe for rationale.
        
      
        """
        raise NotImplementedError
  
    @dbus.service.method('org.freedesktop.Telepathy.Connection.Interface.MailNotification.DRAFT', in_signature='', out_signature='(sua(ss))')
    def RequestInboxURL(self):
        """
        This method creates and returns a URL and an optional POST data that
        allow opening the Inbox folder of a webmail account. This URL MAY
        contain tokens with a short lifetime, so clients SHOULD request a new
        URL for each visit to the webmail interface. This method is implemented
        only if the Supports_Request_Inbox_URL flag is set in
        MailNotificationFlags.

        
          We are not using properties here because the tokens are unsuitable
          for sharing between clients, and network round-trips may be required
          to obtain the information that leads to authentication free webmail
          access.
        
      
        """
        raise NotImplementedError
  
    @dbus.service.method('org.freedesktop.Telepathy.Connection.Interface.MailNotification.DRAFT', in_signature='ss', out_signature='(sua(ss))')
    def RequestMailURL(self, ID, URL_Data):
        """
        This method creates and returns a URL and optional POST data that
        allow opening a specific mail in a webmail interface. This
        method is implemented only if Supports_Request_Mail_URL flag
        is set in MailNotificationFlags.
        
          See RequestInboxURL for design
          rationale.
        
      
        """
        raise NotImplementedError
  
    @dbus.service.signal('org.freedesktop.Telepathy.Connection.Interface.MailNotification.DRAFT', signature='aa{sv}')
    def MailsReceived(self, Mails):
        """
        Emitted when new e-mails messages arrive to the inbox associated with
        this connection. This signal is used for protocols that are not able
        to maintain the UnreadMails list, but
        do provide real-time notification about newly arrived e-mails. It MUST
        NOT be emitted unless Emits_Mails_Received is set in
        MailNotificationFlags.
      
        """
        pass
  
    @dbus.service.signal('org.freedesktop.Telepathy.Connection.Interface.MailNotification.DRAFT', signature='uaa{sv}as')
    def UnreadMailsChanged(self, Count, Mails_Added, Mails_Removed):
        """
        Emitted when UnreadMails or
          UnreadMailCount have changed. It MUST
          NOT be emited if Supports_Unread_Mail_Count flag is not set
          in MailNotificationFlags.

        Mails_Added and
          Mails_Removed MUST be empty if the
          Supports_Unread_Mails flag is not set.
      
        """
        pass
  