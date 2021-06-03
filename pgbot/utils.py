"""
This file is a part of the source code for the PygameCommunityBot.
This project has been licensed under the MIT license.
Copyright (c) 2020-present PygameCommunityDiscord

This file defines some important utility functions.
"""

from __future__ import annotations

import asyncio
import datetime
import os
import platform
import re
import sys
import traceback
import typing

import discord
import pygame

from . import common, embed_utils


def clamp(value, min_, max_):
    return max(min(value, max_), min_)


def color_to_rgb_int(col: pygame.Color):
    """
    Get integer RGB representation of pygame color object. This does not include
    the alpha component of the color, which int(col) would give you
    """
    return (((col.r << 8) + col.g) << 8) + col.b


def discordify(text: str):
    """
    Converts normal string into "discord" string that includes backspaces to
    cancel out unwanted changes
    """
    return discord.utils.escape_markdown(text)


def format_discord_link(link: str, guild_id: int):
    """
    Format a discord link to a channel or message
    """
    link = link.lstrip("<").rstrip(">").rstrip("/")

    for prefix in (
        f"https://discord.com/channels/{guild_id}/",
        f"https://www.discord.com/channels/{guild_id}/",
    ):
        if link.startswith(prefix):
            link = link[len(prefix) :]

    return link


def progress_bar(pct, full_bar: str = "█", empty_bar: str = "░", divisions: int = 10):
    """
    A simple horizontal progress bar generator.
    """
    pct = 0 if pct < 0 else 1 if pct > 1 else pct
    return full_bar * (int(divisions * pct)) + empty_bar * (
        divisions - int(divisions * pct)
    )


def format_time(
    seconds: float,
    decimal_places: int = 4,
    unit_data=(
        (1.0, "s"),
        (1e-03, "ms"),
        (1e-06, "\u03bcs"),
        (1e-09, "ns"),
        (1e-12, "ps"),
        (1e-15, "fs"),
        (1e-18, "as"),
        (1e-21, "zs"),
        (1e-24, "ys"),
    ),
):
    """
    Formats time with a prefix
    """
    for fractions, unit in unit_data:
        if seconds >= fractions:
            return f"{seconds / fractions:.0{decimal_places}f} {unit}"
    return f"very fast"


def format_long_time(seconds: int):
    """
    Formats time into string, which is of the order of a few days
    """
    result = []

    for name, count in (
        ("weeks", 604800),
        ("days", 86400),
        ("hours", 3600),
        ("minutes", 60),
        ("seconds", 1),
    ):
        value = seconds // count
        if value or (not result and count == 1):
            seconds -= value * count
            if value == 1:
                name = name[:-1]
            result.append(f"{value} {name}")

    preset = ", ".join(result[:-1])
    if preset:
        return f"{preset} and {result[-1]}"
    return result[-1]


def format_timedelta(tdelta: datetime.timedelta):
    """
    Formats timedelta object into human readable time
    """
    return format_long_time(int(tdelta.total_seconds()))


def format_byte(size: int, decimal_places=3):
    """
    Formats a given size and outputs a string equivalent to B, KB, MB, or GB
    """
    if size < 1e03:
        return f"{round(size, decimal_places)} B"
    if size < 1e06:
        return f"{round(size / 1e3, decimal_places)} KB"
    if size < 1e09:
        return f"{round(size / 1e6, decimal_places)} MB"

    return f"{round(size / 1e9, decimal_places)} GB"


def split_long_message(message: str):
    """
    Splits message string by 2000 characters with safe newline splitting
    """
    split_output = []
    lines = message.split("\n")
    temp = ""

    for line in lines:
        if len(temp) + len(line) + 1 > 2000:
            split_output.append(temp[:-1])
            temp = line + "\n"
        else:
            temp += line + "\n"

    if temp:
        split_output.append(temp)

    return split_output


def format_code_exception(e, pops: int = 1):
    """
    Provide a formatted exception for code snippets
    """
    tbs = traceback.format_exception(type(e), e, e.__traceback__)
    # Pop out the first entry in the traceback, because that's
    # this function call itself
    for _ in range(pops):
        tbs.pop(1)

    ret = "".join(tbs).replace(os.getcwd(), "PgBot")
    if platform.system() == "Windows":
        # Hide path to python on windows
        ret = ret.replace(os.path.dirname(sys.executable), "Python")

    return ret


