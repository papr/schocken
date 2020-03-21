from .exceptions import SpielLäuft

class SchockenBot:
    def __init__(self):
        self.schock_channel_name = "programmierbereich"
        self.valid_guild_name = "Café A"
        self.game_running = False
        self._start_game_cmd = "schocken"
        self._end_game_cmd = "beenden"

    def init_emojis(self, guild):
        self.emojis = guild.emojis

    def emoji_by_name(self, name):
        return [em for em in self.emojis if em.name==name][0]

    async def parse_input(self, message):
        # all messages from channels with read permissions are read
        msg_text = message.content
        channel = message.channel
        # check if message is in the correct channel
        if channel_name == self.schock_channel_name:
            # check if message is a command
            if msg_text.startswith("!"):
                command = msg_text.split("!")[-1]
                if command == self._start_game_cmd: 
                    if self.game_running:
                        raise SpielLäuft
                    else:
                        self.game_running = True()
                        game = SchockenRunde()
                        msg = f"{message.author.name} will Schocken. `!einwerfen` zum mitmachen"
                        await self.print_to_channel(msg)

                elif command == self._end_game_cmd:
                    if self.game_running:
                        msg = f"{message.author.name} hat das Spiel beendet"
                        self.game_running = False()
                        await self.print_to_channel(msg)
                    else:
                        raise FalscheAktion
                else:
                    #actual game
                    #TODO Fix Logic
                    try:
                        output = game.parse_input(message)
                        await self.print_to_channel(output)
                    except NotImplementedError:
                        msg = "Das geht leider noch nicht."
                        await self.print_to_channel(msg)
            else:
                pass

    async def print_to_channel(self, channel, text):
        return await channel.send(text)
