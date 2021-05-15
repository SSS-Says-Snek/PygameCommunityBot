import asyncio
import os
import random

import discord
import pygame

from pgbot import commands, common, emotion, utils, embed_utils, db


@common.bot.event
async def on_ready():
    """
    Startup routines when the bot starts
    """
    print("The PygameCommunityBot is now online!")
    print("The bot is present in these server(s):")
    for server in common.bot.guilds:
        print("-", server.name)
        for channel in server.channels:
            print(" +", channel.name)
            if channel.id == common.DB_CHANNEL_ID:
                await db.init(channel)
            if channel.id == common.LOG_CHANNEL_ID:
                common.log_channel = channel
            if channel.id == common.ARRIVALS_CHANNEL_ID:
                common.arrivals_channel = channel
            if channel.id == common.GUIDE_CHANNEL_ID:
                common.guide_channel = channel
            if channel.id == common.ROLES_CHANNEL_ID:
                common.roles_channel = channel
            if channel.id == common.ENTRIES_DISCUSSION_CHANNEL_ID:
                common.entries_discussion_channel = channel
            for key, value in common.ENTRY_CHANNEL_IDS.items():
                if channel.id == value:
                    common.entry_channels[key] = channel

    while True:
        await common.bot.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching, name="discord.io/pygame_community"
            )
        )
        await asyncio.sleep(2.5)
        await common.bot.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.playing, name="in discord.io/pygame_community"
            )
        )
        await asyncio.sleep(2.5)


@common.bot.event
async def on_member_join(member: discord.Member):
    """
    This function handles the greet message when a new member joins
    """
    if common.TEST_MODE or member.bot:
        # Do not greet people in test mode, or if a bot joins
        return

    greet = random.choice(common.BOT_WELCOME_MSG["greet"])
    check = random.choice(common.BOT_WELCOME_MSG["check"])

    grab = random.choice(common.BOT_WELCOME_MSG["grab"])
    end = random.choice(common.BOT_WELCOME_MSG["end"])

    # This function is called right when a member joins, even before the member
    # finishes the join screening. So we wait for that to happen and then send
    # the message. Wait for a maximum of six hours.
    for _ in range(10800):
        await asyncio.sleep(2)

        if not member.pending:
            # Don't use embed here, because pings would not work
            await common.arrivals_channel.send(
                f"{greet} {member.mention}! {check} "
                + f"{common.guide_channel.mention}{grab} "
                + f"{common.roles_channel.mention}{end}"
            )
            return


@common.bot.event
async def on_message(msg: discord.Message):
    """
    This function is called for every message by user.
    """
    if msg.author.bot:
        return

    if msg.content.startswith(common.PREFIX):
        try:
            common.cmd_logs[msg.id] = await commands.handle(msg)
            if len(common.cmd_logs) > 100:
                del common.cmd_logs[common.cmd_logs.keys()[0]]
        except discord.HTTPException:
            pass

    elif not common.TEST_MODE:
        await emotion.check_bonk(msg)

        # Check for these specific messages, do not try to generalise, because we do not
        # want the bot spamming the dario quote
        if msg.content.lower() in common.DEAD_CHAT_TRIGGERS:
            await msg.channel.send(
                common.BYDARIO_QUOTE, allowed_mentions=discord.AllowedMentions.none()
            )

        if msg.channel.id in common.ENTRY_CHANNEL_IDS.values():
            if msg.channel.id == common.ENTRY_CHANNEL_IDS["showcase"]:
                entry_type = "showcase"
                color = 0xFF8800
            else:
                entry_type = "resource"
                color = 0x0000AA

            title, fields = utils.format_entries_message(msg, entry_type)
            await embed_utils.send(
                common.entries_discussion_channel, title, "", color, fields=fields
            )
        else:
            lowered = msg.content.lower()
            if "i am" in lowered and len(lowered) < 60:
                # Probablity for triggering dad joke is 1/6 for others.
                # snek is a special case, he loves dad jokes so he will get em
                # everytime
                if msg.author.id != 683852333293109269 and random.randint(0, 5):
                    return

                name = msg.content[lowered.index("i am") + 4 :].strip()
                await msg.channel.send(f"Hi {name}! I am <@!{common.BOT_ID}>")


@common.bot.event
async def on_message_delete(msg: discord.Message):
    """
    This function is called for every message deleted by user.
    """
    if msg.id in common.cmd_logs.keys():
        del common.cmd_logs[msg.id]

    elif msg.author.id == common.bot.user.id:
        for log in common.cmd_logs.keys():
            if common.cmd_logs[log].id == msg.id:
                del common.cmd_logs[log]
                return


@common.bot.event
async def on_message_edit(old: discord.Message, new: discord.Message):
    """
    This function is called for every message edited by user.
    """
    if new.author.bot:
        return

    if new.content.startswith(common.PREFIX):
        try:
            if new.id in common.cmd_logs.keys():
                await commands.handle(new, common.cmd_logs[new.id])
        except discord.HTTPException:
            pass


if __name__ == "__main__":
    os.environ["SDL_VIDEODRIVER"] = "dummy"
    pygame.init()  # pylint: disable=no-member
    common.window = pygame.display.set_mode((1, 1))
    common.bot.run(common.TOKEN)
