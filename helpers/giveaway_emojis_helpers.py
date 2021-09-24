import emojis
import humanize
import json
import re

emoji_map_file = open('DB/emoji_map.json')
emoji_map_json = json.load(emoji_map_file)

def check_emoji_valid(bot_emojis, reaction):
    #Server Emoji
    if reaction.startswith("<"):
        reaction_id = re.findall('\d+', reaction)
        for emoji in bot_emojis:
            if emoji.id == int(reaction_id[0]):
                return True
    #Basic emoji
    else:
        reaction_basic = emojis.decode(reaction)
        reaction_basic = reaction_basic.replace(":", "")
        if emoji_map_json.get(reaction_basic):
            return True
    return False