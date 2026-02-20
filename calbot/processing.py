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
from telegram.ext import ContextTypes

from calbot.formatting import format_event
from calbot.ical import Calendar
from calbot.stats import update_stats

__all__ = ["update_calendars_job", "update_calendars", "update_calendar"]

logger = logging.getLogger("processing")


async def update_calendars_job(context: ContextTypes.DEFAULT_TYPE):
    """
    Job queue callback.
    Runs the update of all calendars one by one.
    Finally, updates statistics.
    """
    config = context.job.data
    await update_calendars(context, config)


async def update_calendars(context: ContextTypes.DEFAULT_TYPE, config):
    """
    Runs the update of all calendars one by one.
    Finally, updates statistics.
    """
    for calendar in config.all_calendars():
        await update_calendar(context, calendar)

    update_stats(config)


async def update_calendar(context: ContextTypes.DEFAULT_TYPE, config):
    """
    Update data from the calendar.
    Reads ical file and notifies events if necessary.
    After the first successful read the calendar is marked as validated.
    """
    if not config.enabled:
        logger.info(
            "Skipping processing of disabled calendar %s of user %s",
            config.id,
            config.user_id,
        )
        return

    bot = context.bot

    try:
        calendar = Calendar(config)

        if not config.verified:
            await bot.send_message(
                chat_id=config.channel_id,
                text=f"Events from {calendar.name} will be notified here",
            )

            config.save_calendar(calendar)

            await bot.send_message(
                chat_id=config.user_id,
                text=(
                    f"Verified calendar {config.id}\n"
                    f"Name: {config.name}\n"
                    f"URL: {config.url}\n"
                    f"Channel: {config.channel_id}"
                ),
            )

        for event in calendar.events:
            await send_event(context, config, event)
            config.event_notified(event)
            config.save_events()

        config.save_error(None)

    except Exception as e:
        logger.warning(
            "Failed to process calendar %s of user %s",
            config.id,
            config.user_id,
            exc_info=True,
        )

        was_enabled = config.enabled
        config.save_error(e)

        if was_enabled and not config.verified:
            try:
                await bot.send_message(
                    chat_id=config.user_id,
                    text=f"Failed to process calendar /cal{config.id}:\n{e}",
                )
            except Exception:
                logger.error(
                    "Failed to send message to user %s",
                    config.user_id,
                    exc_info=True,
                )

        if was_enabled and not config.enabled:
            try:
                await bot.send_message(
                    chat_id=config.user_id,
                    text=(
                        f"Calendar /cal{config.id} is disabled due too many "
                        f"processing errors\n"
                    ),
                )
            except Exception:
                logger.error(
                    "Failed to send message to user %s",
                    config.user_id,
                    exc_info=True,
                )


async def send_event(context: ContextTypes.DEFAULT_TYPE, config, event):
    """
    Sends the event notification to the channel.
    """
    logger.info(
        'Sending event %s "%s" to %s',
        event.id,
        event.title,
        config.channel_id,
    )

    await context.bot.send_message(
        chat_id=config.channel_id,
        text=format_event(config, event),
    )
