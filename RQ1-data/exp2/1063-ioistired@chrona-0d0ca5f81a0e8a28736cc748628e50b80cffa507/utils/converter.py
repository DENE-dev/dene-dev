import re

import discord
from discord.ext.commands import Converter, clean_content, errors

# Using code provided by khazhyk under the MIT License
# © 2017 khazhyk
# https://github.com/khazhyk/dango.py/blob/53fde0538eb8ee063fb10fdf85c29eb7c3bbaae9/dango/plugins/common/converters.py

MESSAGE_ID_RE = re.compile(r'^(?:(?P<channel_id>[0-9]{15,21})[-/:])?(?P<message_id>[0-9]{15,21})$')
MESSAGE_LINK_RE = re.compile(
	r'^https?://(?:(ptb|canary)\.)?discord(?:app)?\.com/channels/'
	r'(?:([0-9]{15,21})|(@me))'
	r'/(?P<channel_id>[0-9]{15,21})/(?P<message_id>[0-9]{15,21})$')

class MessageId(Converter):
	"""Match message_id, channel-message_id, or jump url to a discord.Channel, message_id pair

	Author must be able to view the target channel.
	"""
	async def convert(self, ctx, argument):
		match = MESSAGE_ID_RE.match(argument) or MESSAGE_LINK_RE.match(argument)
		if not match:
			cleaned = await clean_content().convert(ctx, f"{argument} doesn't look like a message to me…")
			raise errors.BadArgument(cleaned)

		msg_id = int(match['message_id'])
		channel_id = int(match['channel_id'] or ctx.channel.id)
		channel = ctx.guild.get_channel(channel_id)
		if not channel:
			channel = ctx.bot.get_channel(channel_id)

		if not channel:
			raise errors.BadArgument(f'Channel {channel_id} not found.')

		if not channel.guild.me.permissions_in(channel).read_messages:
			raise errors.CheckFailure(f"I don't have permission to view channel {channel.mention}.")
		if not author or not channel.permissions_for(ctx.author).read_messages:
			raise errors.CheckFailure(f"You don't have permission to view channel {channel.mention}.")

		return (channel, msg_id)

class Message(Converter):
	"""Match message_id, channel-message_id, or jump url to a discord.Message"""
	async def convert(self, ctx, argument):
		channel, msg_id = await MessageId().convert(ctx, argument)

		msg = discord.utils.get(ctx.bot.cached_messages, id=msg_id)
		if msg is None:
			try:
				msg = await channel.fetch_message(msg_id)
			except discord.NotFound:
				raise errors.BadArgument(f'Message {msg_id} not found in channel {channel.mention}.')
			except discord.Forbidden:
				raise errors.CheckFailure(f"I don't have permission to view channel {channel.mention}.")
		elif msg.channel.id != channel.id:
			raise errors.BadArgument('Message not found.')
		return msg