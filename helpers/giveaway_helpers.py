import asyncio
from enum import Enum
from helpers import giveaway_database_helpers
import os
import sys
import discord
import re
import requests
import nums_from_string
from datetime import datetime, timedelta
from dateutil.parser import parse
import humanize
import yaml
import random
import logging

from . import giveaway_emojis_helpers

class CommandTypes(Enum):
    CREATE = 1
    END = 2
    ABORT = 3
    REROLL = 4
    STATS = 5

async def parse_commands_arguments(context, bot, type: CommandTypes, args):
    if(type == CommandTypes.CREATE):
        return await parse_arguments_create(context, bot, args)
    elif(type == CommandTypes.END):
        return await parse_arguments_end(context, args)
    elif(type == CommandTypes.ABORT):
        return await parse_arguments_abort(context, args)
    elif(type == CommandTypes.REROLL):
        return await parse_arguments_reroll(context, args)

async def send_error_embed(context, title, description):
        embed = discord.Embed(
                    title=title,
                    description=description,
                )
        await context.send(embed=embed)

async def send_new_giveaway_embed(context, author, flower_identifier, flower_rarity, flower_image_url, reaction, end_time, tweet_url):
    displayable_end_time = time_left_beautifier(end_time)
    author_obj = await context.bot.fetch_user(author)
    embed = discord.Embed(title="New giveaway!")
    embed.add_field(name='Author', value=author_obj.mention, inline=False)
    embed.add_field(name='FLOWER', value=f"[{flower_identifier}](https://flowerpatch.app/card/{flower_identifier})", inline=False)
    embed.add_field(name='Reaction', value=reaction, inline=False)
    embed.add_field(name='Time left', value=displayable_end_time, inline=False)
    if len(tweet_url) > 0:
        embed.add_field(name='Twitter link', value=f"[click me]({tweet_url})", inline=False)
    else:
        embed.add_field(name='Twitter link', value="*No link yet...*", inline=False)
    embed.set_image(url=flower_image_url)
    embed.color = get_rarity_color(flower_rarity)
    embed_result = await context.send(embed=embed)
    return embed_result.id, embed_result.jump_url

async def send_giveaway_end_embed(context, winner, author, participants_count, message_id):
    giveaway_original_embed = await context.fetch_message(message_id)
    embed = discord.Embed(title="Giveaway ended!", url=f"{giveaway_original_embed.jump_url}")
    winner_obj = await context.bot.fetch_user(winner)
    embed.add_field(name=':drum: Winner is... :drum: ', value=f"{winner_obj.mention}!", inline=False)
    embed.set_footer(text=f'{participants_count} users were participating in this giveaway')
    result = await context.send(embed=embed)
    await notify_giveaway_end_winner_author(context, result.id, author, winner)
    return

async def notify_giveaway_end_winner_author(context, message_id, author, winner):
    giveaway_end_embed = await context.fetch_message(message_id)
    author_obj = await context.bot.fetch_user(author)
    winner_obj = await context.bot.fetch_user(winner)
    text_message = f"*Notifying {winner_obj.mention}: you should send your ethereum address to {author_obj.mention} to receive the FLOWER.*"
    await giveaway_end_embed.reply(text_message)
    return

async def send_giveaway_reroll_embed(context, next_winner, author, participants_count, message_id):
    giveaway_original_embed = await context.fetch_message(message_id)
    embed = discord.Embed(title="Giveaway rerolled!", url=f"{giveaway_original_embed.jump_url}")
    winner_obj = await context.bot.fetch_user(next_winner)
    embed.add_field(name=':drum: New winner is... :drum: ', value=f"{winner_obj.mention}!", inline=False)
    embed.set_footer(text=f'{participants_count} users were participating in this giveaway')
    result = await context.send(embed=embed)
    await notify_giveaway_end_winner_author(context, result.id, author, next_winner)
    return

async def send_new_list_embed(context, ongoing_giveaways):
    start = datetime.utcnow()
    embed = discord.Embed(title="Here is a list of ongoing giveaways:")

    results = await asyncio.gather(*[get_giveaway_embed(context, giveaway) for giveaway in ongoing_giveaways])

    for f in results:
        embed.add_field(name=f[0], value=f[1], inline=False)

    end = datetime.utcnow()
    embed.set_footer(text=f"Time to create this message: {round((end - start).total_seconds(), 2)}s.")

    message = await context.send(embed=embed)
    return message.id

