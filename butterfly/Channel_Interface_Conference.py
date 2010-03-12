# -*- coding: utf-8 -*-
# Generated from the Telepathy spec
"""Copyright © 2009 Collabora Limited
Copyright © 2009 Nokia Corporation

    This library is free software; you can redistribute it and/or
      modify it under the terms of the GNU Lesser General Public
      License as published by the Free Software Foundation; either
      version 2.1 of the License, or (at your option) any later version.

    This library is distributed in the hope that it will be useful,
      but WITHOUT ANY WARRANTY; without even the implied warranty of
      MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
      Lesser General Public License for more details.

    You should have received a copy of the GNU Lesser General Public
      License along with this library; if not, write to the Free Software
      Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
      02110-1301, USA.
  
"""

import dbus.service

CHANNEL_INTERFACE_CONFERENCE = 'org.freedesktop.Telepathy.Channel.Interface.Conference.DRAFT'

class ChannelInterfaceConference(dbus.service.Interface):
    """\
      An interface for multi-user conference channels that can "continue
        from" one or more individual channels.

      
        This interface addresses freedesktop.org bug
            #24906 (GSM-compatible conference calls) and bug
            #24939 (upgrading calls and chats to multi-user).
          See those bugs for rationale and use cases.

        Examples of usage:

        Active and held GSM calls C1, C2 can be merged into a single
          channel Cn with the Conference interface, by calling
          CreateChannel({...ChannelType: ...Call,
            ...InitialChannels: [C1, C2]})
          which returns Cn.

        An XMPP 1-1 conversation C1 can be continued in a newly created
          multi-user chatroom Cn by calling
          CreateChannel({...ChannelType: ...Text,
            ...InitialChannels: [C1]})
          which returns Cn.

        An XMPP 1-1 conversation C1 can be continued in a specified
          multi-user chatroom by calling
          CreateChannel({...ChannelType: ...Text, ...HandleType: ROOM,
            ...TargetID: 'telepathy@conf.example.com',
            ...InitialChannels: [C1]})
          which returns a Conference channel.

        Either of the XMPP cases could work for Call channels, to
          upgrade from 1-1 Jingle to multi-user Jingle. Any of the XMPP cases
          could in principle work for link-local XMPP (XEP-0174).

        The underlying switchboard representing an MSN 1-1 conversation C1
          with a contact X can be moved to a representation as a nameless
          chatroom, Cn, to which more contacts can be invited, by calling
          CreateChannel({...ChannelType: ...Text,
            ...InitialChannels: [C1]})
          which returns Cn. C1 SHOULD remain open, with no underlying
          switchboard attached. If X establishes a new switchboard with the
          local user, C1 SHOULD pick up that switchboard rather than letting
          it create a new channel.
          [FIXME: should it?]
          Similarly, if the local user sends a message in C1, then
          a new switchboard to X should be created and associated with C1.

        XMPP and MSN do not natively have a concept of merging two or more
          channels C1, C2... into one channel, Cn. However, the GSM-style
          merging API can be supported on XMPP and MSN, as an API short-cut
          for upgrading C1 into a conference Cn (which invites the
          TargetHandle of C1 into Cn), then immediately inviting the
          TargetHandle of C2, the TargetHandle of C3, etc. into Cn as well.

        With a suitable change of terminology, Skype has behaviour similar
          to MSN.
      

      The Group MAY have channel-specific handles for participants;
        clients SHOULD support both Conferences that have channel-specific handles,
        and those that do not.

      
        In the GSM case, the Conference's Group interface MAY have
          channel-specific handles, to reflect the fact that the identities of
          the participants might not be known - it can be possible to know that
          there is another participant in the Conference, but not know who
          they are.
          [FIXME: fact check from GSM gurus needed]
        

        In the XMPP case, the Conference's Group interface SHOULD have
          channel-specific handles, to reflect the fact that the participants
          have MUC-specific identities, and the user might also be able to see
          their global identities, or not.

        In most other cases, including MSN and link-local XMPP, the
          Conference's Group interface SHOULD NOT have channel-specific
          handles, since users' identities are always visible.
      

      Connection managers implementing channels with this interface
        MUST NOT allow the object paths of channels that could be merged
        into a Conference to be re-used, unless the channel re-using the
        object path is equivalent to the channel that previously used it.

      
        If you upgrade some channels into a conference, and then close
          the original channels, InitialChannels
          (which is immutable) will contain paths to channels which no longer
          exist. This implies that you should not re-use channel object paths,
          unless future incarnations of the path are equivalent.

        For instance, on protocols where you can only have
          zero or one 1-1 text channels with Emily at one time, it would
          be OK to re-use the same object path for every 1-1 text channel
          with Emily; but on protocols where this is not true, it would
          be misleading.
      

    """

    def __init__(self):
        self._interfaces.add('org.freedesktop.Telepathy.Channel.Interface.Conference.DRAFT')

    @dbus.service.signal('org.freedesktop.Telepathy.Channel.Interface.Conference.DRAFT', signature='o')
    def ChannelMerged(self, Channel):
        """
        Emitted when a new channel is added to the value of
          Channels.
      
        """
        pass
  
    @dbus.service.signal('org.freedesktop.Telepathy.Channel.Interface.Conference.DRAFT', signature='o')
    def ChannelRemoved(self, Channel):
        """
        Emitted when a channel is removed from the value of
          Channels, either because it closed
          or because it was split using the Splittable.DRAFT.Split method.

        [FIXME: relative ordering of this vs. Closed? Do we
            care?]
      
        """
        pass
  
