# -*- coding: utf-8 -*-

"""
The MIT License (MIT)

Copyright (c) 2015-2017 Rapptz

Permission is hereby granted, free of charge, to any person obtaining a
copy of this software and associated documentation files (the "Software"),
to deal in the Software without restriction, including without limitation
the rights to use, copy, modify, merge, publish, distribute, sublicense,
and/or sell copies of the Software, and to permit persons to whom the
Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
DEALINGS IN THE SOFTWARE.
"""

import asyncio

from .permissions import Permissions
from .colour import Colour
from .mixins import Hashable
from .utils import snowflake_time

class Role(Hashable):
    """Represents a Discord role in a :class:`Guild`.

    Supported Operations:

    +-----------+------------------------------------------------------------------+
    | Operation |                           Description                            |
    +===========+==================================================================+
    | x == y    | Checks if two roles are equal.                                   |
    +-----------+------------------------------------------------------------------+
    | x != y    | Checks if two roles are not equal.                               |
    +-----------+------------------------------------------------------------------+
    | x > y     | Checks if a role is higher than another in the hierarchy.        |
    +-----------+------------------------------------------------------------------+
    | x < y     | Checks if a role is lower than another in the hierarchy.         |
    +-----------+------------------------------------------------------------------+
    | x >= y    | Checks if a role is higher or equal to another in the hierarchy. |
    +-----------+------------------------------------------------------------------+
    | x <= y    | Checks if a role is lower or equal to another in the hierarchy.  |
    +-----------+------------------------------------------------------------------+
    | hash(x)   | Return the role's hash.                                          |
    +-----------+------------------------------------------------------------------+
    | str(x)    | Returns the role's name.                                         |
    +-----------+------------------------------------------------------------------+

    Attributes
    ----------
    id: int
        The ID for the role.
    name: str
        The name of the role.
    permissions: :class:`Permissions`
        Represents the role's permissions.
    guild: :class:`Guild`
        The guild the role belongs to.
    colour: :class:`Colour`
        Represents the role colour. An alias exists under ``color``.
    hoist: bool
         Indicates if the role will be displayed separately from other members.
    position: int
        The position of the role. This number is usually positive. The bottom
        role has a position of 0.
    managed: bool
        Indicates if the role is managed by the guild through some form of
        integrations such as Twitch.
    mentionable: bool
        Indicates if the role can be mentioned by users.
    """

    __slots__ = ('id', 'name', 'permissions', 'color', 'colour', 'position',
                 'managed', 'mentionable', 'hoist', 'guild', '_state' )

    def __init__(self, *, guild, state, data):
        self.guild = guild
        self._state = state
        self.id = int(data['id'])
        self._update(data)

    def __str__(self):
        return self.name

    def __repr__(self):
        return '<Role id={0.id} name={0.name!r}>'.format(self)

    def __lt__(self, other):
        if not isinstance(other, Role) or not isinstance(self, Role):
            return NotImplemented

        if self.guild != other.guild:
            raise RuntimeError('cannot compare roles from two different guilds.')

        if self.position < other.position:
            return True

        if self.position == other.position:
            return int(self.id) > int(other.id)

        return False

    def __le__(self, other):
        r = Role.__lt__(other, self)
        if r is NotImplemented:
            return NotImplemented
        return not r

    def __gt__(self, other):
        return Role.__lt__(other, self)

    def __ge__(self, other):
        r = Role.__lt__(self, other)
        if r is NotImplemented:
            return NotImplemented
        return not r

    def _update(self, data):
        self.name = data['name']
        self.permissions = Permissions(data.get('permissions', 0))
        self.position = data.get('position', 0)
        self.colour = Colour(data.get('color', 0))
        self.hoist = data.get('hoist', False)
        self.managed = data.get('managed', False)
        self.mentionable = data.get('mentionable', False)
        self.color = self.colour

    def is_default(self):
        """Checks if the role is the default role."""
        return self.guild.id == self.id

    @property
    def created_at(self):
        """Returns the role's creation time in UTC."""
        return snowflake_time(self.id)

    @property
    def mention(self):
        """Returns a string that allows you to mention a role."""
        return '<@&{}>'.format(self.id)

    @property
    def members(self):
        """Returns a list of :class:`Member` with this role."""
        all_members = self.guild.members
        if self.is_default():
            return all_members

        return [member for member in all_members if self in member.roles]

    @asyncio.coroutine
    def _move(self, position):
        if position <= 0:
            raise InvalidArgument("Cannot move role to position 0 or below")

        if self.is_default():
            raise InvalidArgument("Cannot move default role")

        if self.position == position:
            return  # Save discord the extra request.

        http = self._state.http

        change_range = range(min(self.position, position), max(self.position, position) + 1)
        sorted_roles = sorted((x for x in self.guild.roles if x.position in change_range and x.id != self.id),
                              key=lambda x: x.position)

        roles = [r.id for r in sorted_roles]

        if self.position > position:
            roles.insert(0, self.id)
        else:
            roles.append(self.id)

        payload = [{"id": z[0], "position": z[1]} for z in zip(roles, change_range)]
        yield from http.move_role_position(self.guild.id, payload)

    @asyncio.coroutine
    def edit(self, **fields):
        """|coro|

        Edits the role.

        You must have the :attr:`Permissions.manage_roles` permission to
        use this.

        All fields are optional.

        Parameters
        -----------
        name: str
            The new role name to change to.
        permissions: :class:`Permissions`
            The new permissions to change to.
        colour: :class:`Colour`
            The new colour to change to. (aliased to color as well)
        hoist: bool
            Indicates if the role should be shown separately in the member list.
        mentionable: bool
            Indicates if the role should be mentionable by others.
        position: int
            The new role's position. This must be below your top role's
            position or it will fail.

        Raises
        -------
        Forbidden
            You do not have permissions to change the role.
        HTTPException
            Editing the role failed.
        InvalidArgument
            An invalid position was given or the default
            role was asked to be moved.
        """

        position = fields.get('position')
        if position is not None:
            yield from self._move(position)
            self.position = position

        try:
            colour = fields['colour']
        except KeyError:
            colour = fields.get('color', self.colour)

        payload = {
            'name': fields.get('name', self.name),
            'permissions': fields.get('permissions', self.permissions).value,
            'color': colour.value,
            'hoist': fields.get('hoist', self.hoist),
            'mentionable': fields.get('mentionable', self.mentionable)
        }

        data = yield from self._state.http.edit_role(self.guild.id, self.id, **payload)
        self._update(data)

    @asyncio.coroutine
    def delete(self):
        """|coro|

        Deletes the role.

        You must have the :attr:`Permissions.manage_roles` permission to
        use this.

        Raises
        --------
        Forbidden
            You do not have permissions to delete the role.
        HTTPException
            Deleting the role failed.
        """

        yield from self._state.http.delete_role(self.guild.id, self.id)