async def get_giveaway_embed(context, giveaway):
    displayable_end_time = time_left_beautifier(parse(giveaway["end_time"]))

    results = await asyncio.gather(context.fetch_message(giveaway["message_id"]), context.bot.fetch_user(giveaway["author"]))
    
    giveaway_embed = results[0]
    author = results[1]
    users_list = await giveaway_embed.reactions[0].users().flatten()

    with open("config.yaml") as file:
        config = yaml.load(file, Loader=yaml.FullLoader)
    if config["environment"] != "Dev":
        filtered_list = [x for x in users_list if not determine_bot_or_author(x, giveaway["author"])]
    else:
        filtered_list = users_list

    return f'{displayable_end_time}', \
            f'**By** {author.mention} \n\
            [{giveaway["flower_identifier"]}]({giveaway["message_url"]})\n\
            {len(filtered_list)} User(s) participating!'

async def send_successfully_aborted_embed(context, giveaway_url):
    embed = discord.Embed()
    embed.add_field(name=f"A giveaway has been aborted...", value=f"I successfully aborted [the giveaway]({giveaway_url}) and removed the tweet about it.", inline=False)
    await context.send(embed=embed)
    return

def format_general_stats(giveaways):
    giveaways_result = {
        "count": 0,
        "total_rarity": 0,
        "count_rerolled": 0,
        "count_aborted": 0,
        "winners": {},
        "authors": {},
        "emojis": {}
    }

    for giveaway in giveaways:
        giveaways_result["count"] = giveaways_result["count"] + 1
        giveaways_result["total_rarity"] = giveaways_result["total_rarity"] + giveaway["flower_rarity"]
        if giveaways_result["winners"].get(giveaway["winner"]) and len(giveaway["rerolls"]) == 0:
            giveaways_result["winners"][giveaway["winner"]] = giveaways_result["winners"][giveaway["winner"]] + 1
        else:
            if len(giveaway["rerolls"]) == 0:
                giveaways_result["winners"][giveaway["winner"]] = 1

        if giveaways_result["authors"].get(giveaway["author"]):
            giveaways_result["authors"][giveaway["author"]] = giveaways_result["authors"][giveaway["author"]] + 1
        else:
            giveaways_result["authors"][giveaway["author"]] = 1
        
        if giveaways_result["emojis"].get(giveaway["reaction"]):
            giveaways_result["emojis"][giveaway["reaction"]] = giveaways_result["emojis"][giveaway["reaction"]] + 1
        else:
            giveaways_result["emojis"][giveaway["reaction"]] = 1

        if len(giveaway["rerolls"]) > 0:
            giveaways_result["count_rerolled"] += 1
            if giveaways_result["winners"].get(giveaway["rerolls"][-1]["winner"]):
                giveaways_result["winners"][giveaway["rerolls"][-1]["winner"]] = giveaways_result["winners"][giveaway["rerolls"][-1]["winner"]] + 1
            else:
                giveaways_result["winners"][giveaway["rerolls"][-1]["winner"]] = 1
        if giveaway["status"] == "ABORTED":
            giveaways_result["count_aborted"] += 1

    sorted_winners = dict(sorted(giveaways_result["winners"].items(), key=lambda item: item[1], reverse=True))
    sorted_authors = dict(sorted(giveaways_result["authors"].items(), key=lambda item: item[1], reverse=True))
    sorted_emojis = dict(sorted(giveaways_result["emojis"].items(), key=lambda item: item[1], reverse=True))

    return {"winners": sorted_winners, "authors": sorted_authors, "emojis": sorted_emojis, "total": giveaways_result["count"], "total_rarity": giveaways_result["total_rarity"], "count_aborted": giveaways_result["count_aborted"], "count_rerolled": giveaways_result["count_rerolled"]}

