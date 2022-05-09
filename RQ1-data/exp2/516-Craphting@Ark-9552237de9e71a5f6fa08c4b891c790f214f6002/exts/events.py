import traceback

import config
import discord
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
        if isinstance(error, commands.CommandNotFound):
            return
        elif isinstance(error, commands.NotOwner):
            await ctx.reply("💣 이 명령어는 봇 소유자만 사용할 수 있습니다.")
        elif isinstance(error, commands.UserInputError):
            await ctx.reply("⛔ 입력한 값이 잘못되었습니다. 입력한 값을 확인하고 다시 시도하세요.")
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
        elif isinstance(error, commands.CheckFailure):
            await ctx.reply(
                "🧭 이 명령어를 사용하려면 당신의 정보를 등록해야 합니다.\n`아크 등록` 명령어를 사용해 등록하세요.")
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
            await ctx.reply(f"🎬 {exc.__class__.__name__}; 개발자 혹은 관리자에게 문의하세요.")


def setup(bot):
    bot.add_cog(Events(bot))