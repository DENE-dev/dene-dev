import discord
from discord.ext import commands


class Events(commands.Cog, name="이벤트"):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print(self.bot.user)
        print(self.bot.user.id)
        print("Project SxU, Ready.")

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        return

    @commands.Cog.listener()
    async def on_slash_command_error(self, ctx, error):
        if isinstance(error, commands.NotOwner) or isinstance(error, commands.MissingPermissions):
            return await ctx.send(f"🛠 **{ctx.author}**님은 이 명령어를 사용할 권한이 없어요.", hidden=True)
        exc = getattr(error, "original", error)
        lines = "".join(
            traceback.format_exception(exc.__class__, exc,
                                       exc.__traceback__))
        lines = f"{ctx.command}에 발생한 예외를 무시합니다;\n{lines}"
        channel = self.bot.get_channel(config.Debug)
        try:
            await self.bot.log(f"```py\n{lines}```", avatar_url=self.bot.user.avatar_url, name=f"{self.bot.user.name} 디버깅")
        except:
                record = await self.bot.record(lines)
                if isinstance(record, discord.File):
                    await self.bot.log(file=record, avatar_url=self.bot.user.avatar_url, name=f"{self.bot.user.name} 디버깅")
                else:
                    await self.bot.log(record, avatar_url=self.bot.user.avatar_url, name=f"{self.bot.user.name} 디버깅")
        await ctx.send(f"🕹 명령어를 실행하던 도중에 오류가 발생했어요.\n자세한 내용은 명령어 사용 기록과 함께 개발자에게 문의해주세요.", hidden=True)


def setup(bot):
    bot.add_cog(Events(bot))