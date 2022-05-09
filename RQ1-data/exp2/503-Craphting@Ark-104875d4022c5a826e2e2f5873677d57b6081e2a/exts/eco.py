# -*-coding:utf-8-*-
import locale
import random
from datetime import datetime
from operator import itemgetter

import humanize
from discord.ext import commands
from discord_components import Button
from discord_components import ButtonStyle
from discord_components import DiscordComponents
from discord.ext import commands

locale.setlocale(locale.LC_ALL, "")
humanize.i18n.activate("ko_KR")


class Economy(commands.Cog, name="자산 관리"):
    """떡상 가즈아!!!!!!!"""

    def __init__(self, bot):
        self.bot = bot

    def is_user():
        async def predicate(ctx):
            rows = await ctx.bot.sql(
                0, f"SELECT * FROM `users` WHERE `user` = '{ctx.author.id}'")
            return len(rows) == 1

        return commands.check(predicate)

    @commands.group(name="도박")
    @is_user()
    async def gamble(self, ctx):
        if ctx.invoked_subcommand is None:
            return await ctx.reply("""
🎰 준비된 게임 목록 : `홀짝`, `가위바위보`

*과도한 도박은 정신 건강에 해롭습니다.*
            """)

    @gamble.command(name="홀짝")
    @is_user()
    @commands.cooldown(rate=10, per=3600, type=commands.BucketType.user)
    async def _twodice(self, ctx, betting: str, bets: str):
        user = (await self.bot.sql(
            0, f"SELECT * FROM `users` WHERE `user` = '{ctx.author.id}'"))[0]
        if betting not in ["홀", "짝"]:
            return await ctx.reply(
                f"🎮 `{betting}`(은)는 잘못된 베팅입니다. `홀` 또는 `짝`에 베팅해주세요.")
        if not bets.isdecimal():
            if bets in ["모두", "전체", "전부", "올인"]:
                bets = int(user["money"])
            elif bets in ["하프", "절반", "반절"]:
                bets = int(user["money"]) // 2
            else:
                return await ctx.reply(
                    "⛱ 옵션이 존재하지 않습니다. 정수 또는 `올인`, `하프`를 사용할 수 있습니다.")
        if int(bets) > int(user["money"]) or int(bets) <= 0:
            return await ctx.reply(
                f"🚀 베팅하기에는 돈이 부족합니다! 베팅 `{humanize.intcomma(bets)}`💰 VS `{humanize.intcomma(user['money'])}`💰 잔액"
            )
        if int(bets) > 100000:
            return await ctx.reply(f"🗃 이 도박은 최대 100,000원까지만 베팅 가능합니다.")
        dice = random.randint(1, 6)
        dice2 = random.randint(1, 6)
        result = dice + dice2
        winner = [True, False]
        prize = 0
        if betting in ["홀", "홀수"]:
            winner = [False, True]
        if winner[(result % 2)] == True:
            await ctx.reply(
                f"🎉 축하합니다! 당신의 승리입니다!\n결과 : 🎲`{result}`(🎲`{dice}`, 🎲`{dice2}`), 베팅 : `{betting}`에 `{humanize.intcomma(bets)}`💰"
            )
            prize = int(user["money"]) + int(bets)
        else:
            await ctx.reply(
                f"🎃 안타깝네요, 패배하고 말았습니다...\n결과 : 🎲`{result}`(🎲`{dice}` + 🎲`{dice2}`), 베팅 : `{betting}`에 `{humanize.intcomma(bets)}`💰"
            )
            prize = int(user["money"]) - int(bets)
        await self.bot.sql(
            1,
            f"UPDATE `users` SET `money` = '{prize}' WHERE `user` = '{ctx.author.id}'",
        )

    @gamble.command(name="가위바위보")
    @is_user()
    @commands.cooldown(rate=10, per=3600, type=commands.BucketType.user)
    async def _rps(self, ctx, bets: str):
        user = (await self.bot.sql(
            0, f"SELECT * FROM `users` WHERE `user` = '{ctx.author.id}'"))[0]
        if not bets.isdecimal():
            if bets in ["모두", "전체", "전부", "올인"]:
                bets = int(user["money"])
            elif bets in ["하프", "절반", "반절"]:
                bets = int(user["money"]) // 2
            else:
                return await ctx.reply(
                    "⛱ 옵션이 존재하지 않습니다. 정수 또는 `올인`, `하프`를 사용할 수 있습니다.")
        if int(bets) > int(user["money"]) or int(bets) <= 0:
            return await ctx.reply(
                f"🚀 베팅하기에는 돈이 부족합니다! 베팅 `{humanize.intcomma(bets)}`💰 VS `{humanize.intcomma(user['money'])}`💰 잔액"
            )
        if int(bets) > 100000:
            return await ctx.reply(f"🗃 이 도박은 최대 100,000원까지만 베팅 가능합니다.")
        pickup = random.choice(["가위", "바위", "보"])
        wins = {"가위": {"바위": "win", "보": "lose"}, "바위": {"가위": "lose", "보": "win"}, "보": {"가위": "win", "바위": "lose"}}
        components = [
            Button(style=ButtonStyle.blue, label="가위", emoji="✌"),
            Button(style=ButtonStyle.blue, label="바위", emoji="✊"),
            Button(style=ButtonStyle.blue, label="보", emoji="🖐"),
        ]
        msg = await ctx.reply("💣 당신의 선택은...?", components=[components])
        prize = 0
        def check(res):
            return (res.channel == ctx.channel and res.user == ctx.author
                    and res.component.label in ["가위", "바위", "보"])
        try:
            res = await self.bot.wait_for("button_click",
                                          check=check,
                                          timeout=60)
        except:
            await res.respond(type=6)
            await msg.delete()
        else:
            await res.respond(type=7, components=[])
            if res.component.label == pickup:
                prize = int(user["money"]) - (int(bets) // 2)
                await msg.edit(content=f"🖐 무승부! 베팅한 금액의 절반을 잃었습니다.\n결과 : 봇 `{pickup}` vs `{res.component.label}` 당신 / {bets}💰 베팅함")
            else:
                final = wins[pickup][res.component.label]
                if final == "win":
                    prize = int(user["money"]) + (int(bets) * 2)
                    await msg.edit(content=f"✌ 승리했습니다! 베팅한 금액의 3배를 얻었습니다.\n결과 : 봇 `{pickup}` vs `{res.component.label}` 당신 / {bets}💰 베팅함")
                else:
                    prize = int(user["money"]) - int(bets)
                    await msg.edit(content=f"✊ 패배했습니다! 베팅한 금액을 모두 잃었습니다...\n결과 : 봇 `{pickup}` vs `{res.component.label}` 당신 / {bets}💰 베팅함")
        await self.bot.sql(
            1,
            f"UPDATE `users` SET `money` = '{prize}' WHERE `user` = '{ctx.author.id}'",
        )

    @commands.command(name="돈줘", aliases=["돈내놔", "돈받기"])
    @is_user()
    @commands.cooldown(rate=1, per=1800, type=commands.BucketType.user)
    async def _givemethemoney(self, ctx):
        user = (
            await self.bot.sql(
                0, f"SELECT * FROM `users` WHERE `user` = '{ctx.author.id}'"
            )
        )[0]
        prize = random.randrange(25000, 100000, 1000)
        add = int(user["money"]) + prize
        text1 = humanize.intcomma(add)
        text2 = humanize.intcomma(prize)
        await self.bot.sql(
            1, f"UPDATE `users` SET `money` = '{add}' WHERE `user` = '{ctx.author.id}'"
        )
        await ctx.reply(f"💵 당신의 계좌에 `{text2}`💰이 추가되었습니다.\n현재 보유 중인 현금 : `{text1}`💰")

    @commands.command(name="차트")
    async def _chart(self, ctx, time: int = 1):
        stocks = await self.bot.sql(0, "SELECT * FROM `stocks`")
        a = f"현재 주가 차트 / {time}주기 이전 주가 대비\n \n"
        for stock in stocks:
            rows = await self.bot.sql(
                0,
                f"SELECT `time`, `{stock['id']}` FROM `prices` ORDER BY `time` DESC LIMIT {time + 1}",
            )
            compare = {"present": rows[0], "past": rows[-1]}
            if int(compare["past"][stock["id"]]) > int(compare["present"][stock["id"]]):
                a += f"- {stock['name']}       {compare['present'][stock['id']]}       🔻 {int(compare['past'][stock['id']]) - int(compare['present'][stock['id']])}\n"
            elif int(compare["present"][stock["id"]]) > int(
                compare["past"][stock["id"]]
            ):
                a += f"+ {stock['name']}       {compare['present'][stock['id']]}       🔺️ {int(compare['present'][stock['id']]) - int(compare['past'][stock['id']])}\n"
            else:
                a += f"= {stock['name']}       {compare['present'][stock['id']]}       🔴 0\n"
        await ctx.reply(f"```diff\n{a}```")

    @commands.command(name="매수")
    @is_user()
    async def _buy(self, ctx, stock, value: str):
        stocks = await self.bot.sql(
            0, f"SELECT * FROM `stocks` WHERE `name` LIKE '%{stock}%'"
        )
        if not stocks or len(stocks) > 1:
            return await ctx.reply(f"🔎 {stock}의 검색 결과가 너무 많거나, 없습니다.")
        data = stocks[0]
        price = (
            await self.bot.sql(
                0, f"SELECT `{data['id']}` FROM `prices` ORDER BY `time` DESC LIMIT 1"
            )
        )[0]
        user = (
            await self.bot.sql(
                0,
                f"SELECT `money`, `{data['id']}` FROM `users` WHERE `user` = '{ctx.author.id}'",
            )
        )[0]
        if not value.isdecimal():
            if value in ["올인", "전체", "풀매수", "모두", "전부", "풀매"]:
                value = int(user["money"]) // int(price[data["id"]])
            elif value in ["절반", "하프"]:
                value = (int(user["money"]) // int(price[data["id"]])) // 2
            else:
                return await ctx.reply("⛱ 옵션이 존재하지 않습니다. 정수 또는 `올인`, `하프`를 사용할 수 있습니다.")
        final = int(price[data["id"]]) * int(value)
        if int(user["money"]) < final or value == 0:
            return await ctx.reply(
                f"💸 돈이 부족한 것 같습니다. 가격 `{humanize.intcomma(final)}`💰 VS `{humanize.intcomma(user['money'])}`💰 잔액"
            )
        else:
            left = int(user["money"]) - final
            bought = int(user[data["id"]]) + int(value)
            await self.bot.sql(
                1,
                f"UPDATE `users` SET `money` = '{left}' WHERE `user` = '{ctx.author.id}'",
            )
            await self.bot.sql(
                1,
                f"UPDATE `users` SET `{data['id']}` = '{bought}' WHERE `user` = '{ctx.author.id}'",
            )
            return await ctx.reply(
                f"🧾 `{data['name']}`의 주식을 `{humanize.intcomma(value)}`개 구매했습니다!\n현재 `{data['name']}`의 주식 `{humanize.intcomma(bought)}`주 보유, {humanize.intcomma(left)}💰 남음."
            )

    @commands.command(name="매도")
    @is_user()
    async def _sell(self, ctx, stock, value: str):
        stocks = await self.bot.sql(
            0, f"SELECT * FROM `stocks` WHERE `name` LIKE '%{stock}%'"
        )
        if not stocks or len(stocks) > 1:
            return await ctx.reply(f"🔎 {stock}의 검색 결과가 너무 많거나, 없습니다.")
        data = stocks[0]
        price = (
            await self.bot.sql(
                0, f"SELECT `{data['id']}` FROM `prices` ORDER BY `time` DESC LIMIT 1"
            )
        )[0]
        user = (
            await self.bot.sql(
                0,
                f"SELECT `money`, `{data['id']}` FROM `users` WHERE `user` = '{ctx.author.id}'",
            )
        )[0]
        if not value.isdecimal():
            if value in ["올인", "전체", "풀매도", "모두", "전부", "풀매"]:
                value = int(user[data["id"]])
            elif value in ["절반", "하프"]:
                value = int(user[data["id"]]) // 2
            else:
                return await ctx.reply("⛱ 옵션이 존재하지 않습니다. 정수 또는 `올인`, `하프`를 사용할 수 있습니다.")
        if int(user[data["id"]]) < int(value) or value == 0:
            return await ctx.reply(
                f"📈 주식 개수가 부족한 것 같습니다. 필요 개수 `{value}`💳 VS `{user[data['id']]}`💳 잔여 개수"
            )
        else:
            final = int(price[data["id"]]) * int(value)
            left = int(user["money"]) + final
            sold = int(user[data["id"]]) - int(value)
            await self.bot.sql(
                1,
                f"UPDATE `users` SET `money` = '{left}' WHERE `user` = '{ctx.author.id}'",
            )
            await self.bot.sql(
                1,
                f"UPDATE `users` SET `{data['id']}` = '{sold}' WHERE `user` = '{ctx.author.id}'",
            )
            return await ctx.reply(
                f"🧾 `{data['name']}`의 주식을 `{humanize.intcomma(value)}`개 판매했습니다!\n현재 `{data['name']}`의 주식 `{humanize.intcomma(sold)}`주 보유, {humanize.intcomma(left)}💰 남음."
            )

    @commands.command(name="지갑")
    @is_user()
    async def _wallet(self, ctx, target: discord.User = None):
        if target is None:
            target = ctx.author
        try:
            user = (
                await self.bot.sql(
                    0, f"SELECT * FROM `users` WHERE `user` = '{target.id}'"
                )
            )[0]
        except IndexError:
            return await ctx.reply(f"🗃 **{target}**님의 자산 정보가 없습니다.")
        else:
            embed = discord.Embed(
                title=f"💳 {target}님의 지갑",
                color=0xAFFDEF,
                timestamp=datetime.utcnow(),
            )
            embed.add_field(
                name="보유 현금", value=f"{humanize.intcomma(user['money'])}💰", inline=False
            )
            assets = 0
            stocks = await self.bot.sql(0, "SELECT * FROM `stocks`")
            for stock in stocks:
                price = (
                    await self.bot.sql(
                        0,
                        f"SELECT `{stock['id']}` FROM `prices` ORDER BY `time` DESC LIMIT 1",
                    )
                )[0]
                value = int(price[stock["id"]]) * int(user[stock["id"]])
                assets += value
                if int(user[stock["id"]]) != 0:
                    embed.add_field(
                        name=stock["name"],
                        value=f"{humanize.intcomma(user[stock['id']])}개 보유 중 (약 {humanize.intcomma(value)}💰)",
                    )
            assets += int(user["money"])
            embed.add_field(
                name="총 자산 가치", value=f"{humanize.intcomma(assets)}💰", inline=False
            )
            embed.set_author(name="Ark 프로젝트", icon_url=self.bot.user.avatar_url)
            embed.set_footer(text="얼어붙은 열정")
            embed.set_thumbnail(url=target.avatar_url_as(format="png", size=2048))
            if (await self.bot.is_owner(ctx.author)) is True:
                lcz = {"true": "ㅇ", "false": "ㄴ"}
                embed.add_field(
                    name="opt-out된 유저인가요?", value=lcz[user["optout"]], inline=False
                )
            await ctx.reply(embed=embed)

    @commands.command(name="랭킹")
    @is_user()
    async def _rank(self, ctx):
        users = await self.bot.sql(0, "SELECT * FROM `users`")
        assets = []
        for user in users:
            asset = 0
            stocks = await self.bot.sql(0, "SELECT * FROM `stocks`")
            for stock in stocks:
                price = (
                    await self.bot.sql(
                        0,
                        f"SELECT `{stock['id']}` FROM `prices` ORDER BY `time` DESC LIMIT 1",
                    )
                )[0]
                value = int(price[stock["id"]]) * int(user[stock["id"]])
                asset += value
            asset += int(user["money"])
            u = self.bot.get_user(int(user["user"]))
            if u is not None and user["optout"] != "true":
                assets.append([u, asset])
        assets.sort(key=itemgetter(1), reverse=True)
        text = "현재 재산 순위 / 순위 이름 자산\n \n"
        where = "순위 없음"
        i = 1
        for a in assets:
            if i <= 10:
                text += f"#{i}   {a[0]}   {humanize.intcomma(a[1])}\n"
            if a[0] == ctx.author:
                where = i
            i += 1
        await ctx.reply(f"```md\n{text}```\n \n현재 당신은 자산 랭킹에서 `{where}`위입니다.")


def setup(bot):
    bot.add_cog(Economy(bot))
    DiscordComponents(bot)