def format_user_stats(giveaways, user_id):
    stats_result = {
        "participation_count": 0,
        "winning_count": 0,
        "winning_rarity_count": 0,
        "giving_count": 0,
        "giving_rarity_count": 0,
        "emojis": {}
    }

    for giveaway in giveaways:

        #Tricky one: if user_id is the winner and there is no reroll, add
        # or (second line) if there is rerolls, take the last one and if our user is the winner, add
        if (len(giveaway["rerolls"]) == 0 and giveaway["winner"] == user_id) \
            or (len(giveaway["rerolls"]) > 0 and giveaway["rerolls"][-1]["winner"] == user_id):
            stats_result["winning_count"] += 1
            stats_result["winning_rarity_count"] += giveaway["flower_rarity"]

        if giveaway["author"] == user_id:
            stats_result["giving_count"] += 1
            stats_result["giving_rarity_count"] += giveaway["flower_rarity"]
            if stats_result["emojis"].get(giveaway["reaction"]):
                stats_result["emojis"][giveaway["reaction"]] += 1
            else:
                stats_result["emojis"][giveaway["reaction"]] = 1

        if user_id in giveaway["participants"]:
            stats_result["participation_count"] += 1

    stats_result["emojis"] = dict(sorted(stats_result["emojis"].items(), key=lambda item: item[1], reverse=True))

    return stats_result

async def print_user_stats_results(context, stats_results, user):
    embed = discord.Embed()
    emojis_text = get_user_emojis_text(stats_results["emojis"])

    embed.add_field(name=f"{user.display_name} has started **{stats_results['giving_count']}** giveaways", value=f"That is a total of **{stats_results['giving_rarity_count']} rarity** given away!\n{emojis_text}", inline=False)
    embed.add_field(name=f"{user.display_name} has participated in **{stats_results['participation_count']}** giveaways", value=f"Winning **{stats_results['winning_count']} of them!**\nFor a total of **{stats_results['winning_rarity_count']} rarity** won", inline=False)

    await context.send(embed=embed)
    return

async def print_stats_results(context, stats_results):
    embed = discord.Embed()
    embed.add_field(name="Informations", value=f"A total of **{stats_results['total']} giveaways** have been made so far\nThat is **{stats_results['total_rarity']} rarity** given away\n **{stats_results['count_aborted']}** have been aborted, and **{stats_results['count_rerolled']}** have been rerolled")
    winners_text = await get_winners_text(context, stats_results["winners"])
    authors_text = await get_authors_text(context, stats_results["authors"])
    emojis_text = get_emojis_text(stats_results["emojis"])
    embed.add_field(name=f"Winners", value=f"{winners_text}", inline=False)
    embed.add_field(name=f"Authors", value=f"{authors_text}", inline=False)
    embed.add_field(name=f"Emojis", value=f"{emojis_text}", inline=False)
    message = await context.send(embed=embed)
    return message.id

async def get_winners_text(context, winners):
    winners_text = ""
    counter = 0
    for winner, winning_count in winners.items():
        if counter < 5:
            try:
                winner_obj = await context.bot.fetch_user(winner)
                winners_text += f"{winner_obj.mention} has won {winning_count} times\n"
                counter += 1
            except:
                pass
    return winners_text

async def get_authors_text(context, authors):
    authors_text = ""
    counter = 0
    for author, authored_count in authors.items():
        if counter < 5:
            try:
                author_obj = await context.bot.fetch_user(author)
                authors_text += f"{author_obj.mention} has created {authored_count} giveaways\n"
                counter += 1
            except:
                pass
    return authors_text

def get_emojis_text(emojis):
    emojis_text = ""
    counter = 0
    for emoji, emoji_count in emojis.items():
        if counter < 5:
            emojis_text += f"{emoji} has been used {emoji_count} times\n"
            counter += 1
    return emojis_text

def get_user_emojis_text(emojis):
    emojis_text = ""
    counter = 0
    for emoji, emoji_count in emojis.items():
        if counter < 3:
            emojis_text += f"Used {emoji} {emoji_count} times\n"
            counter += 1
    return emojis_text

