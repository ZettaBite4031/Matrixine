import datetime as dt
import random as r
import math
import typing as t
import pytz

from discord.ext import commands
import discord

import util


class Leveling(commands.Cog):
    """Leveling commands and handles events"""

    def __init__(self, bot):
        self.bot = bot
        self.database = self.bot.MONGO_DB
        self.leveling = self.database["Leveling"]
        self.guilds = self.database["Guilds"]

    async def level_up_msg(self, msg: discord.Message, old_level, new_level):
        if not (
            embed_settings := self.leveling.find_one(msg.guild.id)["embed_settings"]
        ):
            return
        if not embed_settings["title"] and not embed_settings["desc"]:
            return

        if not (
            level_up_channel_id := self.guilds.find_one(msg.guild.id)["data"]["member"][
                "level_up_channel"
            ]
        ):
            return

        level_up_channel = self.bot.get_channel(int(level_up_channel_id))

        for key in embed_settings.keys():
            if key == "color":
                continue
            embed_settings[key] = util.personalize_message(
                msg.author,
                embed_settings[key] or "",
                level_up_channel,
                old_level,
                new_level,
            )

        embed = discord.Embed(
            title=embed_settings["title"],
            description=embed_settings["desc"],
            timestamp=dt.datetime.now(),
            color=embed_settings["color"],
        )

        if thumbnail := embed_settings["thumbnail"]:
            embed.set_thumbnail(url=thumbnail)
        if image := embed_settings["image"]:
            embed.set_image(url=image)
        if footer := embed_settings["footnote"]:
            embed.set_footer(text=footer)
        if author := embed_settings["author"]:
            embed.set_author(name=author)

        if level_up_channel:
            await level_up_channel.send(embed=embed)
        else:
            ctx = await self.bot.get_context(message=msg)
            await ctx.send(embed=embed)

    async def process_xp(self, msg: discord.Message):
        user = msg.author
        guild = msg.guild
        if not (result := self.leveling.find_one(guild.id)):
            return
        if not self.guilds.find_one(guild.id)["data"]["member"]["leveling_enabled"]:
            return

        members = result["members"]
        try:
            member = members[str(user.id)]
        except KeyError:
            members[str(user.id)] = {
                "xp": 0,
                "level": 0,
                "lock_reason": None,
                "lock_time": dt.datetime.now(pytz.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "times_locked": 0,
            }
            self.leveling.update_one({"_id": guild.id}, {"$set": {"members": members}})
            member = members[str(user.id)]

        lock_time = dt.datetime.strptime(member["lock_time"], "%Y-%m-%dT%H:%M:%SZ")
        lock_time = lock_time.replace(tzinfo=dt.timezone.utc)

        if lock_time < dt.datetime.now(dt.timezone.utc):
            await self.add_xp(msg, result)

        elif lock_time < dt.datetime.now(pytz.utc):
            lock_reason = member["lock_reason"]
            lock_reason = f"NO LONGER LOCKED | {lock_reason}"
            self.leveling.update_one(
                {"_id": guild.id},
                {"$set": {f"member.{user.id}.lock_reason": lock_reason}},
            )

    async def add_xp(self, msg, result):
        xp_to_add = result["multiplier"] * (
            float(r.randint(1, 10)) if result["randomized"] else 5.0
        )

        member = result["members"][str(msg.author.id)]

        xp = member["xp"] + xp_to_add
        current_level = member["level"]

        self.leveling.update_one(
            {"_id": msg.guild.id}, {"$set": {f"members.{str(msg.author.id)}.xp": xp}}
        )

        if (new_level := math.floor(int(xp // 42) ** 0.55)) > current_level:
            self.leveling.update_one(
                {"_id": msg.guild.id},
                {"$set": {f"members.{str(msg.author.id)}.level": new_level}},
            )
            await self.level_up_msg(msg, current_level, new_level)

    @commands.Cog.listener()
    async def on_message(self, msg):
        if msg.author.bot:
            return
        await self.process_xp(msg)

    @commands.hybrid_command(
        name="set_level_up_embed_title",
        aliases=["SetLevelUpEmbedTitle", "SLUE_Title", "SLUETt"],
        description="Sets the level up embed title",
    )
    @commands.has_permissions(manage_guild=True)
    async def set_level_up_embed_title(self, ctx, *, title: t.Optional[str]):
        if not (result := self.guilds.find_one(ctx.guild.id)):
            return
        if not result["data"]["member"]["leveling_enabled"]:
            return await ctx.send(
                "Leveling is not enabstr(target.id)led on this server"
            )

        if not title:
            if not (
                level_title := self.leveling.find_one(ctx.guild.id)["embed_settings"][
                    "title"
                ]
            ):
                return await ctx.send(
                    "There is no level up embed title for this server"
                )
            return await ctx.send(
                f"The current level up embed title is:\n`{level_title}`"
            )

        self.leveling.update_one(
            {"_id": ctx.guild.id}, {"$set": {"embed_settings.title": title}}
        )
        await ctx.send(f"The new level up embed title has been set to:\n`{title}`")

    @commands.hybrid_command(
        name="set_level_up_embed_description",
        aliases=["SetLevelUpEmbedDescription", "SLUE_Description", "SLUED"],
        description="Sets the level up embed description",
    )
    @commands.has_permissions(manage_guild=True)
    async def set_level_up_embed_description(self, ctx, *, desc: t.Optional[str]):
        if not (result := self.guilds.find_one(ctx.guild.id)):
            return
        if not result["data"]["member"]["leveling_enabled"]:
            return await ctx.send("Leveling is not enabled on this server!")

        if not desc:
            if not (
                level_desc := self.leveling.find_one(ctx.guild.id)["embed_settings"][
                    "desc"
                ]
            ):
                return await ctx.send(
                    "There is no level up embed description for this server"
                )
            return await ctx.send(
                f"The current level up embed description is:\n`{level_desc}`"
            )

        self.leveling.update_one(
            {"_id": ctx.guild.id}, {"$set": {"embed_settings.desc": desc}}
        )
        await ctx.send(f"The new level up embed description has been set to:\n`{desc}`")

    @commands.hybrid_command(
        name="set_level_up_embed_color",
        aliases=["SetLevelUpEmbedColor", "SLUE_Color", "SLUEC"],
        description="Sets the color of the level up embed. ACCEPTS ONLY HEX (ex. 0x1EACC4 or 1EACC4",
    )
    @commands.has_permissions(manage_guild=True)
    async def set_level_up_embed_color(self, ctx, color: t.Optional[str]):
        if not (result := self.guilds.find_one(ctx.guild.id)):
            return
        if not result["data"]["member"]["leveling_enabled"]:
            return await ctx.send("Leveling is not enabled on this server")

        if not color:
            if not (
                level_color := self.leveling.find_one(ctx.guild.id)["embed_settings"][
                    "color"
                ]
            ):
                return await ctx.send(
                    "There is no level up embed color for this server"
                )
            return await ctx.send(
                f"The current level up embed color is `{level_color}`"
            )

        self.leveling.update_one(
            {"_id": ctx.guild.id},
            {"$set": {"embed_settings.color": hex(int(color.strip("0x"), 16))}},
        )
        await ctx.send(f"The new level up embed color has been set to 0x`{color}`")

    @commands.hybrid_command(
        name="set_level_up_embed_thumbnail",
        aliases=["SetLevelUpEmbedThumbnail", "SLUE_Thumbnail", "SLUETh"],
    )
    @commands.has_permissions(manage_guild=True)
    async def set_level_up_embed_thumbnail(
        self, ctx, *, thumbnail_url: t.Optional[str]
    ):
        if not (result := self.guilds.find_one(ctx.guild.id)):
            return
        if not result["data"]["member"]["leveling_enabled"]:
            return await ctx.send("Leveling is not enabled on this server")

        if not thumbnail_url:
            if not (
                level_thumbnail := self.leveling.find_one(ctx.guild.id)[
                    "embed_settings"
                ]["thumbnail"]
            ):
                return await ctx.send("There is not level up thumbnail for this server")
            if thumbnail_file := await util.url_to_discord_file(
                level_thumbnail, f"{ctx.guild.name}_LUE_thumbnail.png"
            ):
                return await ctx.send(
                    f"The current level up thumbnail is:", file=thumbnail_file
                )
            return await ctx.send(
                f"The current level up thumbnail is <{level_thumbnail}>"
            )

        self.leveling.update_one(
            {"_id": ctx.guild.id}, {"$set": {"embed_settings.thumbnail": thumbnail_url}}
        )
        if thumbnail_file := await util.url_to_discord_file(
            thumbnail_url, f"{ctx.guild.name}_LUE_thumbnail.png"
        ):
            return await ctx.send(
                f"Updated the level up thumbnail to:", file=thumbnail_file
            )
        await ctx.send(f"Updated the level up thumbnail to <{thumbnail_url}>")

    @commands.hybrid_command(
        name="set_level_up_embed_image",
        aliases=["SetLevelUpEmbedImage", "SLUE_Image", "SLUEI"],
    )
    @commands.has_permissions(manage_guild=True)
    async def set_level_up_embed_image(self, ctx, *, image_url: t.Optional[str]):
        if not (result := self.guilds.find_one(ctx.guild.id)):
            return
        if not result["data"]["member"]["leveling_enabled"]:
            return await ctx.send("Leveling is not enabled on this server")

        if not image_url:
            if not (
                level_image := self.leveling.find_one(ctx.guild.id)["embed_settings"][
                    "image"
                ]
            ):
                return await ctx.send("There is not level up image for this server")
            if image_file := await util.url_to_discord_file(
                level_image, f"{ctx.guild.name}_LUE_image.png"
            ):
                return await ctx.send(
                    f"The current level up image is:", file=image_file
                )
            return await ctx.send(f"The current level up image is <{level_image}>")

        self.leveling.update_one(
            {"_id": ctx.guild.id}, {"$set": {"embed_settings.thumbnail": image_url}}
        )
        if image_file := await util.url_to_discord_file(
            image_url, f"{ctx.guild.name}_LUE_image.png"
        ):
            return await ctx.send(f"Updated the level up image to:", file=image_file)
        await ctx.send(f"Updated the level up image to <{image_url}>")

    @commands.hybrid_command(
        name="set_level_up_embed_footer",
        aliases=["SetLevelUpEmbedFooter", "SLUE_Footer", "SLUEF"],
    )
    @commands.has_permissions(manage_guild=True)
    async def set_level_up_embed_footer(self, ctx, *, footer: t.Optional[str]):
        if not (result := self.guilds.find_one(ctx.guild.id)):
            return
        if not result["data"]["member"]["leveling_enabled"]:
            return await ctx.send("Leveling is not enabled on this server!")

        if not footer:
            if not (
                level_footer := self.leveling.find_one(ctx.guild.id)["embed_settings"][
                    "footer"
                ]
            ):
                return await ctx.send(
                    "There is no level up embed footer for this server"
                )
            return await ctx.send(
                f"The current level up embed footer is:\n`{level_footer}`"
            )

        self.leveling.update_one(
            {"_id": ctx.guild.id}, {"$set": {"embed_settings.footer": footer}}
        )
        await ctx.send(f"The new level up embed footer has been set to:\n`{footer}`")

    @commands.hybrid_command(
        name="set_level_up_embed_author",
        aliases=["SetLevelUpEmbedAuthor", "SLUE_Author", "SLUEA"],
    )
    @commands.has_permissions(manage_guild=True)
    async def set_level_up_embed_author(self, ctx, *, author: t.Optional[str]):
        if not (result := self.guilds.find_one(ctx.guild.id)):
            return
        if not result["data"]["member"]["leveling_enabled"]:
            return await ctx.send("Leveling is not enabled on this server!")

        if not author:
            if not (
                level_author := self.leveling.find_one(ctx.guild.id)["embed_settings"][
                    "author"
                ]
            ):
                return await ctx.send(
                    "There is no level up embed author for this server"
                )
            return await ctx.send(
                f"The current level up embed author is:\n`{level_author}`"
            )

        self.leveling.update_one(
            {"_id": ctx.guild.id}, {"$set": {"embed_settings.author": author}}
        )
        await ctx.send(f"The new level up embed author has been set to:\n`{author}`")

    @commands.hybrid_command(
        name="level_embed_info",
        aliases=["level_embed_help", "LevelEmbedInfo", "LevelEmbedHelp"],
        description="Displays information about the level up embed customization",
    )
    @commands.has_permissions(manage_guild=True)
    async def level_embed_help_info(self, ctx):
        fields = [
            (
                "{user}",
                "Mentions a user. Will not work in the author, title, or footer fields.",
                True,
            ),
            (
                "{nickname}",
                "Displays the user's in-server nickname. Works in all fields.",
                True,
            ),
            ("{username}", "Displays the user's username. Works in all fields.", True),
            (
                "{avatar}",
                "Shows the user's avatar url. Will not be embedded in text fields.",
                True,
            ),
            ("{server}", "Displays the server name. Works in all fields.", True),
            (
                "{level}",
                "Replaced with the user's new level when leveled up. Works in all fields",
                True,
            ),
            (
                "{old_level}",
                "Replaced with the user's old level after leveling up. Works in all fields",
                True,
            ),
            (
                "{@role}",
                "Mentions a role. Works with role name and id. Does not ping role in embeds."
                "Will not work in the author, title, or footer fields",
                True,
            ),
            (
                "{#channel}",
                "Mentions a channel. Works with channel name and id."
                "Will not work in the author, title, or footer fields",
                True,
            ),
            (
                "{everyone}",
                "Mentions everyone. Does not work in the author, title, or footer fields",
                True,
            ),
            (
                "{here}",
                "Mentions here. Does not work in the author, title, or footer fields",
                True,
            ),
            (
                "",
                "",
                True,
            ),  # Empty field makes 9 and will make them line up in the embed
        ]

        embed = discord.Embed(
            title="Level Up Embed Customization Information",
            color=self.bot.COLOR,
            timestamp=dt.datetime.now(),
        )
        for n, v, i in fields:
            embed.add_field(name=n, value=v, inline=i)
        embed.set_author(name=ctx.author.display_name)
        embed.set_footer(text="If there are any questions, ask the dev!")

        await ctx.send(embed=embed)

    @commands.hybrid_command(
        name="set_level_multiplier",
        aliases=["SetLevelMultiplier", "SLM"],
        description="How much XP should users gain from speaking. 0.5 -> Half XP. 1 -> Default. 2 -> Double",
    )
    @commands.has_permissions(manage_guild=True)
    async def set_level_multiplier_command(self, ctx, multiplier: t.Optional[float]):
        if not (result := self.leveling.find_one(ctx.guild.id)):
            return
        if not self.guilds.find_one(ctx.guild.id)["data"]["member"]["leveling_enabled"]:
            return await ctx.send("This server does not have leveling enabled")
        if not multiplier:
            multiplier = self.leveling.find_one(ctx.guild.id)["multiplier"]
            return await ctx.send(f"The server's XP multiplier is {multiplier}")
        if multiplier < 0:
            return await ctx.send(
                "Please supply a positive number. Negative multiplier would take away XP"
            )
        if multiplier == 0:
            return await ctx.send(
                "Please supply a non-zero number. If you don't want users to gain XP, disable leveling"
            )

        self.leveling.update_one(
            {"_id": ctx.guild.id}, {"$set": {"multiplier": multiplier}}
        )
        await ctx.send(f"Alright, the XP multiplier is set to {multiplier}")

    @commands.hybrid_command(name="enable_leveling", aliases=["EnableLeveling"])
    @commands.has_permissions(manage_guild=True)
    async def enable_leveling_command(self, ctx):
        if not (result := self.leveling.find_one(ctx.guild.id)):
            return
        if self.guilds.find_one(ctx.guild.id)["data"]["member"]["leveling_enabled"]:
            return await ctx.send("This server already has leveling enabled")

        self.guilds.update_one(
            {"_id": ctx.guild.id}, {"data.member.leveling_enabled", True}
        )
        await ctx.send("Alright, leveling has been enabled")

    @commands.hybrid_command(name="disable_leveling", aliases=["DisableLeveling"])
    @commands.has_permissions(manage_guild=True)
    async def disable_leveling_command(self, ctx):
        if not (result := self.leveling.find_one(ctx.guild.id)):
            return
        if not self.guilds.find_one(ctx.guild.id)["data"]["member"]["leveling_enabled"]:
            return await ctx.send("This server does not have leveling enabled")

        self.guilds.update_one(
            {"_id": ctx.guild.id}, {"data.member.leveling_enabled", False}
        )
        await ctx.send("Alright, leveling has been disabled")

    @commands.hybrid_command(name="enable_xp_randomizer", aliases=["EnableXPRandomizer"])
    @commands.has_permissions(manage_guild=True)
    async def enable_leveling_command(self, ctx):
        if not (result := self.leveling.find_one(ctx.guild.id)):
            return
        if not self.guilds.find_one(ctx.guild.id)["data"]["member"]["leveling_enabled"]:
            return await ctx.send("This server does not have leveling enabled")
        if self.leveling.find_one(ctx.guild.id)["randomized"]:
            return await ctx.send("This server already has random XP gain")

        self.leveling.update_one({"_id": ctx.guild.id}, {"randomized", True})
        await ctx.send("Alright, random XP gain has been enabled")

    @commands.hybrid_command(name="disable_xp_randomizer", aliases=["DisableXPRandomizer"])
    @commands.has_permissions(manage_guild=True)
    async def disable_leveling_command(self, ctx):
        if not (result := self.leveling.find_one(ctx.guild.id)):
            return
        if not self.guilds.find_one(ctx.guild.id)["data"]["member"]["leveling_enabled"]:
            return await ctx.send("This server does not have leveling enabled")
        if not self.leveling.find_one(ctx.guild.id)["randomized"]:
            return await ctx.send("This server does not have random XP gain")

        self.leveling.update_one({"_id": ctx.guild.id}, {"randomized", False})
        await ctx.send("Alright, random XP gain has been disabled")

    @commands.hybrid_command(name="level", description="Displays a user's level")
    async def level_command(self, ctx, target: t.Optional[discord.Member]):
        if not (result := self.leveling.find_one(ctx.guild.id)):
            return
        if not self.guilds.find_one(ctx.guild.id)["data"]["member"]["leveling_enabled"]:
            return await ctx.send("This server does not have leveling enabled")

        target = target or ctx.author
        if not (
            member := self.leveling.find_one(ctx.guild.id)["members"][str(target.id)]
        ):
            return await ctx.send("It seems that user isn't logged yet")

        xp = member["xp"]
        lvl = member["level"]
        lock_time = dt.datetime.strptime(member["lock_time"], "%Y-%m-%dT%H:%M:%SZ")
        lock_time = lock_time.replace(tzinfo=dt.timezone.utc)

        offset_aware_dtnow = dt.datetime.now(dt.timezone.utc)
        if lock_time > offset_aware_dtnow:
            current_date = dt.datetime.now(dt.timezone.utc)
            time_until = lock_time - current_date
            locked = f"User is xp locked until {time_until}"
        else:
            locked = f"{target.mention} is not xp locked"

        embed = discord.Embed(
            title=f"{target.display_name}'s level",
            description=f"XP: {xp}\nLevel: {lvl}\n{locked}",
            color=self.bot.COLOR,
            timestamp=dt.datetime.now(),
        )

        embed.set_footer(text=f"Leveling system developed by {self.bot.OWNER_UN}")
        embed.set_author(name=ctx.author.display_name)
        await ctx.send(embed=embed)

    @commands.hybrid_command(
        name="xp_lock", description="Lets moderators prevent users from gaining xp"
    )
    @commands.has_permissions(manage_roles=True)
    async def lock_xp_command(
        self,
        ctx,
        target: discord.Member,
        duration: t.Optional[str],
        *,
        reason: str = "No reason",
    ):
        if target == ctx.author:
            return await ctx.send("You can't XP Lock yourself")

        if not duration:
            if not (result := self.guilds.find_one(ctx.guild.id)):
                return
            if not result["data"]["member"]["leveling_enabled"]:
                return await ctx.send("Leveling is not enabled on this server")
            if target.bot:
                return await ctx.send("Bots aren't logged in the database")
            if (
                str(target.id)
                not in (
                    members := self.leveling.find_one(ctx.guild.id)["members"]
                ).keys()
            ):
                return await ctx.send(f"{target.mention} isn't in the database")

            member = members[str(target.id)]
            lock_time = dt.datetime.strptime(
                member["lock_time"], "%Y-%m-%dT%H:%M:%SZ"
            ).replace(tzinfo=dt.timezone.utc)
            if lock_time < dt.datetime.now(dt.timezone.utc):
                return await ctx.send(f"{target.mention} isn't xp locked")
            lock_delta = lock_time - dt.datetime.now(dt.timezone.utc)

            return await ctx.send(
                f"{target.mention} is xp locked "
                f"and still has {util.timedelta_to_string(lock_delta)} to go"
            )

        # command caller specified a duration
        unlock_datetime = util.time_string_to_datetime(duration)
        unlock_db_time = unlock_datetime.strftime("%Y-%m-%dT%H:%M:%SZ")
        self.leveling.update_one(
            {"_id": ctx.guild.id},
            {"$set": {f"members.{str(target.id)}.lock_time": unlock_db_time}},
        )
        times_locked = self.leveling.find_one(ctx.guild.id)["members"][str(target.id)][
            "times_locked"
        ]
        times_locked += 1
        self.leveling.update_one(
            {"_id": ctx.guild.id},
            {"$set": {f"members.{str(target.id)}.times_locked": times_locked}},
        )
        self.leveling.update_one(
            {"_id": ctx.guild.id},
            {"$set": {f"members.{str(target.id)}.lock_reason": reason}},
        )

        await ctx.send(
            f"Alright, {target.mention} has been xp locked until "
            f"{unlock_datetime.strftime('%Y-%m-%d at %H:%M:%S')}"
        )

    @commands.hybrid_command(name="xp_unlock")
    @commands.has_permissions(manage_roles=True)
    async def xp_unlock_command(self, ctx, target: discord.Member):
        if not (result := self.guilds.find_one(ctx.guild.id)):
            return
        if not result["data"]["member"]["leveling_enabled"]:
            return await ctx.send("Leveling is not enabled on this server")
        if target.bot:
            return await ctx.send("Bots aren't logged in the database")
        if (t_id := str(target.id)) not in (
            members := self.leveling.find_one(ctx.guild.id)["members"]
        ).keys():
            return await ctx.send(f"{target.mention} isn't in the database")
        lock_time_offset_naive = dt.datetime.strptime(
            members[t_id]["lock_time"], "%Y-%m-%dT%H:%M:%SZ"
        )
        lock_time_offset_aware = lock_time_offset_naive.replace(tzinfo=pytz.utc)
        if dt.datetime.now(pytz.utc) > lock_time_offset_aware:
            return await ctx.send(f"{target.mention} is not xp locked!")

        format_now = dt.datetime.now(pytz.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        self.leveling.update_one(
            {"_id": ctx.guild.id}, {"$set": {f"members.{t_id}.lock_time": format_now}}
        )

        await ctx.send(f"Alright, {target.mention} is no longer xp locked")


async def setup(bot):
    await bot.add_cog(Leveling(bot))
