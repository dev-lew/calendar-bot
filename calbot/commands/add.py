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

from telegram import Update
from telegram.ext import (
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from calbot.processing import update_calendar

__all__ = ["create_handler"]

logger = logging.getLogger("commands.add")

ENTERING_URL = 0
ENTERING_CHANNEL = 1
END = ConversationHandler.END


def create_handler(config):
    """
    Creates handler for /add command.
    """

    async def add_calendar_with_config(
        update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        return await add_calendar(update, context, config)

    return ConversationHandler(
        entry_points=[CommandHandler("add", start)],
        states={
            ENTERING_URL: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_url)],
            ENTERING_CHANNEL: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    add_calendar_with_config,
                )
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True,
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_chat.id)

    try:
        await update.message.reply_text(
            "You're going to add a new calendar.\nEnter an URL of iCal file or /cancel"
        )
        return ENTERING_URL
    except Exception:
        logger.error("Failed to send reply to user %s", user_id, exc_info=True)
        return END


async def enter_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_chat.id)

    try:
        context.chat_data["calendar_url"] = update.message.text.strip()

        await update.message.reply_text(
            "Enter a channel name or /cancel.\nChannel name should start with @."
        )
        return ENTERING_CHANNEL
    except Exception:
        logger.error("Failed to send reply to user %s", user_id, exc_info=True)
        return END


async def add_calendar(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    config,
):
    user_id = str(update.effective_chat.id)
    url = context.chat_data.get("calendar_url")

    try:
        channel_id = update.message.text.strip()

        calendar = config.add_calendar(user_id, url, channel_id)

        await update.message.reply_text(
            "The new calendar is queued for verification.\n"
            f"Wait for messages here and in the {channel_id}."
        )

        # Trigger immediate verification
        await update_calendar(context, calendar)

    except Exception as e:
        logger.warning(
            "Failed to add calendar for user %s",
            user_id,
            exc_info=True,
        )

        try:
            await update.message.reply_text(f"Failed to add calendar:\n{e}")
        except Exception:
            logger.error(
                "Failed to send reply to user %s",
                user_id,
                exc_info=True,
            )

    return END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_chat.id)

    try:
        await update.message.reply_text("Cancelled.")
    except Exception:
        logger.error(
            "Failed to send reply to user %s",
            user_id,
            exc_info=True,
        )

    return END