async def notify_user_giveaway_end(context, message_id, message_url, author):
    author_obj = await context.bot.fetch_user(author)
    embed = discord.Embed()
    embed.add_field(name=f"A giveaway should end soon...", value=f"Hey {author_obj.mention}, [your giveaway]({message_url}) should end now!\nUse: !giveaway end {message_id}", inline=False)
    embed_result = await context.send(embed=embed)
    return embed_result.id

async def notify_user_giveaway_end_as_text(context, message_id, author):
    author_obj = await context.bot.fetch_user(author)
    giveaway_end_embed = await context.fetch_message(message_id)
    text_message = f"*Notifying* {author_obj.mention}"
    await giveaway_end_embed.reply(text_message)
    return

async def add_twitter_link_to_embed(context, message_id, tweet_url):
    old_embed = await context.fetch_message(message_id)
    if len(tweet_url) == 0:
        tweet_url = "*Failed to tweet*"
    old_embed.embeds[0].set_field_at(4, name="Twitter link", value=f"{tweet_url}", inline=False)
    await old_embed.edit(embed = old_embed.embeds[0])
    return

def time_left_beautifier(end_time):
    if datetime.utcnow() > end_time:
        return f"Should have ended {humanize.naturaltime(datetime.utcnow() - end_time)}"
    else:
        return f"Ends in {humanize.naturaltime(datetime.utcnow() - end_time)}"

def is_end_time_met(end_time):
    if datetime.utcnow() > end_time:
        return True
    else:
        return False

async def remove_old_list_message(context):
    try:
        message_id = giveaway_database_helpers.get_latest_list_message_id()
        if len(message_id) == 0:
            return True
        old_embed = await context.fetch_message(message_id[0]["message_id"])
        await old_embed.delete()
        return True
    except Exception:
        await error_cannot_remove_last_embed(context)
        return False

async def remove_old_stats_message(context):
    try:
        message_id = giveaway_database_helpers.get_latest_stats_message_id()
        if len(message_id) == 0:
            return True
        old_embed = await context.fetch_message(message_id[0]["message_id"])
        await old_embed.delete()
        return True
    except Exception:
        await error_cannot_remove_last_embed(context)
        return False

def get_rarity_color(flower_rarity):
    if flower_rarity <= 19:
        return 0xA0A0A0
    elif flower_rarity >= 20 and flower_rarity <= 39:
        return 0x67C171
    elif flower_rarity >= 40 and flower_rarity <= 59:
        return 0x1999CF
    elif flower_rarity >= 60 and flower_rarity <= 79:
        return 0xFF72D0
    elif flower_rarity >= 80:
        return 0xFFBE44

def is_user_author_or_admin(context, giveaway_author):
    with open("config.yaml") as file:
        config = yaml.load(file, Loader=yaml.FullLoader)
    if giveaway_author == context.message.author.id:
        return True
    elif context.message.author.id in config["owners"]:
        return True
    return False

async def update_original_message_when_aborted(context, message_id):
    old_embed = await context.fetch_message(message_id)
    old_embed.embeds[0].set_field_at(3, name="Ends in", value=f"*Aborted*", inline=False)
    old_embed.embeds[0].set_field_at(4, name="Twitter link", value=f"*Removed*", inline=False)
    await old_embed.edit(embed = old_embed.embeds[0])
    return

async def update_original_message_when_ended(context, message_id, winner):
    old_embed = await context.fetch_message(message_id)
    winner_obj = await context.bot.fetch_user(winner)
    old_embed.embeds[0].set_field_at(3, name="Ends in", value=f"*Ended*", inline=False)
    old_embed.embeds[0].add_field(name="Winner", value=f"{winner_obj.mention}", inline=False)
    await old_embed.edit(embed = old_embed.embeds[0])
    return

async def update_original_message_when_rerolled(context, message_id, next_winner):
    old_embed = await context.fetch_message(message_id)
    winner_obj = await context.bot.fetch_user(next_winner)
    old_embed.embeds[0].set_field_at(3, name="Ends in", value=f"*Rerolled*", inline=False)
    old_embed.embeds[0].set_field_at(5, name="Winner", value=f"{winner_obj.mention}", inline=False)
    await old_embed.edit(embed = old_embed.embeds[0])
    return

