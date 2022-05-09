from datetime import datetime
import discord
from discord.ext import commands
from discord_slash import cog_ext
from discord_slash.utils.manage_commands import create_option, create_choice
from pytz import utc, timezone
from EZPaginator import Paginator


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
        await self.bot.sql(
            1,
            f"INSERT INTO `modlog`(`case`, `type`, `victim`, `admin`, `reason`, `timestamp`) VALUES('{case}', '{type}', '{victim.id}', '{admin.id}', '{reason}', '{now}')",
        )

    @cog_ext.cog_subcommand(
        base="modlog",
        name="remove",
        description="특정 제재내역을 삭제합니다.",
        options=[
            create_option(
                name="case",
                description="삭제할 내역의 고유 번호를 입력해주세요.",
                option_type=4,
                required=True,
            )
        ],
    )
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def _remove(self, ctx, case: int):
        await ctx.defer()
        sql = await self.bot.sql(0, f"SELECT * FROM `modlog` WHERE `case` = '{case}'")
        if not sql:
            await ctx.send(f"🎋 고유 번호 {case}번에 대한 제재내역을 찾지 못했어요.")
        else:
            await self.bot.sql(1, f"DELETE FROM `modlog` WHERE `case` = '{case}'")
            await ctx.send(f"🎲 고유 번호 {case}번의 제재내역을 완전히 삭제했어요.")

    @cog_ext.cog_subcommand(
        base="modlog",
        name="reason",
        description="특정 제재내역의 사유를 새롭게 작성합니다.",
        options=[
            create_option(
                name="case",
                description="수정할 내역의 고유 번호를 입력해주세요.",
                option_type=4,
                required=True,
            ),
            create_option(
                name="reason",
                description="새롭게 지정할 사유를 입력해주세요.",
                option_type=3,
                required=True,
            ),
        ],
    )
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def _reason(self, ctx, case: int, *, reason: str):
        await ctx.defer()
        sql = await self.bot.sql(0, f"SELECT * FROM `modlog` WHERE `case` = '{case}'")
        if not sql:
            await ctx.send(f"🎋 고유 번호 {case}번에 대한 제재내역을 찾지 못했어요.")
        else:
            await self.bot.sql(
                1, f"UPDATE `modlog` SET `reason` = '{reason}' WHERE `case` = '{case}'"
            )
            await ctx.send(
                f"""🧩 고유 번호 {case}번의 사유가 변경되었어요.
이전 사유 : {sql[0]['reason']}
변경된 사유 : {reason}
            """
            )

    @cog_ext.cog_subcommand(
        base="modlog",
        name="view",
        description="유저의 제재내역을 열람합니다.",
        options=[
            create_option(
                name="user",
                description="제재내역을 열람할 유저를 지정해주세요.",
                option_type=6,
                required=True,
            )
        ],
    )
    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)
    @commands.bot_has_permissions(add_reactions=True, embed_links=True)
    async def _modlog(self, ctx, user: discord.Member):
        await ctx.defer()
        sql = await self.bot.sql(
            0,
            f"SELECT * FROM `modlog` WHERE `victim` = '{user.id}' ORDER BY `case` ASC",
        )
        if not sql:
            await ctx.send(f"🧼 `{user}`님은 제재내역이 없어요.")
        else:
            embeds = []
            actions = {
                "warn": "경고",
                "mute": "채팅 제한",
                "unmute": "채팅 제한 해제",
                "kick": "추방",
                "ban": "차단",
            }
            for i in range(len(sql)):
                admin = self.bot.get_user(int(sql[i]["admin"]))
                embed = discord.Embed(
                    title=f"⚠️ {user.name}님의 제재내역 ({i + 1} / {len(sql)})",
                    color=0xFF3333,
                )
                embed.add_field(
                    name="🎬 CASE No.", value=f"CASE #{sql[i]['case']}", inline=False
                )
                embed.add_field(
                    name="📽 Action", value=actions[sql[i]["type"]], inline=False
                )
                embed.add_field(
                    name="🗡 Moderator", value=f"{admin} {admin.mention}", inline=False
                )
                embed.add_field(name="📋 Reason", value=sql[i]["reason"], inline=False)
                embed.add_field(
                    name="⏰ Timestamp", value=sql[i]["timestamp"], inline=False
                )
                embed.set_author(name="관리 기록", icon_url=self.bot.user.avatar_url)
                embed.set_thumbnail(
                    url=user.avatar_url_as(static_format="png", size=2048)
                )
                embed.set_footer(text=ctx.guild.name, icon_url=ctx.guild.icon_url)
                embeds.append(embed)
            msg = await ctx.send(embed=embeds[0])
            page = Paginator(bot=self.bot, message=msg, embeds=embeds)
            await page.start()

    @cog_ext.cog_slash(
        name="warn",
        description="유저에게 경고를 지급합니다.",
        options=[
            create_option(
                name="member",
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
    )
    @commands.guild_only()
    @commands.has_permissions(manage_messages=True)
    async def _warn(self, ctx, member: discord.Member, reason: str = "사유가 없어요."):
        await ctx.defer()
        await self.addModlog("warn", member, ctx.author, reason)
        await ctx.send(
            f"""
⚠️ {member.mention}님에게 경고가 지급되었어요.
사유 : {reason}
        """
        )

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
    )
    @commands.guild_only()
    @commands.has_permissions(manage_messages=True)
    async def _purge(self, ctx, messages: int):
        if messages < 1:
            return await ctx.send("🎋 1개 미만의 메시지를 지울 수 없어요.")
        await ctx.defer()
        deleted = await ctx.channel.purge(limit=(messages + 1))
        await ctx.channel.send(
            f"🧹 {ctx.channel.mention} 채널에서 **{len(deleted) - 1}**개의 메시지를 삭제했어요.",
            delete_after=3,
        )

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
    )
    @commands.guild_only()
    @commands.has_permissions(manage_channels=True)
    @commands.bot_has_permissions(manage_channels=True)
    async def _slowmode(self, ctx, seconds: int):
        if seconds >= 21600 or seconds < 0:
            return await ctx.send(
                "🎋 슬로우 모드는 최대 6시간(21600초), 최소 0초로 설정할 수 있어요.", hidden=True
            )
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
                name="member",
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
    )
    @commands.guild_only()
    @commands.has_permissions(kick_members=True)
    @commands.bot_has_permissions(kick_members=True)
    async def _kick(self, ctx, member: discord.Member, reason: str = "사유가 없어요."):
        await ctx.defer()
        await self.addModlog("kick", member, ctx.author, reason)
        await ctx.guild.kick(member, reason=reason)
        await ctx.send(
            f"""
⚔ **{member}**님이 **{ctx.guild.name}**에서 강제 퇴장되었어요.
사유 : {reason}
        """
        )

    @cog_ext.cog_slash(
        name="ban",
        description="유저를 서버에서 차단합니다. 차단된 유저는 입장이 제한됩니다.",
        options=[
            create_option(
                name="member",
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
    )
    @commands.guild_only()
    @commands.has_permissions(ban_members=True)
    @commands.bot_has_permissions(ban_members=True)
    async def _ban(
        self, ctx, member: discord.Member, delete: int = 0, reason: str = "사유가 없어요."
    ):
        await ctx.defer()
        await self.addModlog("ban", member, ctx.author, reason)
        await ctx.guild.ban(member, delete_message_days=delete, reason=reason)
        await ctx.send(
            f"""
🔒 **{member}**님이 **{ctx.guild.name}**에서 영구적으로 차단되었어요.
사유 : {reason}
        """
        )


def setup(bot):
    bot.add_cog(Moderator(bot))