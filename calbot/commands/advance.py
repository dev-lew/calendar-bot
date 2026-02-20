# -*- coding: utf-8 -*-

# Copyright 2017 Denis Nelubin.
# Copyright 2026 dev-lew.
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

__all__ = ["create_handler"]

logger = logging.getLogger("commands.advance")

SETTING = 0
END = ConversationHandler.END


def create_handler(config):
    async def get_advance_with_config(
        update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        return await get_advance(update, context, config)

    async def set_advance_with_config(
        update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        return await set_advance(update, context, config)

    async def cancel_with_config(update: Update, context: ContextTypes.DEFAULT_TYPE):
        return await cancel(update, context, config)

    return ConversationHandler(
        entry_points=[CommandHandler("advance", get_advance_with_config)],
        states={
            SETTING: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    set_advance_with_config,
                )
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel_with_config)],
        allow_reentry=True,
    )


async def get_advance(update: Update, context: ContextTypes.DEFAULT_TYPE, config):
    user_id = str(update.effective_chat.id)

    try:
        user_config = config.load_user(user_id)

        text = (
            f"Events are notified "
            f"{', '.join(map(str, user_config.advance))} hours in advance.\n\n"
            "Type how many hours in advance events should be notified. "
            "Several intervals can be entered separated by space.\n\n"
            "Example:\n48 24 12 6\n\n"
            "Type /cancel to cancel update."
        )

        await update.message.reply_text(text)
        return SETTING

    except Exception:
        logger.error(
            "Failed to send reply to user %s",
            user_id,
            exc_info=True,
        )
        return END


async def set_advance(update: Update, context: ContextTypes.DEFAULT_TYPE, config):
    user_id = str(update.effective_chat.id)

    try:
        user_config = config.load_user(user_id)

        hours = update.message.text.split()
        user_config.set_advance(hours)

        text = (
            "Advance hours are updated.\n"
            f"Events will be notified "
            f"{', '.join(map(str, user_config.advance))} hours in advance."
        )

        await update.message.reply_text(text)
        return END

    except Exception as e:
        logger.warning(
            "Failed to update advance for user %s",
            user_id,
            exc_info=True,
        )

        try:
            await update.message.reply_text(f"Failed to update advance hours:\n{e}")
            await update.message.reply_text("Try again or /cancel")
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

        text = (
            "Cancelled.\n"
            f"Events will be notified "
            f"{', '.join(map(str, user_config.advance))} hours in advance."
        )

        await update.message.reply_text(text)

    except Exception:
        logger.error(
            "Failed to send reply to user %s",
            user_id,
            exc_info=True,
        )

    return END
