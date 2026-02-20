# -*- coding: utf-8 -*-

# Copyright 2017 Denis Nelubin.
#
# This file is part of Calendar Bot.
#
# Calendar Bot is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Calendar Bot is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Calendar Bot.  If not, see http://www.gnu.org/licenses/.
# -*- coding: utf-8 -*-

import logging
import re

from telegram import Update
from telegram.ext import (
    ConversationHandler,
    MessageHandler,
    CommandHandler,
    ContextTypes,
    filters,
)

from calbot.conf import CalendarConfig
from calbot.processing import update_calendar

__all__ = ["create_handler"]

logger = logging.getLogger("commands.cal")

EDITING = 0
EDITING_URL = 1
EDITING_CHANNEL = 2
END = ConversationHandler.END


def create_handler(config):
    async def entry_point(update: Update, context: ContextTypes.DEFAULT_TYPE):
        match = re.match(r"^/cal(\d+)", update.message.text)
        if not match:
            return END
        calendar_id = match.group(1)
        return await get_cal(update, context, calendar_id, config)

    return ConversationHandler(
        entry_points=[MessageHandler(filters.Regex(r"^/cal\d+"), entry_point)],
        states={
            EDITING: [
                CommandHandler("url", lambda u, c: start_edit_cal_url(u, c, config)),
                CommandHandler(
                    "channel", lambda u, c: start_edit_cal_channel(u, c, config)
                ),
                CommandHandler("enable", lambda u, c: enable_cal(u, c, config)),
                CommandHandler("disable", lambda u, c: disable_cal(u, c, config)),
                CommandHandler("delete", lambda u, c: del_cal(u, c, config)),
            ],
            EDITING_URL: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    lambda u, c: edit_cal_url(u, c, config),
                )
            ],
            EDITING_CHANNEL: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    lambda u, c: edit_cal_channel(u, c, config),
                )
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True,
    )


async def get_cal(
    update: Update, context: ContextTypes.DEFAULT_TYPE, calendar_id, config
):
    user_id = str(update.effective_chat.id)
    context.chat_data["calendar_id"] = calendar_id

    try:
        calendar = config.load_calendar(user_id, calendar_id)

        await update.message.reply_text(
            f"""Calendar {calendar.id} details
Name: {calendar.name}
URL: {calendar.url}
Channel: {calendar.channel_id}
Verified: {calendar.verified}
Enabled: {calendar.enabled}
Last processed: {calendar.last_process_at}
Last error: {calendar.last_process_error}
Errors count: {calendar.last_errors_count}"""
        )

        await update.message.reply_text(
            f"Edit the calendar /url or /channel, or "
            f"{'/disable' if calendar.enabled else '/enable'} it, "
            f"or /delete, or /cancel"
        )

        return EDITING

    except Exception as e:
        logger.warning(
            "Failed to load calendar %s for user %s",
            calendar_id,
            user_id,
            exc_info=True,
        )
        await update.message.reply_text(f"Failed to find calendar {calendar_id}:\n{e}")
        return END


async def del_cal(update: Update, context: ContextTypes.DEFAULT_TYPE, config):
    user_id = str(update.effective_chat.id)
    calendar_id = context.chat_data["calendar_id"]

    try:
        config.delete_calendar(user_id, calendar_id)

        for job in context.job_queue.jobs():
            if (
                hasattr(job, "data")
                and isinstance(job.data, CalendarConfig)
                and job.data.id == calendar_id
            ):
                job.schedule_removal()

        await update.message.reply_text(f"Calendar {calendar_id} is deleted")

    except Exception as e:
        logger.warning(
            "Failed to delete calendar %s for user %s",
            calendar_id,
            user_id,
            exc_info=True,
        )
        await update.message.reply_text(
            f"Failed to delete calendar {calendar_id}:\n{e}"
        )

    return END


async def start_edit_cal_url(update, context, config):
    user_id = str(update.effective_chat.id)
    calendar_id = context.chat_data["calendar_id"]

    try:
        calendar = config.load_calendar(user_id, calendar_id)
        await update.message.reply_text("The current calendar URL is:")
        await update.message.reply_text(calendar.url)
        await update.message.reply_text("Enter a new URL of iCal file or /cancel")
        return EDITING_URL
    except Exception:
        logger.error("Failed to reply to user %s", user_id, exc_info=True)
        return END


async def edit_cal_url(update, context, config):
    user_id = str(update.effective_chat.id)
    calendar_id = context.chat_data["calendar_id"]

    try:
        url = update.message.text.strip()
        calendar = config.change_calendar_url(user_id, calendar_id, url)

        await update.message.reply_text(
            "The updated calendar is queued for verification.\nWait for messages here."
        )

        await update_calendar(context, calendar)

    except Exception as e:
        logger.warning(
            "Failed to change url of calendar %s for user %s",
            calendar_id,
            user_id,
            exc_info=True,
        )
        await update.message.reply_text(
            f"Failed to change url of calendar {calendar_id}:\n{e}"
        )

    return END


async def start_edit_cal_channel(update, context, config):
    user_id = str(update.effective_chat.id)
    calendar_id = context.chat_data["calendar_id"]

    try:
        calendar = config.load_calendar(user_id, calendar_id)
        await update.message.reply_text("The current calendar channel is:")
        await update.message.reply_text(calendar.channel_id)
        await update.message.reply_text("Enter a new channel name or /cancel")
        return EDITING_CHANNEL
    except Exception:
        logger.error("Failed to reply to user %s", user_id, exc_info=True)
        return END


async def edit_cal_channel(update, context, config):
    user_id = str(update.effective_chat.id)
    calendar_id = context.chat_data["calendar_id"]

    try:
        channel_id = update.message.text.strip()
        calendar = config.change_calendar_channel(user_id, calendar_id, channel_id)

        await update.message.reply_text(
            "The updated calendar is queued for verification.\nWait for messages here."
        )

        await update_calendar(context, calendar)

    except Exception as e:
        logger.warning(
            "Failed to change channel of calendar %s for user %s",
            calendar_id,
            user_id,
            exc_info=True,
        )
        await update.message.reply_text(
            f"Failed to change channel of calendar {calendar_id}:\n{e}"
        )

    return END


async def enable_cal(update, context, config):
    user_id = str(update.effective_chat.id)
    calendar_id = context.chat_data["calendar_id"]

    try:
        config.enable_calendar(user_id, calendar_id, True)
        await update.message.reply_text(f"Calendar /cal{calendar_id} is enabled")
    except Exception as e:
        logger.warning(
            "Failed to enable calendar %s for user %s",
            calendar_id,
            user_id,
            exc_info=True,
        )
        await update.message.reply_text(
            f"Failed to enable calendar /cal{calendar_id}:\n{e}"
        )

    return END


async def disable_cal(update, context, config):
    user_id = str(update.effective_chat.id)
    calendar_id = context.chat_data["calendar_id"]

    try:
        config.enable_calendar(user_id, calendar_id, False)
        await update.message.reply_text(f"Calendar /cal{calendar_id} is disabled")
    except Exception as e:
        logger.warning(
            "Failed to disable calendar %s for user %s",
            calendar_id,
            user_id,
            exc_info=True,
        )
        await update.message.reply_text(
            f"Failed to disable calendar /cal{calendar_id}:\n{e}"
        )

    return END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Cancelled.")
    return END
