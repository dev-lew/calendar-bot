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

from calbot.formatting import format_event
from calbot.ical import sample_event

__all__ = ["create_handler"]

logger = logging.getLogger("commands.format")

SETTING = 0
END = ConversationHandler.END


def create_handler(config):
    async def get_format_with_config(
        update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        return await get_format(update, context, config)

    async def set_format_with_config(
        update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        return await set_format(update, context, config)

    async def cancel_with_config(update: Update, context: ContextTypes.DEFAULT_TYPE):
        return await cancel(update, context, config)

    return ConversationHandler(
        entry_points=[CommandHandler("format", get_format_with_config)],
        states={
            SETTING: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    set_format_with_config,
                )
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel_with_config)],
        allow_reentry=True,
    )


async def get_format(update: Update, context: ContextTypes.DEFAULT_TYPE, config):
    user_id = str(update.effective_chat.id)

    try:
        user_config = config.load_user(user_id)

        await update.message.reply_text("Current format:")
        await update.message.reply_text(user_config.format)

        await update.message.reply_text("Sample event:")
        await update.message.reply_text(format_event(user_config, sample_event))

        await update.message.reply_text("Type a new format string to set or /cancel")

        return SETTING

    except Exception:
        logger.error(
            "Failed to send reply to user %s",
            user_id,
            exc_info=True,
        )
        return END


async def set_format(update: Update, context: ContextTypes.DEFAULT_TYPE, config):
    message = update.effective_message
    user_id = str(update.effective_chat.id)

    try:
        user_config = config.load_user(user_id)

        new_format = message.text.strip()
        user_config.set_format(new_format)

        await message.reply_text("Format is updated.\nSample event:")
        await message.reply_text(format_event(user_config, sample_event))

        return END

    except Exception as e:
        logger.warning(
            "Failed to update format for user %s",
            user_id,
            exc_info=True,
        )

        try:
            await message.reply_text(f"Failed to update format:\n{e}")
            await message.reply_text("Try again or /cancel")
        except Exception:
            logger.error(
                "Failed to send reply to user %s",
                user_id,
                exc_info=True,
            )

        return SETTING


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE, config):
    user_id = str(update.effective_chat.id)

    try:
        user_config = config.load_user(user_id)

        await update.message.reply_text("Cancelled.\nCurrent format:")
        await update.message.reply_text(user_config.format)

    except Exception:
        logger.error(
            "Failed to send reply to user %s",
            user_id,
            exc_info=True,
        )

    return END
