from discord.ext import commands
from discord_slash import cog_ext
from discord_slash.utils.manage_components import create_select, create_select_option, create_actionrow

class Role(commands.Cog, name="역할 관리"):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="초기화")
    @commands.is_owner()
    async def _initiate(self, ctx, channel: discord.TextChannel):
        dropdown = create_select(
            custom_id="assign",
            options=[
                create_select_option(
                    label="기본적인 디스코드 팁",
                    value="650655526358614040",
                    emoji="📌",
                ),
                create_select_option(
                    label="디스코드 서버 팁",
                    value="800181453878722570",
                    emoji="📂",
                ),
                create_select_option(
                    label="글자 및 채팅 꾸미기",
                    value="648043207766048768",
                    emoji="🖍️",
                ),
                create_select_option(
                    label="서버 꾸미기",
                    value="661806599127433227",
                    emoji="🛠️",
                ),
                create_select_option(
                    label="개발자",
                    value="662850837978021899",
                    emoji="⚒️",
                ),
                create_select_option(
                    label="해결사",
                    value="754538937283903570",
                    description="언제든지 멘션될 수 있는 역할입니다. 질문을 해결하고 싶다면 이 역할을 받아보세요.",
                    emoji="🕵️",
                ),
                create_select_option(
                    label="서버장",
                    value="805383081955426325",
                    emoji="🗺️",
                ),
            ],
            placeholder="받고 싶은 역할을 선택해주세요.",
            min_values=0,
            max_values=7,
        )
        await channel.send("🎛 Korean Discord Dictionary 역할 관리 시스템\n🎚️ 역할을 제거하려면 선택 해제해주세요.", components=[create_actionrow(dropdown)])

    @cog_ext.cog_component()
    async def assign(self, ctx):
        temp = [
            "650655526358614040",
            "800181453878722570",
            "805383081955426325",
            "662850837978021899",
            "648043207766048768",
            "661806599127433227",
            "754538937283903570"
        ]
        if ctx.guild is not None:
            remove = [x for x in temp if x not in ctx.selected_options]
            await ctx.defer(hidden=True)
            for value in ctx.selected_options:
                role = ctx.guild.get_role(int(value))
                if role is not None:
                    await ctx.author.add_roles(role)
            for value in remove:
                role = ctx.guild.get_role(int(value))
                if role is not None:
                    await ctx.author.remove_roles(role)
            await ctx.send(f"✅ 당신에게 **{len(ctx.selected_options)}**개의 역할이 적용되었어요.", hidden=True)

def setup(bot):
    bot.add_cog(Role(bot))