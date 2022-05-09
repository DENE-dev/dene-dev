import discord
from discord.ext import commands


class VoiceMaster(commands.Cog, name="임시 채널 생성"):
    def __init__(self, bot):
        self.bot = bot

    def is_moderator(**perms):
        original = commands.has_permissions(**perms).predicate

        async def predicate(ctx):
            rows = await ctx.bot.sql(
                0, f"SELECT * FROM `staffrole` WHERE `guild` = '{ctx.guild.id}'"
            )
            if not rows:
                return await original(ctx)
            ids = []
            for row in rows:
                ids.append(int(row["role"]))
            for role in ctx.author.roles:
                if role.id in ids:
                    return True
            return await original(ctx)

        return commands.check(predicate)

    async def getVM(self, guild, channel):
        rows = await self.bot.sql(
            0, f"SELECT * FROM `voicemaker` WHERE `guild` = '{guild.id}' AND `channel` = '{channel.id}'"
        )
        if not rows:
            return
        return row[0]

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if before.channel != after.channel:
            if before.channel is None:
                pass
            else:
                sql = await self.bot.sql(
                    0, f"SELECT * FROM `voicemaster` WHERE `id` = '{before.channel.id}'"
                )
                if not sql:
                    pass
                elif before.channel.members:
                    pass
                else:
                    await self.bot.sql(
                        1,
                        f"DELETE FROM `voicemaster` WHERE `id` = '{before.channel.id}'",
                    )
                    try:
                        await before.channel.delete(
                            reason="VoiceMaster - 음성 채널이 비어서 자동 삭제되었습니다."
                        )
                    except:
                        pass

        if after.channel is not None:
            data = await self.getVM(member.guild, after.channel)
            if data is not None:
                category = after.channel.category
                if category is None:
                    return
                else:
                    naming = member.name
                    if member.nick is not None:
                        naming = member.nick
                    try:
                        voice = None
                        if data["naming"] == "Default":
                            voice = await category.create_voice_channel(
                                name=f"{naming}님의 채널",
                                reason=f"VoiceMaster - {member}님이 채널 생성을 요청했습니다.",
                            )
                        else:
                            name = data["naming"].replace("[유저]", naming)
                            voice = await category.create_voice_channel(
                                name=name,
                                reason=f"VoiceMaster - {member}님이 채널 생성을 요청했습니다.",
                            )
                        await voice.set_permissions(
                            member,
                            overwrite=discord.PermissionOverwrite(
                                view_channel=True,
                                manage_channels=True,
                                manage_permissions=True,
                                connect=True,
                            ),
                        )
                        await voice.set_permissions(
                            member.guild.me,
                            overwrite=discord.PermissionOverwrite(
                                view_channel=True,
                                manage_channels=True,
                                manage_permissions=True,
                            ),
                        )
                        await member.move_to(
                            voice, reason=f"VoiceMaster - {member}님이 채널 생성을 요청했습니다."
                        )
                    except:
                        return
                    else:
                        await self.bot.sql(
                            1,
                            f"INSERT INTO `voicemaster`(`id`, `owner`) VALUES('{voice.id}', '{member.id}')",
                        )

    @commands.group(name="음성", hidden=True)
    @commands.guild_only()
    async def voiceMaster(self, ctx):
        if ctx.invoked_subcommand is None:
            return

    @voiceMaster.command(name="초기화")
    @commands.guild_only()
    @is_moderator(manage_channels=True)
    @commands.bot_has_permissions(manage_channels=True, manage_roles=True)
    async def _setup(self, ctx):
        overwrites = {
            ctx.guild.me: discord.PermissionOverwrite(
                view_channel=True, manage_channels=True, manage_permissions=True
            ),
        }
        category = await ctx.guild.create_category(
            name="음성 채널", overwrites=overwrites, reason="VoiceMaster - 기본 설정 작업"
        )
        voice = await category.create_voice_channel(
            name="🥠ㅣ채널 만들기", overwrites=overwrites, reason="VoiceMaster - 기본 설정 작업"
        )
        await self.bot.sql(
            1,
            f"INSERT INTO `voicemaker`(`guild`, `channel`, `naming`) VALUES('{ctx.guild.id}', '{voice.id}', 'Default')",
        )
        await ctx.reply(
            f"🥠 {voice.mention} 채널이 생성되었습니다! 카테고리를 변경하려면 이 채널을 옮겨주세요."
        )

    @voiceMaster.command(name="잠금")
    @commands.guild_only()
    @commands.cooldown(rate=1, per=30, type=commands.BucketType.user)
    @commands.bot_has_permissions(manage_channels=True, manage_permissions=True)
    async def _lockdown(self, ctx):
        if not ctx.author.voice:
            return await ctx.reply("🎡 이 명령어를 사용하려면 음성 채널에 있어야 합니다.")
        rows = await self.bot.sql(
            0,
            f"SELECT * FROM `voicemaster` WHERE `id` = '{ctx.author.voice.channel.id}'",
        )
        if not rows:
            return await ctx.reply("🥨 이 명령어는 생성된 음성 채널에서만 사용 가능합니다.")
        elif int(rows[0]["owner"]) != ctx.author.id:
            return await ctx.reply("🥐 이 명령어는 자신이 소유자인 음성 채널에서만 사용 가능합니다.")
        await ctx.author.voice.channel.set_permissions(
            ctx.guild.default_role,
            overwrite=discord.PermissionOverwrite(connect=False),
            reason=f"VoiceMaster - {ctx.author}님이 채널 잠금을 요청했습니다.",
        )
        await ctx.reply(f"🥠 당신의 채널에 대한 `@everyone`의 접근을 거부했습니다.")

    @voiceMaster.command(name="해제")
    @commands.guild_only()
    @commands.cooldown(rate=1, per=30, type=commands.BucketType.user)
    @commands.bot_has_permissions(manage_channels=True, manage_permissions=True)
    async def _unlock(self, ctx):
        if not ctx.author.voice:
            return await ctx.reply("🎡 이 명령어를 사용하려면 음성 채널에 있어야 합니다.")
        rows = await self.bot.sql(
            0,
            f"SELECT * FROM `voicemaster` WHERE `id` = '{ctx.author.voice.channel.id}'",
        )
        if not rows:
            return await ctx.reply("🥨 이 명령어는 생성된 음성 채널에서만 사용 가능합니다.")
        elif int(rows[0]["owner"]) != ctx.author.id:
            return await ctx.reply("🥐 이 명령어는 자신이 소유자인 음성 채널에서만 사용 가능합니다.")
        await ctx.author.voice.channel.set_permissions(
            ctx.guild.default_role,
            overwrite=None,
            reason=f"VoiceMaster - {ctx.author}님이 채널 잠금 해제를 요청했습니다.",
        )
        await ctx.reply(
            f"🥠 당신의 채널에 대한 `@everyone`의 접근 권한을 초기화했습니다.\n채널에서 차단당한 유저는 승인 전까지 계속해서 접근할 수 없습니다."
        )

    @voiceMaster.command(name="이름")
    @commands.guild_only()
    @commands.cooldown(rate=1, per=300, type=commands.BucketType.user)
    @commands.bot_has_permissions(manage_channels=True)
    async def _naming(self, ctx, *, new_name):
        if not ctx.author.voice:
            return await ctx.reply("🎡 이 명령어를 사용하려면 음성 채널에 있어야 합니다.")
        rows = await self.bot.sql(
            0,
            f"SELECT * FROM `voicemaster` WHERE `id` = '{ctx.author.voice.channel.id}'",
        )
        if not rows:
            return await ctx.reply("🥨 이 명령어는 생성된 음성 채널에서만 사용 가능합니다.")
        elif int(rows[0]["owner"]) != ctx.author.id:
            return await ctx.reply("🥐 이 명령어는 자신이 소유자인 음성 채널에서만 사용 가능합니다.")
        await ctx.author.voice.channel.edit(
            name=new_name, reason=f"VoiceMaster - {ctx.author}님이 채널 이름 변경을 요청했습니다."
        )
        await ctx.reply(f"🥠 당신의 채널 이름을 `{new_name}`(으)로 변경했습니다.")

    @voiceMaster.command(name="차단")
    @commands.guild_only()
    @commands.cooldown(rate=1, per=30, type=commands.BucketType.user)
    @commands.bot_has_permissions(manage_channels=True, manage_roles=True)
    async def _disconnect(self, ctx, member: discord.Member):
        if not ctx.author.voice:
            return await ctx.reply("🎡 이 명령어를 사용하려면 음성 채널에 있어야 합니다.")
        rows = await self.bot.sql(
            0,
            f"SELECT * FROM `voicemaster` WHERE `id` = '{ctx.author.voice.channel.id}'",
        )
        if not rows:
            return await ctx.reply("🥨 이 명령어는 생성된 음성 채널에서만 사용 가능합니다.")
        elif int(rows[0]["owner"]) != ctx.author.id:
            return await ctx.reply("🥐 이 명령어는 자신이 소유자인 음성 채널에서만 사용 가능합니다.")
        elif member == ctx.author:
            return await ctx.reply("🍅 자신의 음성 채널에서 자신을 차단할 수 없습니다.")
        if member.voice:
            if member.voice.channel == ctx.author.voice.channel:
                try:
                    await member.move_to(
                        None, reason=f"VoiceMaster - {ctx.author}님이 채널에서 추방을 요청했습니다."
                    )
                except:
                    return await ctx.reply("🥁 봇이 이 명령어를 실행할 권한이 없습니다.")
        await ctx.author.voice.channel.set_permissions(
            member,
            overwrite=discord.PermissionOverwrite(connect=False),
            reason=f"VoiceMaster - {ctx.author}님이 채널에서 추방을 요청했습니다.",
        )
        await ctx.reply(f"🥠 당신의 채널에서 `{member}`님을 차단했습니다.")

    @voiceMaster.command(name="승인")
    @commands.guild_only()
    @commands.cooldown(rate=1, per=30, type=commands.BucketType.user)
    @commands.bot_has_permissions(manage_channels=True, manage_roles=True)
    async def _add(self, ctx, member: discord.Member):
        if not ctx.author.voice:
            return await ctx.reply("🎡 이 명령어를 사용하려면 음성 채널에 있어야 합니다.")
        rows = await self.bot.sql(
            0,
            f"SELECT * FROM `voicemaster` WHERE `id` = '{ctx.author.voice.channel.id}'",
        )
        if not rows:
            return await ctx.reply("🥨 이 명령어는 생성된 음성 채널에서만 사용 가능합니다.")
        elif int(rows[0]["owner"]) != ctx.author.id:
            return await ctx.reply("🥐 이 명령어는 자신이 소유자인 음성 채널에서만 사용 가능합니다.")
        elif member == ctx.author:
            return await ctx.reply("🍅 자신의 음성 채널에 자신을 승인할 필요는 없습니다.")
        await ctx.author.voice.channel.set_permissions(
            member,
            overwrite=discord.Overwrite(connect=True),
            reason=f"VoiceMaster - {ctx.author}님이 채널에서 접근 승인을 요청했습니다.",
        )
        await ctx.reply(f"🥠 당신의 채널에서 `{member}`님의 접근을 승인했습니다.")

    @voiceMaster.command(name="제한")
    @commands.guild_only()
    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @commands.bot_has_permissions(manage_channels=True)
    async def _limit(self, ctx, limit: int):
        if not ctx.author.voice:
            return await ctx.reply("🎡 이 명령어를 사용하려면 음성 채널에 있어야 합니다.")
        rows = await self.bot.sql(
            0,
            f"SELECT * FROM `voicemaster` WHERE `id` = '{ctx.author.voice.channel.id}'",
        )
        if not rows:
            return await ctx.reply("🥨 이 명령어는 생성된 음성 채널에서만 사용 가능합니다.")
        elif int(rows[0]["owner"]) != ctx.author.id:
            return await ctx.reply("🥐 이 명령어는 자신이 소유자인 음성 채널에서만 사용 가능합니다.")
        elif ctx.author.voice.channel.user_limit == limit:
            return await ctx.reply("🥑 이미 최대 입장 멤버 수가 {limit}명입니다.")
        elif limit > 99:
            return await ctx.reply("🍓 채널의 최대 입장 멤버 수는 0명(무제한)부터 99명까지만 설정할 수 있습니다.")
        await ctx.author.voice.channel.edit(
            user_limit=limit, reason=f"VoiceMaster - {ctx.author}님이 채널 인원 수 제한을 요청했습니다."
        )
        await ctx.reply(f"🥠 당신의 채널 최대 입장 멤버 수를 {limit}명으로 설정했습니다.")

    @voiceMaster.command(name="비트")
    @commands.guild_only()
    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @commands.bot_has_permissions(manage_channels=True)
    async def _bitrate(self, ctx, bitrate: int):
        maxs = [96, 128, 256, 384]
        if not ctx.author.voice:
            return await ctx.reply("🎡 이 명령어를 사용하려면 음성 채널에 있어야 합니다.")
        rows = await self.bot.sql(
            0,
            f"SELECT * FROM `voicemaster` WHERE `id` = '{ctx.author.voice.channel.id}'",
        )
        if not rows:
            return await ctx.reply("🥨 이 명령어는 생성된 음성 채널에서만 사용 가능합니다.")
        elif int(rows[0]["owner"]) != ctx.author.id:
            return await ctx.reply("🥐 이 명령어는 자신이 소유자인 음성 채널에서만 사용 가능합니다.")
        elif ctx.author.voice.channel.user_limit == bitrate:
            return await ctx.reply("🥑 이미 채널의 비트레이트가 {bitrate}kbps입니다.")
        elif bitrate > maxs[ctx.guild.premium_tier] or bitrate < 8:
            return await ctx.reply(
                f"🍓 채널의 비트레이트는 8kbps부터 {maxs[ctx.guild.premium_tier]}kbps까지만 설정할 수 있습니다."
            )
        await ctx.author.voice.channel.edit(
            bitrate=(bitrate * 1000),
            reason=f"VoiceMaster - {ctx.author}님이 채널 비트레이트 변경을 요청했습니다.",
        )
        await ctx.reply(f"🥠 당신의 채널 비트레이트를 `{bitrate}kbps`로 설정했습니다.")

    @voiceMaster.command(name="얻기")
    @commands.guild_only()
    @commands.cooldown(rate=1, per=30, type=commands.BucketType.user)
    @commands.bot_has_permissions(manage_channels=True, manage_roles=True)
    async def _claim(self, ctx):
        if not ctx.author.voice:
            return await ctx.reply("🎡 이 명령어를 사용하려면 음성 채널에 있어야 합니다.")
        rows = await self.bot.sql(
            0,
            f"SELECT * FROM `voicemaster` WHERE `id` = '{ctx.author.voice.channel.id}'",
        )
        if not rows:
            return await ctx.reply("🥨 이 명령어는 생성된 음성 채널에서만 사용 가능합니다.")
        elif int(rows[0]["owner"]) == ctx.author.id:
            return await ctx.reply("🥐 이 채널은 이미 당신의 채널입니다.")
        owner = ctx.guild.get_member(int(rows[0]["owner"]))
        if owner is not None and owner in ctx.author.voice.channel.members:
            return await ctx.reply("🍑 이 채널의 소유자가 아직 채널에 입장해 있습니다.")
        if owner is not None:
            await ctx.author.voice.channel.set_permissions(owner, overwrite=None)
        await ctx.author.voice.channel.set_permissions(
            ctx.author,
            overwrite=discord.PermissionOverwrite(
                view_channel=True,
                manage_channels=True,
                manage_permissions=True,
                connect=True,
                mute_members=True,
                deafen_members=True,
            ),
        )
        await self.bot.sql(
            1,
            f"UPDATE `voicemaster` SET `owner` = '{ctx.author.id}' WHERE `id` = '{ctx.author.voice.channel.id}'",
        )
        await ctx.reply(f"🥠 이제 {ctx.author.voice.channel.mention} 채널은 당신에게 귀속됩니다.")


def setup(bot):
    bot.add_cog(VoiceMaster(bot))