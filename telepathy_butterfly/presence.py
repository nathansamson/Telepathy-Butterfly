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
import logging

__all__ = ['ButterflyConnectionPresence']

logger = logging.getLogger('telepathy-butterfly:presence')

class ButterflyPresence(object):
    ONLINE = 'available'
    AWAY = 'away'
    BUSY = 'dnd'
    IDLE = 'xa'
    BRB = 'brb'
    PHONE = 'phone'
    LUNCH = 'lunch'
    INVISIBLE = 'hidden'
    OFFLINE = 'offline'

    telepathy_to_pymsn = {
            ONLINE:     pymsn.Presence.ONLINE,
            AWAY:       pymsn.Presence.AWAY,
            BUSY:       pymsn.Presence.BUSY,
            IDLE:       pymsn.Presence.IDLE,
            BRB:        pymsn.Presence.BE_RIGHT_BACK,
            PHONE:      pymsn.Presence.ON_THE_PHONE,
            LUNCH:      pymsn.Presence.OUT_TO_LUNCH,
            INVISIBLE:  pymsn.Presence.INVISIBLE,
            OFFLINE:    pymsn.Presence.OFFLINE
            }

    pymsn_to_telepathy = {
            pymsn.Presence.ONLINE:         ONLINE,
            pymsn.Presence.AWAY:           AWAY,
            pymsn.Presence.BUSY:           BUSY,
            pymsn.Presence.IDLE:           IDLE,
            pymsn.Presence.BE_RIGHT_BACK:  BRB,
            pymsn.Presence.ON_THE_PHONE:   PHONE,
            pymsn.Presence.OUT_TO_LUNCH:   LUNCH,
            pymsn.Presence.INVISIBLE:      INVISIBLE,
            pymsn.Presence.OFFLINE:        OFFLINE
            }

class ButterflyConnectionPresence(
        telepathy.server.ConnectionInterfacePresence):

    def GetStatuses(self):
        # the arguments are in common to all on-line presences
        arguments = {'message' : 's'}

        # you get one of these for each status
        # {name:(type, self, exclusive, {argument:types}}
        return {
            ButterflyPresence.ONLINE:(
                telepathy.CONNECTION_PRESENCE_TYPE_AVAILABLE,
                True, True, arguments),
            ButterflyPresence.AWAY:(
                telepathy.CONNECTION_PRESENCE_TYPE_AWAY,
                True, True, arguments),
            ButterflyPresence.BUSY:(
                telepathy.CONNECTION_PRESENCE_TYPE_AWAY,
                True, True, arguments),
            ButterflyPresence.IDLE:(
                telepathy.CONNECTION_PRESENCE_TYPE_EXTENDED_AWAY,
                True, True, arguments),
            ButterflyPresence.BRB:(
                telepathy.CONNECTION_PRESENCE_TYPE_AWAY,
                True, True, arguments),
            ButterflyPresence.PHONE:(
                telepathy.CONNECTION_PRESENCE_TYPE_AWAY,
                True, True, arguments),
            ButterflyPresence.LUNCH:(
                telepathy.CONNECTION_PRESENCE_TYPE_EXTENDED_AWAY,
                True, True, arguments),
            ButterflyPresence.INVISIBLE:(
                telepathy.CONNECTION_PRESENCE_TYPE_HIDDEN,
                True, True, {}),
            ButterflyPresence.OFFLINE:(
                telepathy.CONNECTION_PRESENCE_TYPE_OFFLINE,
                True, True, {})
        }

    def RequestPresence(self, contacts):
        presences = self.get_presences(contacts)
        self.PresenceUpdate(presences)

    def GetPresence(self, contacts):
        return self.get_presences(contacts)

    def SetStatus(self, statuses):
        status, arguments = statuses.items()[0]
        if status == ButterflyPresence.OFFLINE:
            self.Disconnect()

        presence = ButterflyPresence.telepathy_to_pymsn[status]
        message = arguments.get('message', u'').encode("utf-8")

        logger.debug("SetStatus: presence='%s', message='%s'" % (presence, message))
        if self._status != telepathy.CONNECTION_STATUS_CONNECTED:
            self._initial_presence = presence
            self._initial_personal_message = message
        else:
            self._pymsn_client.profile.personal_message = message
            self._pymsn_client.profile.presence = presence

    def get_presences(self, contacts):
        presences = {}
        for handle_id in contacts:
            handle = self._handle_manager.handle_for_handle_id(
                    telepathy.HANDLE_TYPE_CONTACT, handle_id)
            contact = self._contact_for_handle(handle)
            presence = ButterflyPresence.pymsn_to_telepathy[contact.presence]
            personal_message = unicode(contact.personal_message, "utf-8")

            arguments = {}
            if personal_message:
                arguments = {'message' : personal_message}

            presences[handle] = (0, {presence : arguments}) # TODO: Timestamp
        return presences

    def contact_presence_changed(self, contact):
        presence = ButterflyPresence.pymsn_to_telepathy[contact.presence]
        personal_message = unicode(contact.personal_message, "utf-8")
            
        arguments = {}
        if personal_message:
            arguments = {'message' : personal_message}
                
        handle = self._handle_manager.handle_for_contact(contact)
        self.PresenceUpdate({handle: (0, {presence:arguments})}) 