def filter_id(mention: str):
    """
    Filters mention to get ID "<@!6969>" to "6969"
    Note that this function can error with ValueError on the int call, so the
    caller of this function must take care of that.
    """
    for char in ("<", ">", "@", "&", "#", "!", " "):
        mention = mention.replace(char, "")

    return int(mention)


def filter_emoji_id(name: str):
    """
    Filter emoji name to get "837402289709907978" from
    "<:pg_think:837402289709907978>"
    Note that this function can error with ValueError on the int call, in which
    case it returns the input string (no exception is raised)

    Args:
        name (str): The emoji name

    Returns:
        str|int: The emoji id or the input string if it could not convert it to
        an int.
    """
    if name.count(":") >= 2:
        emoji_id = name.split(":")[-1][:-1]
        return int(emoji_id)

    try:
        return int(name)
    except ValueError:
        return name


def get_doc_from_docstr(string: str, regex: re.Pattern):
    """
    Get the type, signature, description and other information
    from docstrings.

    Args:
        string (str): The string to check
        regex (re.Pattern): The pattern to use

    Returns:
        Dict[str] or Dict[]: The type, signature and description of
        the string. An empty dict will be returned if the string begins
        with "->skip" or there was no information found
    """
    data = {}
    if not string:
        return {}

    string = string.strip()

    if string.startswith("->skip"):
        return {}

    string = string.split("-----")[0]

    finds = regex.findall(string)
    current_key = ""
    if finds:
        for find in finds:
            if find[0].startswith("->"):
                current_key = find[0][2:].strip()
                continue

            if not current_key:
                continue

            # remove useless whitespace
            value = re.sub("  +", "", find[1].strip())
            data[current_key] = value
            current_key = ""

    return data


async def send_help_message(original_msg, invoker, functions, command=None, page=0):
    """
    Edit original_msg to a help message. If command is supplied it will
    only show information about that specific command. Otherwise sends
    the general help embed.

    Args:
        original_msg (discord.Message): The message to edit

        functions (dict[str, callable]): The name-function pairs to get
        the docstrings from

        command (str, optional): The command to send the description about.
        Defaults to None.
    """
    regex = re.compile(
        # If you add a new "section" to this regex dont forget the "|" at the end
        # Does not have to be in the same order in the docs as in here.
        r"(->type|"
        r"->signature|"
        r"->description|"
        r"->example command|"
        r"->extended description\n|"
        r"\Z)|(((?!->).|\n)*)"
    )
    fields = {}

    if not command:
        for func_name in functions:
            docstring = functions[func_name].__doc__
            data = get_doc_from_docstr(docstring, regex)
            if not data:
                continue

            if not fields.get(data["type"]):
                fields[data["type"]] = ["", "", True]

            fields[data["type"]][0] += f"{data['signature'][2:]}\n"
            fields[data["type"]][1] += (
                f"`{data['signature']}`\n" f"{data['description']}\n\n"
            )

        fields_cpy = fields.copy()

        for field_name in fields:
            value = fields[field_name]
            value[1] = f"```\n{value[0]}\n```\n\n{value[1]}"
            value[0] = f"__**{field_name}**__"

        fields = fields_cpy

        embeds = []
        for field in list(fields.values()):
            body = f"{common.BOT_HELP_PROMPT['body']}\n{field[0]}\n\n{field[1]}"
            embeds.append(
                await embed_utils.send_2(
                    None,
                    title=common.BOT_HELP_PROMPT["title"],
                    description=body,
                    color=common.BOT_HELP_PROMPT["color"],
                )
            )

        page_system = embed_utils.PagedEmbed(
            original_msg, embeds, invoker, "help", page
        )

        await page_system.mainloop()
        return

    else:
        for func_name, func in functions.items():
            # TODO: AAAAAAAAAAAAA add help for subcommands, it'd make it easier to look them up
            #       Snek would try to reattempt this after recharging his brain juice
            if func_name != command:
                continue

            # func = functions[func_name]
            doc = get_doc_from_docstr(func.__doc__, regex)

            if not doc:
                # function found, but does not have help.
                break

            body = f"`{doc['signature']}`\n"
            body += f"`Category: {doc['type']}`\n\n"

            desc = doc["description"]

            ext_desc = doc.get("extended description")
            if ext_desc:
                desc += " " + ext_desc

            body += f"**Description:**\n{desc}"

            example_cmd = doc.get("example command")
            if example_cmd:
                body += f"\n\n**Example command(s):**\n{example_cmd}"

            # TODO
            # if hasattr(func, "subcmds"):
            #     body += f"\n\n**Subcommand(s):**\n"
            #     for i, subcmd in enumerate(func.subcmds, 1):
            #         subcmd_doc = get_doc_from_docstr(subcmd.__doc__, regex)
            #         body += f"{i}. `{subcmd_doc['signature']}`\n" \
            #                 f"{subcmd_doc['description']}\n\n"

            await embed_utils.replace(
                original_msg, f"Help for `{func_name}`", body, 0xFFFF00
            )
            return

    await embed_utils.replace(
        original_msg,
        "Command not found",
        f"Help message for command {command} was not found or has no documentation.",
    )


