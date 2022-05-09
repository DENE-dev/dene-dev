import asyncio
import random
from datetime import datetime
from operator import itemgetter
import discord
import humanize
from discord.ext import commands


class Level(commands.Cog, name="레벨링"):
    def __init__(self, bot):
        self.bot = bot

    def level_enabled():
        async def predicate(ctx):
            rows = await ctx.bot.sql(
                0, f"SELECT * FROM `guilds` WHERE `guild` = '{ctx.guild.id}'"
            )
            if not rows:
                return False
            if rows[0]["leveling"] == "false":
                await ctx.reply("🦄 이 서버는 레벨 기능이 활성화되지 않았습니다.")
                raise discord.Forbidden
            return True

        return commands.check(predicate)

    @commands.Cog.listener()
    async def on_message(self, msg):
        if msg.author.bot:
            return

        if msg.channel.type == discord.ChannelType.private:
            return

        if (
            msg.content.startswith("중운아")
            or msg.content.startswith("중운님")
            or msg.content.startswith(self.bot.user.mention)
        ):
            return

        rows = await self.bot.sql(
            0, f"SELECT * FROM `guilds` WHERE `guild` = '{msg.guild.id}'"
        )
        if not rows:
            return

        if rows[0]["leveling"] == "false":
            return

        level_data = await self.bot.sql(
            0,
            f"SELECT * FROM `levels` WHERE `guild` = '{msg.guild.id}' AND `user` = '{msg.author.id}'",
        )
        add = random.randint(15, 25)
        next, now, level, count = 0, 0, 0, 0
        if not level_data:
            return await self.bot.sql(
                1,
                f"INSERT INTO `levels`(`guild`, `user`, `exp`, `nextexp`, `count`, `level`, `cooldown`) VALUES('{msg.guild.id}', '{msg.author.id}', '{add}', '300', '1', '0', 'true')",
            )
        else:
            level_data = level_data[0]
            if level_data["cooldown"] == "true":
                return
            else:
                now = int(level_data["exp"]) + add
                count = int(level_data["count"]) + 1
                if now >= int(level_data["nextexp"]):
                    level = int(level_data["level"]) + 1
                    next = round(int(level_data["nextexp"]) * 1.37)
                    msg = (await self.bot.sql(0, f"SELECT * FROM `messages` WHERE `guild` = '{msg.guild.id}'"))[0]["levelup"]
                    if msg == "Default":
                        await msg.channel.send(
                            f"🎉 축하합니다, {msg.author.mention}님! **{level}**레벨을 달성하셨습니다!"
                        )
                    else:
                        msg = msg.replace("[레벨]", str(level))
                        msg = msg.replace("[유저]", ctx.author.mention)
                        msg = msg.replace("[서버]", ctx.guild.name)
                        await msg.channel.send(msg)
                else:
                    level = level_data["level"]
                    next = level_data["nextexp"]
        await self.bot.sql(
            1,
            f"UPDATE `levels` SET `exp` = '{now}' WHERE `guild` = '{msg.guild.id}' AND `user` = '{msg.author.id}'",
        )
        await self.bot.sql(
            1,
            f"UPDATE `levels` SET `nextexp` = '{next}' WHERE `guild` = '{msg.guild.id}' AND `user` = '{msg.author.id}'",
        )
        await self.bot.sql(
            1,
            f"UPDATE `levels` SET `count` = '{count}' WHERE `guild` = '{msg.guild.id}' AND `user` = '{msg.author.id}'",
        )
        await self.bot.sql(
            1,
            f"UPDATE `levels` SET `level` = '{level}' WHERE `guild` = '{msg.guild.id}' AND `user` = '{msg.author.id}'",
        )
        await self.bot.sql(
            1,
            f"UPDATE `levels` SET `cooldown` = 'true' WHERE `guild` = '{msg.guild.id}' AND `user` = '{msg.author.id}'",
        )

    @commands.group(name="레벨", hidden=True)
    @commands.guild_only()
    @level_enabled()
    async def levels(self, ctx):
        if ctx.invoked_subcommand is None:
            raise commands.UserInputError

    @levels.command(name="정보", aliases=["상태"])
    @commands.guild_only()
    @level_enabled()
    async def _rank(self, ctx, member: discord.Member = None):
        if member is None:
            member = ctx.author
        if member.bot:
            return await ctx.reply("🍱 봇을 파티에 끼워주고 싶은 건 알지만, 이 파티에는 봇이 참여할 수 없습니다.")
        level_data = await self.bot.sql(
            0,
            f"SELECT * FROM `levels` WHERE `guild` = '{ctx.guild.id}' AND `user` = '{member.id}'",
        )
        if not level_data:
            return await ctx.reply(
                f"🎐 `{member}`님은 `{ctx.guild.name}` 서버의 레벨 정보가 없습니다."
            )
        level_data = level_data[0]
        embed = discord.Embed(
            title=f"{member}님의 현재 레벨링 상태",
            description=f"{self.bot.user.name}의 경험치는 1분에 메시지 하나만 축적됩니다.",
            color=0xAFFDEF,
            timestamp=datetime.utcnow(),
        )
        left = int(level_data["nextexp"]) - int(level_data["exp"])
        embed.add_field(
            name="현재 경험치 상태",
            value=f"{level_data['exp']}/{level_data['nextexp']} EXP (다음 레벨까지 {left})",
        )
        embed.add_field(name="경험치로 환산된 메시지", value=f"{level_data['count']}개")
        embed.add_field(name="현재 레벨", value=f"Lv. {level_data['level']}")
        embed.set_author(name="Ark 프로젝트", icon_url=self.bot.user.avatar_url)
        embed.set_thumbnail(url=member.avatar_url_as(size=2048))
        embed.set_footer(text=f"{ctx.author}님이 요청함", icon_url=ctx.author.avatar_url)
        await ctx.reply(embed=embed)

    @levels.command(name="랭킹", aliases=["리더보드", "리더"])
    @commands.guild_only()
    @level_enabled()
    async def _leaderboard(self, ctx):
        users = await self.bot.sql(
            0,
            f"SELECT * FROM `levels` WHERE `guild` = '{ctx.guild.id}' ORDER BY `exp` DESC",
        )
        if not users:
            return await ctx.reply("🦭 이 서버에는 레벨링 데이터 가진 유저가 없습니다.")
        ranking = []
        for user in users:
            u = ctx.guild.get_member(int(user["user"]))
            if u is not None:
                ranking.append(
                    [u, int(user["exp"]), int(user["count"]), int(user["level"])]
                )
        ranking.sort(key=itemgetter(1), reverse=True)
        text = f"{ctx.guild.name} 서버의 레벨링 순위\n \n"
        where = "순위 없음"
        i = 1
        for r in ranking:
            if i <= 10:
                text += f"#{i}   {r[0].name}   {humanize.intcomma(r[1])} XP   Lv. {humanize.intcomma(r[3])}\n"
            if r[0] == ctx.author:
                where = i
            i += 1
        await ctx.reply(f"```md\n{text}```\n \n현재 당신은 이 서버에서 `{where}`위입니다.")


def setup(bot):
    bot.add_cog(Level(bot))