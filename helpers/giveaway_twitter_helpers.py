import os
import sys
import yaml
import tweepy
from datetime import datetime
import humanize

# Only if you want to use variables that are in the config.yaml file.
if not os.path.isfile("config.yaml"):
    sys.exit("'config.yaml' not found! Please add it and try again.")
else:
    with open("config.yaml") as file:
        config = yaml.load(file, Loader=yaml.FullLoader)


# Set up twitter API
auth = tweepy.OAuthHandler(os.getenv("twitter_api_key"), os.getenv("twitter_api_secret"))
auth.set_access_token(os.getenv("twitter_access_token"), os.getenv("twitter_access_token_secret"))
tweepy_api = tweepy.API(auth)

async def send_tweet(flower_identifier, end_time):
    displayable_end_time = humanize.naturaltime(datetime.utcnow() - end_time)
    tweet_text = f"A discord user is giving away https://flowerpatch.app/card/{flower_identifier}\nEnds in {displayable_end_time}!\nJoin @Flowerpatchgame on discord: https://discord.gg/flowerpatch to participate!\n @Nugbase #NFT #giveaway #FreeNFT #flowerpatch"
    try:
        tweet_static_image = tweepy_api.media_upload("giveaway_static.png")
        tweet_flower_image = tweepy_api.media_upload(f"{flower_identifier}.png")

        tweet_result = tweepy_api.update_status(status=tweet_text, media_ids=[tweet_static_image.media_id, tweet_flower_image.media_id])
        
        #Remove tweet ASAP if working in dev environment
        if config["environment"] == "Dev":
            tweepy_api.destroy_status(tweet_result.id)
        
        return tweet_result._json['entities']['urls'][1]['url'], tweet_result.id
    except Exception as e:
        return "", 0

async def remove_tweet(tweet_id):
    #Tweet is already removed when pushed in dev mode
    if config["environment"] != "Dev":
        tweepy_api.destroy_status(tweet_id)

async def update_tweet_giveaway_ended(tweet_id):
    #Tweet is already removed when pushed in dev mode
    if config["environment"] != "Dev":
        tweepy_api.update_status(status="Giveaway has ended! Someone on discord won the giveaway :)", in_reply_to_status_id=tweet_id, auto_populate_reply_metadata=True)

