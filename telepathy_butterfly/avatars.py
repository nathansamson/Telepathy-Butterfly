# telepathy-butterfly - an MSN connection manager for Telepathy
#
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
import logging
import imghdr
import dbus
import base64
import sha

import pymsn.util.StringIO as StringIO

logger = logging.getLogger('telepathy-butterfly:avatars')

class ButterflyConnectionAvatars(\
    telepathy.server.ConnectionInterfaceAvatars):

    def GetAvatarRequirements(self):
        mime_types = ("image/png","image/jpeg","image/gif")
        return (mime_types, 96, 96, 192, 192, 500 * 1024)

    def GetKnownAvatarTokens(self, contacts):
        result = {}
        for handle_id in contacts:
            handle = self._handle_manager.handle_for_handle_id(
                telepathy.HANDLE_TYPE_CONTACT, handle_id)
            if handle == self.GetSelfHandle():
                msn_object = self._pymsn_client.profile.msn_object
            else:
                msn_object = self._contact_for_handle(handle).msn_object
            if msn_object is not None:
                result[handle] = base64.b64encode(msn_object._data_sha)
            else:
                result[handle] = ""
        return result

    def RequestAvatars(self, contacts):
        def __on_msn_object_data_retrieved(msn_object):
            handle = self._handle_for_contact(msn_object._creator)
            if msn_object._data is not None:
                avatar = msn_object._data.read()
                type = imghdr.what('', avatar)
                if type is None: type = 'jpeg'
                avatar = dbus.ByteArray(avatar)
                token = base64.b64encode(msn_object._data_sha)

                self.AvatarRetrieved(handle, token, avatar, 'image/'+type)

        for handle_id in contacts:
            handle = self._handle_manager.handle_for_handle_id(
                telepathy.HANDLE_TYPE_CONTACT, handle_id)
            if handle == self.GetSelfHandle():
                msn_object = self._pymsn_client.profile.msn_object
                if msn_object is not None:
                    __on_msn_object_data_retrieved(msn_object)
            else:
                msn_object = self._contact_for_handle(handle).msn_object
                if msn_object is not None:
                    self._pymsn_client._msn_object_store.request(msn_object,\
                            (__on_msn_object_data_retrieved,))

    def SetAvatar(self, avatar, mime_type):
        if not isinstance(avatar, str):
            avatar = "".join([chr(b) for b in avatar])
        msn_object = pymsn.p2p.MSNObject(self._pymsn_client.profile, 
                         len(avatar),
                         pymsn.p2p.MSNObjectType.DISPLAY_PICTURE,
                         sha.new(avatar).hexdigest() + '.tmp',
                         "",
                         data=StringIO.StringIO(avatar))
        self._pymsn_client.profile.msn_object = msn_object
        avatar_token = base64.b64encode(msn_object._data_sha)
        gobject.idle_add(self.self_msn_object_changed, avatar_token)
        return avatar_token

    def ClearAvatar(self):
        self._pymsn_client.profile.msn_object = None

    def contact_msn_object_changed(self, contact):
        if contact.msn_object is not None:
            avatar_token = base64.b64encode(contact.msn_object._data_sha)
        else:
            avatar_token = ""
        handle = self._handle_for_contact(contact)
        self.AvatarUpdated(handle, avatar_token)

    def self_msn_object_changed(self, avatar_token):
        handle = self._handle_manager.handle_for_self(None)
        self.AvatarUpdated(handle, avatar_token)
        return False
    


