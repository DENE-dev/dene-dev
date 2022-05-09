import locale
import os
from datetime import datetime

import aiohttp
import discord
import humanize
import psutil
from discord.ext import commands

locale.setlocale(locale.LC_ALL, "")
humanize.i18n.activate("ko_KR")


class Snowflake(commands.Cog, name="중운"):
    """그 외 잡다한 거 전부"""
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="핑")
    async def _latency(self, ctx):
        start = datetime.utcnow()
        msg = await ctx.reply("🌨 **ㄹㅇㅋㅋ**")
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
        embed.add_field(name="API 레이턴시",
                        value=f"{api_latency}ms",
                        inline=False)
        embed.add_field(name="메시지 지연",
                        value=f"{msg_latency}ms",
                        inline=False)
        embed.add_field(name="CPU 점유율", value=f"{psutil.cpu_percent()}% 사용 중", inline=False)
        embed.add_field(name="메모리 점유율", value=f"{psutil.Process().memory_full_info().uss / 1048576:.2f}MB 사용 중", inline=False)
        embed.add_field(name="구동 시간", value=uptime, inline=False)
        embed.set_footer(text="얼어붙은 열정")
        embed.set_thumbnail(
            url=self.bot.user.avatar_url_as(static_format="png", size=2048))
        embed.set_author(name=f"Ark 프로젝트", icon_url=self.bot.user.avatar_url)
        await msg.edit(content="🌨 **안녕!**", embed=embed)

    @commands.command(name="한강")
    async def _hanriver(self, ctx):
        async with ctx.channel.typing():
            async with aiohttp.ClientSession() as cs:
                async with cs.get("http://hangang.dkserver.wo.tc") as r:
                    response = await r.json(content_type=None)
                    temp = None
                    time = (response["time"]).split(" ")[0]
                    if "." in response["temp"]:
                        temp = int(response["temp"].split(".")[0])
                    else:
                        temp = int(response["temp"])
                    embed = discord.Embed(
                        title=f"지금 한강의 온도는 {temp}도야.",
                        description=f"`{time}`에 마지막으로 확인했어.",
                        color=ctx.guild.me.top_role.color,
                        timestamp=datetime.utcnow(),
                    )
                    embed.set_author(name="Ark 프로젝트",
                                     icon_url=self.bot.user.avatar_url)
                    if result[0] > 10:
                        embed.set_footer(text="생각보다는 따뜻하네.")
                    else:
                        embed.set_footer(text="차갑네.")
                    await ctx.reply("🐋 무슨 이런 걸 물어봐.", embed=embed)

    @commands.command(name="나락")
    @commands.cooldown(rate=1, per=10, type=commands.BucketType.user)
    async def _narack(self, ctx, *, text):
        await ctx.reply(f"⬇️⤵️↘️↙️🔽🔻 **나 락 행  열 차** 탑승객 : `{text}`")


def setup(bot):
    bot.add_cog(Snowflake(bot))