async def update_time_left_on_message(context, message_id, end_time):
    old_embed = await context.fetch_message(message_id)
    displayable_end_time = time_left_beautifier(end_time)
    old_embed.embeds[0].set_field_at(3, name="Time left", value=f"{displayable_end_time}", inline=False)
    await old_embed.edit(embed = old_embed.embeds[0])
    return

async def update_time_left_on_list_message(context, message_id, ongoing_giveaways):
    old_embed = await context.fetch_message(message_id)

    results = await asyncio.gather(*[get_giveaway_embed(context, giveaway) for giveaway in ongoing_giveaways])
    if old_embed != 0:
        if len(old_embed.embeds[0].fields) != len(ongoing_giveaways):
            old_embed.embeds[0].clear_fields()
            for f in results:
                old_embed.embeds[0].add_field(name=f[0], value=f[1], inline=False)
        else:
            field_iterator = 0
            for f in results:
                old_embed.embeds[0].set_field_at(field_iterator, name=f"{f[0]}", value=f"{f[1]}", inline=False)
                field_iterator += 1
        await old_embed.edit(embed = old_embed.embeds[0])

    return

async def react_to_message(context, message_id, reaction):
    embedded_message = await context.fetch_message(message_id)
    await embedded_message.add_reaction(emoji=reaction)
    return

async def error_arguments_create(context):
    await send_error_embed(context, "There is a problem with your command", f"**Usage:** !giveaway create network-id timedelta emoji\n \
                **network-id** is the ID and network of the FLOWER. Example: poly-1337 or eth-7331.\n \
                **timedelta** is in how much time the giveaway ends, in minutes, hours or days.\nExamples: 30m, 6h, 5d.\n \
                **emoji** is the emoji that people will use to participate.")
    return

async def error_arguments_abort(context):
    await send_error_embed(context, "There is a problem with your command", f"**Usage:** !giveaway abort message_id/message_url\n \
                **message_id/message_url** is the discord message ID, or message URL, pointing to the giveaway message.")
    return

async def error_invalid_flower_identifier(context):
    await send_error_embed(context, "There is a problem with your command", "I cannot understand which FLOWER you are giving away.\n \
                **network-id** is the ID and network of the FLOWER. Example: poly-1337 or eth-7331.\n \
                Try again!")
    return

async def error_invalid_flower_url_image(context):
    await send_error_embed(context, "There is a problem with your command", "I cannot find the image related to the FLOWER.\n \
                **network-id** is the ID and network of the FLOWER. Example: poly-1337 or eth-7331.\n \
                Try again!")
    return

async def error_invalid_end_time(context):
    await send_error_embed(context, "There is a problem with your command", "I cannot understand when should the giveaway end.\n \
                **timedelta** is in how much time the giveaway ends, in minutes, hours or days.\nExamples: 30m, 6h, 5d.\n \
                Try again!")
    return

async def error_invalid_emoji(context):
    await send_error_embed(context, "There is a problem with your command", "I cannot understand the emoji you are trying to use.\n \
                **emoji** is the emoji that people will use to participate.\n \
                *Note: emojis from other servers won't work* \n \
                Try again!")
    return

async def error_invalid_message_id(context):
    await send_error_embed(context, "There is a problem with your command", "I cannot parse the message ID or url.\n \
                **message_id/message_url** is the message ID or link you can get when you hover a message.\n \
                *Note: it must be the message I sent about the giveaway*")
    return

async def error_cannot_find_giveaway_in_database(context):
    await send_error_embed(context, "There is a problem with your command", "I cannot find the giveaway in database.\n \
                The message ID or URL you provided seems wrong.\n")
    return

async def error_giveaway_already_ended(context):
    await send_error_embed(context, "There is a problem with your command", "Your giveaway looks already ended and already has a winner.")
    return

async def error_giveaway_not_yet_ended(context, message_id):
    await send_error_embed(context, "There is a problem with your command", f"Your giveaway is not yet ended, please end it first.\n*Use:!giveaway end {message_id}")
    return

async def error_user_is_not_authorized(context):
    await send_error_embed(context, "There is a problem with your command", "You are not authorized to do this.")
    return

