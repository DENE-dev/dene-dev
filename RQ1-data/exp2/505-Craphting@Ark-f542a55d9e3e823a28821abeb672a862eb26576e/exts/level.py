import asyncio
import random
from datetime import datetime
import discord
import humanize
from discord.ext import commands

class Level(commands.Cog, name="λ λ²¨λ§"):
    def __init__(self, bot):
        self.bot = bot

    def level_enabled():
        async def predicate(ctx):
            rows = await ctx.bot.sql(0, f"SELECT * FROM `guilds` WHERE `guild` = '{ctx.guild.id}'")
            if not rows:
                return False
            if rows[0]["leveling"] == "false":
                await ctx.reply("π¦ μ΄ μλ²λ λ λ²¨ κΈ°λ₯μ΄ νμ±νλμ§ μμμ΅λλ€.")
                raise discord.Forbidden
            return True
        return commands.check(predicate)

    @commands.Cog.listener()
    async def on_message(self, msg):
        if msg.author.bot:
            return

        if msg.channel.type == discord.ChannelType.private:
            return

        if msg.content.startswith("μ€μ΄μ") or msg.content.startswith("μ€μ΄λ") or msg.content.startswith(self.bot.user.mention):
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
                    await msg.channel.send(f"π μΆνν©λλ€, {msg.author.mention}λ! **{level}**λ λ²¨μ λ¬μ±νμ¨μ΅λλ€!")
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

    @commands.group(name="λ λ²¨")
    @commands.guild_only()
    @level_enabled()
    async def levels(self, ctx, member: discord.Member = None):
        if ctx.invoked_subcommand is None:
            if member is None:
                member = ctx.author
            level_data = await self.bot.sql(0, f"SELECT * FROM `levels` WHERE `guild` = '{ctx.guild.id}' AND `user` = '{member.id}'")
            if not level_data:
                return await ctx.reply(f"π `{member}`λμ `{ctx.guild.name}` μλ²μ λ λ²¨ μ λ³΄κ° μμ΅λλ€.")
            level_data = level_data[0]
            embed = discord.Embed(title=f"{member}λμ νμ¬ λ λ²¨λ§ μν", description=f"{self.bot.user.name}μ κ²½νμΉλ 1λΆμ λ©μμ§ νλλ§ μΆμ λ©λλ€.", color=0xAFFDEF, timestamp=datetime.utcnow())
            left = int(level_data["nextexp"]) - int(level_data["exp"])
            embed.add_field(name="νμ¬ κ²½νμΉ μν", value=f"{level_data['exp']}/{level_data['nextexp']} EXP (λ€μ λ λ²¨κΉμ§ {left})")
            embed.add_field(name="κ²½νμΉλ‘ νμ°λ λ©μμ§", value=f"{level_data['count']}κ°")
            embed.add_field(name="νμ¬ λ λ²¨", value="Lv. {level_data['level']}")
            embed.set_author(name="Ark νλ‘μ νΈ", icon_url=self.bot.user.avatar_url)
            embed.set_thumbnail(url=member.avatar_url_as(size=2048))
            embed.set_footer(text=f"{ctx.author}λμ΄ μμ²­ν¨")
            await ctx.reply(embed=embed)

    @levels.command(name="λ­νΉ", aliases=["λ¦¬λλ³΄λ", "λ¦¬λ"])
    @commands.guild_only()
    @level_enabled()
    async def _leaderboard(self, ctx):
        users = await self.bot.sql(0, f"SELECT * FROM `levels` WHERE `guild` = '{ctx.guild.id}' ORDER BY `exp` DESC")
        if not users:
            return await ctx.reply("π¦­ μ΄ μλ²μλ λ λ²¨λ§ λ°μ΄ν° κ°μ§ μ μ κ° μμ΅λλ€.")
        ranking = []
        for user in users:
            u = ctx.guild.get_member(int(user["user"]))
            if u is not None:
                ranking.append([u, int(user["exp"]), int(user["count"]), int(user["level"])])
        ranking.sort(key=itemgetter(1), reverse=True)
        text = "{ctx.guild.name}μλ²μ λ λ²¨λ§ μμ\n \n"
        where = "μμ μμ"
        i = 1
        for r in ranking:
            if i <= 10:
                text += f"#{i}   {a[0].name}   {humanize.intcomma(a[1])} XP   Lv. {humanize.intcomma(a[3])}\n"
            if a[0] == ctx.author:
                where = i
            i += 1
        await ctx.reply(f"```md\n{text}```\n \nνμ¬ λΉμ μ μ΄ μλ²μμ `{where}`μμλλ€.")

def setup(bot):
    bot.add_cog(Level(bot))