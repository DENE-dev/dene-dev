import random
from datetime import datetime

import config
import discord
import hcskr
from discord.ext import commands
from discord.ext import tasks
from pytz import timezone
from pytz import utc


class Automatic(commands.Cog, name="자동 작업"):
    """자동 작업 실행"""

    def __init__(self, bot):
        self.bot = bot
        self.changePrice.start()
        self.healthCheck.start()
        self.statusChanger.start()
    #   self.changeNews.start()

    @tasks.loop()
    async def statusChanger(self):
        activities = [
            discord.Game("얼어붙은 열정과 함께"),
            discord.Streaming(name="중운아 도움말 / v1.2", url="https://twitch.tv/craph_"),
            discord.Activity(name=f"{len(self.bot.guilds)}개의 서버", type=5),
            discord.Activity(name=f"{len(self.bot.users)}명의 말을", type=discord.ActivityType.listening),
            discord.Activity(name=f"{len(list(self.bot.get_all_channels()))}개의 채널을", type=discord.ActivityType.watching),
        ]
        for act in activities:
            await self.bot.change_presence(status=discord.Status.idle, activity=act, afk=True)
            await asyncio.sleep(5)

    @tasks.loop(seconds=1)
    async def healthCheck(self):
        KST = timezone("Asia/Seoul")
        abc = utc.localize(datetime.utcnow()).astimezone(KST)
        time = abc.strftime("%H시 %M분 %S초")
        debug = self.bot.get_channel(config.Debug)
        if time == "07시 00분 00초":
            rows = await self.bot.sql(0, "SELECT * FROM `hcskr`")
            success = []
            result = {"success": "", "failed": ""}
            failed = []
            for row in rows:
                user = self.bot.get_user(int(row["user"]))
                hcs = await hcskr.asyncTokenSelfCheck(
                    row["token"], customloginname=row["custom"]
                )
                if hcs["code"] == "SUCCESS":
                    success.append([user, hcs])
                    result["success"] += f"{user.mention}\n"
                else:
                    failed.append([user, hcs])
                    result["failed"] += f"{user.mention}\n"
                    await debug.send(
                        f"`{user}`의 자가진단이 실패함.\n```{hcs['code']} - {hcs['message']}```"
                    )
            channel = self.bot.get_channel(838105895832649738)
            embed = discord.Embed(
                title="오늘의 자가진단",
                description=f"{len(success)}/{len(rows)}명의 자가진단이 성공했습니다.",
                color=debug.guild.me.top_role.color,
                timestamp=datetime.utcnow(),
            )
            if result["success"] != "":
                embed.add_field(name="성공", value=result["success"], inline=False)
            if result["failed"] != "":
                embed.add_field(name="실패", value=result["failed"], inline=False)
            embed.set_thumbnail(
                url=channel.guild.icon_url_as(static_format="png", size=2048)
            )
            embed.set_footer(text="즐거운 학교생활")
            embed.set_author(name="자가진단", icon_url=self.bot.user.avatar_url)
            msg = await channel.fetch_message(860296498390499389)
            await msg.edit(content="🎯 <@&838104633950994432> 자가진단 결과 안내", embed=embed)
            await channel.send("🎯 <@&838104633950994432> 자가진단 결과 안내", delete_after=1)

    @tasks.loop(minutes=5)
    async def changeNews(self):
        return

    @tasks.loop(seconds=1)
    async def changePrice(self):
        change = False
        a = ["0분 0초", "5분 0초"]
        KST = timezone("Asia/Seoul")
        abc = utc.localize(datetime.utcnow()).astimezone(KST)
        time = abc.strftime("%M분 %S초")
        for i in a:
            if time.endswith(i):
                change = True
        if change is True:
            stocks = await self.bot.sql(0, "SELECT * FROM `stocks`")
            temp = "`time`"
            prices = ""
            time = ""
            for stock in stocks:
                temp += f", `{stock['id']}`"
                row = (
                    await self.bot.sql(
                        0,
                        f"SELECT `time`, {stock['id']} FROM `prices` ORDER BY `time` DESC LIMIT 1",
                    )
                )[0]
                time = str(int(row["time"]) + 1)
                change = random.randint(-50, 50)
                now = int(row[stock["id"]]) + change
                if now <= 200:
                    prices += ", '1000'"
                    await self.bot.sql(1, f"UPDATE `users` SET `{stock['id']}` = '0'")
                    channel = self.bot.get_channel(868731782219055114)
                    await (
                        await channel.send(
                            f"💥 `{stock['name']}`의 주가가 200💰 이하가 되어 상장 폐지되었습니다.\n**모든 유저의 `{stock['name']}` 주식이 몰수되고, 주가가 기본가로 초기화됩니다.**"
                        )
                    ).publish()
                elif now >= 2000:
                    prices += ", '1000'"
                    users = await self.bot.sql(
                        0,
                        f"SELECT `user`, `money`, `{stock['id']}` FROM `users` WHERE `{stock['id']}` != '0'",
                    )
                    await self.bot.sql(1, f"UPDATE `users` SET `{stock['id']}` = '0'")
                    for user in users:
                        payback = int(user[stock["id"]]) * now
                        have = int(user["money"]) + payback
                        await self.bot.sql(
                            1,
                            f"UPDATE `users` SET `money` = '{have}' WHERE `user` = '{user['user']}'",
                        )
                    channel = self.bot.get_channel(868731782219055114)
                    await (
                        await channel.send(
                            f"🏝 `{stock['name']}`의 주가가 2000💰 이상이 되어 매각되었습니다.\n**모든 유저의 `{stock['name']}` 주식이 판매되고, 주가가 기본가로 초기화됩니다.**"
                        )
                    ).publish()
                else:
                    prices += f", '{now}'"
            await self.bot.sql(
                1, f"INSERT INTO `prices`({temp}) VALUES('{time}'{str(prices)})"
            )

    @changePrice.before_loop
    async def _wai1(self):
        await self.bot.wait_until_ready()

    @changeNews.before_loop
    async def _wait2(self):
        await self.bot.wait_until_ready()

    @healthCheck.before_loop
    async def _wait3(self):
        await self.bot.wait_until_ready()

    @statusChanger.before_loop
    async def _wait4(self):
        await self.bot.wait_until_ready()


def setup(bot):
    bot.add_cog(Automatic(bot))