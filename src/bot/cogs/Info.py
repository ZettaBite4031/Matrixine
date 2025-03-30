import typing as t
import datetime as dt

import discord
from discord.ext import commands


class Info(commands.Cog):
    """Simple info commands for users and servers"""

    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(
        name="user_info",
        aliases=["user", "member"],
        description="Sends information about a target user's discord account",
    )
    async def user_info_command(self, ctx, target: t.Optional[discord.Member]):
        target = target or ctx.author

        activity = None
        for _activity in target.activities:
            if (
                isinstance(_activity, discord.Game)
                or isinstance(_activity, discord.Streaming)
                or isinstance(_activity, discord.Spotify)
                or _activity.type == discord.ActivityType.playing
            ):
                activity = _activity
                break

        embed = discord.Embed(
            title=f"{target.display_name} information",
            timestamp=dt.datetime.now(),
            colour=target.colour,
        )
        embed.set_author(
            name=f"Requested by {ctx.author.display_name}", url=ctx.author.avatar.url
        )
        embed.set_thumbnail(url=target.avatar.url)
        embed.set_footer(text=f"Requested by {ctx.author.display_name}")
        fields = [
            ("ID", target.id, False),
            ("Global name", target.global_name, True),
            ("Username", target.name, True),
            ("Bot?", "Yes" if target.bot else "No", True),
            ("Top Role", target.top_role.mention, True),
            ("Status", str(target.status).title(), True),
            (
                "Playing",
                f"{activity.name if activity else 'Nothing'}\n"
                f"{activity.details if hasattr(activity, 'details') else ''}\n"
                f"{activity.state if hasattr(activity, 'state') else ''}",
                True,
            ),
            ("Created on", target.created_at.strftime("%Y/%m/%d\n%H:%M:%S"), True),
            ("Joined on", target.joined_at.strftime("%Y/%m/%d\n%H:%M:%S"), True),
            ("Boost", bool(target.premium_since), True),
        ]

        for n, v, i in fields:
            embed.add_field(name=n, value=v, inline=i)

        await ctx.reply(embed=embed)

    @commands.hybrid_command(
        name="server_info",
        aliases=["serverinfo", "server"],
        descriptino="Sends the information about the server!",
    )
    async def server_info_command(self, ctx: commands.Context):
        guild: discord.Guild = ctx.guild
        name: str = guild.name
        owner: discord.Member = guild.owner
        total_member_count = guild.member_count
        bot_count = 0
        human_count = 0
        for member in guild.members:
            if member.bot:
                bot_count += 1
            else:
                human_count += 1
        num_boosts = guild.premium_subscription_count
        boost_tier = guild.premium_tier
        creation_date = guild.created_at
        num_text_channels = len(guild.text_channels)
        num_voice_channels = len(guild.voice_channels)
        num_channels = num_text_channels + num_voice_channels
        num_stage_channels = 0
        num_announcement_channels = 0
        categories = 0
        for channel in guild.channels:
            if channel.type == discord.ChannelType.stage_voice:
                num_stage_channels += 1
            elif channel.type == discord.ChannelType.news:
                num_announcement_channels += 1
            elif channel.type == discord.ChannelType.category:
                categories += 1
        animated_emojis = 0
        normal_emojis = 0
        emoji: discord.Emoji
        for emoji in guild.emojis:
            if emoji.animated:
                animated_emojis += 1
            else:
                normal_emojis += 1

        embed = discord.Embed(
            title="**Server Information**",
            color=self.bot.COLOR,
            timestamp=dt.datetime.now(),
        )

        embed.set_author(name=name, icon_url=ctx.author.avatar.url)
        embed.set_thumbnail(url=guild.icon.url)
        embed.set_footer(text=f"Requested by {ctx.author.display_name}")

        fields = [
            ("**Server Name**", f"```{name}```", True),
            ("**Server Owner**", f"```{owner.name}```", True),
            (
                "**Server Creation Date**",
                f"```{creation_date.strftime('%Y-%m-%d %H:%M:%S')}```",
                False,
            ),
            ("**Server ID**", f"```{guild.id}```", True),
            (
                f"**Server Members [{total_member_count}]**",
                f"```Members: {human_count} | Bots: {bot_count}```",
                True,
            ),
            (
                f"**Server Categories and Channels [{num_channels}]**",
                f"```Categories: {categories} | Text: {num_text_channels} | Voice: {num_voice_channels} | "
                f"Announcement: {num_announcement_channels} | Stage: {num_stage_channels}```",
                False,
            ),
            (
                "**Server Emojis**",
                f"```Normal: {normal_emojis} | Animated: {animated_emojis}```",
                False,
            ),
            ("**Server Boost Tier**", f"```{boost_tier}```", True),
            ("**Server Boosts**", f"```{num_boosts}```", True),
        ]

        for name, val, inline in fields:
            embed.add_field(value=val, name=name, inline=inline)

        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Info(bot))
