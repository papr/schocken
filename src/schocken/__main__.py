import os

import discord
from discord.utils import get
from dotenv import load_dotenv

from schocken.exceptions import FalscherServer
from schocken.bot import SchockenBot

def run_bot():
    load_dotenv()
    TOKEN = os.getenv("DISCORD_TOKEN")
    GUILD = os.getenv("DISCORD_GUILD")
    client = discord.Client()

    # when connecting
    @client.event
    async def on_ready():
        client.bot = SchockenBot(client)
        # check if server is correct:
        for guild in client.guilds:
            if guild.name != client.bot.valid_guild_name:
                raise FalscherServer("Dieser Bot darf nur ins Café A")

        ch = client.get_channel(690929770355097610)  # schocktresen
        await ch.send("Schocken kann jetzt losgehen. :muscle:")
        print("Success")
        return


    # when a message is read by the bot
    @client.event
    async def on_message(message):
        await client.bot.parse_input(message)
        return


    client.run(TOKEN)
