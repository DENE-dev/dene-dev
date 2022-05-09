import io
import locale
import os
import sys
import traceback

import aiohttp
import aiomysql
import config
import discord
from discord.ext import commands

locale.setlocale(locale.LC_ALL, "")


class Ark(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    async def log(self, *args, **kwargs):
        async with aiohttp.ClientSession() as cs:
            webhook = Webhook.from_url(config.Debug, adapter=AsyncWebhookAdapter(cs))
            await webhook.send(*args, **kwargs)

    async def is_owner(self, user: discord.User):
        users = await self.sql(0, f"SELECT * FROM `users` WHERE `user` = '{user.id}'")
        if users:
            data = users[0]
            if data["permissions"] == "Administrator":
                return True

        return await super().is_owner(user)

    async def sql(self, type: int, exec: str):
        o = await aiomysql.connect(
            host=config.DB["host"],
            port=config.DB["port"],
            user=config.DB["user"],
            password=config.DB["password"],
            db=config.DB["schema"],
            autocommit=True,
        )
        c = await o.cursor(aiomysql.DictCursor)
        try:
            await c.execute(exec)
        except Exception as e:
            raise e
            o.close()
        else:
            if type == 0:
                results = await c.fetchall()
                o.close()
                return results
            o.close()
            return "Successfully Executed"

    async def record(self, content):
        try:
            payload = content.encode("utf-8")
            async with aiohttp.ClientSession(raise_for_status=True) as cs:
                async with cs.post("https://hastebin.com/documents", data=payload) as r:
                    post = await r.json()
                    uri = post["key"]
                    return f"https://hastebin.com/{uri}"
        except aiohttp.ClientResponseError:
            return discord.File(io.StringIO(content), filename="Traceback.txt")


bot = Ark(
    status=discord.Status.idle,
    activity=discord.Activity(name="레이드", type=5),
    description="천하의 모든 요마를 퇴치하고 나면... 계율을 무시하고 온천에 몸을 담그겠어!",
    command_prefix=commands.when_mentioned_or("중운님", "중운아"),
    strip_after_prefix=True,
    #    help_command=None,
    chunk_guilds_at_startup=True,
    intents=discord.Intents.all(),
    max_messages=10000,
)


def initiate(bot):
    exts = []
    for module in os.listdir("./exts"):
        if module.endswith(".py"):
            a = module.replace(".py", "")
            exts.append(f"exts.{a}")
    exts.append("jishaku")
    for ext in exts:
        try:
            bot.load_extension(ext)
        except Exception as e:
            s = traceback.format_exc()
            print(f"{e.__class__.__name__}: {s}")


@bot.event
async def on_error(event, *args, **kwargs):
    s = traceback.format_exc()
    content = f"{event}에 발생한 예외를 무시합니다;\n{s}"
    try:
        await bot.log(f"```{content}```")
    except:
        record = await bot.record(content)
        if isinstance(record, discord.File):
            await bot.log(file=record)
        else:
            await bot.log(record)


@bot.event
async def on_message(msg):
    if msg.author.bot:
        return

    if msg.content in ["중운아", "중운님", bot.user.mention]:
        await msg.reply(f"🚀 반갑습니다, **{msg.author}**님! 여기는 <#{msg.channel.id}> 채널입니다.")

    await bot.process_commands(msg)


@bot.check
async def _identify(ctx):
    rows = await bot.sql(0, f"SELECT * FROM `users` WHERE `user` = '{ctx.author.id}'")
    data = (await bot.sql(0, f"SELECT * FROM `ark` WHERE `bot` = '{bot.user.id}'"))[0]
    if not rows:
        if ctx.message.content in ["중운아 등록", "중운님 등록", f"{bot.user.mention} 등록"]:
            return True
        return False
    elif rows[0]["permissions"] == "Banned":
        await ctx.reply(f"⚛ 당신은 `{bot.user.name}`의 시스템에서 차단되었습니다. 자세한 내용은 개발자에게 문의하세요.")
        raise discord.Forbidden
    elif (await bot.is_owner(ctx.author)) is True:
        if data["maintain"] == "true":
            await ctx.reply("🔰 현재 점검 모드가 활성화되어 있습니다.")
        return True
    elif data["maintain"] == "true":
        await ctx.reply(f"🔰 현재 관리자에 의해 제한 모드가 활성화되어 있습니다.\n사유 : {data['reason']}")
        raise discord.Forbidden
    return True


initiate(bot)
bot.run(config.Token)