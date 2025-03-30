import datetime as dt
import io
import typing as t

import discord
from discord.ext import commands

import util


class Mod(commands.Cog):
    """Handles moderation commands and lets people abuse their power."""

    def __init__(self, bot):
        self.bot = bot
        self.guilds = self.bot.MONGO_DB["Guilds"]
        self.moderation = self.bot.MONGO_DB["Moderation"]

    def update_punishments(self, ctx, target, reason, count_string, reasons_string):
        if result := self.moderation.find_one(ctx.guild.id):
            try:
                entry = result["moderation"]["punishments"][str(target.id)]
                entry[count_string] += 1
                entry[reasons_string].append(reason)
                result["moderation"]["punishments"][str(target.id)] = entry
            except KeyError:
                new_entry = util.DEFAULT_MODERATION_PUNISHMENT_ENTRY
                new_entry[count_string] = 1
                new_entry[reasons_string] = [reason]
                result["moderation"]["punishments"][str(target.id)] = new_entry
            print(result)
            self.moderation.update_one(
                {"_id": ctx.guild.id}, {"$set": {"moderation": result["moderation"]}}
            )

    @commands.hybrid_command(
        name="ban",
        description="Bans the mentioned users. Can accept multiple users at once.",
    )
    @commands.has_permissions(ban_members=True)
    async def ban_user_command(
        self,
        ctx,
        targets: commands.Greedy[discord.User],
        *,
        reason: t.Optional[str] = "No reason",
    ):
        if not len(targets):
            help_command: commands.Command = self.bot.get_command("help")
            return await ctx.invoke(help_command, "mod", command_tree_str="ban")

        banned = ""
        colorAvg = ctx.author.id
        for target in targets:
            self.update_punishments(ctx, target, reason, "times_banned", "ban_reasons")
            guild = ctx.guild
            member = guild.get_member(target.id)
            banned += f"{target.name}\n"
            if member:
                if (
                    ctx.guild.me.top_role.position > target.top_role.position
                    and not target.guild_permissions.administrator
                ):
                    await target.ban(reason=reason)

                elif (
                    ctx.guild.me.top_role.position < target.top_role.position
                    or target.guild_permissions.administrator
                ):
                    await ctx.send(f"I can't ban {target.name}")

            else:
                await guild.ban(target, reason=reason)

            await self.on_member_ban(guild, target, reason, ctx.author)

            colorAvg += (ctx.author.id + target.id) / 2

        if len(targets) == 1:
            msg = f"1 member banned for {reason.lower()}"
        else:
            msg = f"{len(targets)} members banned {reason.lower()}"

        embed = discord.Embed(
            title=msg,
            description=f"{ctx.author.mention} had {msg}:\n{banned}",
            color=discord.Color.random(seed=colorAvg),
            timestamp=dt.datetime.now(),
        )
        embed.set_author(
            name=f"{ctx.author.name}#{ctx.author.discriminator}",
            icon_url=ctx.author.avatar_url,
        )
        embed.set_footer(text="Imagine being a loser.")

        await ctx.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_ban(
        self,
        guild: discord.Guild,
        user: discord.User,
        reason: t.Optional[str],
        moderator: t.Optional[discord.Member],
    ):
        if not (result := self.guilds.find_one(guild.id)):
            return
        logs = result["data"]["logs"]
        if not (ban_channel := logs["member_ban_channel"]):
            return

        embed = discord.Embed(
            title="Member Banned",
            description=f"**Offender:** {user.name}\n"
            f"**Reason:** {reason or 'not banned from bot'}\n"
            f"**Responsible moderator:** {moderator.mention or 'not banned from bot'}",
            color=self.bot.COLOR,
            timestamp=dt.datetime.now(),
        )
        embed.set_footer(text=f"ID: {user.id}")
        embed.set_author(
            icon_url=moderator.avatar.url or "",
            name=moderator.name or "Not banned from bot",
        )
        await ban_channel.send(embed=embed)

    @commands.hybrid_command(
        name="unban",
        description="Unbans the mentioned users. Can accept multiple users at once.",
    )
    @commands.has_permissions(ban_members=True)
    async def unban_member_command(
        self,
        ctx,
        targets: commands.Greedy[discord.User],
        *,
        reason: t.Optional[str] = "No reason",
    ):
        if not len(targets):
            help_command: commands.Command = self.bot.get_command("help")
            return await ctx.invoke(help_command, "mod", command_tree_str="unban")

        unbanned = ""
        for target in targets:
            await ctx.guild.unban(target, reason=reason)
            unbanned += f"{target.name}\n"

        if len(targets) == 1:
            msg = f"1 member unbanned for {reason.lower()}"
        else:
            msg = f"{len(targets)} members unbanned for {reason.lower()}"

        embed = discord.Embed(
            title=msg,
            description=f"{ctx.author.mention} had {msg}:\n{unbanned}",
            color=discord.Color.random(seed=ctx.author.id),
            timestamp=dt.datetime.now(),
        )
        embed.set_author(
            name=f"{ctx.author.name}#{ctx.author.discriminator}",
            icon_url=ctx.author.avatar_url,
        )
        embed.set_footer(text="No longer losers.")
        await ctx.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_unban(
        self,
        guild: discord.Guild,
        user: discord.User,
        reason: t.Optional[str],
        moderator: t.Optional[discord.Member],
    ):
        if not (result := self.guilds.find_one(guild.id)):
            return
        logs = result["data"]["logs"]
        if not (ban_channel := logs["member_ban_channel"]):
            return

        embed = discord.Embed(
            title="Member Unbanned",
            description=f"**User:** {user.name}\n"
            f"**Reason:** {reason or 'not unbanned from bot'}\n"
            f"**Responsible moderator:** {moderator.mention or 'not unbanned from bot'}",
            color=self.bot.COLOR,
            timestamp=dt.datetime.now(),
        )
        embed.set_footer(text=f"ID: {user.id}")
        embed.set_author(
            icon_url=moderator.avatar.url or "",
            name=moderator.name or "Not banned from bot",
        )
        await ban_channel.send(embed=embed)

    @commands.hybrid_command(
        name="purge",
        description="Deletes the amount of messages specified up to 2 weeks",
    )
    @commands.has_permissions(manage_messages=True)
    async def purge_message_command(
        self,
        ctx: commands.Context,
        count: int,
        targets: commands.Greedy[discord.User],
        *,
        reason: t.Optional[str] = "No reason",
    ):
        def _check(msg: discord.Message):
            return not targets or msg.author in targets

        if count <= 0:
            help_command: commands.Command = self.bot.get_command("help")
            return await ctx.invoke(help_command, "mod", command_tree_str="purge")

        async with ctx.typing():
            deleted = await ctx.channel.purge(limit=count + 1, check=_check)
        await ctx.send(f"{len(deleted) - 1} messages were purged from the channel")

    @commands.hybrid_command(
        name="mute",
        aliases=["timeout"],
        description="Times out the mentioned users. Can accept multiple users at once",
    )
    @commands.has_permissions(manage_roles=True)
    async def mute_member_command(
        self,
        ctx,
        targets: commands.Greedy[discord.Member],
        time: str,
        *,
        reason: t.Optional[str] = "No reason",
    ):
        if not len(targets) or not time:
            help_command: commands.Command = self.bot.get_command("help")
            return await ctx.invoke(help_command, "mod", command_tree_str="mute")

        timedelta = util.time_string_to_timedelta(time)

        muted = ""
        for target in targets:
            self.update_punishments(ctx, target, reason, "times_muted", "mute_reasons")
            await target.timeout(timedelta, reason=reason)
            muted += f"| {target.mention} "

        if len(targets) == 1:
            msg = f"1 member muted for {reason.lower()}"
        else:
            msg = f"{len(targets)} members muted for {reason.lower()}"

        embed = discord.Embed(
            title=msg,
            description=f"{ctx.author.mention} had {msg}:\n{muted}",
            color=self.bot.COLOR,
            timestamp=dt.datetime.now(),
        )
        embed.set_author(
            name=f"{ctx.author.display_name}",
            icon_url=ctx.author.avatar.url,
        )
        embed.set_footer(text="Imagine being losers.")

        return await ctx.send(embed=embed)

    @commands.hybrid_command(
        name="unmute",
        description="Removes the time out from the mentioned users. Can accept multiple users at once.",
    )
    @commands.has_permissions(manage_roles=True)
    async def unmute_member_command(
        self,
        ctx,
        targets: commands.Greedy[discord.Member],
        *,
        reason: t.Optional[str] = "No reason",
    ):
        if not len(targets):
            help_command: commands.Command = self.bot.get_command("help")
            return await ctx.invoke(help_command, "mod", command_tree_str="unmute")

        unmuted = ""
        for target in targets:
            await target.timeout(None)
            unmuted += f"{target.mention} "

        if len(targets) == 1:
            msg = f"1 member unmuted for {reason.lower()}"
        else:
            msg = f"{len(targets)} members unmuted for {reason.lower()}"

        embed = discord.Embed(
            title=msg,
            description=f"{ctx.author.mention} had {msg}:\n{unmuted}",
            color=self.bot.COLOR,
            timestamp=dt.datetime.now(),
        )
        embed.set_author(
            name=f"{ctx.author.display_name}",
            icon_url=ctx.author.avatar.url,
        )
        embed.set_footer(text="No longer losers.")
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="kick", description="Kicks users.")
    @commands.has_permissions(kick_members=True)
    async def kick_members_command(
        self,
        ctx: commands.Context,
        targets: commands.Greedy[discord.Member],
        *,
        reason: t.Optional[str] = "No reason",
    ):
        if not targets:
            help_command: commands.Command = self.bot.get_command("help")
            return await ctx.invoke(help_command, "mod", command_tree_str="kick")

        kicked = ""
        for target in targets:
            self.update_punishments(ctx, target, reason, "times_kicked", "kick_reasons")
            await target.kick(reason=reason)
            kicked += f"{target.mention} "

        if len(targets) == 1:
            msg = f"1 member kicked for {reason.lower()}"
        else:
            msg = f"{len(targets)} members kicked for {reason.lower()}"

        embed = discord.Embed(
            title=msg,
            description=f"{ctx.author.mention} had {msg}:\n{kicked}",
            color=self.bot.COLOR,
            timestamp=dt.datetime.now(),
        )
        embed.set_author(
            name=f"{ctx.author.display_name}", icon_url=ctx.author.avatar.url
        )

        await ctx.send(embed=embed)

    async def warn_member(member: discord.Member, length: str):
        if length.lower() == "forever":
            pass
        else:
            util.time_string_to_timedelta(length)

            
        pass

    @commands.hybrid_command(name="warn", description="Warns users. 'Forever' is a valid value for the 'length' argument.")
    @commands.has_permissions(ban_members=True)
    async def warn_members_command(self, ctx: commands.Context, targets: commands.Greedy[discord.Member], length: t.Optional[str], *, reason: t.Optional[str] = "No reason"):
        if not targets:
            return await ctx.invoke(self.bot.get_command("help"), "mod", command_tree_str="kick")
        
        warned = ""
        for target in targets:
            self.update_punishments(ctx, target, reason, "times_warned", "warn_reasons")
            self.warn_member(target, length)
            warned += f"{target.mention} "
        
        if len(targets) == 1:
            msg = f"1 member warned for {reason.lower()}"
        else:
            msg = f"{len(targets)} members warned for {reason.lower()}"

        embed = discord.Embed(
            title=msg,
            description=f"{ctx.author.mention} had {msg}:\n{warned}",
            color=self.bot.COLOR,
            timestamp=dt.datetime.now(),
        )
        embed.set_author(
            name=f"{ctx.author.display_name}", icon_url=ctx.author.avatar.url
        )

        await ctx.send(embed=embed)

    @commands.hybrid_command(
        name="change_prefix",
        aliases=["prefix"],
        description="Changes the server prefix of the bot",
    )
    @commands.has_permissions(manage_guild=True)
    async def change_guild_prefix(self, ctx: commands.Context, prefix: str):
        if not (result := self.guilds.find_one(ctx.guild.id)):
            return await ctx.send(
                "There was an issue and I could not find your server in my database!"
            )

        self.guilds.update_one(
            {"_id": ctx.guild.id}, {"$set": {"server_prefix": prefix}}
        )
        await ctx.send(
            f"Alright! I changed the server prefix from {result['server_prefix']} to {prefix}!"
        )

    @commands.hybrid_command(
        name="punishments",
        description="Displays the amount of punishments the user has in the server",
    )
    async def show_punishments_command(
        self, ctx: commands.Context, target: t.Optional[discord.User]
    ):
        target = target or ctx.author
        if not (result := self.moderation.find_one(ctx.guild.id)):
            return await ctx.send(
                "There was an issue and I could not find your server in my database!"
            )
        try:
            result = result["moderation"]["punishments"][str(target.id)]
        except KeyError:
            return await ctx.send(
                f"{target.mention} is not in the punishments database. Have they been punished?"
            )

        times_muted: int = result["times_muted"]
        mute_reasons: list[str] = result["mute_reasons"]
        times_warned: int = result["times_warned"]
        warn_reasons: list[str] = result["warn_reasons"]
        times_kicked: int = result["times_kicked"]
        kick_reasons: list[str] = result["kick_reasons"]
        times_banned: int = result["times_banned"]
        ban_reasons: list[str] = result["ban_reasons"]
        total_punishments = times_warned + times_muted + times_kicked + times_banned

        embed = discord.Embed(
            title=f"{target.display_name}'s punishments",
            description=(
                f"{target.display_name} has been punished {total_punishments} time"
                + "s"
                if total_punishments != 1
                else ""
            ),
            color=self.bot.COLOR,
        )

        embed.add_field(
            name=f"{times_warned} Warn" + "s" if times_warned != 1 else "",
            value=f"Most recent warn reasons (5):\n{util.format_elements_with_index(warn_reasons[:5]) or 'No punishments'}",
            inline=True,
        )
        embed.add_field(
            name=f"{times_muted} Mute" + "s" if times_muted != 1 else "",
            value=f"Most recent mute reasons (5):\n{util.format_elements_with_index(mute_reasons[:5]) or 'No punishments'}",
            inline=True,
        )
        embed.add_field(
            name=f"{times_kicked} Kick" + "s" if times_kicked != 1 else "",
            value=f"Most recent kick reasons (5):\n{util.format_elements_with_index(kick_reasons[:5]) or 'No punishments'}",
            inline=True,
        )
        embed.add_field(
            name=f"{times_banned} Ban" + "s" if times_banned != 1 else "",
            value=f"Most recent ban reasons (5):\n{util.format_elements_with_index(ban_reasons[:5]) or 'No punishments'}",
            inline=True,
        )
        embed.set_author(
            name=f"{ctx.author.display_name}'s history", icon_url=ctx.guild.icon.url
        )
        embed.set_footer(
            text=f"Punishment history requested by {ctx.author.display_name}",
            icon_url=ctx.author.avatar.url,
        )
        embed.set_thumbnail(url=target.avatar.url)

        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Mod(bot))