async def error_noone_entered(context):
    await send_error_embed(context, "There is a problem with your command", "It looks like no-one reacted to the original message.")
    return

async def error_cannot_remove_last_embed(context):
    await send_error_embed(context, "There is a problem with your command", "I cannot remove the last message.")
    return

def check_valid_flower_identifier(arg):
    flower_identifier = str(arg)
    pattern = re.compile(r"(poly|eth)(-)(\d*)")
    if not re.fullmatch(pattern, flower_identifier):
        return False
    return True

def get_flower_image_url(flower_identifier):
    if flower_identifier.startswith("poly"):
        flower_id = str(nums_from_string.get_nums(flower_identifier)[0])
        if flower_id[0] == '-':
            flower_id = flower_id[1:]
        flower_url = f"https://flowerpatch.app/polygon/render/card-{flower_id}.png"
    elif flower_identifier.startswith("eth"):
        #TODO: Change url of ethereum images when this is fixed, should be /ethereum/render/card-xxx
        flower_id = str(nums_from_string.get_nums(flower_identifier)[0])
        if flower_id[0] == '-':
            flower_id = flower_id[1:]
        flower_url = f"https://flowerpatch.app/render/card-{flower_id}.png"
    else:
        return None
    return flower_url

def get_flower_data_url(flower_identifier):
    if flower_identifier.startswith("poly"):
        flower_id = str(nums_from_string.get_nums(flower_identifier)[0])
        if flower_id[0] == '-':
            flower_id = flower_id[1:]
        flower_data_url = f"https://flowerpatch.app/polygon/data/flower-{flower_id}.opensea.json"
    elif flower_identifier.startswith("eth"):
        #TODO: Change url of ethereum images when this is fixed, should be /ethereum/render/card-xxx
        flower_id = str(nums_from_string.get_nums(flower_identifier)[0])
        if flower_id[0] == '-':
            flower_id = flower_id[1:]
        flower_data_url = f"https://flowerpatch.app/data/flower-{flower_id}.opensea.json"
    else:
        return None
    return flower_data_url

def get_end_time(timedelta_input):
    pattern = re.compile(r"\d+[mhd]")
    if re.fullmatch(pattern, str(timedelta_input)):
        time_delta_quantity = int(timedelta_input[:-1])
        time_delta_limiter = str(timedelta_input[len(timedelta_input)-1])
        if time_delta_limiter == 'm':
            end_time = datetime.utcnow() + timedelta(minutes=time_delta_quantity)
        elif time_delta_limiter == 'h':
            end_time = datetime.utcnow() + timedelta(hours=time_delta_quantity)
        elif time_delta_limiter == 'd':
            end_time = datetime.utcnow() + timedelta(days=time_delta_quantity)
        else:
            return None
        return end_time
    else:
        return None

def save_flower_png(flower_url, flower_identifier, bleed):
    if bleed:
        image_stream = requests.get(flower_url + "?bleed=true", stream=True)
        file_name = f"{flower_identifier}_bleeding.png"
    if not bleed:
        image_stream = requests.get(flower_url, stream=True)
        file_name = f"{flower_identifier}.png"
    if image_stream.status_code == 200:
        try:

            with open(file_name, 'wb') as image:
                for chunk in image_stream:
                    image.write(chunk)
            return True
        except:
            return False
    else:
        return False

def get_flower_rarity(flower_data_url):
    response = requests.get(flower_data_url)
    json_data = response.json()
    rarity = json_data["attributes"][1]["value"]
    return rarity

def remove_flower_png(flower_identifier, bleed):
    if bleed:
        if os.path.exists(f"{flower_identifier}_bleeding.png"):
            os.remove(f"{flower_identifier}_bleeding.png")
        return True
    if not bleed:
        if os.path.exists(f"{flower_identifier}.png"):
            os.remove(f"{flower_identifier}.png")
        return True
    return False

def determine_bot_or_author(user, author):
    #Flowerawaybot
    if user.id == 849948423893024779:
        return True
    #Floweraway dev
    if user.id == 878761291483844649:
        return True
    #author itself
    if user.id == author:
        return True
    return False

