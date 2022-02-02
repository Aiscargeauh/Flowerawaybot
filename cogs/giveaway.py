import asyncio
import logging
import yaml
from helpers import giveaway_database_helpers, giveaway_emojis_helpers, giveaway_helpers
import random
import re
import datetime

from discord.ext import commands

import helpers


class giveaway(commands.Cog, name="Giveaway"):
    """
    Give away a FLOWER!
    """

    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger("GiveawayLogger")

    # Here you can just add your own commands, you'll always need to provide "self" as first parameter.
    @commands.group(name="giveaway", aliases=["giveaways", "giveway", "givaway", "giveways", "givaways", "gieaway", "giveaay", "giveavay", "giveaays", "giveavays"])
    async def giveaway(self, context):
        """
        Shortcut for 'giveaway list'
        """
        if context.invoked_subcommand is None:
            await context.invoke(self.giveaway_list)

    @giveaway.command(name="create", aliases=["start", "crate", "creat"])
    async def giveaway_create(self, context):
        # TODO: Start timer and ping the author when it's about to end
        """
        Lets start a new giveaway!
        **Usage:** !giveaway create network-id timedelta emoji
        """

        # Start typing
        async with context.typing():

            # Parse arguments (sends embeds if errors)
            # Fast, as it's mostly string manipulation
            try:
                self.logger.info(
                    f"Getting args for !giveaway create: {context.message.content} by {context.message.author.display_name}")
                args = await helpers.giveaway_helpers.parse_commands_arguments(context, self.bot.emojis, helpers.giveaway_helpers.CommandTypes.CREATE, context.message.content)
            except Exception as e:
                self.logger.error(f"Missing parameter(s) in !giveaway create")
                return

            # Send initial embed
            # First response to the user
            args["message_id"], args["message_url"] = await helpers.giveaway_helpers.send_new_giveaway_embed(context, args["author"], args["flower_identifier"], args["flower_rarity"], args["flower_url"], args["reaction"], args["end_time"], "")
            self.logger.info(f"Sent new giveaway embed")

        # Add first reaction to the embedded message
        await helpers.giveaway_helpers.react_to_message(context, args["message_id"], args["reaction"])
        self.logger.info(f"Reacted to the new giveaway embed")

        # Tweet about the giveaway
        # Slow (has to upload images and push tweet: 3 http requests)
        args["tweet_url"], args["tweet_id"] = await helpers.giveaway_twitter_helpers.send_tweet(args["flower_identifier"], args["end_time"])
        self.logger.info(f"Tweeted about new giveaway: {args['tweet_url']}")

        # Update the previsously sent embed to add the twitter link
        await helpers.giveaway_helpers.add_twitter_link_to_embed(context, args["message_id"], args["tweet_url"])
        self.logger.info(f"Edited embed to show twitter link")

        # Save discord message information for quick search when !abort or !end
        # TODO: Fallback if task failed, inform user a problem happened, ping @Aiscargeauh#0954
        helpers.giveaway_database_helpers.save_new_giveaway(args["flower_identifier"], args["flower_rarity"], args["start_time"],
                                                            args["end_time"], args["author"], args["reaction"], args["message_url"], args["message_id"], args["tweet_id"])
        self.logger.info(f"saved everything in database")

        # Remove both images from server's disk
        helpers.giveaway_helpers.remove_flower_png(
            args["flower_identifier"], True)
        helpers.giveaway_helpers.remove_flower_png(
            args["flower_identifier"], False)
        self.logger.info(f"Removed flower images from server")

        # Start thread to update the message itself with up to date "Ends in"
        asyncio.get_event_loop().create_task(helpers.giveaway_worker.threaded_time_left_update(
            context, args["message_id"], args["message_url"], args["end_time"], args["author"]))
        self.logger.info(f"Started task to update embed")
        return

    @giveaway.command(name="redeemable", aliases=["redeem", "redeemab", "redemable", "redeemables"])
    async def giveaway_reedeemable(self, context):
        """
        Lets start a new giveaway, but using redeemable this time!
        **Usage:** !giveaway redeemable
        """
        # Start typing
        async with context.typing():
            try:
                if context.message.channel.type.name != "private":
                    await context.message.author.send("Hey, I'm contacting you as you would like to give away a FLOWER using Redeemable")
                    await context.message.reply("Sending you a DM for that")
            except:
                await context.message.reply("Sorry it looks like I cannot send you a direct message...")
                return

        # Get redeemable url
        try:
            await context.message.author.send("First, please send me the redeemable link")
            msg = await giveaway_helpers.wait_for_dm_reply(context)

            # If regex says it's valid link:
            pattern = re.compile(
                r"https://redeemable\.app\/r\/0x[\dabcdef]{64}")
            while not re.match(pattern, msg.content):
                await context.message.author.send("URL looks invalid, try again?")
                msg = await giveaway_helpers.wait_for_dm_reply(context)
            # TODO: Get flower info when redeemable API is ready
            redeemable_link = msg.content
            await context.message.author.send("Looks like a valid redeemable URL!\nNow I should know in how much time should the giveaway end (examples: 30m, 1h, 3d)")

            msg = await giveaway_helpers.wait_for_dm_reply(context)
            while not giveaway_helpers.get_end_time(msg.content):
                await context.message.author.send("It doesn't look valid to me, try again?\n*Examples: 30m, 1h, 3d*")
                msg = await giveaway_helpers.wait_for_dm_reply(context)
            end_time = giveaway_helpers.get_end_time(msg.content)
            await context.message.author.send("Looks like a valid time delta!\nNow I should know which emoji to use, for participants")

            msg = await giveaway_helpers.wait_for_dm_reply(context)
            while not giveaway_emojis_helpers.check_emoji_valid(self.bot.emojis, msg.content):
                await context.message.author.send("Emoji looks invalid, try again?")
                msg = await giveaway_helpers.wait_for_dm_reply(context)
            reaction = msg.content
            await context.message.author.send("Looks like a valid emoji!\nNow, last question: should the giveaway be ended automatically?\nJust answer `y` or `n`")

            msg = await giveaway_helpers.wait_for_dm_reply(context)
            while ("y" not in msg.content or "n" not in msg.content):
                if len(msg.content) != 1:
                    await context.message.author.send("I didn't understand, please reply just with `y` or `n`.")
                    msg = await giveaway_helpers.wait_for_dm_reply(context)
                else:
                    if "y" in msg.content:
                        automatic_ending = True
                        await context.message.author.send("Got it! It will end automatically, winner will receive the link in his DM")
                        break
                    elif "n" in msg.content:
                        automatic_ending = False
                        await context.message.author.send("Got it! You will have to end it with `!giveaway end` command when it's time, you will be notified.")
                        break
                    else:
                        await context.message.author.send("I didn't understand, please reply just with `y` or `n`.")
                        msg = await giveaway_helpers.wait_for_dm_reply(context)

            await context.message.author.send("Everything's ready! I'm sending that to the #🎁user-giveaways channel")

            # # TODO: Add flower_identifier, flower_rarity, flower_url here when pash finished his API
            # message_id, message_url = await helpers.giveaway_helpers.send_new_giveaway_embed(context, context.message.author.id, args["flower_identifier"], args["flower_rarity"], giveaway_helpers.get_flower_image_url(args["flower_identifier"]), reaction, end_time, "")
            # self.logger.info(f"Sent new giveaway embed")

            # # Add first reaction to the embedded message
            # await helpers.giveaway_helpers.react_to_message(context, message_id, reaction)
            # self.logger.info(f"Reacted to the new giveaway embed")

            # # Tweet about the giveaway
            # # Slow (has to upload images and push tweet: 3 http requests)
            # # TODO: add flower_identifier here
            # tweet_url, tweet_id = await helpers.giveaway_twitter_helpers.send_tweet(args["flower_identifier"], end_time)
            # self.logger.info(f"Tweeted about new giveaway: {tweet_url}")

            # # Update the previsously sent embed to add the twitter link
            # await helpers.giveaway_helpers.add_twitter_link_to_embed(context, message_id, tweet_url)
            # self.logger.info(f"Edited embed to show twitter link")

            # # Save discord message information for quick search when !abort or !end
            # helpers.giveaway_database_helpers.save_new_giveaway(args["flower_identifier"], args["flower_rarity"], datetime.utcnow(),
            #                                                     end_time, context.message.author.id, reaction, message_url, message_id, tweet_id)
            # self.logger.info(f"saved everything in database")

            # # Remove both images from server's disk
            # # TODO: Change flower_identifier
            # helpers.giveaway_helpers.remove_flower_png(
            #     args["flower_identifier"], True)
            # helpers.giveaway_helpers.remove_flower_png(
            #     args["flower_identifier"], False)
            # self.logger.info(f"Removed flower images from server")

            # # Start thread to update the message itself with up to date "Ends in"
            # asyncio.get_event_loop().create_task(helpers.giveaway_worker.threaded_time_left_update(context, message_id, message_url, end_time, context.message.author.id))
            # self.logger.info(f"Started task to update embed")

        except asyncio.TimeoutError:
            await context.message.author.send('Timed out, trigger me again with `!giveaway redeemable` if you want to retry.')

        # finally:
            # await context.message.author.send(msg.content)

        return

    @giveaway.command(name="abort", aliases=["abrt", "abor"])
    async def giveaway_abort(self, context):
        """
        Ends your giveaway without drawing a winner. Also removing the tweet about it.
        **Usage:** !giveaway abort message_id
        """
        async with context.typing():

            # Parse arguments (sends embeds if errors)
            # Fast, as it's mostly string manipulation
            try:
                self.logger.info(
                    f"Getting args for !giveaway abort: {context.message.content} by {context.message.author.display_name}")
                args = await helpers.giveaway_helpers.parse_commands_arguments(context, self.bot.emojis, helpers.giveaway_helpers.CommandTypes.ABORT, context.message.content)
            except Exception as e:
                self.logger.error(f"Missing parameter(s) in !giveaway create")
                return

            # Get the giveaway object
            self.logger.info(f"Getting giveaway embed to abort it")
            giveaway_object = helpers.giveaway_database_helpers.get_giveaway_by_message_id(
                args["message_id"])
            if giveaway_object is None:
                self.logger.error(f"Giveaway not found in DB!")
                await helpers.giveaway_helpers.error_cannot_find_giveaway_in_database(context)
                return

            # Check if the user has the rights to do that
            if not helpers.giveaway_helpers.is_user_author_or_admin(context, giveaway_object["author"]):
                self.logger.error(
                    f"User {context.message.author.display_name} doesn't have the rights to abort")
                await helpers.giveaway_helpers.error_user_is_not_authorized(context)
                return

            # Just check if the giveaway is still ongoing, before aborting it
            if giveaway_object["status"] != "ONGOING":
                await helpers.giveaway_helpers.error_giveaway_already_ended(context)
                self.logger.error(
                    f"Giveaway already does not have the ONGOING status")
                return

            # Set it as aborted in database
            helpers.giveaway_database_helpers.change_giveaway_status(
                args["message_id"], "ABORTED")
            self.logger.info(f"Giveaway set as aborted in DB")

            # Remove the tweet
            await helpers.giveaway_twitter_helpers.remove_tweet(giveaway_object["tweet_id"])
            self.logger.info(f"Removed tweet about it")

            # Acknowledgement to the user
            await helpers.giveaway_helpers.send_successfully_aborted_embed(context, giveaway_object["message_url"])
            self.logger.info(
                f"Send notification that the giveaway has been aborted")

        # And lastly, update the original message
        await helpers.giveaway_helpers.update_original_message_when_aborted(context, args["message_id"])
        self.logger.info(f"Updated original giveaway message")
        return

    @giveaway.command(name="end", aliases=["nd"])
    async def giveaway_end(self, context):
        """
        Ends your giveaway, draw a winner!
        **Usage:** !giveaway end message_id
        """
        async with context.typing():

            # Parse arguments (sends embeds if errors)
            # Fast, as it's mostly string manipulation
            try:
                self.logger.info(
                    f"Getting args for !giveaway end: {context.message.content} by {context.message.author.display_name}")
                args = await helpers.giveaway_helpers.parse_commands_arguments(context, self.bot.emojis, helpers.giveaway_helpers.CommandTypes.END, context.message.content)
            except Exception as e:
                self.logger.error(f"Missing parameter(s) in !giveaway end")
                return

            # Get the giveaway object
            self.logger.info(f"Getting the giveaway object from DB")
            giveaway_object = helpers.giveaway_database_helpers.get_giveaway_by_message_id(
                args["message_id"])
            if giveaway_object is None:
                self.logger.error(f"Cannot find giveaway in DB")
                await helpers.giveaway_helpers.error_cannot_find_giveaway_in_database(context)
                return

            # Check if the user has the rights to do that
            if not helpers.giveaway_helpers.is_user_author_or_admin(context, giveaway_object["author"]):
                self.logger.error(
                    f"User does not have rights to end a giveaway")
                await helpers.giveaway_helpers.error_user_is_not_authorized(context)
                return

            # Just check if the giveaway is still ongoing, before aborting it
            if giveaway_object["status"] != "ONGOING":
                self.logger.error(f"Giveaway is already ended")
                await helpers.giveaway_helpers.error_giveaway_already_ended(context)
                return

            # Get a winner
            winner, participants = await helpers.giveaway_helpers.pick_a_winner(context, giveaway_object["message_id"], giveaway_object["author"])
            self.logger.info(
                f"Picked a winner: {winner} from {len(participants)} participants")

            # If command before is sending errors, it also returns None
            if winner is None:
                return

            # Set giveaway as ended in database
            helpers.giveaway_database_helpers.change_giveaway_status(
                args["message_id"], "ENDED")

            # Set winner in database
            helpers.giveaway_database_helpers.change_giveaway_winner(
                args["message_id"], winner, participants)
            self.logger.info(f"Changed status, winner and participants in DB")

            # Notify winner!
            await helpers.giveaway_helpers.send_giveaway_end_embed(context, winner, giveaway_object["author"], len(participants), args["message_id"])

        # Update original message
        await helpers.giveaway_helpers.update_original_message_when_ended(context, args["message_id"], winner)
        self.logger.info(f"Notified winner and updated original message")

        # Update tweet
        await helpers.giveaway_twitter_helpers.update_tweet_giveaway_ended(giveaway_object["tweet_id"])
        self.logger.info(f"Successfully updated the tweet")
        return

    def filter_active(self, a): return a == ""

    @giveaway.command(name="list", aliases=["lst"])
    async def giveaway_list(self, context):
        """
        Lists active giveaways.
        **Usage:** !giveaway list
        """
        async with context.typing():

            # Get all ONGOING giveaways
            ongoing_giveaways = helpers.giveaway_database_helpers.get_ongoing_giveaways()
            self.logger.info(f"Counted {len(ongoing_giveaways)} in DB")

            # Print new list
            message_id = await helpers.giveaway_helpers.send_new_list_embed(context, ongoing_giveaways)

        # Remove old list
        await helpers.giveaway_helpers.remove_old_list_message(context)

        # Save new message id
        helpers.giveaway_database_helpers.set_latest_list_message_id(
            message_id)
        self.logger.info(
            f"Sent a new list embed and removed old one, saved in DB")

        # Restart worker?
        asyncio.get_event_loop().create_task(
            helpers.giveaway_worker.threaded_list_time_left_update(context, message_id))
        self.logger.info(f"Started task about updating time left in list")
        return

    @giveaway.command(name="stats", aliases=["stat", "statistics", "statistic"])
    async def giveaway_stats(self, context):
        """
        General statistics about giveaways.
        **Usage:** !giveaway stats
        """
        # Check if it's for a specific user
        user_mentioned_list = context.message.mentions
        message_id = 0
        async with context.typing():

            if len(user_mentioned_list) > 0:
                self.logger.info(
                    f"Starting stats for user {user_mentioned_list[0].display_name}")
                selected_giveaways = giveaway_database_helpers.get_not_ongoing_giveaways()
                stats_results = giveaway_helpers.format_user_stats(
                    selected_giveaways, user_mentioned_list[0].id)
                await giveaway_helpers.print_user_stats_results(context, stats_results, user_mentioned_list[0])
            else:
                self.logger.info(f"Starting general stats")
                selected_giveaways = giveaway_database_helpers.get_not_ongoing_giveaways()
                stats_results = giveaway_helpers.format_general_stats(
                    selected_giveaways)
                message_id = await giveaway_helpers.print_stats_results(context, stats_results)

        if len(user_mentioned_list) < 0:
            # Remove old list
            self.logger.info(f"Removing old stats message")
            await helpers.giveaway_helpers.remove_old_stats_message(context)

            # Save new message id
            self.logger.info(f"Saving new stats message id")
            helpers.giveaway_database_helpers.set_latest_stats_message_id(
                message_id)

        return

    @giveaway.command(name="reroll", aliases=["redraw", "rerol"])
    async def giveaway_reroll(self, context):
        """
        Rerolls a giveaway.
        **Usage:** !giveaway reroll message_id
        """
        async with context.typing():

            # Parse arguments (sends embeds if errors)
            # Fast, as it's mostly string manipulation
            try:
                self.logger.info(
                    f"Getting args for !giveaway reroll: {context.message.content} by {context.message.author.display_name}")
                args = await helpers.giveaway_helpers.parse_commands_arguments(context, self.bot.emojis, helpers.giveaway_helpers.CommandTypes.REROLL, context.message.content)
            except Exception as e:
                self.logger.error(f"Missing parameter(s) in !giveaway reroll")
                return

            # Get the giveaway object
            giveaway_object = helpers.giveaway_database_helpers.get_giveaway_by_message_id(
                args["message_id"])
            self.logger.info(f"Got the giveaway object")
            if giveaway_object is None:
                self.logger.error(f"Haven't found the giveaway in database")
                await helpers.giveaway_helpers.error_cannot_find_giveaway_in_database(context)
                return

            # Check if the user has the rights to do that
            if not helpers.giveaway_helpers.is_user_author_or_admin(context, giveaway_object["author"]):
                self.logger.error(
                    f"User does not have rights to reroll giveaway")
                await helpers.giveaway_helpers.error_user_is_not_authorized(context)
                return

            # Just check if the giveaway is already ended, just to keep the database integrity correct
            if giveaway_object["status"] != "ENDED":
                self.logger.error(f"Giveaway should have been ended first")
                await helpers.giveaway_helpers.error_giveaway_not_yet_ended(context, args["message_id"])
                return

            # No need to pick_a_winner, just taking the giveaway_object["participants"] and make a random.choice on it it enough
            users_were_in = giveaway_object["participants"]
            try:
                with open("config.yaml") as file:
                    config = yaml.load(file, Loader=yaml.FullLoader)
                if config["environment"] != "Dev":
                    users_were_in.remove(giveaway_object["winner"])
            except Exception:
                pass
            finally:
                next_winner = random.choice(users_were_in)
                self.logger.info(f"Chosen next winner: {next_winner}")

            # Notify second winner
            await helpers.giveaway_helpers.send_giveaway_reroll_embed(context, next_winner, giveaway_object["author"], len(users_were_in), args["message_id"])
            self.logger.info(f"Notified users")

        # Save it in DB
        helpers.giveaway_database_helpers.append_giveaway_reroll(
            args["message_id"], next_winner)
        self.logger.info(f"Saved reroll event in DB")

        # No update on twitter this time, no need to spam
        # But update the original giveaway message / embed
        await helpers.giveaway_helpers.update_original_message_when_rerolled(context, args["message_id"], next_winner)
        self.logger.info(f"Updated original embedded message")
        return

    @giveaway.command(name="win")
    async def giveaway_win(self, context):
        """
        Win a giveaway!.
        **Usage:** !giveaway win
        """
        possibilities = [
            "Haha no way you can do that! <:pepecannabis:720807661469171743>",
            "Hm no it is not worth it...<:pepeohno:754892181709520906>",
            "You really thought that would work? <:smughonk:665037775481077770>",
            "That command is taboo... <:pepealpha:570230833198399489>",
            "Try again when I finished my smoke break <:pepestoner:720807661745995877>",
            "Herbert said no! <:koalasad:755306633973727323>",
            "Sorry gaissa is already registered as future winner <:pepeultrasad:743232149632712805>",
            "<:hidethepain:720807661918093402>"
        ]
        await context.message.reply(f"{random.choice(possibilities)}")
        self.logging.info("Sent a funny answer to !giveaway win")
        return

    # Add listener for reactions, so the bot updates the latest !giveaway list message
    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if giveaway_database_helpers.is_giveaway_message(payload.message_id):
            ongoing_giveaways = helpers.giveaway_database_helpers.get_ongoing_giveaways()
            list_message_id = helpers.giveaway_database_helpers.get_latest_list_message_id()[
                0]["message_id"]
            channel = await self.bot.fetch_channel(payload.channel_id)
            giveaway_context_message = await channel.fetch_message(payload.message_id)
            context = await self.bot.get_context(giveaway_context_message)
            self.logger.info(
                f"User has added a reaction to the giveaway {giveaway_context_message}")
            await helpers.giveaway_helpers.update_time_left_on_list_message(context, list_message_id, ongoing_giveaways)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        if giveaway_database_helpers.is_giveaway_message(payload.message_id):
            ongoing_giveaways = helpers.giveaway_database_helpers.get_ongoing_giveaways()
            list_message_id = helpers.giveaway_database_helpers.get_latest_list_message_id()[
                0]["message_id"]
            channel = await self.bot.fetch_channel(payload.channel_id)
            giveaway_context_message = await channel.fetch_message(payload.message_id)
            context = await self.bot.get_context(giveaway_context_message)
            self.logger.info(
                f"User has removed a reaction to the giveaway {giveaway_context_message}")
            await helpers.giveaway_helpers.update_time_left_on_list_message(context, list_message_id, ongoing_giveaways)

# And then we finally add the cog to the bot so that it can load, unload, reload and use it's content.


def setup(bot):
    bot.add_cog(giveaway(bot))
