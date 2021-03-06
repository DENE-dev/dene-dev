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

import aiohttp
import asyncio
import json
import sys
import logging
import weakref
import datetime
from email.utils import parsedate_to_datetime

log = logging.getLogger(__name__)

from .errors import HTTPException, Forbidden, NotFound, LoginFailure, GatewayNotFound
from . import __version__, utils

@asyncio.coroutine
def json_or_text(response):
    text = yield from response.text(encoding='utf-8')
    if response.headers['content-type'] == 'application/json':
        return json.loads(text)
    return text

class Route:
    BASE = 'https://discordapp.com/api/v7'

    def __init__(self, method, path, **parameters):
        self.path = path
        self.method = method
        url = (self.BASE + self.path)
        if parameters:
            self.url = url.format(**parameters)
        else:
            self.url = url

        # major parameters:
        self.channel_id = parameters.get('channel_id')
        self.guild_id = parameters.get('guild_id')

    @property
    def bucket(self):
        # the bucket is just method + path w/ major parameters
        return '{0.method}:{0.channel_id}:{0.guild_id}:{0.path}'.format(self)

class MaybeUnlock:
    def __init__(self, lock):
        self.lock = lock
        self._unlock = True

    def __enter__(self):
        return self

    def defer(self):
        self._unlock = False

    def __exit__(self, type, value, traceback):
        if self._unlock:
            self.lock.release()

