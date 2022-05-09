import aiohttp
import config
import discord
from discord import Webhook, AsyncWebhookAdapter
from discord.ext import commands
from discord_slash import cog_ext
from discord_slash.utils.manage_commands import create_option
from datetime import datetime


class Inquiry(commands.Cog, name="지원"):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, msg):
        if msg.author.bot:
            return

        if msg.content.startswith("스우") and (await self.bot.is_owner(msg.author)) is True:
            return

        content = None
        if len(msg.content) > 500:
            content = await self.bot.record(msg.content)

        if msg.channel.type == discord.ChannelType.private:
            rows = await self.bot.sql(0, f"SELECT * FROM `inquiries` WHERE `user` = '{msg.author.id}' AND `archived` = 'false'")
            guild = self.bot.get_guild(642630345967271946)
            if not rows:
                a = False
                number = None
                while a is False:
                    temp = random.randint(1048576, 16777215)
                    number = str(hex(temp))[-6:]
                    check = await self.bot.sql(0, f"SELECT * FROM `inquiries` WHERE `number` = '{number}'")
                    if not check:
                        a = True
                category = guild.get_channel(873864538431324191)
                channel = await category.create_text_channel(name=str(msg.author))
                embed = discord.Embed(
                    title="새로운 문의가 도착했어요!",
                    description=f"""
**이 문의에 답장하려면 어떻게 해야 하나요?**

1️⃣. 이 채널(<#{channel.id}>)에 메시지를 보내세요.
2️⃣. `/reply no: {number} content: 답장할 내용`
                    """,
                    color=0xD29B73,
                    timestamp=datetime.utcnow(),
                )
                embed.add_field(name="문의한 유저", value="ID: {msg.author.id}\n멘션: <@!{msg.author.id}>", inline=False)
                if len(msg.content) <= 500:
                    if msg.content != "":
                        embed.add_field(name="메시지 내용", value=msg.content, inline=False)
                else:
                    if isinstance(content, discord.File):
                        embed.add_field(name="메시지 내용", value="아래 파일을 참조하세요.", inline=False)
                    else:
                        embed.add_field(name="메시지 내용", value=f"[메시지 내용 확인하기]({content})", inline=False)
                if msg.attachments:
                    i = 1
                    for attachment in msg.attachments:
                        a += "[파일 #{i}]({attachment.url})\n"
                        i += 1
                    embed.add_field(name="파일 목록", value=a)
                embed.set_thumbnail(url=msg.author.avatar_url)
                embed.set_footer(text=f"이 문의의 고유 번호는 {number}")
                embed.set_author(name="Project SxU", icon_url=self.bot.user.avatar_url)
                if isinstance(content, discord.File):
                    return await channel.send("📨 새로운 문의가 도착했어요!", embed=embed, file=content)
                await channel.send("📨 새로운 문의가 도착했어요!", embed=embed)
                await self.bot.sql(1, f"INSERT INTO `inquiries`(`inquiry`, `user`, `channel`, `archived`) VALUES('{number}', '{msg.author.id}', '{channel.id}', 'false')")
            else:
                return
            

def setup(bot):
    bot.add_cog(Inquiry(bot))