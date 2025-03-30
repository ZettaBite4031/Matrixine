import typing as t
import datetime as dt
import re
import pytz

import discord
from discord.ext import commands

import util


class Welcomer(commands.Cog):
    """Handles all the member events and message customization"""
    def __init__(self, bot):
        self.bot = bot
        self.database = self.bot.MONGO_DB
        self.guilds = self.database["Guilds"]
        self.leveling = self.database["Leveling"]
        self.moderation = self.database["Moderation"]

    @commands.hybrid_command(
        name="update_guild_info",
        description="For zettabite to update the testing server's DB entry",
    )
    @commands.is_owner()
    async def update_guild_info_command(self, ctx):
        await self.on_guild_join(ctx.guild)

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        result = self.guilds.find_one(guild.id)
        if result:
            self.guilds.delete_one({"_id": guild.id})
        result = self.leveling.find_one(guild.id)
        if result:
            self.leveling.delete_one({"_id": guild.id})
        result = self.moderation.find_one(guild.id)
        if result:
            self.moderation.delete_one({"_id": guild.id})

        data = {
            "join": {
                "welcome_channel": None,
                "welcome_message": None,
                "leave_channel": None,
                "leave_message": None,
                "ban_message": None,
                "auto_roles": [],
            },
            "log": {
                "member_joined_channel": None,
                "member_left_channel": None,
                "deleted_message_channel": None,
                "edited_message_channel": None,
                "role_create_channel": None,
                "role_deleted_channel": None,
                "role_edited_channel": None,
                "member_update_channel": None,
                "channel_create_channel": None,
                "channel_edit_channel": None,
                "channel_delete_channel": None,
                "mod_ban_channel": None,
                "mod_kick_channel": None,
                "mod_mute_channel": None,
                "mod_purge_channel": None,
                "voice_update_channel": None,
                "invite_sent_log_channel": None,
                "new_account_age": 7,
                "ignored_channels": [],
                "ignored_roles": [],
            },
            "member": {
                "leveling_enabled": True,
                "level_up_channel": None,
                "no_level_roles": [],
            },
        }

        self.guilds.insert_one(
            {
                "_id": guild.id,
                "name": guild.name,
                "owner_id": guild.owner_id,
                "server_prefix": self.bot.PREFIX,
                "blacklisted_phrases": [],
                "data": data,
            }
        )

        member = {
            str(guild.owner_id): {
                "xp": 0,
                "level": 0,
                "lock_reason": None,
                "lock_time": dt.datetime.now(pytz.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "times_locked": 0,
            }
        }

        embed = {
            "title": None,
            "desc": None,
            "color": self.bot.COLOR,
            "thumbnail": None,
            "image": None,
            "footnote": None,
            "author": None,
        }

        self.leveling.insert_one(
            {
                "_id": guild.id,
                "name": guild.name,
                "multiplier": 1.0,
                "randomized": False,
                "members": member,
                "embed_settings": embed,
                "no_xp_channels": [],
            }
        )

        moderation = {
            "punishments": {
                str(guild.owner_id): {
                    "times_muted": 0,
                    "mute_reasons": [""],
                    "times_warned": 0,
                    "warn_reasons": [""],
                    "times_kicked": 0,
                    "kick_reasons": [""],
                    "times_banned": 0,
                    "ban_reasons": [""],
                }
            },
        }

        self.moderation.insert_one({"_id": guild.id, "moderation": moderation})



    @commands.Cog.listener()
    async def on_guild_remove(self, guild: discord.Guild):
        if self.guilds.find_one(guild.id):
            self.guilds.delete_one(guild.id)
            self.leveling.delete_one(guild.id)

    @commands.Cog.listener()
    async def on_guild_update(self, before: discord.Guild, after: discord.Guild):
        if self.guilds.find_one(before.id):
            self.guilds.update_one(
                {"_id": before.id},
                {
                    "$set": {
                        "_id": after.id,
                        "name": after.name,
                        "owner_id": after.owner_id,
                    }
                },
            )

    @commands.is_owner()
    @commands.hybrid_command(
        name="update_db",
        aliases=["force_db_update"],
        description="A command for the developer(s) to use to force a guild into the database",
    )
    async def force_update_db(self, ctx):
        await self.on_guild_join(ctx.guild)

    @commands.hybrid_command(
        name="member_join_test",
        aliases=["mjt"],
        description="A command to let the developer(s) test the member join functionality",
    )
    @commands.is_owner()
    async def member_join_test_command(self, ctx):
        await self.on_member_join(ctx.author)

    @commands.hybrid_command(
        name="member_leave_test",
        aliases=["mlt"],
        description="A command to let the developer(s) test the member leave functionality",
    )
    @commands.is_owner()
    async def member_leave_test_command(self, ctx):
        await self.on_member_remove(ctx.author)

    @commands.hybrid_command(
        name="member_ban_test",
        aliases=["mbt"],
        description="A command to let the developer(s) test the member ban functionality",
    )
    @commands.is_owner()
    async def member_ban_test_command(self, ctx):
        await self.on_member_ban(ctx.guild, ctx.author)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        await self.bot.wait_until_ready()
        if not (result := self.guilds.find_one(member.guild.id)):
            return

        if not (welcome_message := str(result["data"]["join"]["welcome_message"])):
            return
        if not (welcome_channel_id := result["data"]["join"]["welcome_channel"]):
            return
        welcome_channel = member.guild.get_channel(int(welcome_channel_id))
        welcome_message = util.personalize_message(
            member, welcome_message, welcome_channel
        )
        await welcome_channel.send(welcome_message) if welcome_channel else None
        if not (autoroles := result["data"]["join"]["auto_roles"]):
            return
        await member.edit(roles=[member.guild.get_role(int(id_)) for id_ in autoroles])

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        if member.bot:
            return
        if not (result := self.guilds.find_one(member.guild.id)):
            return
        if not (leave_channel_id := result["data"]["join"]["leave_channel"]):
            return
        if not (leave_message := result["data"]["join"]["leave_message"]):
            return
        leave_channel = member.guild.get_channel(int(leave_channel_id))
        leave_message = util.personalize_message(member, leave_message, leave_channel)
        await leave_channel.send(leave_message) if leave_channel else None

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        pass  # TODO: IMPLEMENT UPDATE LOGGING IN Logging.py

    @commands.Cog.listener()
    async def on_member_ban(self, guild: discord.Guild, member: discord.Member):
        if not (result := self.guilds.find_one(guild.id)):
            return
        if not (leave_channel_id := result["data"]["join"]["leave_channel"]):
            return
        if not (ban_message := result["data"]["join"]["ban_message"]):
            return
        leave_channel = member.guild.get_channel(int(leave_channel_id))
        ban_message = util.personalize_message(member, ban_message, leave_channel)
        await leave_channel.send(ban_message)

    @commands.Cog.listener()
    async def on_member_unban(self, guild: discord.Guild, member: discord.Member):
        pass  # TODO: IMPLEMENT UNBAN LOGGING IN Logging.py

    @commands.hybrid_command(
        name="set_welcome_channel",
        aliases=["welcome_channel"],
        description="Sets welcome channel. Defaults to the one you're in if no channel provided",
    )
    @commands.has_permissions(manage_guild=True)
    async def set_welcome_channel_command(
        self, ctx: commands.Context, channel: t.Optional[discord.TextChannel]
    ):
        if not (results := self.guilds.find_one(ctx.guild.id)):
            return
        if not channel:
            current_channel_id = results["data"]["join"]["welcome_channel"]
            current_channel = (
                self.bot.get_channel(int(current_channel_id)).mention
                if current_channel_id
                else "No channel"
            )
            return await ctx.send(f"Current welcome channel: {current_channel}")

        old_channel_id = results["data"]["join"]["welcome_channel"]
        self.guilds.update_one(
            {"_id": ctx.guild.id},
            {"$set": {"data.join.welcome_channel": str(channel.id)}},
        )
        old_channel = (
            self.bot.get_channel(int(old_channel_id)).mention
            if old_channel_id
            else "no channel"
        )
        await ctx.send(f"Changed the welcome channel from {old_channel} to {channel}")

    @commands.hybrid_command(
        name="set_welcome_message",
        aliases=["welcome_message"],
        description="Sets the member join message.",
    )
    @commands.has_permissions(manage_guild=True)
    async def set_welcome_message_command(
        self, ctx: commands.Context, *, message: t.Optional[str]
    ):
        if not (results := self.guilds.find_one(ctx.guild.id)):
            return
        if not message:
            current_message = results["data"]["join"]["welcome_message"]
            return await ctx.send(f"Current welcome message:\n`{current_message}`")

        old_message = results["data"]["join"]["welcome_message"]
        self.guilds.update_one(
            {"_id": ctx.guild.id}, {"$set": {"data.join.welcome_message": message}}
        )
        await ctx.send(
            f"Changed the welcome message from `{old_message}` to `{message}`"
        )

    @commands.hybrid_command(
        name="set_leave_channel",
        aliases=["leave_channel"],
        description="Sets welcome channel. Defaults to the one you're in if no channel provided",
    )
    @commands.has_permissions(manage_guild=True)
    async def set_leave_channel_command(
        self, ctx: commands.Context, channel: t.Optional[discord.TextChannel]
    ):
        if not (results := self.guilds.find_one(ctx.guild.id)):
            return
        if not channel:
            current_channel_id = results["data"]["join"]["leave_channel"]
            current_channel = (
                self.bot.get_channel(int(current_channel_id)).mention
                if current_channel_id
                else "No channel"
            )
            return await ctx.send(f"Current leave channel: {current_channel}")

        old_channel_id = results["data"]["join"]["leave_channel"]
        self.guilds.update_one(
            {"_id": ctx.guild.id},
            {"$set": {"data.join.leave_channel": str(channel.id)}},
        )
        old_channel = (
            self.bot.get_channel(int(old_channel_id)).mention
            if old_channel_id
            else "no channel"
        )
        await ctx.send(f"Changed the leave channel from {old_channel} to {channel}")

    @commands.hybrid_command(
        name="set_leave_message",
        aliases=["leave_message"],
        description="Sets the member leave message",
    )
    @commands.has_permissions(manage_guild=True)
    async def set_leave_message_command(
        self, ctx: commands.Context, *, message: t.Optional[str]
    ):
        if not (results := self.guilds.find_one(ctx.guild.id)):
            return
        if not message:
            current_message = results["data"]["join"]["leave_message"]
            return await ctx.send(f"Current leave message:\n`{current_message}`")

        old_message = results["data"]["join"]["leave_message"]
        self.guilds.update_one(
            {"_id": ctx.guild.id}, {"$set": {"data.join.leave_message": message}}
        )
        await ctx.send(
            f"Changed the leave message from `{old_message}`\nv\n`{message}`"
        )

    @commands.hybrid_command(
        name="autoroles",
        description="Sets on-join autoroles. WILL ONLY WORK IF YOU PING THE ROLE",
    )
    @commands.has_permissions(manage_guild=True)
    async def set_autoroles_command(
        self, ctx: commands.Context, action: str = "none", *, roles: str = ""
    ):
        if not (results := self.guilds.find_one(ctx.guild.id)):
            return

        autoroles = results["data"]["join"]["auto_roles"]
        if action.lower() in ("show", "display", "none"):
            if not autoroles:
                return await ctx.send("This server has no autoroles!")
            role_list = [ctx.guild.get_role(int(id)) for id in autoroles]
            autorole_string = "\n".join(
                role.mention if role else "UNKNOWN" for role in role_list
            )
            return await ctx.send(
                f"This server has {len(autoroles)} autorole(s):\n{autorole_string}"
            )
        elif action.lower() in ("remove", "rem", "del", "delete"):
            if not autoroles:
                return await ctx.send("This server has no autoroles!")
            removed_count = 0
            if not (role_ids := re.findall(r"<@&(\d+)>", roles)):
                return await ctx.send("Please supply at least one role to remove!")
            for id in role_ids:
                if id in autoroles:
                    autoroles.remove(id)
                    removed_count += 1
            self.guilds.update_one(
                {"_id": ctx.guild.id}, {"$set": {"data.join.auto_roles": autoroles}}
            )
            return await ctx.send(f"Removed {removed_count} role(s)")
        elif action.lower() == "add":
            if not (role_ids := re.findall(r"<@&(\d+)>", roles)):
                return await ctx.send("Please supply at least 1 role")
            self.guilds.update_one(
                {"_id": ctx.guild.id}, {"$set": {"data.join.auto_roles": role_ids}}
            )
        else:
            await ctx.send(
                "That's not a valid option. Make sure to check `M!help Welcomer autoroles`"
            )


async def setup(bot):
    await bot.add_cog(Welcomer(bot))
