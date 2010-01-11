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
        connection manager has the means to provide necessary
        information (URL, method, POST data) so that the client is 
        able to open the user's inbox and possibly individual messages without 
        having to re-authenticate. To use this interface, a client must first
        subscribe using the Subscribe method.

      When unread e-mails arrive into the into or unread e-mails are marked 
        read or deleted the
        UnreadMailsChanged signal
        will be emitted with the new value of
        UnreadMailCount, an array
        of new or modified mails and the list of removed e-mail unique IDs. 
        To open the web base mail client for the inbox folder or a specific
        mail client must call RequestInboxURL
        or RequestMailURL. Those methods
        will do proper actions to retreive the information and provide
        authentication free URL to the requested Web client interface.
      
      
        Some protocol may not be able to provide a list of unread e-mails
        but may provide some information about the messages received. On
        such protocols, the MailsReceived
        signal will also be emitted, with information about the e-mails.
        The protocol does not keep track of any of this information.
      
    """

    def __init__(self):
        self._interfaces.add('org.freedesktop.Telepathy.Connection.Interface.MailNotification.DRAFT')

    @dbus.service.method('org.freedesktop.Telepathy.Connection.Interface.MailNotification.DRAFT', in_signature='', out_signature='')
    def Subscribe(self):
        """
        This method subscribes a client to the notification interface. This
        should be called if a client wants to get notified of incoming
        e-mails. Before anyone subscribes to the interface, the connection
        manager should try to minimized memory usage and network traffic as
        much as possible. The Control Manager must detect client disconnection
        (e.g. in case of crash) and free resources that are no longer required.
      
        """
        raise NotImplementedError
  
    @dbus.service.method('org.freedesktop.Telepathy.Connection.Interface.MailNotification.DRAFT', in_signature='', out_signature='')
    def Unsubscribe(self):
        """
        This method unsubscribes a client from the notification interface. This
        should called if a client no longer wants tot get notified of incoming
        e-mails. When all the client has been Unsubscribed, the connection manager
        should free all non-required information and reduce network traffic. It must
        be possible to call Subscribe later.
      
        """
        raise NotImplementedError
  
    @dbus.service.method('org.freedesktop.Telepathy.Connection.Interface.MailNotification.DRAFT', in_signature='', out_signature='(sua(ss))')
    def RequestInboxURL(self):
        """
        This method create and return a URL and optionnal POST data that allow
        openning the Inbox folder of your Web mail account. This URL may 
        contains token with short life time. Thus, a client should not reuse it
        and request a new URL whenever it is needed.
        
          We are not using properties here because the tokens may not be shared
          between clients and that network may be required to obtain the
          information that leads to authentication free Web access.
        
      
        """
        raise NotImplementedError
  
    @dbus.service.method('org.freedesktop.Telepathy.Connection.Interface.MailNotification.DRAFT', in_signature='ss', out_signature='(sua(ss))')
    def RequestMailURL(self, id, url_data):
        """
        This method create and return a URL and optionnal POST data that allow
        openning specific mail of your Web mail account. Refer to 
        RequestInboxURL.
      
        """
        raise NotImplementedError
  
    @dbus.service.signal('org.freedesktop.Telepathy.Connection.Interface.MailNotification.DRAFT', signature='aa{sv}')
    def MailsReceived(self, mails):
        """
        Emitted when new e-mails messages arrive to the inbox associated with
        this connection. This signal is used for protocol that are not able
        to maintained UnreadMails list but
        receives real-time notification about newly arrived e-mails.
      
        """
        pass
  
    @dbus.service.signal('org.freedesktop.Telepathy.Connection.Interface.MailNotification.DRAFT', signature='uaa{sv}as')
    def UnreadMailsChanged(self, count, mails_added, mails_removed):
        """
        Emitted when UnreadMails or 
        UnreadMailCount have changed.
      
        """
        pass
  