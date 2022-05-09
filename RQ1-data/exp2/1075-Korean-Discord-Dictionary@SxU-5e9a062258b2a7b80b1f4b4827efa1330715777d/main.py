import io
import locale
import sys
import traceback

import aiohttp
import aiomysql
import config
import discord
from discord.ext import commands
from discord_slash import SlashCommand

locale.setlocale(locale.LC_ALL, "")


class SxU(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    async def log(self, *args, **kwargs):
        async with aiohttp.ClientSession() as cs:
            webhook = Webhook.from_url(config.Debug, adapter=AsyncWebhookAdapter(cs))
            await webhook.send(*args, **kwargs)

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
            return "실행 완료"

    async def record(self, content):
        try:
            payload = content.encode("utf-8")
            async with aiohttp.ClientSession(raise_for_status=True) as cs:
                async with cs.post("https://hastebin.com/documents",
                                   data=payload) as r:
                    post = await r.json()
                    uri = post["key"]
                    return f"https://hastebin.com/{uri}"
        except aiohttp.ClientResponseError:
            return discord.File(io.StringIO(content), filename="Traceback.txt")


bot = SxU(
    status=discord.Status.dnd,
    activity=discord.Activity(name="어딘가에 귀를 기울여", type=discord.ActivityType.listening),
    description="...을 위해 배신할 수 있다는 게 부러워서.",
    command_prefix=commands.when_mentioned_or("스우"),
    strip_after_prefix=True,
    help_command=None,
    chunk_guilds_at_startup=True,
    intents=discord.Intents.all(),
    max_messages=200000,
)
slash = SlashCommand(
    client=bot,
    sync_commands=True,
    delete_from_unused_guilds=False,
    sync_on_cog_reload=True,
    override_type=False,
)


@bot.command(name="동기화")
@commands.is_owner()
async def _sync(ctx):
    await slash.sync_all_commands()
    await ctx.reply("🌧 동기화 완료!")


def initiate(bot):
    exts = [
        "exts.events",
        "exts.mods",
        "jishaku",
    ]
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
        await bot.log(f"```py\n{content}```", avatar_url=bot.user.avatar_url, name=f"{bot.user.name} 디버깅")
    except:
        record = await bot.record(content)
        if isinstance(record, discord.File):
            await bot.log(file=record, avatar_url=bot.user.avatar_url, name=f"{bot.user.name} 디버깅")
        else:
            await bot.log(record, avatar_url=bot.user.avatar_url, name=f"{bot.user.name} 디버깅")


initiate(bot)
bot.run(config.Token)