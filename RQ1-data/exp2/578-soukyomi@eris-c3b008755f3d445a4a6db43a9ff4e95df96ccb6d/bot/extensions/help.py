'''
MIT License

Copyright (c) 2021 Caio Alexandre

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
'''

from typing import Mapping
from collections import defaultdict

from discord.ext import commands, menus
from discord.ext.commands import Cog, Command

from eris import Eris
from utils.context import ErisContext


class HelpPageSource(menus.ListPageSource):
    def __init__(self, mapping: Mapping[Cog, list[Command]]):
        entries = sorted(mapping.keys(), key=lambda c: c.qualified_name)
        self.mapping = mapping

        super().__init__(entries, per_page=6)

    def get_opening_note(self, ctx: ErisContext):
        command = f'{ctx.clean_prefix}{ctx.invoked_with}'
        messages = [
            'Use `{0} [command]` for more info on a command.',
            'Use `{0} [category]` for more info on a category.'
        ]

        return '\n'.join(messages).format(command)

    async def format_page(self, menu: menus.Menu, cogs: list[Cog]):
        ctx = menu.ctx
        footer = f'Page {menu.current_page + 1}/{self.get_max_pages()}'

        embed = ctx.get_embed(self.get_opening_note(ctx))
        embed.set_footer(text=footer)

        fields = []
        for cog in cogs:
            commands = [f'`{command.qualified_name}`' for command in self.mapping.get(cog)]
            name = f'{cog.emoji} {cog.qualified_name}'

            embed.add_field(name=name, value=', '.join(commands), inline=False)

        return embed


class HelpCommand(commands.HelpCommand):
    '''This class formats the bot's help command.'''

    async def send_bot_help(self, mapping: Mapping[Cog, list[Command]]):
        '''When the command is invoked without any argument.'''
        ctx = self.context
        bot = ctx.bot

        entries = await self.filter_commands(bot.commands, sort=True)
        all_commands = defaultdict(list)

        for command in entries:
            if not command.cog:
                continue

            if not hasattr(command.cog, 'emoji'):
                continue
            
            all_commands[command.cog].append(command)

        source = HelpPageSource(all_commands)
        menu = menus.MenuPages(source=source, check_embeds=True, clear_reactions_after=True)

        await menu.start(ctx)

    async def send_cog_help(self, cog: Cog):
        '''When the command is invoked with a cog as argument.'''
        if not hasattr(cog, 'emoji'):
            return

        ctx = self.context
        command = f'{ctx.clean_prefix}{ctx.invoked_with}'

        entries = await self.filter_commands(cog.get_commands(), sort=True)
        all_commands = [f'`{c.qualified_name}`' for c in entries]

        embed = ctx.get_embed()
        description = f'{cog.description}\nUse `{command} [command]` for more info on a command.'

        embed.title = f'{cog.emoji} {cog.qualified_name}'
        embed.description = description
        embed.add_field(name='Commands', value=', '.join(all_commands))

        await ctx.reply(embed=embed)

    async def send_group_help(self, group: commands.Group):
        '''When the command is invoked with a group as argument.'''
        ctx = self.context

        entries = await self.filter_commands(group.walk_commands(), sort=True)
        all_commands = [f'`{c.qualified_name}`' for c in entries]

        embed = ctx.get_embed()
        signature = command.usage or command.signature

        embed.title = f'{ctx.clean_prefix}{group.qualified_name} {signature}'
        embed.description = group.short_doc
        embed.add_field(name='Subcommands', value=', '.join(all_commands))

        await ctx.reply(embed=embed)

    async def send_command_help(self, command: Command):
        '''When the command is invoked with a command as argument.'''
        ctx = self.context

        embed = ctx.get_embed()
        signature = command.usage or command.signature

        embed.title = f'{ctx.clean_prefix}{command.qualified_name} {signature}'
        embed.description = command.short_doc

        await ctx.reply(embed=embed)


class Help(commands.Cog):
    '''Commands related to user help.'''

    def __init__(self, bot: Eris):
        self.bot = bot
        self.emoji = '\U0001f4da'

        self._original_help = bot.help_command
        bot.help_command = HelpCommand()
        bot.help_command.cog = self

    def cog_unload(self):
        self.bot.help_command = self._original_help

    @commands.command()
    async def about(self, ctx: ErisContext):
        '''Shows some information about the bot.'''
        app_info = await ctx.bot.application_info()
        owner = app_info.owner

        await ctx.reply(f'This bot was made by {owner}.')


def setup(bot: Eris):
    bot.add_cog(Help(bot))