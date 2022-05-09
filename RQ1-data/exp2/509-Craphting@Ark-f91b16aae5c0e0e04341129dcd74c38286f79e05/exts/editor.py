import asyncio
import discord
from discord.ext import commands


class Settings(commands.Cog, name="설정"):
    """개인 설정부터 범용 설정까지 모두"""
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="등록")
    async def _register(self, ctx):
        rows = await self.bot.sql(
            0, f"SELECT * FROM `users` WHERE `user` = '{ctx.author.id}'")
        if rows:
            return await ctx.reply("🕋 승인되지 않은 접근입니다. 데이터 등록 값이 이미 존재합니다.")
        req = await ctx.reply(f"""
🎹 등록을 완료하려면 아래 내용을 읽고 `확인`이라고 입력해주세요.

{self.bot.user.name}의 원활한 작동을 위해 아래 정보가 수집됩니다.
자세한 개인정보 수집 내용 및 데이터 삭제는 봇 관리자에게 문의해주세요.
```diff
+ 수집되는 정보
+ 사용한 명령어의 기록
+ 유저 고유 정보
+ 사용한 서버의 정보

- 수집하지 않는 정보
- 위에서 명시하지 모든 정보
```
""")

        def check(msg):
            return (msg.author == ctx.author and msg.channel == ctx.channel
                    and msg.content == "확인")

        try:
            msg = await self.bot.wait_for("message", timeout=30, check=check)
        except:
            await req.edit(content="🧲 요청이 취소되었습니다.", delete_after=5)
        else:
            try:
                await msg.delete()
            except:
                pass
            stocks = await self.bot.sql(0, "SELECT `id` FROM `stocks`")
            temp = "`user`, `money`, `optout`"
            temp2 = f"'{ctx.author.id}', '500000', 'false'"
            for stock in stocks:
                temp += f", {stock['id']}"
                temp2 += f", '0'"
            await self.bot.sql(1,
                               f"INSERT INTO `users`({temp}) VALUES({temp2})")
            await req.edit(
                content="🖨 당신의 등록 요청이 성공적으로 처리되었습니다.")

    @commands.group(name="채널")
    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)
    async def channels(self, ctx):
        if ctx.invoked_subcommand is None:
            raise commands.UserInputError

    @channels.command(name="로그")
    @commands.has_permissions(manage_guild=True)
    @commands.bot_has_permissions(manage_webhooks=True)
    async def _log(self, ctx, channel: discord.TextChannel):
        webhook = await channel.create_webhook(name="중운 로그", avatar=self.bot.user.avatar_url.read())
        await self.bot.sql(1, f"UPDATE `guilds` SET `log` = '{webhook.url}' WHERE `guild` = '{ctx.guild.id}'")
        await ctx.reply(f"❄ 이제 {channel.mention} 채널에 이벤트 로깅을 시작합니다.")

    @channels.command(name="환영")
    @commands.has_permissions(manage_guild=True)
    async def _welcome(self, ctx, channel: discord.TextChannel):
        if not ctx.guild.me.permissions_in(channel).send_messages:
            return await ctx.reply("🥝 해당 채널에는 메시지를 보낼 수 없어 취소되었습니다.")
        await self.bot.sql(1, f"UPDATE `guilds` SET `welcome` = '{channel.id}' WHERE `guild` = '{ctx.guild.id}'")
        await ctx.reply(f"🍞 이제 유저가 입장 시 {channel.mention} 채널에 짧은 인사말을 출력합니다.")

    @commands.group(name="역할")
    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)
    async def roles(self, ctx):
        if ctx.invoked_subcommand is None:
            raise commands.UserInputError

    @roles.command(name="뮤트")
    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)
    @commands.bot_has_permissions(manage_channels=True, manage_roles=True)
    async def _muteRole(self, ctx):
        role = await ctx.guild.create_role(name="채팅 제한", color=0x777777, reason="뮤트 기능 설정")
        for category in ctx.guild.categories:
            await category.set_permission(role, overwrite=discord.PermissionOverwrite(send_messages=False, add_reactions=False, send_tts_messages=False, speak=False, video=False, request_to_speak=False))
        for text in ctx.guild.text_channels:
            await text.set_permission(role, overwrite=discord.PermissionOverwrite(send_messages=False, add_reactions=False, send_tts_messages=False))
        for voice in ctx.guild.voice_channels:
            await voice.set_permission(role, overwrite=discord.PermissionOverwrite(speak=False, video=False))
        for stage in ctx.guild.stage_channels:
            await voice.set_permission(role, overwrite=discord.PermissionOverwrite(request_to_speak=False))
        await self.bot.sql(1, f"UPDATE `guilds` SET `mute` = '{role.id}' WHERE `guild` = '{ctx.guild.id}'")
        await ctx.reply(f"🍏 뮤트 설정이 완료되었습니다. {role.mention} 역할이 생성되었습니다.")

    @roles.command(name="DJ", aliases=["Dj", "dj"])
    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)
    async def _djRole(self, ctx, role: discord.Role):
        await self.bot.sql(1, f"UPDATE `guilds` SET `dj` = '{role.id}' WHERE `guild` = '{ctx.guild.id}'")
        await ctx.reply(f"🍒 {role.name} 역할로 DJ 역할을 설정했습니다.")

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        rows = await self.bot.sql(0, f"SELECT * FROM `guilds` WHERE `guild` = '{ctx.guild.id}'")
        if not rows:
            await self.bot.sql(1, f"INSERT INTO `guilds`(`guild`, `mute`, `log`, `welcome`, `dj`, `voicemaster`) VALUES('{guild.id}', '1234', 'asdf', '1234', '1234', '1234')")
        try:
            await guild.owner.send("🛶 Ark 프로젝트와 함께 해주셔서 감사합니다!\n \n지원이 필요하시다면 아래 지원 서버로 접속해주세요. https://discord.gg/qqfb9HdUwS")
        except:
            pass


def setup(bot):
    bot.add_cog(Settings(bot))