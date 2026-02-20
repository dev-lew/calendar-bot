# -*- coding: utf-8 -*-

# Copyright 2016 Denis Nelubin.
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
from functools import partial

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from calbot import stats
from calbot.commands import add as add_command
from calbot.commands import cal as cal_command
from calbot.commands import format as format_command
from calbot.commands import advance as advance_command
from calbot.processing import update_calendars_job

__all__ = ["run_bot"]

GREETING = """Hello, I'm calendar bot, please give me some commands.
/add — add new iCal to be sent to a channel
/list — see all configured calendars
/format — get and set a calendar event formatting, use {title}, {date}, {time}, {location} and {description} variables
/advance — get and set calendar events advance, i.e. how many hours before the event to publish it
"""

logger = logging.getLogger("bot")


def run_bot(config):
    application = Application.builder().token(config.token).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", start))

    application.add_handler(add_command.create_handler(config))

    application.add_handler(
        CommandHandler("list", partial(list_calendars, config=config))
    )

    application.add_handler(cal_command.create_handler(config))
    application.add_handler(format_command.create_handler(config))
    application.add_handler(advance_command.create_handler(config))

    application.add_handler(CommandHandler("stats", partial(get_stats, config=config)))

    application.add_handler(CommandHandler("cancel", cancel))
    application.add_handler(MessageHandler(filters.COMMAND, unknown))

    application.add_error_handler(error)

    # Job queue
    application.job_queue.run_repeating(
        update_calendars_job,
        interval=config.interval,
        first=0,
        data=config,
    )

    if config.webhook:
        webhook_url = f"https://{config.domain}/{config.token}"

        application.run_webhook(
            listen=config.listen,
            port=config.port,
            url_path=config.token,
            webhook_url=webhook_url,
        )

        logger.info("Started webhook on %s:%s", config.listen, config.port)
        logger.info("Set webhook to %s", webhook_url)

    else:
        application.run_polling()
        logger.info("Started polling")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info("Started from %s", update.effective_chat.id)
    await update.message.reply_text(GREETING)


async def list_calendars(update: Update, context: ContextTypes.DEFAULT_TYPE, config):
    user_id = str(update.effective_chat.id)

    text = "ID\tNAME\tCHANNEL\n"
    for calendar in config.user_calendars(user_id):
        text += "/cal%s\t%s\t%s%s\n" % (
            calendar.id,
            calendar.name,
            calendar.channel_id,
            ("" if calendar.enabled else "\tDISABLED"),
        )

    await update.message.reply_text(text)


async def get_stats(update: Update, context: ContextTypes.DEFAULT_TYPE, config):
    text = str(stats.get_stats(config))
    await update.message.reply_text(text)


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Sorry, there's nothing to cancel.")


async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Sorry, I don't understand this command.")


async def error(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.warning('Update "%s" caused error "%s"', update, context.error)
