import asyncio
import random
from datetime import datetime
import discord
import humanize
from discord.ext import commands

class Level(commands.Cog, name="레벨링"):
    def __init__(self, bot):
        self.bot = bot

    def level_enabled():
        async def predicate(ctx):
            rows = await ctx.bot.sql(0, f"SELECT * FROM `guilds` WHERE `guild` = '{ctx.guild.id}'")
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

        if msg.content.startswith("중운아") or msg.content.startswith("중운님") or msg.content.startswith(self.bot.user.mention):
            return

        rows = await self.bot.sql(0, f"SELECT * FROM `guilds` WHERE `guild` = '{msg.guild.id}'")
        if not rows:
            return

        if rows[0]["leveling"] == "false":
            return

        level_data = await self.bot.sql(0, f"SELECT * FROM `levels` WHERE `guild` = '{msg.guild.id}' AND `user` = '{msg.author.id}'")
        add = random.randint(15, 25)
        next, now, level, count = 0
        if not level_data:
            return await self.bot.sql(1, f"INSERT INTO `levels`(`guild`, `user`, `exp`, `nextexp`, `count`, `level`) VALUES('{msg.guild.id}', '{msg.author.id}', '{add}', '300', '1', '0')")
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
                    await msg.channel.send(f"🎉 축하합니다, {msg.author.mention}님! **{level}**레벨을 달성하셨습니다!")
                else:
                    level = level_data["level"]
                    next = level_data["nextexp"]
        await self.bot.sql(1, f"UPDATE `levels` SET `exp` = '{now}' WHERE `guild` = '{msg.guild.id} AND `user` = '{msg.author.id}'")
        await self.bot.sql(1, f"UPDATE `levels` SET `nextexp` = '{next}' WHERE `guild` = '{msg.guild.id} AND `user` = '{msg.author.id}'")
        await self.bot.sql(1, f"UPDATE `levels` SET `count` = '{count}' WHERE `guild` = '{msg.guild.id} AND `user` = '{msg.author.id}'")
        await self.bot.sql(1, f"UPDATE `levels` SET `level` = '{level}' WHERE `guild` = '{msg.guild.id} AND `user` = '{msg.author.id}'")
        await self.bot.sql(1, f"UPDATE `levels` SET `cooldown` = 'true' WHERE `guild` = '{msg.guild.id} AND `user` = '{msg.author.id}'")
        await asyncio.sleep(60)
        await self.bot.sql(1, f"UPDATE `levels` SET `cooldown` = 'false' WHERE `guild` = '{msg.guild.id} AND `user` = '{msg.author.id}'")

    @commands.group(name="레벨")
    @commands.guild_only()
    @level_enabled()
    async def levels(self, ctx, member: discord.Member = None):
        if ctx.invoked_subcommand is None:
            if member is None:
                member = ctx.author
            level_data = await self.bot.sql(0, f"SELECT * FROM `levels` WHERE `guild` = '{ctx.guild.id}' AND `user` = '{member.id}'")
            if not level_data:
                return await ctx.reply(f"🎐 `{member}`님은 `{ctx.guild.name}` 서버의 레벨 정보가 없습니다.")
            level_data = level_data[0]
            embed = discord.Embed(title=f"{member}님의 현재 레벨링 상태", description=f"{self.bot.user.name}의 경험치는 1분에 메시지 하나만 축적됩니다.", color=0xAFFDEF, timestamp=datetime.utcnow())
            left = int(level_data["nextexp"]) - int(level_data["exp"])
            embed.add_field(name="현재 경험치 상태", value=f"{level_data['exp']}/{level_data['nextexp']} EXP (다음 레벨까지 {left})")
            embed.add_field(name="경험치로 환산된 메시지", value=f"{level_data['count']}개")
            embed.add_field(name="현재 레벨", value="Lv. {level_data['level']}")
            embed.set_author(name="Ark 프로젝트", icon_url=self.bot.user.avatar_url)
            embed.set_thumbnail(url=member.avatar_url_as(size=2048))
            embed.set_footer(text=f"{ctx.author}님이 요청함")
            await ctx.reply(embed=embed)

    @levels.command(name="랭킹", aliases=["리더보드", "리더"])
    @commands.guild_only()
    @level_enabled()
    async def _leaderboard(self, ctx):
        users = await self.bot.sql(0, f"SELECT * FROM `levels` WHERE `guild` = '{ctx.guild.id}' ORDER BY `exp` DESC")
        if not users:
            return await ctx.reply("🦭 이 서버에는 레벨링 데이터 가진 유저가 없습니다.")
        ranking = []
        for user in users:
            u = ctx.guild.get_member(int(user["user"]))
            if u is not None:
                ranking.append([u, int(user["exp"]), int(user["count"]), int(user["level"])])
        ranking.sort(key=itemgetter(1), reverse=True)
        text = "{ctx.guild.name}서버의 레벨링 순위\n \n"
        where = "순위 없음"
        i = 1
        for r in ranking:
            if i <= 10:
                text += f"#{i}   {a[0].name}   {humanize.intcomma(a[1])} XP   Lv. {humanize.intcomma(a[3])}\n"
            if a[0] == ctx.author:
                where = i
            i += 1
        await ctx.reply(f"```md\n{text}```\n \n현재 당신은 이 서버에서 `{where}`위입니다.")

def setup(bot):
    bot.add_cog(Level(bot))