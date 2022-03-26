import asyncio
from datetime import datetime
import discord
import yaml
from discord.ext import commands
from tinydb import TinyDB
import logging

import helpers

# Load giveaway database
giveaway_db = TinyDB('DB/giveaways.json')

class owner(commands.Cog, name="Owner"):
    """
    Commands reserved for owners, mostly management
    """
    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger("GiveawayLogger")

    @commands.command(name="shutdown")
    async def shutdown(self, context):
        """
        Make the bot shutdown
        """
        with open("config.yaml") as file:
            config = yaml.load(file, Loader=yaml.FullLoader)
        if context.message.author.id in config["owners"]:
            embed = discord.Embed(
                description="Shutting down. Bye! :wave:"
            )
            await context.send(embed=embed)
            await self.bot.logout()
            await self.bot.close()
        else:
            embed = discord.Embed(
                title="Error!",
                description="You don't have the permission to use this command.",
            )
            await context.send(embed=embed)

    @commands.command(name="startup")
    async def startup(self, context):
        """
        Make the bot start threads
        """
        with open("config.yaml") as file:
            config = yaml.load(file, Loader=yaml.FullLoader)
        if context.message.author.id in config["owners"]:
            
            ongoing_giveaways = helpers.giveaway_database_helpers.get_ongoing_giveaways()
    
            #One for the list (if list message exists)
            list_message_id = helpers.giveaway_database_helpers.get_latest_list_message_id()
            asyncio.get_event_loop().create_task(
                    helpers.giveaway_worker.threaded_list_time_left_update(context, list_message_id))
            self.logger.info(f"Started task about updating time left in list")

            for giveaway in ongoing_giveaways:
                end_time = datetime.strptime(giveaway["end_time"], "%Y-%m-%d %H:%M:%S.%f")
                asyncio.get_event_loop().create_task(helpers.giveaway_worker.threaded_time_left_update(self,
                                                                                            context, giveaway["message_id"], giveaway["message_url"], end_time, giveaway["author"]))
                self.logger.info(f"Started task giveaway {giveaway['flower_identifier']}")
