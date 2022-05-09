import aiohttp
import random
import re
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

        if (
            msg.content.startswith("스우")
            and (await self.bot.is_owner(msg.author)) is True
        ):
            return

        content = msg.content
        if content == "" or content is None:
            content = "*메시지 내용이 없어요.*"

        if len(content) > 800:
            content = await self.bot.record(msg.content)

        if msg.channel.type == discord.ChannelType.private:
            rows = await self.bot.sql(
                0,
                f"SELECT * FROM `inquiries` WHERE `user` = '{msg.author.id}' AND `archived` = 'false'",
            )
            guild = self.bot.get_guild(642630345967271946)
            if not rows:
                a = False
                number = None
                while a is False:
                    temp = random.randint(1048576, 16777215)
                    number = str(hex(temp))[-6:]
                    check = await self.bot.sql(
                        0, f"SELECT * FROM `inquiries` WHERE `inquiry` = '{number}'"
                    )
                    if not check:
                        a = True
                category = guild.get_channel(873864538431324191)
                channel = await category.create_text_channel(name=str(msg.author))
                embed = discord.Embed(
                    title="새로운 문의가 도착했어요!",
                    description=f"""
**문의 처리는 어떻게 해야 하나요?**

1️⃣. 이 채널(<#{channel.id}>)에 답장하세요.
2️⃣. `/close inquiry: {number}`를 사용해 종료하세요.
                    """,
                    color=0xD29B73,
                    timestamp=datetime.utcnow(),
                )
                embed.add_field(
                    name="문의한 유저",
                    value=f"ID: {msg.author.id}\n멘션: <@!{msg.author.id}>",
                    inline=False,
                )
                if isinstance(content, discord.File):
                    embed.add_field(name="메시지 내용", value="아래 파일을 참조하세요.", inline=False)
                else:
                    embed.add_field(name="메시지 내용", value=content, inline=False)
                if msg.attachments:
                    a = ""
                    i = 1
                    for attachment in msg.attachments:
                        a += f"[파일 #{i}]({attachment.url})\n"
                        i += 1
                    embed.add_field(name="파일 목록", value=a)
                embed.set_thumbnail(url=msg.author.avatar_url)
                embed.set_footer(text=f"이 문의의 고유 번호는 {number}")
                embed.set_author(name="Project SxU", icon_url=self.bot.user.avatar_url)
                top = None
                if isinstance(content, discord.File):
                    top = await channel.send(
                        "📨 새로운 문의가 도착했어요!", embed=embed, file=content
                    )
                else:
                    top = await channel.send("📨 새로운 문의가 도착했어요!", embed=embed)
                await top.pin()
                await self.bot.sql(
                    1,
                    f"INSERT INTO `inquiries`(`inquiry`, `user`, `channel`, `top`, `archived`) VALUES('{number}', '{msg.author.id}', '{channel.id}', '{top.id}', 'false')",
                )
                return await msg.reply(
                    f"""
💎 새로운 문의가 등록되었어요!
관리자가 최소 24시간 내에 답장할 거에요.
더 남기실 내용이 있으시다면 DM으로 자유롭게 남겨주세요 :)

*이 문의의 고유 번호는 `{number}`(이)에요.*
*문의에 문제가 있다면 이 번호를 사용해 크래프#1234로 문의해주세요.*
                """
                )
            else:
                data = rows[0]
                channel = self.bot.get_channel(int(data["channel"]))
                if channel is None:
                    await self.bot.sql(
                        1,
                        f"UPDATE `inquiries` SET `archived` = 'true' WHERE `inquiry` = '{data['inquiry']}'",
                    )
                    return await msg.reply(
                        "🔇 이 문의는 전달되지 않았어요. 채널을 찾지 못했어요.\n이 문의는 자동으로 종료 처리 되었어요.",
                        delete_after=3,
                    )
                embed = discord.Embed(
                    color=0xD29B73,
                    timestamp=datetime.utcnow(),
                )
                embed.add_field(
                    name="문의한 유저",
                    value=f"ID: {msg.author.id}\n멘션: <@!{msg.author.id}>",
                    inline=False,
                )
                if isinstance(content, discord.File):
                    embed.add_field(name="메시지 내용", value="아래 파일을 참조하세요.", inline=False)
                else:
                    embed.add_field(name="메시지 내용", value=content, inline=False)
                if msg.attachments:
                    a = ""
                    i = 1
                    for attachment in msg.attachments:
                        a += f"[파일 #{i}]({attachment.url})\n"
                        i += 1
                    embed.add_field(name="파일 목록", value=a)
                embed.set_thumbnail(url=msg.author.avatar_url)
                embed.set_footer(text=f"이 문의의 고유 번호는 {data['inquiry']}")
                embed.set_author(name="Project SxU", icon_url=self.bot.user.avatar_url)
                if isinstance(content, discord.File):
                    return await channel.send(embed=embed, file=content)
                await channel.send(embed=embed)
                return await msg.reply("✉ 문의가 전달되었어요.", delete_after=3)

        if msg.channel.category.id == 873864538431324191:
            if msg.content.startswith("#"):
                return
            rows = await self.bot.sql(
                0, f"SELECT * FROM `inquiries` WHERE `channel` = '{msg.channel.id}'"
            )
            if rows[0]["archived"] == "true":
                await msg.delete()
                return await msg.channel.send(
                    f"🔇 {msg.author.mention} - 이 답장은 전달되지 않았어요. `{rows[0]['inquiry']}` 문의는 종료되었어요.",
                    delete_after=3,
                )
            member = msg.guild.get_member(int(rows[0]["user"]))
            if member is None:
                await msg.delete()
                await self.bot.sql(
                    0,
                    f"UPDATE `inquiries` SET `archived` = 'true' WHERE `channel` = '{msg.channel.id}'",
                )
                return await msg.channel.send(
                    f"🔇 {msg.author.mention} - 이 답장은 전달되지 않았어요. 유저가 서버에서 나간 것 같아요.\n이 문의는 자동으로 종료 처리 되었어요.",
                    delete_after=3,
                )
            try:
                files = []
                for attachment in msg.attachments:
                    file = await attachment.to_file()
                    files.append(file)
                await member.send(f"✉ **{msg.author}** : {content}", files=files)
                return await msg.reply("📤 답장 전달이 완료되었어요!", delete_after=3)
            except:
                await msg.delete()
                return await msg.channel.send(
                    f"🔇 {msg.author.mention} -  이 답장은 전달되지 않았어요. {member} 유저의 DM이 차단되어 있어요.",
                    delete_after=3,
                )

    @cog_ext.cog_slash(
        name="close",
        description="문의를 종료합니다. 종료 후에는 되돌릴 수 없습니다!",
        options=[
            create_option(
                name="inquiry",
                description="문의의 고유 번호를 입력해주세요.",
                option_type=3,
                required=True,
            ),
        ],
        guild_ids=[642630345967271946],
    )
    @commands.has_permissions(administrator=True)
    async def _close(self, ctx, inquiry: str):
        await ctx.defer(hidden=True)
        inquiry = (inquiry.lower()).strip()
        if len(inquiry) != 6:
            return await ctx.send("📻 문의 고유 번호는 6자리 숫자 및 영어만 사용되어요.", hidden=True)
        abc = (re.sub("[^a-z0-9]", "", inquiry)).strip()
        if abc != inquiry:
            return await ctx.send("📻 문의 고유 번호는 6자리 숫자 및 영어만 사용되어요.", hidden=True)
        rows = await self.bot.sql(
            0, f"SELECT * FROM `inquiries` WHERE `inquiry` = '{inquiry}'"
        )
        if not rows:
            return await ctx.send(f"✉ `{inquiry}` 문의를 찾지 못했어요.", hidden=True)
        if rows[0]["archived"] == "true":
            return await ctx.send(f"🔒 `{inquiry}` 문의는 이미 종료되었어요.", hidden=True)
        user = ctx.guild.get_member(int(rows[0]["user"]))
        try:
            await user.send(f"🎓 당신의 문의(`{inquiry}`)가 종료되었어요.")
        except:
            pass
        channel = ctx.guild.get_channel(int(rows[0]["channel"]))
        if channel is not None:
            msg = await channel.fetch_message(int(rows[0]["top"]))
            if msg is not None:
                await msg.edit(content="📁 이 문의는 종료되었어요.")
            await channel.edit(topic="⛔ 종료됨")
        await self.bot.sql(
            1,
            f"UPDATE `inquiries` SET `archived` = 'true' WHERE `inquiry` = '{inquiry}'",
        )
        await ctx.send(f"🗂 `{inquiry}` 문의를 종료했어요. 필요하다면 이 채널을 삭제해도 돼요.", hidden=True)


def setup(bot):
    bot.add_cog(Inquiry(bot))