async def pick_a_winner(context, message_id, author):
    giveaway_embed = await context.fetch_message(message_id)
    users_list = await giveaway_embed.reactions[0].users().flatten()
    
    filtered_list = [x for x in users_list if not determine_bot_or_author(x, author)]
    with open("config.yaml") as file:
            config = yaml.load(file, Loader=yaml.FullLoader)
    if len(filtered_list) == 0 and config["environment"] != "Dev":
        await error_noone_entered(context)
        return None
    if config["environment"] == "Dev":
        filtered_list = await giveaway_embed.reactions[0].users().flatten()

    filtered_formatted_list = []
    for user in filtered_list:
        filtered_formatted_list.append(user.id)

    winner = random.choice(filtered_formatted_list)
    return winner, filtered_formatted_list

async def parse_arguments_create(context, context_emojis, args):
    splitted_args = args.split(" ")
    #Arg[0] = !giveaway
    #Arg[1] = create
    #Arg[2] = flower identifier "poly-23054" || "eth-24864"
    #Arg[3] = time delta
    #Arg[4] = emoji
    #Create object later returned
    parsed_args = {}
    parsed_args["start_time"] = datetime.utcnow()
    parsed_args["author"] = context.message.author.id

    #Is there enough arguments
    if len(splitted_args) != 5:
        await error_arguments_create(context)
        return None

    #Arg[2] = flower identifier
    if not check_valid_flower_identifier(splitted_args[2].lower()):
        await error_invalid_flower_identifier(context)
        return None
    else:
        parsed_args["flower_identifier"] = splitted_args[2].lower()

    #Start getting image
    parsed_args["flower_url"] = get_flower_image_url(parsed_args["flower_identifier"])
    if parsed_args["flower_url"] is None:
        await error_invalid_flower_identifier(context)
        return None
    else:
        if not save_flower_png(parsed_args["flower_url"], parsed_args["flower_identifier"], True):
            await error_invalid_flower_url_image(context)
            return None
        if not save_flower_png(parsed_args["flower_url"], parsed_args["flower_identifier"], False):
            await error_invalid_flower_url_image(context)
            return None
    parsed_args["flower_data_url"] = get_flower_data_url(parsed_args["flower_identifier"])
    if parsed_args["flower_data_url"] is None:
        await error_invalid_flower_identifier(context)
        return None
    else:
        parsed_args["flower_rarity"] = get_flower_rarity(parsed_args["flower_data_url"])
    
    #Arg[3] get time delta
    parsed_args["end_time"] = get_end_time(splitted_args[3].lower())
    if parsed_args["end_time"] is None:
        await error_invalid_end_time(context)
        return None

    #Arg[4] get emoji
    parsed_args["reaction"] = splitted_args[4]
    if not giveaway_emojis_helpers.check_emoji_valid(context_emojis, parsed_args["reaction"]):
        await error_invalid_emoji(context)
        return None

    return parsed_args

async def parse_arguments_abort(context, args):
    splitted_args = args.split(" ")
    #Arg[0] = !giveaway
    #Arg[1] = abort
    #Arg[2] = message link OR ID
    #Create object later returned
    parsed_args = {}

    #Is there enough arguments
    if len(splitted_args) != 3:
        await error_arguments_abort(context)
        return None

    possible_message_id = splitted_args[2]
    if len(possible_message_id) == 85 or len(possible_message_id) == 18:
        if len(possible_message_id) == 85:
            possible_message_id = possible_message_id[85-18:]
        if possible_message_id.isnumeric():
            parsed_args["message_id"] = possible_message_id
        else:
            await error_invalid_message_id(context)
            return None    
    else:
        await error_invalid_message_id(context)
        return None

    #Return message_id only, as it has been validated
    return parsed_args

async def parse_arguments_end(context, args):
    #Arg[0] = !giveaway
    #Arg[1] = end
    #Arg[2] = message link OR ID
    #It's the same as parse_arguments_abort, so proxying
    return await parse_arguments_abort(context, args)

async def parse_arguments_reroll(context, args):
    #Arg[0] = !giveaway
    #Arg[1] = reroll
    #Arg[2] = message link OR ID
    #It's the same as parse_arguments_abort, so proxying
    return await parse_arguments_abort(context, args)
