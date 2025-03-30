import typing as t
import datetime as dt

import discord
from discord.ext.menus import MenuPages, ListPageSource
from discord.ext import commands


def syntax(command: commands.Command):
    cmd_and_aliases = "|".join([str(command), *command.aliases])
    params = []

    for k, v in command.params.items():
        if k not in ("self", "ctx"):
            params.append(
                f"[{k}]"
                if any(
                    substring in str(v)
                    for substring in ["Optional", "None", "NoneType"]
                )
                else f"<{k}>"
            )

    params = " ".join(params)
    _syntax = f'`{cmd_and_aliases}{f" {params}" if params != "" else ""}`'
    return _syntax


class HelpMenu(ListPageSource):
    def __init__(self, ctx, data, cog, bot):
        self.ctx = ctx
        self.bot = bot
        self.cog = cog
        super().__init__(data, per_page=3)

    async def write_page(self, menu, fields=[]):
        offset = (menu.current_page * self.per_page) + 1
        len_data = len(self.entries)

        embed = discord.Embed(
            title=f"Help `{self.cog}`",
            description=f"Welcome to the Matrixine help menu!\nPrefix is {self.bot.PREFIX}",
            color=self.bot.COLOR,
        )
        embed.set_thumbnail(url=self.ctx.guild.me.avatar.url)
        embed.set_footer(
            text=f"{offset:,} - {min(len_data, offset + self.per_page - 1):,} of {len_data:,} commands."
        )

        for v, n in fields:
            embed.add_field(name=n, value=f"**{v}**", inline=False)

        return embed

    async def format_page(self, menu, entries):
        fields = []
        for e in entries:
            fields.append((e.description or "No description", syntax(e)))
        return await self.write_page(menu, fields)


class Help(commands.Cog):
    """Handles formatting the help menus!"""
    def __init__(self, bot):
        self.bot = bot

    async def print_default_help_menu(self, ctx):
        embed = discord.Embed(
            title="Welcome to the Matrixine Help Menu!",
            description=f"Use `{self.bot.PREFIX}help module` to gain more information about that module!"
            f"\nThe prefix is case insensitive.",
            colour=self.bot.COLOR,
            timestamp=dt.datetime.now(),
        )
        embed.set_thumbnail(url=self.bot.user.avatar.url)
        embed.set_footer(
            text=f"Requested by {ctx.author.display_name}",
            icon_url=ctx.author.avatar.url,
        )
        embed.add_field(
            name="About",
            value=f"*{self.bot.BOT_INFO.name}* is developed in Discord.py v2.5.2 "
            f"by `{self.bot.OWNER_UN}`\n*{self.bot.BOT_INFO.name}* "
            f"is running on {self.bot.VERSION}",
            inline=False,
        )
        value = []
        for cog in self.bot.cogs:
            value.append(f"`{cog}`: {self.bot.cogs[cog].__doc__ or 'No description'}")
            msg = "\n".join(value)
        embed.add_field(name="Modules", value=msg, inline=False)
        return await ctx.send(embed=embed)

    async def print_cog_help_menu(self, ctx, cog):
        cog_commands = self.bot.get_cog(cog).get_commands()
        if cog_commands:
            menu = MenuPages(
                source=HelpMenu(ctx, list(cog_commands), cog, self.bot),
                delete_message_after=True,
                timeout=60.0,
            )
            return await menu.start(ctx)

        else:
            embed = discord.Embed(
                title=f"Help {cog}!",
                description=f"{self.bot.cogs[cog].__doc__ if self.bot.cogs[cog].__doc__ else 'No description.'}\n",
                colour=self.bot.COLOR,
                timestamp=dt.datetime.now(),
            )
            embed.set_thumbnail(url=self.bot.user.avatar.url)
            embed.set_footer(text=f"Requested by {ctx.author.display_name}")
            embed.add_field(
                name="This module has no commands.",
                value="This module is purely functional and contains no commands.",
                inline=False,
            )
            return await ctx.send(embed=embed)

    async def walk_subcommands(self, ctx: commands.Context, command_tree: list[str]):
        current_command: commands.Command = self.bot.get_command(command_tree[0])
        if not current_command:
            return None
        for subcommand_name in command_tree[1:]:
            current_command = current_command.get_command(subcommand_name)
            if not current_command:
                return None
        return current_command, "::".join([c.capitalize() for c in command_tree])

    async def print_command_help_menu(
        self, ctx, module: commands.Cog, command: commands.Command, command_tree: str
    ):
        embed = discord.Embed(
            title=f"Help with `{command_tree}`",
            description=syntax(command),
            color=self.bot.COLOR,
        )
        embed.add_field(
            name="Command description",
            value=command.description if command.description else "No description",
            inline=False,
        )
        embed.set_thumbnail(url=self.bot.user.avatar.url)
        await ctx.send(embed=embed)

    @commands.hybrid_command(
        name="help", aliases=["h"], description="Shows this message"
    )
    async def show_help_test(
        self, ctx, module: t.Optional[str], *, command_tree_str: t.Optional[str]
    ):
        if not module:
            return await self.print_default_help_menu(ctx)

        cog = module.lower()
        if (
            any((desired_cog := bot_cog).lower() == cog for bot_cog in self.bot.cogs)
            and not command_tree_str
        ):
            return await self.print_cog_help_menu(ctx, desired_cog)
        elif not any(cog == bot_cog.lower() for bot_cog in self.bot.cogs):
            return await ctx.send(f"Module `{module}` is not a thing!")

        command_tree = command_tree_str.split(" ")
        desired_command, command_tree = await self.walk_subcommands(ctx, command_tree)
        if not desired_command:
            return await ctx.send(f"The command `{command_tree_str}` does not exist!")

        await self.print_command_help_menu(ctx, module, desired_command, command_tree)

async def setup(bot):
    await bot.add_cog(Help(bot))
