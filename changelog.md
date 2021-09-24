# Changelog

## Usage

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


## General

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
 - TODO: Old giveaway database has been restructured to keep history
 - More logging on each command
   - Better understanding of history
   - Daily rolling file
 - TODO: Tokens are now environment variables
   - **Make the project open-source!**


## Notes

- Only `!giveaway` commands and subcommands have prefixes
- Bot will not react at all when a blacklisted user is posting a message