import discord
from discord.ext import commands

class RoleManager(commands.Cog, name="역할 관리자"):
    def __init__(self, bot):
        self.bot = bot

    @commands.group(name="역할")
    @commands.guild_only()
    async def roleSet(self, ctx):
        if ctx.invoked_subcommand is None:
            rows = await self.bot.sql(0, f"SELECT * FROM `roles` WHERE `guild` = '{ctx.guild.id}'")
            if not rows:
                return await ctx.reply("🥀 이 서버에는 직접 받을 수 있는 역할이 없습니다.")
            gets = []
            for row in rows:
                if row["receive"] == "true":
                    role = ctx.guild.get_role(int(row["role"]))
                    if role is not None:
                        gets.append({"role": role, "code": row["code"]})
            if not gets:
                return await ctx.reply("🥀 이 서버에는 직접 받을 수 있는 역할이 없습니다.")
            text = f"🪴 {ctx.guild.name}의 역할 목록\n \n"
            for get in gets:
                text += f"`{get['code']}` - `{get['role'].name}`\n"
            await ctx.reply(text)

    @roleSet.command(name="주기")
    @commands.guild_only()
    @commands.has_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    async def _give(self, ctx, roles: commands.Greedy[discord.Role], member: discord.Member):
        if not roles:
            raise commands.BadArgument
        applied = []
        for role in roles:
            if role >= ctx.guild.me.top_role:
                continue
            if role not in member.roles:
                await member.add_roles(role)
                applied.append(role)
        await ctx.reply(f"🌴 {member}님에게 {len(applied)}개의 역할을 적용했습니다.")

    @roleSet.command(name="뺏기")
    @commands.guild_only()
    @commands.has_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    async def _remove(self, ctx, roles: commands.Greedy[discord.Role], member: discord.Member):
        if not roles:
            raise commands.BadArgument
        disapplied = []
        for role in roles:
            if role >= ctx.guild.me.top_role:
                continue
            if role not in member.roles:
                await member.add_roles(role)
                disapplied.append(role)
        await ctx.reply(f"⚘ {member}님에게서 {len(applied)}개의 역할을 삭제했습니다.")

def setup(bot):
    bot.add_cog(RoleManager(bot))