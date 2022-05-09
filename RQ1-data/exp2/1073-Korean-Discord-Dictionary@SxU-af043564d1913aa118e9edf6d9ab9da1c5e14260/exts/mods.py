from datetime import datetime
import discord
from discord.ext import commands
from discord_slash import cog_ext
from discord_slash.utils.manage_commands import create_option
from pytz import utc, timezone
from discord_slash.utils.manage_components import create_select, create_select_option, create_button, create_actionrow, wait_for_component
from discord_slash.model import ButtonStyle

class Moderator(commands.Cog, name="관리자"):
    def __init__(self, bot):
        self.bot = bot

    async def addModlog(self, type, victim, admin, reason):
        now = datetime.utcnow()
        KST = timezone("Asia/Seoul")
        now = utc.localize(now).astimezone(KST)
        now = now.strftime("%Y년 %m월 %d일 %H시 %M분 %S초")
        logs = await self.bot.sql(0, "SELECT * FROM `modlog` ORDER BY `case` DESC")
        case = 0
        if logs:
            case = int(logs[0]["case"]) + 1
        await self.bot.sql(1, f"INSERT INTO `modlog`(`case`, `type`, `victim`, `admin`, `reason`, `timestamp`) VALUES('{case}', '{type}', '{victim.id}', '{admin.id}', '{reason}', '{now}')")

    @cog_ext.cog_slash(
        name="warn",
        description="유저에게 경고를 지급합니다.",
        options=[
            create_option(
                name="user",
                description="경고를 지급할 유저를 선택해주세요.",
                option_type=6,
                required=True,
            ),
            create_option(
                name="reason",
                description="경고 지급 사유를 지정해주세요.",
                option_type=3,
                required=False,
            ),
        ],
        guild_ids=[642630345967271946],
    )
    @commands.has_permissions(administrator=True)
    async def _warn(self, ctx, member: discord.Member, reason: str = "사유가 없어요."):
        await ctx.defer()
        await self.addModlog("warn", member, ctx.author, reason)
        await ctx.send(f"""
⚠️ {member.mention}님에게 **{ctx.guild.name}**에서 경고를 지급했어요.
사유 : {reason}
        """)

    @cog_ext.cog_slash(
        name="purge",
        description="채널의 메시지를 삭제합니다.",
        options=[
            create_option(
                name="messages",
                description="삭제할 메시지의 개수를 설정해주세요.",
                option_type=4,
                required=True,
            ),
        ],
        guild_ids=[642630345967271946],
    )
    @commands.has_permissions(manage_messages=True)
    async def _purge(self, ctx, messages: int):
        if messages < 1:
            return await ctx.send("🎋 1개 미만의 메시지를 지울 수 없어요.")
        await ctx.defer()
        deleted = await ctx.channel.purge(limit=(messages + 1))
        await ctx.channel.send(f"🧹 {ctx.channel.mention} 채널에서 **{len(deleted) - 1}**개의 메시지를 삭제했어요.", delete_after=3)

    @cog_ext.cog_slash(
        name="slowmode",
        description="채널의 슬로우 모드를 설정합니다.",
        options=[
            create_option(
                name="seconds",
                description="설정할 슬로우 모드의 시간 (초 단위)를 입력해주세요.",
                option_type=4,
                required=True,
            ),
        ],
        guild_ids=[642630345967271946],
    )
    @commands.has_permissions(manage_channels=True)
    async def _slowmode(self, ctx, seconds: int):
        if seconds >= 21600 or seconds < 0:
            return await ctx.send("🎋 슬로우 모드는 최대 6시간(21600초), 최소 0초로 설정할 수 있어요.", hidden=True)
        await ctx.defer()
        await ctx.channel.edit(slowmode_delay=seconds)
        if seconds == 0:
            return await ctx.send(f"⏰ {ctx.channel.mention} 채널의 슬로우 모드를 껐어요.")
        time = []
        time.append(f"{seconds // 3600}시간")
        left = seconds % 3600
        time.append(f"{left // 60}분")
        time.append(f"{left % 60}초")
        a = ""
        for i in time:
            if not i.startswith("0"):
                a += f"{i} "
        await ctx.send(f"⏰ {ctx.channel.mention} 채널의 슬로우 모드를 {a.strip()}로 설정했어요!")

    @cog_ext.cog_slash(
        name="kick",
        description="유저를 서버에서 추방합니다. 추방된 유저는 다시 입장할 수 있습니다.",
        options=[
            create_option(
                name="user",
                description="서버에서 추방할 유저를 선택해주세요.",
                option_type=6,
                required=True,
            ),
            create_option(
                name="reason",
                description="추방 사유를 지정해주세요.",
                option_type=3,
                required=False,
            ),
        ],
        guild_ids=[642630345967271946],
    )
    @commands.has_permissions(kick_members=True)
    async def _kick(self, ctx, member: discord.Member, reason: str = "사유가 없어요."):
        await ctx.defer()
        await self.addModlog("kick", member, ctx.author, reason)
        await ctx.guild.kick(member, reason=reason)
        await ctx.send(f"""
⚔ **{member}**님이 **{ctx.guild.name}**에서 강제 퇴장되었어요.
사유 : {reason}
        """)

    @cog_ext.cog_slash(
        name="ban",
        description="유저를 서버에서 차단합니다. 차단된 유저는 입장이 제한됩니다.",
        options=[
            create_option(
                name="user",
                description="서버에서 차단할 유저를 선택해주세요.",
                option_type=6,
                required=True,
            ),
            create_option(
                name="delete",
                description="해당 유저의 최근 몇 일간의 메시지를 삭제할 지 정해주세요.",
                choices=[
                    create_choice(
                        name="아무 것도 삭제하지 않음",
                        value=0,
                    ),
                    create_choice(
                        name="최근 24시간 동안의 메시지",
                        value=1,
                    ),
                    create_choice(
                        name="최근 2일간의 메시지",
                        value=2,
                    ),
                    create_choice(
                        name="최근 3일간의 메시지",
                        value=3,
                    ),
                    create_choice(
                        name="최근 4일간의 메시지",
                        value=4,
                    ),
                    create_choice(
                        name="최근 5일간의 메시지",
                        value=5,
                    ),
                    create_choice(
                        name="최근 6일간의 메시지",
                        value=6,
                    ),
                    create_choice(
                        name="최근 일주일간의 메시지",
                        value=7,
                    ),
                ],
                option_type=4,
                required=False,
            ),
            create_option(
                name="reason",
                description="차단 사유를 지정해주세요.",
                option_type=3,
                required=False,
            ),
        ],
        guild_ids=[642630345967271946],
    )
    @commands.has_permissions(ban_members=True)
    async def _ban(self, ctx, member: discord.Member, delete: int = 0, reason: str = "사유가 없어요."):
        await ctx.defer()
        await self.addModlog("ban", member, ctx.author, reason)
        await ctx.guild.ban(member, message_delete_days=delete, reason=reason)
        await ctx.send(f"""
🔒 **{member}**님이 **{ctx.guild.name}**에서 영구적으로 차단되었어요.
사유 : {reason}
        """)

def setup(bot):
    bot.add_cog(Moderator(bot))