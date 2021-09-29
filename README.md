# Giveaway bot Flowerpatch
This discord bot is made for hosting giveaways on [Flowerpatch](flowerpatch.app)'s [discord](discord.gg/flowerpatch).

## How to contribute (running code on host)
1. Clone this repository
2. Set new environment variables in your operating system:
    - `discord_token`
    - `twitter_access_token`
    - `twitter_access_token_secret`
    - `twitter_api_key`
    - `twitter_api_secret`
    - Discord token can be found on [discord dev portal](https://discord.com/developers/applications)
    - Twitter tokens can be found on [twitter dev portal](https://developer.twitter.com/en/portal/dashboard) (yes, there are 4 tokens just to push a tweet...)
3. Check that the environment is "Dev" in config.yaml
4. Run bot.py with python3
5. 

## How to contribute (running code on docker)
1. Clone this repository
2. Uncomment `ENV` lines in dockerfile and add your own tokens ([discord dev portal](https://discord.com/developers/applications), [twitter dev portal](https://developer.twitter.com/en/portal/dashboard))
3. Use the docker image created by running `docker build -t floweraway_bot .` in the same folder as the repository
4. (Optional) If you prefer using docker-compose, here is a template I use: 
```yaml
version: "3.8"
services:
    bot:
        build: .
        container_name: flowerawaybot_2
        volumes:
            - /path/to/your/DockerStorage/flowerawaybot/DB:/app/DB
            - /path/to/your/DockerStorage/flowerawaybot/Logs:/app/Logs
        environment:
            discord_token: 
            twitter_access_token: 
            twitter_access_token_secret: 
            twitter_api_key: 
            twitter_api_secret: 
```

## Steps to production (from old version to this public repo - september 2021)

Note the server and bot tokens are private and maintained by Aiscargeauh#0954
1. Do !updatedb on old bot
2. Get giveaways_converted.json from the old bot
3. Stop the old bot
4. Update token in docker-compose.yaml
5. Set environment to "Prod" in config.yaml
6. docker-compose up -d
7. Check manually for invalid data in giveaways_converted.json
8. Update giveaways.json to the giveaways_converted.json
9. Restart the new bot
10. All rolling! !giveaway stats should be interesting

## Changelog 

### Big update in september 2021, first changelog:

#### Usage

 - `!giveaway create` now takes the flower identifier the same way as done on flowerpatch.
   - Now in the form: *network-id*. Ex: `eth-1234` or `poly-14652`
   - Bot reacts to the giveaway message, making the first reaction
   - Dynamically updating the embed (time left) every minute
   - Asynchronous:
     - Display embed first, then edit the message to add twitter URL
   - Discord invite link in tweets is now vanity URL: discord.gg/flowerpatch
 - `!giveaway end` now takes either the message id or message url
   - More verifications done:
     - Only author or bot owners can end a giveaway
     - Author or bot will never win
 - `!giveaway reroll`
   - More verifications done:
     - Only author or bot owners can reroll a giveaway
     - Only ended giveaways can be rerolled, suggests to do `!giveawway end` first
 - `!giveaway abort`
   - More verifications done:
     - Only author or bot owners can abort a giveaway
     - Cannot abort when already ended, suggests to do `!giveaway reroll` first
 - `!giveaway list` or just `!giveaway`
   - Only one list message at a time (delete previous then re-send embed message)
   - Dynamically updated every minute + every reaction (add or remove)
 - `!giveaway stats`
   - New feature
   - Show who gave the most flowers, biggest rarity and who won the most
   - One statistics message at a time (delete previous then re-send embed message)
   - Possible to mention someone to see their specific statistics
 - `!giveaway win`
   - New feature, only fun!
#### General

 - More aliases
   - `giveaway` = `giveaways`, `giveway`, `givaway`, `giveways`, `givaways`
   - `create` = `start`, `crate`, `creat`
   - `abort` = `abrt`, `abor`
   - `end` = `nd`
   - `list` = `lst`
   - `stats` = `stat`, `statistics`, `statistic`
   - `reroll` = `redraw`, `rerol`
 - Much better time displays
 - All current members in roles `@administrator`, `@moderator` and `@staff` are bot owners and can override some permissions (in case of conflicts / litigations / problems)
   - Note: it has been done manually, it does not work by role but by user ID so a new owner needs to be added if someone gets one of those roles
   - Owners have access to commands listed in `!help owner`
     - `!shutdown` -> /!\ Disconnects the bot
     - `!say` or `!echo` -> See if the bot print some text
     - `!embed` -> Try some embeds
     - `!prefix` -> Change the prefix of the bot ("!" by default)
     - `!purge giveaways` -> /!\ Removes all giveaways in database (yep, everything)
     - `!blacklist add @user` or `!blacklist remove @user` to prevent someone from using the bot or authorize the user again
     - `!owner add @user` or `!owner remove @user` to add someone to the owners list (and give user rights to override commands / use the ones listed above)
 - Old giveaway database has been restructured to keep history
 - More logging on each command
   - Better understanding of history
   - Daily rolling file
 - Tokens are now environment variables
   - **Make the project open-source!**


#### Notes

- Only `!giveaway` commands and subcommands have aliases
- Bot will not react at all when a blacklisted user is posting a message