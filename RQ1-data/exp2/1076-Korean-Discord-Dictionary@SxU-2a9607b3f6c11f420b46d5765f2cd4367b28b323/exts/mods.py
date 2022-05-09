from discord.ext import commands
from discord_slash import cog_ext
from discord_slash.utils.manage_commands import create_option

class Moderator(commands.Cog, name="관리자"):
    def __init__(self, bot):
        self.bot = bot

    async def addModlog(self, type, victim, admin, reason):
        logs = await self.bot.sql(0, "SELECT * FROM `modlog` ORDER BY `case` DESC")
        case = 0
        if logs:
            case = int(logs[0]["case"]) + 1
        await self.bot.sql(1, "INSERT INTO `modlog`(`case`, `type`, `victim`, `admin`, `reason`, `timestamp`) VALUES('{case}', '{type}', '{victim.id}', '{admin.id}', '{reason}', '{now}')")

    @cog_ext.cog_slash(
        name="warn",
        description="유저에게 경고를 지급합니다.",
        options=[
            create_option(
                name="대상 유저",
                description="경고를 지급할 유저를 선택해주세요.",
                option_type=6,
                required=True,
            ),
            create_option(
                name="사유",
                description="경고 지급 사유를 지정해주세요.",
                option_type=3,
                required=False,
            ),
        ],
    )
    @commands.has_permissions(administrator=True)
    async def _warn(self, ctx, member: discord.Member, reason: str = "사유가 없어요."):
        await ctx.defer()
        await self.addModlog("warn", member, ctx.author, reason)
        await ctx.send(f"⚠️ {member}님에게 경고를 지급했어요.\n사유 : {reason}")

def setup(bot):
    bot.add_cog(Moderator(bot))