def format_entries_message(msg: discord.Message, entry_type: str):
    """
    Formats an entries message to be reposted in discussion channel
    """
    title = f"New {entry_type.lower()} in #{common.ZERO_SPACE}{common.entry_channels[entry_type].name}"

    attachments = ""
    if msg.attachments:
        for i, attachment in enumerate(msg.attachments):
            attachments += f" • [Link {i + 1}]({attachment.url})\n"
    else:
        attachments = "No attachments"

    desc = msg.content if msg.content else "No description provided."

    fields = [
        ["**Posted by**", msg.author.mention, True],
        ["**Original msg.**", f"[View]({msg.jump_url})", True],
        ["**Attachments**", attachments, True],
        ["**Description**", desc, True],
    ]
    return title, fields


def code_block(string: str, max_characters=2048):
    """
    Formats text into discord code blocks
    """
    string = string.replace("```", "\u200b`\u200b`\u200b`\u200b")
    max_characters -= 7

    if len(string) > max_characters:
        return f"```\n{string[:max_characters - 7]} ...```"
    else:
        return f"```\n{string[:max_characters]}```"


def check_channel_permissions(
    member: discord.Member,
    channel: discord.TextChannel,
    bool_func: typing.Callable[typing.Iterable, bool] = all,
    permissions: typing.Iterable[str] = (
        "view_channel",
        "send_messages",
    ),
) -> bool:

    """
    Checks if the given permissions apply to the given member in the given channel.
    """

    channel_perms = channel.permissions_for(member)
    return bool_func(getattr(channel_perms, perm_name) for perm_name in permissions)


def check_channels_permissions(
    member: discord.Member,
    *channels: discord.TextChannel,
    bool_func: typing.Callable[typing.Iterable, bool] = all,
    skip_invalid_channels: bool = False,
    permissions: typing.Iterable[str] = (
        "view_channel",
        "send_messages",
    ),
) -> typing.Tuple[bool]:

    """
    Checks if the given permissions apply to the given member in the given channels.
    """

    if skip_invalid_channels:
        booleans = tuple(
            bool_func(getattr(channel_perms, perm_name) for perm_name in permissions)
            for channel_perms in (
                channel.permissions_for(member)
                for channel in channels
                if isinstance(channel, discord.TextChannel)
            )
        )
    else:
        booleans = tuple(
            bool_func(getattr(channel_perms, perm_name) for perm_name in permissions)
            for channel_perms in (
                channel.permissions_for(member) for channel in channels
            )
        )
    return booleans


async def coro_check_channels_permissions(
    member: discord.Member,
    *channels: discord.TextChannel,
    bool_func: typing.Callable[typing.Iterable, bool] = all,
    skip_invalid_channels: bool = False,
    permissions: typing.Iterable[str] = (
        "view_channel",
        "send_messages",
    ),
) -> typing.List[bool]:

    """
    Checks if the given permissions apply to the given member in the given channels.
    """

    booleans = []
    if skip_invalid_channels:
        for i, channel in channels:
            if isinstance(channel, discord.TextChannel):
                channel_perms = channel.permissions_for(member)
                booleans.append(
                    bool_func(getattr(channel_perms, perm) for perm in permissions)
                )

            if not i % 5:
                await asyncio.sleep(0)
    else:
        for i, channel in channels:
            channel_perms = channel.permissions_for(member)
            booleans.append(
                bool_func(getattr(channel_perms, perm) for perm in permissions)
            )

            if not i % 5:
                await asyncio.sleep(0)

    return booleans
