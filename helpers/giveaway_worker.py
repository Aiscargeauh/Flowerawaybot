import asyncio
import logging
import helpers
from time import time

async def threaded_time_left_update(context, message_id, message_url, end_time, author):
    end_time_met = False
    logger = logging.getLogger("GiveawayLogger")
    while not end_time_met:
        await asyncio.sleep(60 - time() % 60)
        logger.info(f"Threaded time left is updating")
        if helpers.giveaway_database_helpers.is_giveaway_ended_or_aborted(message_id):
            logger.error(f"Giveaway has been ended or aborted, stopping thread")
            return
        await helpers.giveaway_helpers.update_time_left_on_message(context, message_id, end_time)
        logger.info(f"Updated time on giveaway embed")
        end_time_met = helpers.giveaway_helpers.is_end_time_met(end_time)
        if end_time_met:
            first_message_id = await helpers.giveaway_helpers.notify_user_giveaway_end(context, message_id, message_url, author)
            await helpers.giveaway_helpers.notify_user_giveaway_end_as_text(context, first_message_id, author)
            logger.info(f"End time has been met, notified author")

async def threaded_list_time_left_update(context, list_message_id):
    message_exists = True
    logger = logging.getLogger("GiveawayLogger")
    while message_exists:
        await asyncio.sleep(60 - time() % 60)
        logger.info(f"Threaded task updating list message")
        try:
            message_exists = await context.fetch_message(list_message_id) != None
        except:
            return
        if message_exists:
            ongoing_giveaways = helpers.giveaway_database_helpers.get_ongoing_giveaways()
            await helpers.giveaway_helpers.update_time_left_on_list_message(context, list_message_id, ongoing_giveaways)
            logger.info(f"Updated time left on list message")
        else:
            return