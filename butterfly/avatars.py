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

import logging
import imghdr
import sha
import dbus

import telepathy
import pymsn
import pymsn.event
import pymsn.util.string_io as StringIO

from butterfly.handle import ButterflyHandleFactory
from butterfly.util.decorator import async

__all__ = ['ButterflyAvatars']

logger = logging.getLogger('Butterfly.Avatars')


class ButterflyAvatars(\
        telepathy.server.ConnectionInterfaceAvatars,
        pymsn.event.ContactEventInterface):

    def __init__(self):
    	self._avatar_known = False
        telepathy.server.ConnectionInterfaceAvatars.__init__(self)
        pymsn.event.ContactEventInterface.__init__(self, self.msn_client)

    def GetAvatarRequirements(self):
        mime_types = ("image/png","image/jpeg","image/gif")
        return (mime_types, 96, 96, 192, 192, 500 * 1024)

    def GetKnownAvatarTokens(self, contacts):
        result = {}
        for handle_id in contacts:
            handle = self.handle(telepathy.HANDLE_TYPE_CONTACT, handle_id)
            if handle == self.GetSelfHandle():
                contact = handle.profile
            else:
                contact = handle.contact

            if contact is not None:
                msn_object = contact.msn_object
            else:
                msn_object = None
            
            if msn_object is not None:
                result[handle] = msn_object._data_sha.encode("hex")
            elif self._avatar_known:
                result[handle] = ""
        return result

    def RequestAvatars(self, contacts):
        for handle_id in contacts:
            handle = self.handle(telepathy.HANDLE_TYPE_CONTACT, handle_id)
            if handle == self.GetSelfHandle():
                msn_object = handle.profile.msn_object
                if msn_object is not None:
                    self._msn_object_retrieved(msn_object, handle)
            else:
                contact = handle.contact
                if contact is not None:
                    msn_object = contact.msn_object
                else:
                    msn_object = None
                if msn_object is not None:
                    self.msn_client.msn_object_store.request(msn_object,\
                            (self._msn_object_retrieved, handle))

    def SetAvatar(self, avatar, mime_type):
        self._avatar_known = True
        if not isinstance(avatar, str):
            avatar = "".join([chr(b) for b in avatar])
        msn_object = pymsn.p2p.MSNObject(self.msn_client.profile, 
                         len(avatar),
                         pymsn.p2p.MSNObjectType.DISPLAY_PICTURE,
                         sha.new(avatar).hexdigest() + '.tmp',
                         "",
                         data=StringIO.StringIO(avatar))
        self.msn_client.profile.msn_object = msn_object
        avatar_token = msn_object._data_sha.encode("hex")
        logger.info("Setting self avatar to %s" % avatar_token)
        self._self_msn_object_changed(avatar_token)
        return avatar_token

    def ClearAvatar(self):
        self.msn_client.profile.msn_object = None
        self._avatar_known = True

    # pymsn.event.ContactEventInterface
    def on_contact_msn_object_changed(self, contact):
        if contact.msn_object is not None:
            avatar_token = contact.msn_object._data_sha.encode("hex")
        else:
            avatar_token = ""
        handle = ButterflyHandleFactory(self, 'contact',
                contact.account, contact.network_id)
        self.AvatarUpdated(handle, avatar_token)

    @async
    def _self_msn_object_changed(self, avatar_token):
        handle = ButterflyHandleFactory(self, 'self')
        self.AvatarUpdated(handle, avatar_token)
        self._msn_object_retrieved(self.msn_client.profile.msn_object, handle)

    @async
    def _msn_object_retrieved(self, msn_object, handle):
        if msn_object._data is not None:
            msn_object._data.seek(0, 0)
            avatar = msn_object._data.read()
            msn_object._data.seek(0, 0)
            type = imghdr.what('', avatar)
            if type is None: type = 'jpeg'
            avatar = dbus.ByteArray(avatar)
            token = msn_object._data_sha.encode("hex")
            self.AvatarRetrieved(handle, token, avatar, 'image/' + type)