#2022-03-27 20:40:01.167703
        else:
            embed = discord.Embed(
                title="Error!",
                description="You don't have the permission to use this command.",
            )
            await context.send(embed=embed)

    @commands.command(name="say", aliases=["echo"])
    async def say(self, context, *, args):
        """
        The bot will say anything you want.
        """
        with open("config.yaml") as file:
            config = yaml.load(file, Loader=yaml.FullLoader)
        if context.message.author.id in config["owners"]:
            await context.send(args)
        else:
            embed = discord.Embed(
                title="Error!",
                description="You don't have the permission to use this command."
            )
            await context.send(embed=embed)

    @commands.command(name="embed")
    async def embed(self, context, *, args):
        """
        The bot will say anything you want, but within embeds.
        """
        with open("config.yaml") as file:
            config = yaml.load(file, Loader=yaml.FullLoader)
        if context.message.author.id in config["owners"]:
            embed = discord.Embed(
                description=args
            )
            await context.send(embed=embed)
        else:
            embed = discord.Embed(
                title="Error!",
                description="You don't have the permission to use this command."
            )
            await context.send(embed=embed)

    @commands.command(name="prefix")
    async def prefix(self, context, *, args):
        """
        Change the server-wide prefix.
        """
        with open("config.yaml") as file:
            config = yaml.load(file, Loader=yaml.FullLoader)
        if context.message.author.id in config["owners"]:
            try:
                prefix = str(args[0])
                config["bot_prefix"] = prefix
                with open('config.yaml', 'w') as f:
                    yaml.dump(config, f)
                self.bot.command_prefix = prefix
                embed = discord.Embed(
                    title="Success!",
                    description=f"Changed prefix to {args}."
                )
                await context.send(embed=embed)
            except Exception as e:
                self.logger.error(e)
                embed = discord.Embed(
                    title="Error!",
                    description=f"An unknown error occurred when trying to change prefix."
                )
                await context.send(embed=embed)
        else:
            embed = discord.Embed(
                title="Error!",
                description="You don't have the permission to use this command."
            )
            await context.send(embed=embed)

    @commands.group(name="purge")
    async def purge(self, context):
        """
        Lets you purge DB.
        """
        with open("config.yaml") as file:
            config = yaml.load(file, Loader=yaml.FullLoader)
        if context.message.author.id in config["owners"]:
            if context.invoked_subcommand is None:
                embed = discord.Embed(
                    description=f"Cannot purge nothing, purge giveaways maybe?"
                )
                await context.send(embed=embed)
        else:
            embed = discord.Embed(
                title="Error!",
                description="You don't have the permission to use this command."
            )
            await context.send(embed=embed)

    @purge.command(name="giveaways", aliases=["giveaway"])
    async def giveaways(self, context):
        """
        Warning, flushes the giveaways database!
        """
        with open("config.yaml") as file:
            config = yaml.load(file, Loader=yaml.FullLoader)
        if context.message.author.id in config["owners"]:
            if len(giveaway_db.all()) > 0:
                try:
                    giveaway_db.truncate()
                    embed = discord.Embed(
                        title="Success!",
                        description="No more giveaways in DB."
                    )
                    await context.send(embed=embed)
                except Exception as e:
                    self.logger.error(e)
                    embed = discord.Embed(
                        title="Error!",
                        description=f"An unknown error occurred when trying to flush giveaways DB."
                    )
                    await context.send(embed=embed)
            else:
                embed = discord.Embed(
                description="Nothing to purge."
                )
                await context.send(embed=embed)
        else:
            embed = discord.Embed(
                title="Error!",
                description="You don't have the permission to use this command."
            )
            await context.send(embed=embed)

    @commands.group(name="blacklist")
    async def blacklist(self, context):
        """
        Lets you add or remove a user from not being able to use the bot.
        """
        with open("config.yaml") as file:
            config = yaml.load(file, Loader=yaml.FullLoader)
        if context.invoked_subcommand is None:
            embed = discord.Embed(
                title=f"There are currently {len(config['blacklist'])} blacklisted IDs"
            )
            await context.send(embed=embed)

    @blacklist.command(name="add")
    async def blacklist_add(self, context, member: discord.Member):
        """
        Lets you prevent someone from using the bot.
        """
        with open("config.yaml") as file:
            config = yaml.load(file, Loader=yaml.FullLoader)
        if not member:
            embed = discord.Embed(
                    title="Error!",
                    description=f"Missing argument."
                )
            await context.send(embed=embed)
        if context.message.author.id in config["owners"]:
            userID = member.id
            try:
                if userID in config["blacklist"]:
                    embed = discord.Embed(
                        title="Error!",
                        description=f"User already blacklisted."
                    )
                    await context.send(embed=embed)
                    return
                config["blacklist"].append(userID)
                with open("config.yaml", "w") as file:
                    yaml.dump(config, file, sort_keys=True)
                embed = discord.Embed(
                    title="User Blacklisted",
                    description=f"**{member.name}** has been successfully added to the blacklist"
                )
                embed.set_footer(
                    text=f"There are now {len(config['blacklist'])} users in the blacklist"
                )
                await context.send(embed=embed)
            except Exception as e:
                self.logger.error(e)
                embed = discord.Embed(
                    title="Error!",
                    description=f"An unknown error occurred when trying to add **{member.name}** to the blacklist."
                )
                await context.send(embed=embed)
        else:
            embed = discord.Embed(
                title="Error!",
                description="You don't have the permission to use this command."
            )
            await context.send(embed=embed)

    @blacklist.command(name="remove")
    async def blacklist_remove(self, context, member: discord.Member):
        """
        Lets you remove a user from not being able to use the bot.
        """
        with open("config.yaml") as file:
            config = yaml.load(file, Loader=yaml.FullLoader)
        if not member:
            embed = discord.Embed(
                    title="Error!",
                    description=f"Missing argument."
                )
            await context.send(embed=embed)
        if context.message.author.id in config["owners"]:
            userID = member.id
            try:
                if not userID in config["blacklist"]:
                    embed = discord.Embed(
                        title="Error!",
                        description=f"User is not blacklisted."
                    )
                    await context.send(embed=embed)
                    return
                config["blacklist"].remove(userID)
                with open("config.yaml", "w") as file:
                    yaml.dump(config, file, sort_keys=True)
                embed = discord.Embed(
                    title="User Unblacklisted",
                    description=f"**{member.name}** has been successfully removed from the blacklist"
                )
                embed.set_footer(
                    text=f"There are now {len(config['blacklist'])} users in the blacklist"
                )
                await context.send(embed=embed)
            except Exception as e:
                self.logger.error(e)
                embed = discord.Embed(
                    title="Error!",
                    description=f"An unknown error occurred when trying to remove **{member.name}** from the blacklist."
                )
                await context.send(embed=embed)
        else:
            embed = discord.Embed(
                title="Error!",
                description="You don't have the permission to use this command."
            )
            await context.send(embed=embed)

    @commands.group(name="owner")
    async def owner(self, context):
        """
        Lets you add or remove a user from not being able to use the bot.
        """
        if context.invoked_subcommand is None:
            with open("config.yaml") as file:
                config = yaml.load(file, Loader=yaml.FullLoader)
            embed = discord.Embed(
                title=f"There are currently {len(config['owners'])} owners",
                description=f""
            )
            await context.send(embed=embed)

    @owner.command(name="add")
    async def owner_add(self, context, member: discord.Member):
        """
        Lets you add someone as owner of the bot.
        """
        if not member:
            embed = discord.Embed(
                    title="Error!",
                    description=f"Missing argument."
                )
            await context.send(embed=embed)
            return
        with open("config.yaml") as file:
            config = yaml.load(file, Loader=yaml.FullLoader)
        if context.message.author.id in config["owners"]:
            userID = member.id
            try:
                if userID in config["owners"]:
                    embed = discord.Embed(
                        title="Error!",
                        description=f"User already owner."
                    )
                    await context.send(embed=embed)
                    return
                config["owners"].append(userID)
                with open("config.yaml", "w") as file:
                    yaml.dump(config, file, sort_keys=True)
                embed = discord.Embed(
                    title="User promoted",
                    description=f"**{member.name}** has been successfully added to the owners"
                )
                embed.set_footer(
                    text=f"There are now {len(config['owners'])} owners"
                )
                await context.send(embed=embed)
                return
            except Exception as e:
                self.logger.error(e)
                embed = discord.Embed(
                    title="Error!",
                    description=f"An unknown error occurred when trying to add **{member.name}** to the owners list."
                )
                await context.send(embed=embed)
                return
        else:
            embed = discord.Embed(
                title="Error!",
                description="You don't have the permission to use this command."
            )
            await context.send(embed=embed)
            return

    @owner.command(name="remove")
    async def owner_remove(self, context, member: discord.Member):
        """
        Lets you remove a user from not being able to use the bot.
        """
        if not member:
            embed = discord.Embed(
                    title="Error!",
                    description=f"Missing argument."
                )
            await context.send(embed=embed)
        with open("config.yaml") as file:
            config = yaml.load(file, Loader=yaml.FullLoader)
        if context.message.author.id in config["owners"]:
            userID = member.id
            try:
                if userID not in config["owners"]:
                    embed = discord.Embed(
                        title="Error!",
                        description=f"User not owner."
                    )
                    await context.send(embed=embed)
                    return
                config["owners"].remove(userID)
                with open("config.yaml", "w") as file:
                    yaml.dump(config, file, sort_keys=True)
                embed = discord.Embed(
                    title="User demoted",
                    description=f"**{member.name}** has been successfully removed from the owners list"
                )
                embed.set_footer(
                    text=f"There are now {len(config['owners'])} owners"
                )
                await context.send(embed=embed)
            except Exception as e:
                self.logger.error(e)
                embed = discord.Embed(
                    title="Error!",
                    description=f"An unknown error occurred when trying to remove **{member.name}** from the owner list."
                )
                await context.send(embed=embed)
        else:
            embed = discord.Embed(
                title="Error!",
                description="You don't have the permission to use this command."
            )
            await context.send(embed=embed)

def setup(bot):
    bot.add_cog(owner(bot))