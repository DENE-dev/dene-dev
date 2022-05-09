import random
import traceback

import config
import discord
import humanize
from discord.ext import commands


class Events(commands.Cog, name="이벤트 리스너"):
    """여러 이벤트들을 핸들링"""
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print(self.bot.user)
        print(self.bot.user.id)
        print("Bot is ready.")

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        if isinstance(error, discord.NotFound) or isinstance(error, discord.Forbidden):
            return
        elif isinstance(error, commands.CommandNotFound) or isinstance(error, commands.NotOwner):
            rows = await self.bot.sql(
                0, f"SELECT * FROM `users` WHERE `user` = '{ctx.author.id}'")
            data = (await
                    self.bot.sql(0, f"SELECT * FROM `ark` WHERE `bot` = '{bot.user.id}'"))[0]
            if not rows:
                return await ctx.reply(
                    "🧭 이 명령어를 사용하려면 당신의 정보를 등록해야 합니다.\n`중운아 등록` 명령어를 사용해 등록할 수 있습니다."
                )
            elif rows[0]["permissions"] == "Banned":
                return await ctx.reply(
                    f"⚛ 당신은 `{bot.user.name}`의 시스템에서 차단되었습니다. 자세한 내용은 개발자에게 문의하세요.")
            elif (await self.bot.is_owner(ctx.author)) is True:
                if data["maintain"] == "true":
                    await ctx.reply("🔰 현재 점검 모드가 활성화되어 있습니다.")
            elif data["maintain"] == "true":
                return await ctx.reply(
                    f"🔰 현재 관리자에 의해 제한 모드가 활성화되어 있습니다.\n사유 : {data['reason']}")
            responses = await self.bot.sql(0, "SELECT * FROM `responses`")
            reply = random.choice(responses)
            await ctx.reply(f"💬 ...*'{reply['response']}'*")
        elif isinstance(error, commands.UserInputError):
            await ctx.reply("⛔ 입력한 값이 잘못되었습니다. 입력한 값을 확인하고 다시 시도하세요.")
        elif isinstance(error, commands.MissingPermissions):
            await ctx.reply("🎷 당신은 이 명령어를 사용할 권한이 없습니다.")
        elif isinstance(error, commands.BotMissingPermissions):
            await ctx.reply("🥁 봇이 이 명령어를 실행할 권한이 없습니다.")
        elif isinstance(error, commands.CommandOnCooldown):
            cooldown = []
            cooldown.append(f"{round(error.cooldown.per) // 3600}시간")
            left = round(error.cooldown.per) % 3600
            cooldown.append(f"{left // 60}분")
            cooldown.append(f"{left % 60}초")
            b = ""
            for i in cooldown:
                if not i.startswith("0"):
                    b += f"{i} "
            time = []
            time.append(f"{round(error.retry_after) // 3600}시간")
            left = round(error.retry_after) % 3600
            time.append(f"{left // 60}분")
            time.append(f"{left % 60}초")
            a = ""
            for i in time:
                if not i.startswith("0"):
                    a += f"{i} "
            await ctx.reply(
                f"📽 이 명령어는 `{b.strip()}`에 {humanize.intcomma(round(error.cooldown.rate))}번만 사용할 수 있습니다.\n`{a.strip()}` 후에 다시 시도해주세요."
            )
        elif isinstance(error, commands.NoPrivateMessage):
            await ctx.reply("📭 이 명령어는 개인 메시지에서 사용할 수 없습니다.")
        elif isinstance(error, commands.PrivateMessageOnly):
            await ctx.reply("✉️ 이 명령어는 개인 메시지에서만 사용할 수 있습니다.")
        elif isinstance(error, commands.CheckFailure):
            await ctx.reply(
                "🧭 이 명령어를 사용하려면 당신의 정보를 등록해야 합니다.\n`중운아 등록` 명령어를 사용해 등록할 수 있습니다."
            )
        else:
            exc = getattr(error, "original", error)
            lines = "".join(
                traceback.format_exception(exc.__class__, exc,
                                           exc.__traceback__))
            lines = f"{ctx.command}에 발생한 예외를 무시합니다;\n{lines}"
            channel = self.bot.get_channel(config.Debug)
            try:
                await channel.send(f"```{lines}```")
            except:
                record = await self.bot.record(lines)
                if isinstance(record, discord.File):
                    await channel.send(file=record)
                else:
                    await channel.send(record)
            await ctx.reply(f"🎬 {exc.__class__.__name__} 예외가 발생했습니다. 개발자에게 문의하세요.")

    @commands.Cog.listener()
    async def on_member_join(self, member):
        if member.bot:
            return

        rows = await self.bot.sql(0, f"SELECT * FROM `guilds` WHERE `guild` = '{member.guild.id}'")
        if not rows:
            return
        channel = self.bot.get_channel(int(rows[0]["welcome"]))
        if channel is not None:
            await channel.send(f"{member.mention}, 반가워.")


def setup(bot):
    bot.add_cog(Events(bot))