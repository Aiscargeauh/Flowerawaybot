import json
import os
import sys

import aiohttp
import discord
import yaml
from discord.ext import commands

if not os.path.isfile("config.yaml"):
    sys.exit("'config.yaml' not found! Please add it and try again.")
else:
    with open("config.yaml") as file:
        config = yaml.load(file, Loader=yaml.FullLoader)


class general(commands.Cog, name="General"):
    """
    General commands about this bot and crypto
    """
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="serverinfo", alases=["info"])
    async def serverinfo(self, context):
        """
        Get some useful (or not) information about the server.
        """
        server = context.message.guild
        roles = [x.name for x in server.roles]
        role_length = len(roles)
        if role_length > 50:
            roles = roles[:50]
            roles.append(f">>>> Displaying[50/{len(roles)}] Roles")
        roles = ", ".join(roles)
        channels = len(server.channels)
        time = str(server.created_at)
        time = time.split(" ")
        time = time[0]

        embed = discord.Embed(
            title="**Server Name:**",
            description=f"{server}"
        )
        embed.set_thumbnail(
            url=server.icon_url
        )
        # embed.add_field(
        #     name="Owner",
        #     value=f"{server.owner}\n{server.owner.id}"
        # )
        embed.add_field(
            name="Server ID",
            value=server.id,
            inline=False
        )
        embed.add_field(
            name="Member Count",
            value=server.member_count,
            inline=False
        )
        embed.add_field(
            name="Text/Voice Channels",
            value=f"{channels}",
            inline=False
        )
        embed.set_footer(
            text=f"Created at: {time}"
        )
        await context.send(embed=embed)

    @commands.command(name="ping")
    async def ping(self, context):
        """
        Check if the bot is alive.
        """
        embed = discord.Embed()
        embed.add_field(
            name="Pong!",
            value=":ping_pong:",
            inline=True
        )
        embed.set_footer(
            text=f"Pong request by {context.message.author}"
        )
        await context.send(embed=embed)

    @commands.command(name="bitcoin", aliases=["btc"])
    async def bitcoin(self, context):
        """
        Get the current price of bitcoin.
        """
        url = "https://api.coingecko.com/api/v3/coins/bitcoin?localization=false&tickers=false&market_data=true&community_data=false&developer_data=false&sparkline=false"
        # Async HTTP request
        async with aiohttp.ClientSession() as session:
            raw_response = await session.get(url)
            response = await raw_response.text()
            response = json.loads(response)
            embed = discord.Embed(
                title=":information_source: Info",
                description=f"Bitcoin price is: **${response['market_data']['current_price']['usd']}**"
            )
            await context.send(embed=embed)

    @commands.command(name="ethereum", aliases=["ether", "eth"])
    async def ethereum(self, context):
        """
        Get the current price of ethereum.
        """
        url = "https://api.coingecko.com/api/v3/coins/ethereum?localization=false&tickers=false&market_data=true&community_data=false&developer_data=false&sparkline=false"
        # Async HTTP request
        async with aiohttp.ClientSession() as session:
            raw_response = await session.get(url)
            response = await raw_response.text()
            response = json.loads(response)
            embed = discord.Embed(
                title=":information_source: Info",
                description=f"Ethereum price is: **${response['market_data']['current_price']['usd']}**"
            )
            await context.send(embed=embed)

    @commands.command(name="gas", aliases=["fees", "ethfees", "ethgas"])
    async def gas(self, context):
        """
        Get the current price of a transaction on ethereum.
        """
        url = "https://ethgasstation.info/api/ethgasAPI.json?api-key=4d4c66901e500964d3b59110f3cfd771ca9b61c7f0f4811a6c274d3f60f8"
        # Async HTTP request
        async with aiohttp.ClientSession() as session:
            raw_response = await session.get(url)
            response = await raw_response.text()
            response = json.loads(response)
            embed = discord.Embed(
                title=":information_source: Info",
                description=f"**Gas price is:** \nAverage: **{response['average']/10} gwei.**\nFast: **{response['fast']/10} gwei.**\nFastest: **{response['fastest']/10} gwei.**"
            )
            await context.send(embed=embed)

def setup(bot):
    bot.add_cog(general(bot))