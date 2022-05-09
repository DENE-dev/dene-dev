from discord.ext import commands
from discord_slash import cog_ext
from datetime import datetime
import psutil
import os
import humanize
import locale

locale.setlocale(locale.LC_ALL, "")
humanize.i18n.activate("ko_KR")

class Rainy(commands.Cog, name="SxU"):
    def __init__(self, bot):
        self.bot = bot

    @cog_ext.cog_slash(
        name="ping",
        description="지연 시간을 표시합니다.",
        guild_ids=[642630345967271946],
    )
    async def _ping(self, ctx):
        start = datetime.utcnow()
        msg = await ctx.send("⚡ **아니, ...을 위해 배신한다는 게 부러워서.**")
        end = datetime.utcnow()
        msg_latency = round((float(str(end - start)[6:]) * 1000), 2)
        api_latency = round(self.bot.latency * 1000, 2)
        uptime = datetime.now() - datetime.fromtimestamp(
            psutil.Process(os.getpid()).create_time())
        uptime = (humanize.precisedelta(uptime,
                                        minimum_unit="seconds",
                                        format="%0.0f")).replace("and ", "")
        uptime = uptime.replace(",", "")
        embed = discord.Embed(color=ctx.guild.me.top_role.color,
                              timestamp=datetime.utcnow())
        embed.add_field(name="API",
                        value=f"{api_latency}ms",
                        inline=False)
        embed.add_field(name="메시지",
                        value=f"{msg_latency}ms",
                        inline=False)
        embed.add_field(name="CPU", value=f"{psutil.cpu_percent()}% 사용 중", inline=False)
        embed.add_field(name="메모리", value=f"{psutil.Process().memory_full_info().uss / 1048576:.2f}MB 사용 중", inline=False)
        embed.add_field(name="업타임", value=uptime, inline=False)
        embed.set_footer(text="Powered by CRaPH_#7777")
        embed.set_thumbnail(
            url=self.bot.user.avatar_url_as(static_format="png", size=2048))
        embed.set_author(name=f"Project SxU", icon_url=self.bot.user.avatar_url)
        await msg.edit(embed=embed)

def setup(bot):
    bot.add_cog(Rainy(bot))