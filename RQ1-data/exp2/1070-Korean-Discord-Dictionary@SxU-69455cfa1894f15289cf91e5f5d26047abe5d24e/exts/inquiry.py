import discord
from discord.ext import commands
from discord_slash import cog_ext
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

        if len(str(msg.content)) <= 10 and len(files) <= 0:
            return await msg.reply("✉️ 문의를 남기려면 최소한 10자 이상 작성해야 해요.")

        async with aiohttp.ClientSession as cs:
            webhook = Webhook.from_url(config.Inquiry, adapter=AsyncWebhookAdapter(cs))
            embed = discord.Embed(description=f"유저 : <@{msg.author.id}>\nID : {msg.author.id}", color=0xD29B73, timestamp=datetime.utcnow())
            if not files:
                await webhook.send(msg.content, embed=embed, avatar=msg.author.avatar_url, name=msg.author)
            else:
                await webhook.send(msg.content, embed=embed, files=files, avatar=msg.author.avatar_url, name=msg.author)

    @cog_ext.cog_slash(
        name="answer",
        description="문의에 답장합니다.",
        options=[
            create_option(
                name="member",
                description="답변을 전달할 유저를 선택해주세요.",
                option_type=6,
                required=True,
            ),
        ],
    )
    @commands.has_permissions(administrator=True)
    async def _answer(self, ctx, member: discord.Member, *, reply):
        try:
            embed = discord.Embed(title="응답이 도착했어요!")
            await member.send(reply, embed=embed)
        except:
            return await ctx.send("👒 전송 실패; DM이 막혀있거나 서버에 더 이상 존재하지 않는 유저입니다.")
        await ctx.send("🗺 전송 완료!")

def setup(bot):
    bot.add_cog(Inquiry(bot))