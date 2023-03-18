import sys

import discord
from discord.ext import commands

from utils.txt_parser import get_help_list

sys.path.append("utils")


class HelpCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.help_list = get_help_list()
        self.text = self.help_list[0]
        self.image = self.help_list[1]
        self.voice = self.help_list[2]


    @commands.group(name='help', invoke_without_command=True)
    async def help(self, ctx: commands.Context):
        embed = discord.Embed(
            title='Help Command!',
            description='',
            color=discord.Color.purple()
        )
        embed.set_thumbnail(
            url='https://img.icons8.com/ios-glyphs/60/undefined/help.png')
        embed.add_field(name='Prefix', value="```'```", inline=False)
        embed.add_field(name='Text Channel', value="```" +
                        self.text[0] + "```" + self.text[1], inline=True)
        embed.add_field(name='Voice Channel', value="```" +
                        self.voice[0] + "```" + self.voice[1], inline=True)
        await ctx.send(embed=embed)

    @help.command(name='img')
    async def help_image(self, ctx: commands.Context):
        embed = discord.Embed(
            title='Image commands!',
            description='',
            color=discord.Color.dark_blue()
        )
        embed.set_thumbnail(
            url='https://img.icons8.com/ios-glyphs/60/undefined/help.png')
        embed.add_field(name='Endpoints', value="```" +
                        self.image[0] + "```", inline=True)
        embed.add_field(name='How to use?', value=self.image[1], inline=True)
        await ctx.send(embed=embed)

    @help.command(name='pl')
    async def help_pl(self, ctx: commands.Context):
        embed = discord.Embed(
            title='pl command!',
            description='',
            color=discord.Color.dark_blue()
        )
        embed.set_thumbnail(
            url='https://img.icons8.com/ios-glyphs/60/undefined/help.png')
        pl = """
```
pl create <playlist-name> - Creates an empty playlist.
pl <playlist-url/playlist-name> - Adds the playlist to the queue.
pl add <url/name> <playlist-name> - Adds an item to the playlist. Creates a new one if it does not exists.
pl remove <id> <playlist-name> - Remove an item from playlist.
pl server - Get a list of server's playlist.
pl list <playlist-name> - Lists the items in a playlist.```
        """
        embed.add_field(name='Usage', value=pl)
        embed.set_footer(text="Note: < > are not not needed when using the actual command!")
        await ctx.send(embed=embed)

    @help.command(name="ping")
    async def _ping(self, ctx: commands.Context):
        embed = discord.Embed(
            title="Ping",
            description="Get bot's latency.",
            color=discord.Color.dark_blue()
        )
        embed.set_thumbnail(
            url="https://img.icons8.com/ios-glyphs/60/undefined/help.png")
        embed.add_field(name="How to use?", value="```'ping```")
        await ctx.send(embed=embed)

    @help.command(name="info")
    async def _info(self, ctx: commands.Context):
        embed = discord.Embed(
            title="Info",
            description="Get a user's info.",
            color=discord.Color.dark_blue()
        )
        embed.set_thumbnail(
            url="https://img.icons8.com/ios-glyphs/60/undefined/help.png")
        embed.add_field(name="How to use?",
                        value="```'info <mention/user-id>```")
        await ctx.send(embed=embed)

    @help.command(name="server")
    async def _server(self, ctx: commands.Context):
        embed = discord.Embed(
            title="Server",
            description="Get the server's info.",
            color=discord.Color.dark_blue()
        )
        embed.set_thumbnail(
            url="https://img.icons8.com/ios-glyphs/60/undefined/help.png")
        embed.add_field(name="How to use?", value="```'server```")
        await ctx.send(embed=embed)

    @help.command(name="join")
    async def _join_(self, ctx: commands.Context):
        embed = discord.Embed(
            title="Join",
            description="Joins a Voice Channel.",
            color=discord.Color.dark_blue()
        )
        embed.set_thumbnail(
            url="https://img.icons8.com/ios-glyphs/60/undefined/help.png")
        embed.add_field(name="How to use?", value="```'join```")
        await ctx.send(embed=embed)

    @help.command(name="leave")
    async def _leave_(self, ctx: commands.Context):
        embed = discord.Embed(
            title="Leave",
            description="Leaves a Voice Channel.",
            color=discord.Color.dark_blue()
        )
        embed.set_thumbnail(
            url="https://img.icons8.com/ios-glyphs/60/undefined/help.png")
        embed.add_field(name="How to use?", value="```'leave```")
        await ctx.send(embed=embed)

    @help.command(name="volume", aliases=['vol'])
    async def _volume_(self, ctx: commands.Context):
        embed = discord.Embed(
            title="Volume",
            description="Set/Get player's volume.",
            color=discord.Color.dark_blue()
        )
        embed.set_thumbnail(
            url="https://img.icons8.com/ios-glyphs/60/undefined/help.png")
        embed.add_field(name="How to use?", value="```'volume <1-100>```")
        await ctx.send(embed=embed)

    @help.command(name="np", aliases=['current', 'nowplaying'])
    async def _Np_(self, ctx: commands.Context):
        embed = discord.Embed(
            title="Now Playing",
            description="Get the current song.",
            color=discord.Color.dark_blue()
        )
        embed.set_thumbnail(
            url="https://img.icons8.com/ios-glyphs/60/undefined/help.png")
        embed.add_field(name="How to use?",
                        value="```'nowplaying or 'np or 'current```")
        await ctx.send(embed=embed)

    @help.command(name="pause")
    async def _pau_(self, ctx: commands.Context):
        embed = discord.Embed(
            title="Pause",
            description="Pauses the current song.",
            color=discord.Color.dark_blue()
        )
        embed.set_thumbnail(
            url="https://img.icons8.com/ios-glyphs/60/undefined/help.png")
        embed.add_field(name="How to use?", value="```'pause```")
        await ctx.send(embed=embed)

    @help.command(name="resume")
    async def _res_(self, ctx: commands.Context):
        embed = discord.Embed(
            title="Resume",
            description="Resumes the paused song.",
            color=discord.Color.dark_blue()
        )
        embed.set_thumbnail(
            url="https://img.icons8.com/ios-glyphs/60/undefined/help.png")
        embed.add_field(name="How to use?", value="```'resume```")
        await ctx.send(embed=embed)

    @help.command(name="play")
    async def _pla_(self, ctx: commands.Context):
        embed = discord.Embed(
            title="Play",
            description="Plays a song/Adds it to the queue.",
            color=discord.Color.dark_blue()
        )
        embed.set_thumbnail(
            url="https://img.icons8.com/ios-glyphs/60/undefined/help.png")
        embed.add_field(name="How to use?", value="```'play <url>```")
        await ctx.send(embed=embed)

    @help.command(name="skip")
    async def _ski_(self, ctx: commands.Context):
        embed = discord.Embed(
            title="Skip",
            description="Skips the current song.",
            color=discord.Color.dark_blue()
        )
        embed.set_thumbnail(
            url="https://img.icons8.com/ios-glyphs/60/undefined/help.png")
        embed.add_field(name="How to use?", value="```'skip```")
        await ctx.send(embed=embed)

    @help.command(name="queue")
    async def _que_(self, ctx: commands.Context):
        embed = discord.Embed(
            title="Queue",
            description="Gets the queue.",
            color=discord.Color.dark_blue()
        )
        embed.set_thumbnail(
            url="https://img.icons8.com/ios-glyphs/60/undefined/help.png")
        embed.add_field(name="How to use?", value="```'queue```")
        await ctx.send(embed=embed)

    @help.command(name="shuffle")
    async def _shuf_(self, ctx: commands.Context):
        embed = discord.Embed(
            title="Shuffle",
            description="Shuffles the queue.",
            color=discord.Color.dark_blue()
        )
        embed.set_thumbnail(
            url="https://img.icons8.com/ios-glyphs/60/undefined/help.png")
        embed.add_field(name="How to use?", value="```'shuffle```")
        await ctx.send(embed=embed)

    @help.command(name="remove")
    async def _reo_(self, ctx: commands.Context):
        embed = discord.Embed(
            title="Remove",
            description="Removes a song from the queue.",
            color=discord.Color.dark_blue()
        )
        embed.set_thumbnail(
            url="https://img.icons8.com/ios-glyphs/60/undefined/help.png")
        embed.add_field(name="How to use?", value="```'remove <index>```")
        await ctx.send(embed=embed)

    # @help.command(name="slice")
    # async def _slice_(self, ctx: commands.Context):
    #     embed = discord.Embed(
    #       title="Slice",
    #       description="Slices the queue.",
    #       color=discord.Color.dark_blue()
    #     )
    #     embed.set_thumbnail(url="https://img.icons8.com/ios-glyphs/60/undefined/help.png")
    #     embed.add_field(name="How to use?", value="```'slice <start> <stop>```")
    #     await ctx.send(embed=embed)

    @help.error
    async def help_error(self, ctx: commands.Context, error):
        if isinstance(error, commands.CommandNotFound):
            await ctx.send("No such help command exists!")


async def setup(bot):
    await bot.add_cog(HelpCog(bot))
