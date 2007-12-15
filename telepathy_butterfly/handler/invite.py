# telepathy-butterfly - an MSN connection manager for Telepathy
#
# Copyright (C) 2007 Ali Sabil <ali.sabil@gmail.com>
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

import pymsn
import pymsn.event
import telepathy

__all__ = ['ButterflyInviteEventsHandler']

logger = logging.getLogger('telepathy-butterfly:event:invite')

class ButterflyInviteEventsHandler(pymsn.event.InviteEventInterface):
    def __init__(self, client, telepathy_connection):
        self._telepathy_connection = weakref.proxy(telepathy_connection)
        pymsn.event.InviteEventInterface.__init__(self, client)

    def on_invite_conversation(self, conversation):
        logger.debug("conversation invite")
        #FIXME: get rid of this crap and implement group support
        participants = conversation.participants 
        for p in participants:
            participant = p
            break
        handle = self._telepathy_connection._handle_manager.handle_for_contact(participant)
        channel = self._telepathy_connection._channel_manager.\
                channel_for_text(handle, conversation)
