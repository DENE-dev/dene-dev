# Modified MIT License (MIT)
#
# Copyright (c) 2020 shroomdog27
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, and sublicense
# the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
import discord
from redbot.core import commands as Commands
from redbot.core import Config


class VCLoggerCog(Commands.Cog):
    """My custom cog"""

    def __init__(self):
        self.config = Config.get_conf(self, identifier=777761593677316458)
        default_guild = {"links": {}}

        self.config.register_guild(**default_guild)
        self.config.init_custom

    @Commands.group()
    @Commands.guild_only()
    async def vclog(self, ctx):
        """Root command for Voice Chat Logger Commands"""
        pass

    @vclog.command(name="link")
    async def vclog_link(self, ctx, vc_channel: discord.VoiceChannel, txt_channel: discord.TextChannel):
        """Links a Voice Chat Channel to a text Channel"""
        vc_id = vc_channel.id
        txt_id = txt_channel.id
        async with self.config.guild(ctx.guild).links() as links:
            links[vc_id] = txt_id
        await ctx.send(f"Successfully linked {vc_channel.name} to {txt_channel.name}")
        return

    @vclog.command(name="unlink")
    async def vclog_unlink(self, ctx, vc_channel: discord.VoiceChannel):
        """Unlinks a Voice Chat Channel"""
        vc_id = vc_channel.id
        txt_id = txt_channel.id
        async with self.config.guild(ctx.guild).links() as links:
            del links[vc_id]
        await ctx.send(f"Successfully unlinked {vc_channel.name}")
        return

    async def handle_channel_leave(self, member: discord.Member, before: discord.VoiceChannel):
        guild = before.guild
        try:
            async with self.config.guild(guild).links() as links:
                txt_id = links[str(before.id)]
        except KeyError as key_error:
            return
        text_channel = guild.get_channel(txt_id)
        await text_channel.send(f"{member.display_name} has left the channel.")
        return

    async def handle_channel_join(self, member: discord.Member, after: discord.VoiceChannel):
        guild = after.guild
        try:
            async with self.config.guild(guild).links() as links:
                txt_id = links[str(after.id)]
        except KeyError as key_error:
            return
        text_channel = guild.get_channel(txt_id)
        await text_channel.send(f"{member.display_name} has joined the channel.")
        return

    @Commands.Cog.listener()
    async def on_voice_state_update(
        self, member: discord.Member, before_state: discord.VoiceState, after_state: discord.VoiceState,
    ) -> None:
        before = before_state.channel
        after = after_state.channel
        if before is None:
            await self.handle_channel_join(member, after)
            return
        if after is None:
            await self.handle_channel_leave(member, before)
            return
        if before == after:
            return
        guild = before.guild
        await self.handle_channel_join(member, after)
        await self.handle_channel_leave(member, before)
        return