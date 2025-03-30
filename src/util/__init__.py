import os
import typing as t
import datetime as dt
import random as r
import math
import re
from io import BytesIO

import aiohttp
import discord
from discord.ext import commands
from discord.utils import get

TIME_REGEX = r"((?P<weeks>\d+)w)?((?P<days>\d+)d)?((?P<hours>\d+)h)?((?P<minutes>\d+)m)?((?P<seconds>\d+)s)?"
DATETIME_FORMAT_STRING = "%Y-%m-%dT%H:%M:%SZ"


async def url_to_discord_file(url, file_name="image.txt"):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            image = await resp.read()
            return discord.File(BytesIO(image), filename=file_name)


def personalize_message(
    member: discord.Member, message, channel, old_level=0, new_level=0
) -> str:
    # Handle simple replacements
    replacement_mapping = {
        "{user}": member.mention,
        "{nickname}": member.nick or member.global_name,
        "{username}": member.name,
        "{avatar}": member.avatar.url,
        "{server}": member.guild.name,
        "{channel}": channel,
        "{level}": new_level,
        "{old_level}": old_level,
        "{everyone}": "@everyone",
        "{here}": "@here",
    }

    for template, value in replacement_mapping.items():
        message = message.replace(f"{template}", f"{value}")

    # Handle custom channel placeholders
    channel_placeholders = re.findall(r"{#(.*?)}", message)
    for channel_mention in channel_placeholders:
        custom_channel = None
        if channel_mention.isdigit():
            # Channel was passed by ID
            custom_channel = member.guild.get_channel(int(channel_mention))
        else:
            # Channel was passed by name
            custom_channel = discord.utils.get(
                member.guild.channels, name=channel_mention
            )
        if custom_channel:
            message = message.replace(f"{{#{channel_mention}}}", custom_channel.mention)

    # Handle custom role placeholders
    role_placeholders = re.findall(r"{@(.*?)}", message)
    for role_mention in role_placeholders:
        role = None
        if role_mention.isdigit():
            # Role was passed by ID
            role = member.guild.get_role(int(role_mention))
        else:
            # Role was passed by name
            role = discord.utils.get(member.guild.roles, name=role_mention)
        if role:
            message = message.replace(f"{{@{role_mention}}}", role.mention)

    return message


def time_string_to_timedelta(time_string):
    time_dict = re.match(TIME_REGEX, time_string).groupdict()
    return dt.timedelta(
        weeks=int(time_dict.get("weeks") or 0),
        days=int(time_dict.get("days") or 0),
        hours=int(time_dict.get("hours") or 0),
        minutes=int(time_dict.get("minutes") or 0),
        seconds=int(time_dict.get("seconds") or 0),
    )


def time_string_to_seconds(time_string):
    return time_string_to_timedelta(time_string).total_seconds()


def time_string_formatted_string(time_string):
    """
    Turns a time string into a datetime formatted string
    1d12h -> 1 day 12 hours in the future.
    Parameters
    -----------
    time_string: str
        Converts the string to the designated time in the future.
    """
    return timedelta_to_datetime(time_string_to_timedelta(time_string)).strftime(
        DATETIME_FORMAT_STRING
    )


def time_string_to_datetime(time_string):
    """
    Turns a time string into a datetime
    1d12h -> 1 day 12 hours in the future.
    Parameters
    -----------
    time_string: str
        Converts the string to the designated date-time in the future.
    """
    return timedelta_to_datetime(time_string_to_timedelta(time_string))


