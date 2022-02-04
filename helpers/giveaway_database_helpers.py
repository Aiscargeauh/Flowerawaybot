from datetime import datetime
from tinydb import TinyDB, Query

# Load giveaway database
giveaway_db = TinyDB('DB/giveaways.json')
list_message_tracker = TinyDB('DB/list_messages.json')
stats_message_tracker = TinyDB('DB/stats_messages.json')

def save_new_giveaway(flower_identifier, flower_rarity, start_time, end_time, author, reaction, message_url, message_id, tweet_id, redeemable_url):
    giveaway_data = {
        'status': "ONGOING",
        'flower_identifier': flower_identifier,
        'flower_rarity': flower_rarity,
        'start_time': str(start_time),
        'end_time': str(end_time),
        'author': author,
        'reaction': reaction,
        'message_url': message_url,
        'message_id': message_id,
        'winner': "",
        'participants': [],
        'rerolls': []
    }
    if tweet_id > 0:
        giveaway_data["tweet_id"] = tweet_id
    if redeemable_url != "":
        giveaway_data["redeemable_url"] = redeemable_url
    giveaway_db.clear_cache()
    giveaway_db.insert(giveaway_data)

def get_not_ongoing_giveaways():
    giveaway_db.clear_cache()
    giveaway_query = Query()
    try:
        return giveaway_db.search(giveaway_query["status"] != "ONGOING")
    except:
        return None

def get_participation_count(user_id):
    giveaway_db.clear_cache()
    giveaway_query = Query()
    try:
        list_of_giveaways = giveaway_db.search(giveaway_query["participants"].test(lambda x: user_id in x))
        return len(list_of_giveaways)
    except:
        return None

def get_favorite_emoji(user_id):
    giveaway_db.clear_cache()
    giveaway_query = Query()
    try:
        list_of_giveaways = giveaway_db.search(giveaway_query["author"] == user_id)
        emojis = {}
        for giveaway in list_of_giveaways:
            if emojis.get(giveaway["reaction"]):
                emojis[giveaway["reaction"]] += 1
            else:
                emojis[giveaway["reaction"]] = 1
        emojis = dict(sorted(emojis.items(), key=lambda item: item[1], reverse=True))
        return next(iter(emojis))
    except:
        return None

def get_latest_list_message_id():
    list_message_tracker.clear_cache()
    return list_message_tracker.all()

def get_latest_stats_message_id():
    stats_message_tracker.clear_cache()
    return stats_message_tracker.all()

def set_latest_list_message_id(message_id):
    list_message_tracker.clear_cache()
    list_message_tracker.truncate()
    list_message_tracker.insert({'message_id': message_id})

def set_latest_stats_message_id(message_id):
    stats_message_tracker.clear_cache()
    stats_message_tracker.truncate()
    stats_message_tracker.insert({'message_id': message_id})

def get_ongoing_giveaways():
    giveaway_db.clear_cache()
    giveaway_query = Query()
    try:
        return giveaway_db.search(giveaway_query["status"] == "ONGOING")
    except:
        return None

def get_giveaways_by_user(user_id):
    giveaway_db.clear_cache()
    giveaway_query = Query()
    try:
        return giveaway_db.search(\
            (giveaway_query["author"] == user_id) | \
            (user_id in giveaway_query["participants"]) | \
            (giveaway_query["winner"] == user_id) | \
            (giveaway_query["reroll"][-1]["winner"] == user_id))
    except Exception as e:
        return None

def get_giveaway_by_message_id(message_id):
    giveaway_db.clear_cache()
    giveaway_query = Query()
    try:
        result = giveaway_db.search(giveaway_query["message_id"] == int(message_id))
        return result[0]
    except:
        return None

def is_giveaway_ended_or_aborted(message_id):
    giveaway_db.clear_cache()
    giveaway_query = Query()
    try:
        giveaway_status = giveaway_db.search(giveaway_query.message_id == message_id)[0]["status"]
        if giveaway_status == "ONGOING":
            return False
        return True
    except:
        return True

def is_giveaway_message(message_id):
    giveaway_db.clear_cache()
    giveaway_query = Query()
    try:
        giveaway = giveaway_db.search(giveaway_query.message_id == message_id)[0]
        if giveaway:
            return True
        else:
            return False
    except:
        return False

def change_giveaway_status(message_id, new_status):
    giveaway_db.clear_cache()
    giveaway_query_update = Query()
    giveaway_db.update({"status": new_status}, giveaway_query_update.message_id == int(message_id) )

def change_giveaway_winner(message_id, username, participants):
    giveaway_db.clear_cache()
    giveaway_query_update = Query()
    giveaway_db.update({"winner": username, 'participants': participants}, giveaway_query_update.message_id == int(message_id) )

def append_giveaway_reroll(message_id, username):
    giveaway_db.clear_cache()
    giveaway_query = Query()
    giveaway_rerolls = giveaway_db.search(giveaway_query.message_id == int(message_id))[0]["rerolls"]
    giveaway_rerolls.append({"timestamp": str(datetime.utcnow()), "winner": username})
    giveaway_query_update = Query()
    giveaway_db.update({"rerolls": giveaway_rerolls}, giveaway_query_update.message_id == int(message_id) )