class HTTPClient:
    """Represents an HTTP client sending HTTP requests to the Discord API."""

    SUCCESS_LOG = '{method} {url} has received {text}'
    REQUEST_LOG = '{method} {url} with {json} has returned {status}'

    def __init__(self, connector=None, *, loop=None):
        self.loop = asyncio.get_event_loop() if loop is None else loop
        self.connector = connector
        self._session = aiohttp.ClientSession(connector=connector, loop=self.loop)
        self._locks = weakref.WeakValueDictionary()
        self._global_over = asyncio.Event(loop=self.loop)
        self._global_over.set()
        self.token = None
        self.bot_token = False

        user_agent = 'DiscordBot (https://github.com/Rapptz/discord.py {0}) Python/{1[0]}.{1[1]} aiohttp/{2}'
        self.user_agent = user_agent.format(__version__, sys.version_info, aiohttp.__version__)

    @asyncio.coroutine
    def request(self, route, *, header_bypass_delay=None, **kwargs):
        bucket = route.bucket
        method = route.method
        url = route.url

        lock = self._locks.get(bucket)
        if lock is None:
            lock = asyncio.Lock(loop=self.loop)
            if bucket is not None:
                self._locks[bucket] = lock

        # header creation
        headers = {
            'User-Agent': self.user_agent,
        }

        if self.token is not None:
            headers['Authorization'] = 'Bot ' + self.token if self.bot_token else self.token

        # some checking if it's a JSON request
        if 'json' in kwargs:
            headers['Content-Type'] = 'application/json'
            kwargs['data'] = utils.to_json(kwargs.pop('json'))

        kwargs['headers'] = headers

        if not self._global_over.is_set():
            # wait until the global lock is complete
            yield from self._global_over.wait()

        yield from lock
        with MaybeUnlock(lock) as maybe_lock:
            for tries in range(5):
                r = yield from self._session.request(method, url, **kwargs)
                log.debug(self.REQUEST_LOG.format(method=method, url=url, status=r.status, json=kwargs.get('data')))
                try:
                    # even errors have text involved in them so this is safe to call
                    data = yield from json_or_text(r)

                    # check if we have rate limit header information
                    remaining = r.headers.get('X-Ratelimit-Remaining')
                    if remaining == '0' and r.status != 429:
                        # we've depleted our current bucket
                        if header_bypass_delay is None:
                            now = parsedate_to_datetime(r.headers['Date'])
                            reset = datetime.datetime.fromtimestamp(int(r.headers['X-Ratelimit-Reset']), datetime.timezone.utc)
                            delta = (reset - now).total_seconds()
                        else:
                            delta = header_bypass_delay

                        fmt = 'A rate limit bucket has been exhausted (bucket: {bucket}, retry: {delta}).'
                        log.info(fmt.format(bucket=bucket, delta=delta))
                        maybe_lock.defer()
                        self.loop.call_later(delta, lock.release)

                    # the request was successful so just return the text/json
                    if 300 > r.status >= 200:
                        log.debug(self.SUCCESS_LOG.format(method=method, url=url, text=data))
                        return data

                    # we are being rate limited
                    if r.status == 429:
                        fmt = 'We are being rate limited. Retrying in {:.2} seconds. Handled under the bucket "{}"'

                        # sleep a bit
                        retry_after = data['retry_after'] / 1000.0
                        log.info(fmt.format(retry_after, bucket))

                        # check if it's a global rate limit
                        is_global = data.get('global', False)
                        if is_global:
                            log.info('Global rate limit has been hit. Retrying in {:.2} seconds.'.format(retry_after))
                            self._global_over.clear()

                        yield from asyncio.sleep(retry_after, loop=self.loop)
                        log.debug('Done sleeping for the rate limit. Retrying...')

                        # release the global lock now that the
                        # global rate limit has passed
                        if is_global:
                            self._global_over.set()
                            log.debug('Global rate limit is now over.')

                        continue

                    # we've received a 502, unconditional retry
                    if r.status == 502 and tries <= 5:
                        yield from asyncio.sleep(1 + tries * 2, loop=self.loop)
                        continue

                    # the usual error cases
                    if r.status == 403:
                        raise Forbidden(r, data)
                    elif r.status == 404:
                        raise NotFound(r, data)
                    else:
                        raise HTTPException(r, data)
                finally:
                    # clean-up just in case
                    yield from r.release()

    def get(self, *args, **kwargs):
        return self.request('GET', *args, **kwargs)

    def put(self, *args, **kwargs):
        return self.request('PUT', *args, **kwargs)

    def patch(self, *args, **kwargs):
        return self.request('PATCH', *args, **kwargs)

    def delete(self, *args, **kwargs):
        return self.request('DELETE', *args, **kwargs)

    def post(self, *args, **kwargs):
        return self.request('POST', *args, **kwargs)

    # state management

    @asyncio.coroutine
    def close(self):
        yield from self._session.close()

    def _token(self, token, *, bot=True):
        self.token = token
        self.bot_token = bot
        self._ack_token = None

    # login management

    @asyncio.coroutine
    def static_login(self, token, *, bot):
        old_token, old_bot = self.token, self.bot_token
        self._token(token, bot=bot)

        try:
            data = yield from self.request(Route('GET', '/users/@me'))
        except HTTPException as e:
            self._token(old_token, bot=old_bot)
            if e.response.status == 401:
                raise LoginFailure('Improper token has been passed.') from e
            raise e

        return data

    def logout(self):
        return self.request(Route('POST', '/auth/logout'))

    # Group functionality

    def start_group(self, user_id, recipients):
        payload = {
            'recipients': recipients
        }

        return self.request(Route('POST', '/users/{user_id}/channels', user_id=user_id), json=payload)

    def leave_group(self, channel_id):
        return self.request(Route('DELETE', '/channels/{channel_id}', channel_id=channel_id))

    def add_group_recipient(self, channel_id, user_id):
        r = Route('PUT', '/channels/{channel_id}/recipients/{user_id}', channel_id=channel_id, user_id=user_id)
        return self.request(r)

    def remove_group_recipient(self, channel_id, user_id):
        r = Route('DELETE', '/channels/{channel_id}/recipients/{user_id}', channel_id=channel_id, user_id=user_id)
        return self.request(r)

    def edit_group(self, channel_id, **options):
        valid_keys = ('name', 'icon')
        payload = {
            k: v for k, v in options.items() if k in valid_keys
        }

        return self.request(Route('PATCH', '/channels/{channel_id}', channel_id=channel_id), json=payload)

    def convert_group(self, channel_id):
        return self.request(Route('POST', '/channels/{channel_id}/convert', channel_id=channel_id))

    # Message management

    def start_private_message(self, user_id):
        payload = {
            'recipient_id': user_id
        }

        return self.request(Route('POST', '/users/@me/channels'), json=payload)

    def send_message(self, channel_id, content, *, tts=False, embed=None):
        r = Route('POST', '/channels/{channel_id}/messages', channel_id=channel_id)
        payload = {}

        if content:
            payload['content'] = content

        if tts:
            payload['tts'] = True

        if embed:
            payload['embed'] = embed

        return self.request(r, json=payload)

    def send_typing(self, channel_id):
        return self.request(Route('POST', '/channels/{channel_id}/typing', channel_id=channel_id))

    def send_files(self, channel_id, *, files, content=None, tts=False, embed=None):
        r = Route('POST', '/channels/{channel_id}/messages', channel_id=channel_id)
        form = aiohttp.FormData()

        payload = {'tts': tts}
        if content:
            payload['content'] = content
        if embed:
            payload['embed'] = embed

        form.add_field('payload_json', utils.to_json(payload))
        if len(files) == 1:
            fp = files[0]
            form.add_field('file', fp[0], filename=fp[1], content_type='application/octet-stream')
        else:
            for index, (buffer, filename) in enumerate(files):
                form.add_field('file%s' % index, buffer, filename=filename, content_type='application/octet-stream')

        return self.request(r, data=form)

    @asyncio.coroutine
    def ack_message(self, channel_id, message_id):
        r = Route('POST', '/channels/{channel_id}/messages/{message_id}/ack', channel_id=channel_id,
                                                                          message_id=message_id)
        data = yield from self.request(r, json={'token': self._ack_token})
        self._ack_token = data['token']

    def ack_guild(self, guild_id):
        return self.request(Route('POST', '/guilds/{guild_id}/ack', guild_id=guild_id))

    def delete_message(self, channel_id, message_id):
        r = Route('DELETE', '/channels/{channel_id}/messages/{message_id}', channel_id=channel_id,
                                                                            message_id=message_id)
        return self.request(r)

    def delete_messages(self, channel_id, message_ids):
        r = Route('POST', '/channels/{channel_id}/messages/bulk_delete', channel_id=channel_id)
        payload = {
            'messages': message_ids
        }

        return self.request(r, json=payload)

    def edit_message(self, message_id, channel_id, **fields):
        r = Route('PATCH', '/channels/{channel_id}/messages/{message_id}', channel_id=channel_id,
                                                                           message_id=message_id)
        return self.request(r, json=fields)

    def add_reaction(self, message_id, channel_id, emoji):
        r = Route('PUT', '/channels/{channel_id}/messages/{message_id}/reactions/{emoji}/@me',
                  channel_id=channel_id, message_id=message_id, emoji=emoji)
        return self.request(r, header_bypass_delay=0.25)

    def remove_reaction(self, message_id, channel_id, emoji, member_id):
        r = Route('DELETE', '/channels/{channel_id}/messages/{message_id}/reactions/{emoji}/{member_id}',
                  channel_id=channel_id, message_id=message_id, member_id=member_id, emoji=emoji)
        return self.request(r, header_bypass_delay=0.25)

    def get_reaction_users(self, message_id, channel_id, emoji, limit, after=None):
        r = Route('GET', '/channels/{channel_id}/messages/{message_id}/reactions/{emoji}',
                         channel_id=channel_id, message_id=message_id, emoji=emoji)

        params = {'limit': limit}
        if after:
            params['after'] = after
        return self.request(r, params=params)

    def clear_reactions(self, message_id, channel_id):
        r = Route('DELETE', '/channels/{channel_id}/messages/{message_id}/reactions',
                  channel_id=channel_id, message_id=message_id)

        return self.request(r)

    def get_message(self, channel_id, message_id):
        r = Route('GET', '/channels/{channel_id}/messages/{message_id}', channel_id=channel_id, message_id=message_id)
        return self.request(r)

    def logs_from(self, channel_id, limit, before=None, after=None, around=None):
        params = {
            'limit': limit
        }

        if before:
            params['before'] = before
        if after:
            params['after'] = after
        if around:
            params['around'] = around

        return self.request(Route('GET', '/channels/{channel_id}/messages', channel_id=channel_id), params=params)

    def pin_message(self, channel_id, message_id):
        return self.request(Route('PUT', '/channels/{channel_id}/pins/{message_id}',
                            channel_id=channel_id, message_id=message_id))

    def unpin_message(self, channel_id, message_id):
        return self.request(Route('DELETE', '/channels/{channel_id}/pins/{message_id}',
                            channel_id=channel_id, message_id=message_id))

    def pins_from(self, channel_id):
        return self.request(Route('GET', '/channels/{channel_id}/pins', channel_id=channel_id))

    # Member management

    def kick(self, user_id, guild_id, reason=None):
        r = Route('DELETE', '/guilds/{guild_id}/members/{user_id}', guild_id=guild_id, user_id=user_id)
        if reason:
            return self.request(r, params={'reason': reason })
        return self.request(r, params=params)

    def ban(self, user_id, guild_id, delete_message_days=1, reason=None):
        r = Route('PUT', '/guilds/{guild_id}/bans/{user_id}', guild_id=guild_id, user_id=user_id)
        params = {
            'delete-message-days': delete_message_days,
        }
        if reason:
            params['reason'] = reason

        return self.request(r, params=params)

    def unban(self, user_id, guild_id):
        r = Route('DELETE', '/guilds/{guild_id}/bans/{user_id}', guild_id=guild_id, user_id=user_id)
        return self.request(r)

    def guild_voice_state(self, user_id, guild_id, *, mute=None, deafen=None):
        r = Route('PATCH', '/guilds/{guild_id}/members/{user_id}', guild_id=guild_id, user_id=user_id)
        payload = {}
        if mute is not None:
            payload['mute'] = mute

        if deafen is not None:
            payload['deaf'] = deafen

        return self.request(r, json=payload)

    def edit_profile(self, password, username, avatar, **fields):
        payload = {
            'password': password,
            'username': username,
            'avatar': avatar
        }

        if 'email' in fields:
            payload['email'] = fields['email']

        if 'new_password' in fields:
            payload['new_password'] = fields['new_password']

        return self.request(Route('PATCH', '/users/@me'), json=payload)

    def change_my_nickname(self, guild_id, nickname):
        payload = {
            'nick': nickname
        }
        return self.request(Route('PATCH', '/guilds/{guild_id}/members/@me/nick', guild_id=guild_id), json=payload)

    def change_nickname(self, guild_id, user_id, nickname):
        r = Route('PATCH', '/guilds/{guild_id}/members/{user_id}', guild_id=guild_id, user_id=user_id)
        payload = {
            'nick': nickname
        }
        return self.request(r, json=payload)

    def edit_member(self, guild_id, user_id, **fields):
        r = Route('PATCH', '/guilds/{guild_id}/members/{user_id}', guild_id=guild_id, user_id=user_id)
        return self.request(r, json=fields)

    # Channel management

    def edit_channel(self, channel_id, **options):
        valid_keys = ('name', 'topic', 'bitrate', 'user_limit', 'position')
        payload = {
            k: v for k, v in options.items() if k in valid_keys
        }

        return self.request(Route('PATCH', '/channels/{channel_id}', channel_id=channel_id), json=payload)

    def move_channel_position(self, guild_id, positions):
        r = Route('PATCH', '/guilds/{guild_id}/channels', guild_id=guild_id)
        return self.request(r, json=positions)

    def create_channel(self, guild_id, name, channe_type, permission_overwrites=None):
        payload = {
            'name': name,
            'type': channe_type
        }

        if permission_overwrites is not None:
            payload['permission_overwrites'] = permission_overwrites

        return self.request(Route('POST', '/guilds/{guild_id}/channels', guild_id=guild_id), json=payload)

    def delete_channel(self, channel_id):
        return self.request(Route('DELETE', '/channels/{channel_id}', channel_id=channel_id))

    # Guild management

    def leave_guild(self, guild_id):
        return self.request(Route('DELETE', '/users/@me/guilds/{guild_id}', guild_id=guild_id))

    def delete_guild(self, guild_id):
        return self.request(Route('DELETE', '/guilds/{guild_id}', guild_id=guild_id))

    def create_guild(self, name, region, icon):
        payload = {
            'name': name,
            'icon': icon,
            'region': region
        }

        return self.request(Route('POST', '/guilds'), json=payload)

    def edit_guild(self, guild_id, **fields):
        valid_keys = ('name', 'region', 'icon', 'afk_timeout', 'owner_id',
                      'afk_channel_id', 'splash', 'verification_level')

        payload = {
            k: v for k, v in fields.items() if k in valid_keys
        }

        return self.request(Route('PATCH', '/guilds/{guild_id}', guild_id=guild_id), json=payload)

    def get_bans(self, guild_id):
        return self.request(Route('GET', '/guilds/{guild_id}/bans', guild_id=guild_id))

    def get_vanity_code(self, guild_id):
        return self.request(Route('GET', '/guilds/{guild_id}/vanity-url', guild_id=guild_id))

    def change_vanity_code(self, guild_id, code):
        payload = { 'code': code }
        return self.request(Route('PATCH', '/guilds/{guild_id}/vanity-url', guild_id=guild_id), json=payload)

    def prune_members(self, guild_id, days):
        params = {
            'days': days
        }
        return self.request(Route('POST', '/guilds/{guild_id}/prune', guild_id=guild_id), params=params)

    def estimate_pruned_members(self, guild_id, days):
        params = {
            'days': days
        }
        return self.request(Route('GET', '/guilds/{guild_id}/prune', guild_id=guild_id), params=params)

    def create_custom_emoji(self, guild_id, name, image):
        payload = {
            'name': name,
            'image': image
        }

        r = Route('POST', '/guilds/{guild_id}/emojis', guild_id=guild_id)
        return self.request(r, json=payload)

    def delete_custom_emoji(self, guild_id, emoji_id):
        return self.request(Route('DELETE', '/guilds/{guild_id}/emojis/{emoji_id}', guild_id=guild_id, emoji_id=emoji_id))

    def edit_custom_emoji(self, guild_id, emoji_id, *, name):
        payload = {
            'name': name
        }
        r = Route('PATCH', '/guilds/{guild_id}/emojis/{emoji_id}', guild_id=guild_id, emoji_id=emoji_id)
        return self.request(r, json=payload)

    def get_audit_logs(self, guild_id, limit=100, before=None, after=None, user_id=None, action_type=None):
        params = { 'limit': limit }
        if before:
            params['before'] = before
        if after:
            params['after'] = after
        if user_id:
            params['user_id'] = user_id
        if action_type:
            params['action_type'] = action_type

        r = Route('GET', '/guilds/{guild_id}/audit-logs', guild_id=guild_id)
        return self.request(r, params=params)

    # Invite management

    def create_invite(self, channel_id, **options):
        r = Route('POST', '/channels/{channel_id}/invites', channel_id=channel_id)
        payload = {
            'max_age': options.get('max_age', 0),
            'max_uses': options.get('max_uses', 0),
            'temporary': options.get('temporary', False),
            'unique': options.get('unique', True)
        }

        return self.request(r, json=payload)

    def get_invite(self, invite_id):
        return self.request(Route('GET', '/invite/{invite_id}', invite_id=invite_id))

    def invites_from(self, guild_id):
        return self.request(Route('GET', '/guilds/{guild_id}/invites', guild_id=guild_id))

    def invites_from_channel(self, channel_id):
        return self.request(Route('GET', '/channels/{channel_id}/invites', channel_id=channel_id))

    def delete_invite(self, invite_id):
        return self.request(Route('DELETE', '/invite/{invite_id}', invite_id=invite_id))

    # Role management

    def edit_role(self, guild_id, role_id, **fields):
        r = Route('PATCH', '/guilds/{guild_id}/roles/{role_id}', guild_id=guild_id, role_id=role_id)
        valid_keys = ('name', 'permissions', 'color', 'hoist', 'mentionable')
        payload = {
            k: v for k, v in fields.items() if k in valid_keys
        }
        return self.request(r, json=payload)

    def delete_role(self, guild_id, role_id):
        r = Route('DELETE', '/guilds/{guild_id}/roles/{role_id}', guild_id=guild_id, role_id=role_id)
        return self.request(r)

    def replace_roles(self, user_id, guild_id, role_ids):
        return self.edit_member(guild_id=guild_id, user_id=user_id, roles=role_ids)

    def create_role(self, guild_id, **fields):
        r = Route('POST', '/guilds/{guild_id}/roles', guild_id=guild_id)
        return self.request(r, json=fields)

    def move_role_position(self, guild_id, positions):
        r = Route('PATCH', '/guilds/{guild_id}/roles', guild_id=guild_id)
        return self.request(r, json=positions)

    def add_role(self, guild_id, user_id, role_id):
        r = Route('PUT', '/guilds/{guild_id}/members/{user_id}/roles/{role_id}',
                  guild_id=guild_id, user_id=user_id, role_id=role_id)
        return self.request(r)

    def remove_role(self, guild_id, user_id, role_id):
        r = Route('DELETE', '/guilds/{guild_id}/members/{user_id}/roles/{role_id}',
                  guild_id=guild_id, user_id=user_id, role_id=role_id)
        return self.request(r)

    def edit_channel_permissions(self, channel_id, target, allow, deny, type):
        payload = {
            'id': target,
            'allow': allow,
            'deny': deny,
            'type': type
        }
        r = Route('PUT', '/channels/{channel_id}/permissions/{target}', channel_id=channel_id, target=target)
        return self.request(r, json=payload)

    def delete_channel_permissions(self, channel_id, target):
        r = Route('DELETE', '/channels/{channel_id}/permissions/{target}', channel_id=channel_id, target=target)
        return self.request(r)

    # Voice management

    def move_member(self, user_id, guild_id, channel_id):
        return self.edit_member(guild_id=guild_id, user_id=user_id, channel_id=channel_id)


    # Relationship related

    def remove_relationship(self, user_id):
        r = Route('DELETE', '/users/@me/relationships/{user_id}', user_id=user_id)
        return self.request(r)

    def add_relationship(self, user_id, type=None):
        r = Route('PUT', '/users/@me/relationships/{user_id}', user_id=user_id)
        payload = {}
        if type is not None:
            payload['type'] = type

        return self.request(r, json=payload)

    def send_friend_request(self, username, discriminator):
        r = Route('POST', '/users/@me/relationships')
        payload = {
            'username': username,
            'discriminator': int(discriminator)
        }
        return self.request(r, json=payload)

    # Misc

    def application_info(self):
        return self.request(Route('GET', '/oauth2/applications/@me'))

    @asyncio.coroutine
    def get_gateway(self):
        try:
            data = yield from self.request(Route('GET', '/gateway'))
        except HTTPException as e:
            raise GatewayNotFound() from e
        return data.get('url') + '?encoding=json&v=6'

    @asyncio.coroutine
    def get_bot_gateway(self):
        try:
            data = yield from self.request(Route('GET', '/gateway/bot'))
        except HTTPException as e:
            raise GatewayNotFound() from e
        else:
            return data['shards'], data['url'] + '?encoding=json&v=6'

    def get_user_info(self, user_id):
        return self.request(Route('GET', '/users/{user_id}', user_id=user_id))

    def get_user_profile(self, user_id):
        return self.request(Route('GET', '/users/{user_id}/profile', user_id=user_id))