def timedelta_to_string(timedelta):
    duration_string = ""
    if timedelta.days > 1:
        if (weeks := timedelta.days // 7) >= 1:
            duration_string += f"{weeks} weeks "
        if days := timedelta.days % 7:
            duration_string += f"{days} days "
    hours, remainder = divmod(timedelta.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours >= 1:
        duration_string += f"{hours} hours "
    if minutes >= 1:
        duration_string += f"{minutes} minutes"
    if seconds >= 1:
        duration_string += f"{seconds} seconds"
    return duration_string


def timedelta_to_datetime(timedelta):
    """
    Returns a datetime object in the future by timedelta.

    Args:
        timedelta (datetime.timedelta): The input time delta.

    Returns:
        datetime (datetime.datetime): The date in the future.
    """
    return dt.datetime.now() + timedelta


def ordinal_suffix(n):
    """
    Returns the ordinal suffix for a given number.

    Args:
        n (int): The input number.

    Returns:
        str: The ordinal suffix for the number.
    """
    # Special cases for 11, 12, 13
    if 11 <= (n % 100) <= 13:
        suffix = "th"
    else:
        # Determine suffix based on the last digit
        last_digit = n % 10
        if last_digit == 1:
            suffix = "st"
        elif last_digit == 2:
            suffix = "nd"
        elif last_digit == 3:
            suffix = "rd"
        else:
            suffix = "th"

    return f"{n}{suffix}"


def format_elements_with_index(elems: list[str], padding: str = "\n") -> str | None:
    if len(elems) < 2: 
        return None
    
    res = []
    for i, e in enumerate(elems):
        res.append(f"{i + 1}: {e}")
    return padding.join(res)


PERMISSION_DICT = {
    "Read Messages": "Allows members to view channels by default (excluding private channels).",
    "Manage Channels": "Allows members to create, edit, or delete channels.",
    "Manage Roles": "Allows members to create new roles and edit/delete roles lower than their highest. "
    "Also allows members to change permissions of channels they have access to.",
    "Create Expressions": "Allows members to add custom emojis, stickers, and sounds in this server.",
    "Manage Expressions": "Allows members to edit/remove custom emojis, stickers, and sounds in this server.",
    "View Audit Log": "Allows members to view a record of who made which changes in this server.",
    "Manage Webhooks": "Allows members to create, edit, or delete webhooks, "
    "which can post messages from other apps or sites into this server.",
    "Manage Guild": "Allows members to change the server's name, voice region, view all invites, "
    "add apps (bots) to this server and create/update AutoMod rules.",
    "Create Instant Invite": "Allows members to invite new people to this server.",
    "Change Nickname": "Allows members to change their own nickname, a custom name just for this server.",
    "Manage Nickname": "Allows members to change the nicknames of other members.",
    "Kick Members": "Allows members to remove other members from this server. "
    "Kicked members will be able to rejoin if they have another invite.",
    "Ban Members": "Allows members to permanently ban and delete the message history of other members from this server.",
    "Moderate Members": "Allows members to timeout users. Timed out users will not be able to send messages in chat, "
    "reply within threads, react to messages, or speak in voice channels.",
    "Send Messages": "Allows members to send messages in text channels.",
    "Send Messages In Threads": "Allows members to send messages in threads.",
    "Create Public Threads": "Allows members to create threads that everyone in a channel can view.",
    "Create Private Threads": "Allows members to create invite-only threads.",
    "Embed Links": "Allows links that members share to show embedded content in text channels.",
    "Attach Files": "Allows members to upload files and other media in text channels.",
    "Add Reactions": "Allows members to add new emoji reactions to a message.",
    "External Emojis": "Allows members to use emojis from other servers, if they're a Discord Nitro member.",
    "External Stickers": "Allows members to use stickers from other servers, if they're a Discord Nitro member.",
    "Mention Everyone": "Allows members to use @everyone or @here. They can also @mention all roles, "
    'even if the role\'s "Allow anyone to mention this role" is disabled',
    "Manage Messages": "Allows members to delete messages by other members or pin any message.",
    "Manage Threads": "Allows members to rename, delete, close, edit slow-mode for threads. "
    "They can also view all private threads.",
    "Read Message History": "Allows members to read previous messages sent in channels. "
    "If this permission is disabled, members only see messages sent when they are online, "
    "and focused in that channel.",
    "Send Tts Messages": "Allows members to send text-to-speech messages by starting a message with /tts. "
    "These messages can be heard by anyone focused on that channel.",
    "Use Application Commands": "Allows members to use commands from applications (bots), "
    "including slash commands and context menu commands.",
    "Send Voice Messages": "Allows members to send voice messages",
    "Create Polls": "Allows members to create polls.",
    "Connect": "Allows members to join voice channels and hear others",
    "Speak": "Allows members to talk in voice channels. If this permission is disabled, members are default muted"
    'until someone with the "Mute Members" permission un-mutes them.',
    "Stream": "Allows members to share their video, screen share, or stream a game in this server.",
    "Use Embedded Activities": "Allows members to use Activities in this server.",
    "Use Soundboard": "Allows members to send sounds from server soundboard.",
    "Use External Sounds": "Allows members to use sounds from other servers, if they're a Discord Nitro member.",
    "Use Voice Activation": "Allows members to speak in voice channels by simply talking. If this is disabled, "
    "members are required to use push-to-talk.",
    "Priority Speaker": "Allows members to be more easily heard in voice channels. When activated, the volume of "
    "others without permission will be automatically lowered.",
    "Mute Members": "Allows members to mute other members in voice channels for everyone.",
    "Deafen Members": "Allows members to deafen other members in voice channels, which means they won't be able to "
    "speak or hear others.",
    "Move Members": "Allows members to disconnect or move other members between voice channels.",
    "Set Voice Channel Status": "Allows members to create and edit voice channel status.",
    "Create Events": "Allows members to create events.",
    "Manage Events": "Allows members to edit/cancel events.",
    "Administrator": "Members with this permission will have every permission and will also bypass all channel specific"
    " permissions or restrictions.\n__**THIS IS A DANGEROUS PERMISSION TO GRANT**__",
}

LOG_NAME_DICT = {
    "member_joined_channel": "Member Join log",
    "member_left_channel": "Member Leave log",
    "member_ban_channel": "Member Ban log",
    "deleted_message_channel": "Message Delete log",
    "edited_message_channel": "Message Edited log",
    "role_create_channel": "Role Created log",
    "role_delete_channel": "Role Delete log",
    "role_edited_channel": "Role Deleted log",
    "member_general_update_channel": "Member Update log",
    "channel_create_channel": "Channel Create log",
    "channel_delete_channel": "Channel Delete log",
    "voice_update_channel": "Voice State Update log",
    "invite_sent_log_channel": "Invite log",
    "new_account_age": "number of days the join/leave logs will show precisely how old the account is",
    "ignored_channels": "Channels that do not get logged",
    "ignored_roles": "Roles that do not get logged",
}

DEFAULT_MODERATION_PUNISHMENT_ENTRY = {
    "times_muted": 0,
    "mute_reasons": [""],
    "times_warned": 0,
    "warn_reasons": [""],
    "times_kicked": 0,
    "kick_reasons": [""],
    "times_banned": 0,
    "ban_reasons": [""],
}
