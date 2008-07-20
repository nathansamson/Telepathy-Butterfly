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

import logging
import time

import telepathy
import pymsn

from butterfly.handle import ButterflyHandleFactory
from butterfly.util.decorator import async

__all__ = ['ButterflyPresence']

logger = logging.getLogger('Butterfly.Presence')

class ButterflyPresenceMapping(object):
    ONLINE = 'available'
    AWAY = 'away'
    BUSY = 'dnd'
    IDLE = 'xa'
    BRB = 'brb'
    PHONE = 'phone'
    LUNCH = 'lunch'
    INVISIBLE = 'hidden'
    OFFLINE = 'offline'

    to_pymsn = {
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

    to_telepathy = {
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


class ButterflyPresence(telepathy.server.ConnectionInterfacePresence,
        pymsn.event.ContactEventInterface,
        pymsn.event.ProfileEventInterface):

    def __init__(self):
        telepathy.server.ConnectionInterfacePresence.__init__(self)
        pymsn.event.ContactEventInterface.__init__(self, self.msn_client)
        pymsn.event.ProfileEventInterface.__init__(self, self.msn_client)

    def GetStatuses(self):
        # the arguments are in common to all on-line presences
        arguments = {'message' : 's'}

        # you get one of these for each status
        # {name:(type, self, exclusive, {argument:types}}
        return {
            ButterflyPresenceMapping.ONLINE:(
                telepathy.CONNECTION_PRESENCE_TYPE_AVAILABLE,
                True, True, arguments),
            ButterflyPresenceMapping.AWAY:(
                telepathy.CONNECTION_PRESENCE_TYPE_AWAY,
                True, True, arguments),
            ButterflyPresenceMapping.BUSY:(
                telepathy.CONNECTION_PRESENCE_TYPE_AWAY,
                True, True, arguments),
            ButterflyPresenceMapping.IDLE:(
                telepathy.CONNECTION_PRESENCE_TYPE_EXTENDED_AWAY,
                True, True, arguments),
            ButterflyPresenceMapping.BRB:(
                telepathy.CONNECTION_PRESENCE_TYPE_AWAY,
                True, True, arguments),
            ButterflyPresenceMapping.PHONE:(
                telepathy.CONNECTION_PRESENCE_TYPE_AWAY,
                True, True, arguments),
            ButterflyPresenceMapping.LUNCH:(
                telepathy.CONNECTION_PRESENCE_TYPE_EXTENDED_AWAY,
                True, True, arguments),
            ButterflyPresenceMapping.INVISIBLE:(
                telepathy.CONNECTION_PRESENCE_TYPE_HIDDEN,
                True, True, {}),
            ButterflyPresenceMapping.OFFLINE:(
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
        if status == ButterflyPresenceMapping.OFFLINE:
            self.Disconnect()

        presence = ButterflyPresenceMapping.to_pymsn[status]
        message = arguments.get('message', u'').encode("utf-8")

        logger.info("Setting Presence to '%s'" % presence)
        logger.info("Setting Personal message to '%s'" % message)

        if self._status != telepathy.CONNECTION_STATUS_CONNECTED:
            self._initial_presence = presence
            self._initial_personal_message = message
        else:
            self.msn_client.profile.personal_message = message
            self.msn_client.profile.presence = presence

    def get_presences(self, contacts):
        presences = {}
        for handle_id in contacts:
            handle = self.handle(telepathy.HANDLE_TYPE_CONTACT, handle_id)
            try:
                contact = handle.contact
            except AttributeError:
                contact = handle.profile

            if contact is not None:
                presence = ButterflyPresenceMapping.to_telepathy[contact.presence]
                personal_message = unicode(contact.personal_message, "utf-8")
            else:
                presence = ButterflyPresenceMapping.OFFLINE
                personal_message = u""

            arguments = {}
            if personal_message:
                arguments = {'message' : personal_message}

            presences[handle] = (0, {presence : arguments}) # TODO: Timestamp
        return presences

    # pymsn.event.ContactEventInterface
    def on_contact_presence_changed(self, contact):
        handle = ButterflyHandleFactory(self, 'contact',
                contact.account, contact.network_id)
        logger.info("Contact %r presence changed to '%s'" % (handle, contact.presence))
        self._presence_changed(handle, contact.presence, contact.personal_message)

    # pymsn.event.ContactEventInterface
    on_contact_personal_message_changed = on_contact_presence_changed

    # pymsn.event.ProfileEventInterface
    def on_profile_presence_changed(self):
        profile = self.msn_client.profile
        self._presence_changed(ButterflyHandleFactory(self, 'self'),
                profile.presence, profile.personal_message)

    # pymsn.event.ProfileEventInterface
    on_profile_personal_message_changed = on_profile_presence_changed

    @async
    def _presence_changed(self, handle, presence, personal_message):
        presence = ButterflyPresenceMapping.to_telepathy[presence]
        personal_message = unicode(personal_message, "utf-8")

        arguments = {}
        if personal_message:
            arguments = {'message' : personal_message}

        self.PresenceUpdate({handle: (int(time.time()), {presence:arguments})})
