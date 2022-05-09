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
        files = []

        if msg.author.bot:
            return

        if msg.channel.type != discord.ChannelType.private:
            return

        if msg.attachments:
            for attachment in msg.attachments:
                file = await attachment.to_file()
                files.append(file)

        if len(str(msg.content)) <= 5 and len(files) <= 0:
            return await msg.reply("✉️ 문의를 남기려면 최소한 5자 이상 작성해야 해요.")

        async with aiohttp.ClientSession() as cs:
            webhook = Webhook.from_url(config.Inquiry, adapter=AsyncWebhookAdapter(cs))
            embed = discord.Embed(
                title="새로운 문의가 도착했어요!",
                description=f"유저 : <@{msg.author.id}>\nID : {msg.author.id}",
                color=0xD29B73,
                timestamp=datetime.utcnow(),
            )
            embed.set_thumbnail(
                url=msg.author.avatar_url_as(static_format="png", size=2048)
            )
            embed.set_author(name="Project SxU", icon_url=self.bot.user.avatar_url)
            if not files:
                await webhook.send(
                    msg.content,
                    embed=embed,
                    avatar_url=str(msg.author.avatar_url),
                    username=str(msg.author),
                )
            else:
                await webhook.send(
                    msg.content,
                    embed=embed,
                    files=files,
                    avatar_url=str(msg.author.avatar_url),
                    username=str(msg.author),
                )
        await msg.reply("📩 문의 전달 완료! 관리자가 답변하기까지 최대 24시간이 소요될 수 있어요.")

    @cog_ext.cog_slash(
        name="reply",
        description="문의의 답변을 전달합니다.",
        options=[
            create_option(
                name="member",
                description="답변을 전달할 유저를 선택해주세요.",
                option_type=6,
                required=True,
            ),
            create_option(
                name="content",
                description="답변의 내용을 입력해주세요.",
                option_type=3,
                required=True,
            ),
        ],
    )
    @commands.has_permissions(administrator=True)
    async def _reply(self, ctx, member: discord.Member, *, content):
        await ctx.defer()
        try:
            embed = discord.Embed(
                title="응답이 도착했어요!",
                description=reply,
                color=0xD29B73,
                timestamp=datetime.utcnow(),
            )
            embed.set_thumbnail(
                url=member.avatar_url_as(static_format="png", size=2048)
            )
            embed.set_footer(text=f"{ctx.author.name}님이 답장함")
            embed.set_author(name="Project SxU", icon_url=self.bot.user.avatar_url)
            await member.send(embed=embed)
        except:
            return await ctx.send("👒 전송에 실패했어요. 개인 메시지가 꺼져있거나 서버에 참여하지 않은 유저에요.")
        await ctx.send(f"🗺 **{member}**님에게 전송을 완료했어요!")


def setup(bot):
    bot.add_cog(Inquiry(bot))