import discord
from discord.ext import commands

class VoiceMaster(commands.Cog, name="임시 채널 생성"):
    def __init__(self, bot):
        self.bot = bot

    async def getVM(self, guild):
        rows = await self.bot.sql(0, f"SELECT `voicemaster` FROM `guilds` WHERE `guild` = '{guild.id}'")
        if not rows:
            return
        return rows[0]

    @commands.Cog.listener()
    async def on_voice_state_update(member, before, after):
        data = await self.getVM(member.guild)
        if data is None:
            return

        if before.channel != after.channel:
            sql = await self.bot.sql(0, f"SELECT * FROM `voicemaster` WHERE `id` = '{before.channel.id}'")
            if not sql:
                return
            if before.channel.members:
                return
            await self.bot.sql(1, f"DELETE FROM `voicemaster` WHERE `id` = '{before.channel.id}'")
            await before.channel.delete(reason="VoiceMaster - 음성 채널이 비어서 자동 삭제되었습니다.")

        if after.channel.id == int(data["voicemaster"]):
            category = after.channel.category
            if category is None:
                return
            overwrites = {
                member: discord.PermissionOverwrite(manage_channels=True, manage_permissions=True, connect=True, mute_members=True, deafen_members=True),
                member.guild.me: discord.PermissionOvererite(manage_channels=True, manage_permissions=True),
                member.guild.default_role: discord.PermissionOverwrite(connect=True),
            }
            voice = await category.create_voice_channel(name=f"{member.name}님의 채널", overwrites=overwrites, reason=f"VoiceMaster - {member}님이 채널 생성을 요청했습니다.")
            await member.move_to(voice, reason=f"VoiceMaster - {member}님이 채널 생성을 요청했습니다.")
            await self.bot.sql(1, f"INSERT INTO `voicemaster`(`id`, `owner`) VALUES('{voice.id}', '{member.id}')")

    @commands.group(name="음성")
    @commands.guild_only()
    async def voiceMaster(self, ctx):
        if ctx.invoked_subcommand is None:
            return

    @voiceMaster.command(name="이름")
    @commands.guild_only()
    @commands.cooldown(rate=1, per=300, type=commands.BucketType.user)
    async def _naming(self, ctx, *, new_name):
        if not ctx.author.voice:
            return await ctx.reply("🎡 이 명령어를 사용하려면 음성 채널에 있어야 합니다.")
        rows = await self.bot.sql(f"SELECT * FROM `voicemaster` WHERE `id` = '{ctx.author.voice.channel.id}'")
        if not rows:
            return await ctx.reply("🥨 이 명령어는 생성된 음성 채널에서만 사용 가능합니다.")
        elif int(rows[0]["owner"]) != ctx.author.id:
            return await ctx.reply("🥐 이 명령어는 자신이 소유자인 음성 채널에서만 사용 가능합니다..")
        else:
            await ctx.author.voice.channel.edit(name=new_name, reason=f"VoiceMaster - {ctx.author}님이 채널 이름 변경을 요청했습니다.")
            await ctx.reply("🥠 채널 이름을 `{new_name}`(으)로 변경했습니다.")

def setup(bot):
    bot.add_cog(VoiceMaster(bot))