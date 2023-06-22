import re
import asyncio
from urllib.parse import parse_qs, urlparse
from timeit import default_timer as timer
import itertools
import logging
import math
import random
import discord
import yt_dlp
from async_timeout import timeout
from discord.ext import commands
from discord.ext.commands import Parameter
from database.music import MusicDB, MusicItem
from googleapiclient.errors import HttpError
from api import youtube

bot = commands.Bot(command_prefix="'", help_command=None, intents=discord.Intents.all())
logger = logging.getLogger("discord")


class VoiceError(Exception):
    pass


class YTDLError(Exception):
    pass


class QueueButton(discord.ui.View):
    def __init__(self, ctx: commands.Context, current: int, pages: int):
        super().__init__(timeout=60 * 2)
        self.ctx = ctx
        self.current = current
        self.pages = pages

    async def on_timeout(self) -> None:
        for item in self.children:
            item.disabled = True
        await self.message.edit(view=self)

    async def on_error(self, interaction: discord.Interaction, error, item):
        logger.error(error)
        await interaction.response.send_message("An error occurred!", ephemeral=True)
        return

    @discord.ui.button(label="⬅", style=discord.ButtonStyle.green)
    async def prev_button_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current == 1 and self.pages == 1:
            return await interaction.response.send_message("No next page!", ephemeral=True)
        if self.current == 1:
            prev_page = self.pages
        else:
            prev_page = self.current - 1
        embed, pages = MusicUtils.get_queue(self.ctx, prev_page)
        self.pages = pages
        self.current = prev_page
        await interaction.response.edit_message(embed=embed)

    @discord.ui.button(label="➡", style=discord.ButtonStyle.green)
    async def next_button_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current == 1 and self.pages == 1:
            return await interaction.response.send_message("No next page!", ephemeral=True)
        if self.current == self.pages:
            next_page = 1
        else:
            next_page = self.current + 1
        embed, pages = MusicUtils.get_queue(self.ctx, next_page)
        self.pages = pages
        self.current = next_page
        await interaction.response.edit_message(embed=embed)


class YTDLSource(discord.PCMVolumeTransformer):
    YTDL_OPTIONS = {
        'format': 'bestaudio/best',
        'extractaudio': True,
        'audioformat': 'wav/mp3/webm',
        'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
        'restrictfilenames': True,
        'noplaylist': True,
        'nocheckcertificate': True,
        'ignoreerrors': False,
        'logtostderr': False,
        'quiet': True,
        'no_warnings': True,
        'default_search': 'auto',
        'source_address': '0.0.0.0',
    }

    FFMPEG_OPTIONS = {
        'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5'
    }

    # FILTERS = [
    #     'bass=g=20,dynaudnorm=f=200',  # bass boost
    #     'apulsator=hz=0.08',  # 8D
    #     'aresample=48000,asetrate=48000*0.8',  # vapor wave
    #     'aresample=48000,asetrate=48000*1.25',  # nightcore
    #     'aphaser=in_gain=0.4',  # phaser
    #     'tremolo',  # tremolo
    #     'vibrato=f=6.5',  # vibrato
    #     'surround',  # surrounding
    #     'apulsator=hz=1',  # pulsator
    #     'asubboost'  # sub boost
    # ]

    ytdlp = yt_dlp.YoutubeDL(YTDL_OPTIONS)

    def __init__(self, ctx: commands.Context, source: discord.FFmpegPCMAudio, *, data: dict, volume: float = 0.5):
        super().__init__(source, volume)

        self.requester = ctx.author
        self.channel = ctx.channel
        self.data = data

        self.uploader = data.get('uploader')
        self.uploader_url = data.get('uploader_url')
        # date = data.get('upload_date')
        self.title = data.get('title')
        self.thumbnail = data.get('thumbnail')
        self.int_duration = int(data.get('duration'))
        self.duration = self.parse_duration(int(data.get('duration')))
        self.url = data.get('webpage_url')
        self.views = data.get('view_count')
        # self.likes = data.get('like_count')
        self.stream_url = data.get('url')

    def __str__(self):
        return '**{0.title}** by **{0.uploader}**'.format(self)

    @classmethod
    async def create_source(cls, ctx: commands.Context, search: str, *,
                            time: int = 0):
        with YTDLSource.ytdlp as ytdl:
            data = ytdl.sanitize_info(ytdl.extract_info(search, download=False))
        if 'entries' in data:
            data = data['entries'][0]

        opt = cls.FFMPEG_OPTIONS
        opt['options'] = f'-vn -ss {time}'
        # opt['options'] = f'-vn -ss {time} -af "{filter}" -b:a 320k'
        return cls(ctx, discord.FFmpegPCMAudio(source=data['url'], **opt), data=data)

    @staticmethod
    def parse_duration(duration: int):
        minutes, seconds = divmod(duration, 60)
        hours, minutes = divmod(minutes, 60)
        days, hours = divmod(hours, 24)

        duration = []
        if days > 0:
            duration.append('{} days'.format(int(days)))
        if hours > 0:
            duration.append('{} hours'.format(int(hours)))
        if minutes > 0:
            duration.append('{} minutes'.format(int(minutes)))
        if seconds > 0:
            duration.append('{} seconds'.format(int(seconds)))

        return ', '.join(duration)


class Song:
    __slots__ = ('source', 'requester', 'time')

    def __init__(self, source: YTDLSource, time=timer()):
        self.source = source
        self.requester = source.requester
        self.time = time

    def create_embed(self):
        embed = (discord.Embed(title='Now playing',
                               description='[{0.source.title}]({0.source.url})'.format(self),
                               color=discord.Color.blurple())
                 .add_field(name='Duration', value=self.source.duration, inline=False)
                 .add_field(name='Requested by', value=self.requester.mention, inline=False)
                 .add_field(name='Uploader', value='[{0.source.uploader}]({0.source.uploader_url})'.format(self),
                            inline=False)
                 .set_thumbnail(url=self.source.thumbnail))
        return embed


class SongQueue(asyncio.Queue):
    def __getitem__(self, item):
        if isinstance(item, slice):
            return list(itertools.islice(self._queue, item.start, item.stop, item.step))
        else:
            return self._queue[item]

    def __iter__(self):
        return self._queue.__iter__()

    def __len__(self):
        return self.qsize()

    def clear(self):
        self._queue.clear()

    def shuffle(self):
        random.shuffle(self._queue)

    def remove(self, index: int):
        del self._queue[index]


class VoiceState:
    def __init__(self, bot: commands.Bot, ctx: commands.Context):
        self.bot = bot
        self._ctx = ctx

        self.current = None
        self.start = None
        self.voice = None
        self.next = asyncio.Event()
        self.songs = SongQueue()

        self._loop = False
        self._volume = 0.5

        self.audio_player = bot.loop.create_task(self.audio_player_task())

    def __del__(self):
        self.audio_player.cancel()

    @property
    def loop(self):
        return self._loop

    @loop.setter
    def loop(self, value: bool):
        self._loop = value

    @property
    def volume(self):
        return self._volume

    @volume.setter
    def volume(self, value: float):
        self._volume = value

    @property
    def is_playing(self):
        return self.voice and self.current

    async def check_source(self):
        elapsed = timer() - self.current.time
        if elapsed > 60 * 5:  # 5 minutes
            # recreate source
            # since YouTube streaming links expire after some time
            new_source = await YTDLSource.create_source(self._ctx, self.current.source.url)
            self.current = Song(new_source, timer())
            self.current.requester = self.current.requester

    async def audio_player_task(self):
        while True:
            self.next.clear()

            if not self.loop:
                # Try to get the next song within 3 minutes.
                # If no song will be added to the queue in time,
                # the player will disconnect due to performance
                # reasons.
                try:
                    async with timeout(60 * 3):  # 3 minutes
                        self.current = await self.songs.get()
                except asyncio.TimeoutError:
                    self.bot.loop.create_task(self.stop())
                    return
            else:
                # await self.songs.put(self.current)
                o_src = await YTDLSource.create_source(self._ctx, self.current.source.url)
                await self.songs.put(Song(o_src, timer()))
                self.current = await self.songs.get()
            await self.check_source()
            self.current.source.volume = self._volume
            self.voice.play(self.current.source, after=self.play_next_song)
            self.start = timer()
            await self.current.source.channel.send(embed=self.current.create_embed())
            await self.next.wait()

    def play_next_song(self, error=None):

        if error:
            logger.error(error)

        self.next.set()

    def skip(self):

        if self.is_playing:
            self.voice.stop()

    async def stop(self):
        self.songs.clear()

        if self.voice:
            await self.voice.disconnect()
            self.voice.cleanup()
            self.voice = None
            self.current = None


# will be updated in future

# async def import_playlist(ctx: commands.Context, attach: discord.Attachment):
#     playlists = get_playlists(ctx.guild.id)
#     await attach.save(f"tmp/playlist.{ctx.guild.id}.1.json")
#     with open(f"tmp/playlist.{ctx.guild.id}.1.json", 'r') as f:
#         data = json.load(f)
#     pl_name = data['playlist_name']
#     if playlists is not None:
#         if pl_name in playlists:
#             return await ctx.send(
#                 embed=discord.Embed(title=f"Playlist with name: **{pl_name.capitalize()}** already exists!",
#                                     color=discord.Color.magenta())
#             )
#     try:
#         create_playlist(ctx.guild.id, pl_name)
#     except OperationalError:
#         create_guild_playlist(ctx.guild.id)
#         create_playlist(ctx.guild.id, pl_name)
#     for key in data.keys():
#         if key == "playlist_name":
#             continue
#         tmp = data[key]
#         name, url = tmp["name"], tmp["url"]
#
#         insert_playlist_data(ctx.guild.id, pl_name, [name, url])
#     os.remove(f"tmp/playlist.{ctx.guild.id}.1.json")
#     await ctx.send(embed=discord.Embed(title=f"Imported playlist: **{pl_name.capitalize()}**",
#                                        color=discord.Color.magenta()))
class MusicUtils:
    @staticmethod
    def get_queue(ctx: commands.Context, page: int = 1):
        items_per_page = 10
        pages = math.ceil(len(ctx.voice_state.songs) / items_per_page)

        start = (page - 1) * items_per_page
        end = start + items_per_page

        queue = ''
        for i, song in enumerate(ctx.voice_state.songs[start:end], start=start):
            name = song.source.title
            _id = song.source.url
            if "://" not in _id:
                _id = f"https://youtu.be/{_id}"
            queue += '`{0}.` [**{1}**]({2})\n'.format(i + 1, name, _id)
        embed = (
            discord.Embed(title="Queue", description='**{} tracks:**\n\n{}'.format(len(ctx.voice_state.songs), queue))
            .set_footer(text='Viewing page {}/{}'.format(page, pages)))
        return embed, pages

    @staticmethod
    async def check_db_value(ctx: commands.Context, name: str | None, val: list[MusicItem] | None | int) -> bool:
        if val == 0:
            await ctx.send(embed=discord.Embed(
                title=f'Playlist {name} does not exist!',
                color=discord.Color.magenta()
            ))
            return False
        elif val == -1:
            await ctx.send(embed=discord.Embed(
                title=f'Playlist {name} is empty!',
                color=discord.Color.magenta()
            ))
            return False
        elif val == 1:
            await ctx.send(embed=discord.Embed(
                title='Item does not exist!',
                color=discord.Color.magenta()
            ))
            return False
        elif val is None:
            await ctx.send(embed=discord.Embed(
                title='No playlists!'
            ))
        else:
            return True


class Music(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.voice_states: dict[int, VoiceState] = {}

    def get_voice_state(self, ctx: commands.Context) -> VoiceState:
        state = self.voice_states.get(ctx.guild.id)
        if not state:
            state = VoiceState(self.bot, ctx)
            self.voice_states[ctx.guild.id] = state

        return state

    def cog_unload(self):
        for state in self.voice_states.values():
            self.bot.loop.create_task(state.stop())

    def cog_check(self, ctx: commands.Context):
        if not ctx.guild:
            raise commands.NoPrivateMessage('This command can\'t be used in DM channels.')

        return True

    async def cog_before_invoke(self, ctx: commands.Context):
        ctx.voice_state = self.get_voice_state(ctx)

    @commands.command(name='join', invoke_without_subcommand=True, aliases=['j', 'c'])
    async def _join(self, ctx: commands.Context):
        """Joins a voice channel."""

        try:
            destination = ctx.author.voice.channel
        except AttributeError:
            return await ctx.send(embed=discord.Embed(
                title="You're not connected to a voice channel!",
                color=discord.Color.magenta()
            ), delete_after=5)
        ctx.voice_state = self.get_voice_state(ctx)
        if ctx.voice_state.voice:
            await ctx.voice_state.voice.move_to(destination)
            return

        ctx.voice_state.voice = await destination.connect()

        embed = discord.Embed(
            title=f'Joined: **{ctx.author.voice.channel}**',
            description="",
            color=discord.Color.magenta()
        )
        await ctx.send(embed=embed)

    @commands.command(name='leave', aliases=['disconnect', 'l'])
    async def _leave(self, ctx: commands.Context):
        """Clears the queue and leaves the voice channel."""

        ctx.voice_state = self.get_voice_state(ctx)
        if not ctx.voice_state.voice:
            embed = discord.Embed(
                title='Not connected to any voice channel.',
                description="",
                color=discord.Color.magenta()
            )
            return await ctx.send(embed=embed)
        else:
            await ctx.voice_state.stop()
            embed = discord.Embed(
                title=f'Disconnected from: **{ctx.author.voice.channel}**',
                description="",
                color=discord.Color.magenta()
            )
        await ctx.send(embed=embed)
        ctx.voice_state.voice.cleanup()
        del self.voice_states[ctx.guild.id]

    @commands.command(name='volume', aliases=['v'])
    async def _volume(self, ctx: commands.Context, *, volume: int = None):
        """Sets the volume of the player."""

        ctx.voice_state = self.get_voice_state(ctx)
        if volume is None:
            state = self.get_voice_state(ctx)
            embed = discord.Embed(
                title=f'Player volume: {state.current.source.volume * 100}%',
                description='',
                color=discord.Color.magenta()
            )
            return await ctx.send(embed=embed)

        if not ctx.voice_state.voice.is_playing:
            embed = discord.Embed(
                title='Nothing being played at the moment.',
                description="",
                color=discord.Color.magenta()
            )
            return await ctx.send(embed=embed)

        if volume > 200 or volume < 0:
            embed = discord.Embed(
                title='Volume must be between 0 and 200',
                description="",
                color=discord.Color.magenta()
            )
            return await ctx.send(embed=embed)

        state = self.get_voice_state(ctx)
        state.current.source.volume = volume / 100
        ctx.voice_state.volume = volume / 100

        embed = discord.Embed(
            title=f'Volume of the player set to {volume}%',
            description="",
            color=discord.Color.magenta()
        )
        await ctx.send(embed=embed)

    @commands.command(name='np', aliases=['current', 'playing', 'currentsong', 'nowplaying'])
    async def _now(self, ctx: commands.Context):
        """Displays the currently playing song."""

        vc = self.get_voice_state(ctx)
        if not vc.is_playing:
            embed = discord.Embed(
                title="I am playing nothing!",
                description="",
                color=discord.Color.magenta()
            )
            await ctx.send(embed=embed)
        else:
            curr = timer() - vc.start
            played = YTDLSource.parse_duration(curr)
            embed = discord.Embed(
                title="Now Playing!",
                description='[{0.source.title}]({0.source.url})'.format(vc.current),
                color=discord.Color.blurple()
            )
            embed.add_field(name='Duration', value=vc.current.source.duration, inline=False)
            embed.add_field(name="Played", value=played, inline=False)
            embed.add_field(name='Requested by', value=vc.current.requester.mention, inline=False)
            embed.add_field(name='Uploader', value='[{0.source.uploader}]({0.source.uploader_url})'.format(vc.current),
                            inline=False)
            embed.set_thumbnail(url=vc.current.source.thumbnail)
            return await ctx.send(embed=embed)

    @commands.command(name='pause')
    async def _pause(self, ctx: commands.Context):
        """Pauses the currently playing song."""

        ctx.voice_state = self.get_voice_state(ctx)
        if not ctx.voice_state.voice.is_playing:
            embed = discord.Embed(
                title='Not playing any music right now...',
                description="",
                color=discord.Color.magenta()
            )
            return await ctx.send(embed=embed)

        if ctx.voice_state.voice.is_playing():
            ctx.voice_state.voice.pause()
            await ctx.message.add_reaction('⏯')
            embed = discord.Embed(
                title=f"{ctx.message.author} Paused the song!",
                description="",
                color=discord.Color.magenta()
            )
            await ctx.send(embed=embed)

    @commands.command(name='resume')
    async def _resume(self, ctx: commands.Context):
        """Resumes a currently paused song."""

        ctx.voice_state = self.get_voice_state(ctx)
        if not ctx.voice_state.voice.is_playing:
            embed = discord.Embed(
                title='Not playing any music right now...',
                description="",
                color=discord.Color.magenta()
            )
            await ctx.send(embed=embed)
            return

        if ctx.voice_state.voice.is_paused():
            ctx.voice_state.voice.resume()
            await ctx.message.add_reaction('⏯')
            embed = discord.Embed(
                title=f"{ctx.message.author} Resumed the song!",
                description="",
                color=discord.Color.magenta()
            )
            await ctx.send(embed=embed)

    @commands.command(name='stop')
    async def _stop(self, ctx: commands.Context):
        """Stops playing song and clears the queue."""

        vc = self.get_voice_state(ctx)
        if not vc:
            embed = discord.Embed(
                title='I am not currently playing anything!',
                description="",
                color=discord.Color.magenta()
            )
            await ctx.send(embed=embed)
            return

        if not ctx.voice_client.is_connected():
            embed = discord.Embed(
                title="Not connected to a VC!",
                description="",
                color=discord.Color.magenta()
            )
            await ctx.send(embed=embed)
            return

        else:
            await ctx.message.add_reaction('⏹')
            embed = discord.Embed(
                title="Stopped!",
                description="",
                color=discord.Color.magenta()
            )
            await ctx.send(embed=embed)
            await vc.stop()
            del self.voice_states[ctx.guild.id]

    @commands.command(name='seek')
    async def _seek(self, ctx: commands.Context, pos: int):
        """Seeks to the give position"""

        ctx.voice_state = self.get_voice_state(ctx)
        if not ctx.voice_state.voice.is_playing:
            embed = discord.Embed(
                title='Not playing any music right now...',
                description="",
                color=discord.Color.magenta()
            )
            await ctx.send(embed=embed)
            return
        if pos is None or pos == 0:
            raise commands.MissingRequiredArgument(param=Parameter('pos', int))
        vc = ctx.voice_state
        vc.voice.pause()
        elapsed = timer() - vc.start
        if elapsed > vc.current.source.int_duration:
            return await ctx.send(embed=discord.Embed(
                title="Song has finished!",
                colour=discord.Color.magenta()
            ))
        if pos == -1:
            start_time = 0
        else:
            start_time = elapsed + pos

        vc.current.source = await YTDLSource.create_source(ctx, vc.current.source.url, time=start_time)
        vc.current.source.volume = vc.volume
        # just to get accurate start time...
        if pos == -1:
            vc.start = timer()
        else:
            vc.start = vc.start - pos
        vc.voice.play(vc.current.source, after=vc.play_next_song)
        vc.end = vc.current.source.int_duration
        embed = discord.Embed(
            title=f"Skipped {pos} sec(s)!" if pos > 0 else "Restarting the song!",
            color=discord.Color.magenta()
        )
        return await ctx.send(embed=embed)

    @commands.command(name='skip')
    async def _skip(self, ctx: commands.Context):
        """
        Skip the current song
        """

        ctx.voice_state = self.get_voice_state(ctx)
        if not ctx.voice_state.voice.is_playing:
            embed = discord.Embed(
                title='Not playing any music right now...',
                description="",
                color=discord.Color.magenta()
            )
            await ctx.send(embed=embed)
        else:
            await ctx.message.add_reaction('⏭')
            ctx.voice_state.skip()

    @commands.command(name='clear')
    async def _clear_queue(self, ctx: commands.Context):
        """Clears the queue"""

        ctx.voice_state = self.get_voice_state(ctx)
        if len(ctx.voice_state.songs) == 0:
            return await ctx.send("Empty queue!")
        ctx.voice_state.songs.clear()
        embed = discord.Embed(
            title='Cleared the queue!',
            color=discord.Color.magenta()
        )
        await ctx.send(embed=embed)
        return

    @commands.command(name='queue')
    async def _queue(self, ctx: commands.Context, *, page: int = 1):
        """Shows the player's queue.
        You can optionally specify the page to show. Each page contains 10 elements.
        """

        ctx.voice_state = self.get_voice_state(ctx)
        if len(ctx.voice_state.songs) == 0:
            return await ctx.send('Empty queue.')

        embed, pages = MusicUtils.get_queue(ctx, page)
        view = QueueButton(ctx, page, pages)
        msg = await ctx.send(embed=embed, view=view)
        view.message = msg

    @commands.command(name='shuffle')
    async def _shuffle(self, ctx: commands.Context):
        """Shuffles the queue."""

        ctx.voice_state = self.get_voice_state(ctx)
        if len(ctx.voice_state.songs) == 0:
            embed = discord.Embed(
                title='Empty queue.',
                description="",
                color=discord.Color.magenta()
            )
            return await ctx.send(embed=embed)

        ctx.voice_state.songs.shuffle()
        await ctx.message.add_reaction('✅')
        embed = discord.Embed(
            title=f"{ctx.message.author} Shuffled the queue!",
            description="",
            color=discord.Color.magenta()
        )
        await ctx.send(embed=embed)

    @commands.command(name='remove')
    async def _remove(self, ctx: commands.Context, index: int):
        """Removes a song from the queue at a given index."""

        ctx.voice_state = self.get_voice_state(ctx)
        if len(ctx.voice_state.songs) == 0:
            embed = discord.Embed(
                title='Empty queue.',
                description="",
                color=discord.Color.magenta()
            )
            return await ctx.send(embed=embed)

        if len(ctx.voice_state.songs) < (index - 1):
            return await ctx.send(embed=discord.Embed(
                title="Index out of range!",
                color=discord.Color.magenta()
            ))

        ctx.voice_state.songs.remove(index - 1)
        await ctx.message.add_reaction('✅')
        embed = discord.Embed(
            title=f"{ctx.message.author} Removed a song from the queue!",
            description="",
            color=discord.Color.magenta()
        )
        await ctx.send(embed=embed)

    @commands.command(name='loop')
    async def _loop(self, ctx: commands.Context):
        """Enable/Disable loop"""
        # Loops the currently playing song.
        # Invoke this command again to unloop the song.

        ctx.voice_state = self.get_voice_state(ctx)
        if not ctx.voice_state.voice.is_playing:
            return await ctx.send('Nothing being played at the moment.')

        # Inverse boolean value to loop and unloop.
        ctx.voice_state.loop = not ctx.voice_state.loop
        await ctx.message.add_reaction('✅')

    async def add_to_queue(self, ctx: commands.Context, items: list[dict | MusicItem], name: str = None):

        ctx.voice_state = self.get_voice_state(ctx)

        for video in items:
            try:
                # from online playlist, keys -> title, id
                video_id = video.get("id")
            except AttributeError:
                # from local database, MusicItem
                video_id = video.id
            try:
                source = await YTDLSource.create_source(ctx, video_id)
                await ctx.voice_state.songs.put(Song(source, timer()))
            except yt_dlp.DownloadError as e:
                logger.error(e)
                continue
        embed = discord.Embed(
            title=f'Added playlist {name if name is not None else ""} to the queue!',
            description='',
            color=discord.Color.magenta()
        )
        await ctx.send(embed=embed)

    @commands.group('pl', aliases=['playlist'], invoke_without_command=True)
    async def _playlist(self, ctx: commands.Context, s: str):

        ctx.voice_state = self.get_voice_state(ctx)
        if not ctx.voice_state.voice:
            await ctx.invoke(self._join)

        # check if it's a playlist url or id
        if "://" in s or s.startswith("RD"):
            try:
                playlist_id = parse_qs(urlparse(s).query)['list'][0] or None
                if playlist_id is None:
                    raise HttpError
                items = youtube.playlist(playlist_id)
            except HttpError:
                return await ctx.send(embed=discord.Embed(
                    title='Playlist does not exists!',
                    color=discord.Color.magenta()
                ))
            s = None
        else:
            db = MusicDB(ctx.guild.id)
            db.create_connection()
            items = db.get_playlist_items(s.lower())
            db.close()
            if not MusicUtils.check_db_value(ctx, s, items):
                return
        embed = discord.Embed(
            title='Just a sec!',
            description=f"Adding playlist {s if s is not None else ''} to the queue!",
            color=discord.Color.magenta()
        )
        await ctx.send(embed=embed)
        await asyncio.gather(self.add_to_queue(ctx, items, s))

    @_playlist.command('create', aliases=['c'])
    async def _p_create(self, ctx: commands.Context, playlist_name: str):
        db = MusicDB(ctx.guild.id)
        db.create_connection()
        db.create_playlist(playlist_name.lower())
        db.close()
        return await ctx.send(embed=discord.Embed(
            title=f'Created playlist {playlist_name.capitalize()}!',
            color=discord.Color.magenta()
        ))

    @_playlist.command('add', aliases=['a'])
    async def _p_add(self, ctx: commands.Context, playlist_name: str, *, item: str):
        # video or playlist url
        if "://" in item:
            try:
                if "list=" in item:
                    playlist_id = parse_qs(urlparse(item).query)['list'][0]
                    _items = youtube.playlist(playlist_id)
                else:
                    patt = re.compile(r"((?<=(v|V)/)|(?<=be/)|(?<=(\?|\&)v=)|(?<=embed/))([\w-]+)")
                    result = patt.search(item)
                    if result is None:
                        raise HttpError
                    start, end = result.span()
                    video_id = item[start:end]
                    _items = [youtube.video(video_id)]
            except HttpError:
                return await ctx.send(embed=discord.Embed(
                    title="Invalid playlist/video url!",
                    color=discord.Color.magenta()
                ))
            items = [MusicItem.from_dict(i) for i in _items]
        else:  # search query or video id
            if youtube.video_exists(item):
                items = [MusicItem.from_dict(youtube.video(item))]
            else:
                # get first item from search
                items = [MusicItem.from_dict(youtube.search_video(item)[0])]
        db = MusicDB(ctx.guild.id)
        db.create_connection()
        for video in items:
            db.insert_item(playlist_name.lower(), video)
        db.close()
        return await ctx.send(embed=discord.Embed(
            title=f'Added item to {playlist_name.capitalize()}!',
            color=discord.Color.magenta()
        ))

    @_playlist.command('list', aliases=['l'])
    async def _p_list(self, ctx: commands.Context, playlist_name: str):
        db = MusicDB(ctx.guild.id)
        db.create_connection()
        items = db.get_playlist_items(playlist_name.lower())
        db.close()
        if not MusicUtils.check_db_value(ctx, playlist_name, items):
            return
        _list = "\n".join([str(i) for i in items])
        return await ctx.send(embed=discord.Embed(
            title=playlist_name.capitalize(),
            description=_list,
            color=discord.Color.magenta()
        ))

    @_playlist.command('server', aliases=['s', 'all'])
    async def _p_server(self, ctx: commands.Context):
        db = MusicDB(ctx.guild.id)
        db.create_connection()
        items = db.get_playlists()
        db.close()
        if not MusicUtils.check_db_value(ctx, None, items):
            return
        _list = "\n".join([str(i).capitalize() for i in items])
        return await ctx.send(embed=discord.Embed(
            title='Playlists',
            description=_list,
            color=discord.Color.magenta()
        ))

    @_playlist.command('remove', aliases=['r', 'delete', 'd'])
    async def _p_remove(self, ctx: commands.Context, playlist_name: str, id: int):
        db = MusicDB(ctx.guild.id)
        db.create_connection()
        item = db.delete_from_id(playlist_name.lower(), id)
        db.close()
        if not MusicUtils.check_db_value(ctx, playlist_name, item):
            return
        item.id = None
        return await ctx.send(embed=discord.Embed(
            title=f"Removed an item from {playlist_name.capitalize()}",
            description=str(item),
            color=discord.Color.magenta()
        ))

    @_playlist.command('removen', aliases=['rn', 'deleten', 'dn'])
    async def _p_remove_n(self, ctx: commands.Context, playlist_name: str, *, item: str):
        db = MusicDB(ctx.guild.id)
        db.create_connection()
        _items = db.get_items_from_name(playlist_name.lower(), item)
        if not MusicUtils.check_db_value(ctx, playlist_name, _items):
            return
        if len(_items) != 1:
            await ctx.send(embed=discord.Embed(
                title='Items found!',
                description="\n".join([str(i) for i in _items]),
                color=discord.Color.magenta()
            ).set_footer(text="Reply with the id within 60 seconds!"))

            def check(message: discord.Message):
                return message.author == ctx.message.author

            msg = await self.bot.wait_for('message', check=check, timeout=60)
            _id = msg.content.strip()
        else:
            _id = _items[0].id
        _item = db.delete_from_id(playlist_name.lower(), _id)
        db.close()
        return await ctx.send(embed=discord.Embed(
            title=f'Removed an item from {playlist_name.capitalize()}',
            description=str(_item),
            color=discord.Color.magenta()
        ))

    @commands.command(name='search', aliases=['s'])
    async def _search(self, ctx: commands.Context, *, query: str):
        if query is None or len(query) == 0:
            await ctx.message.delete()
            return await ctx.send("Search query required!", delete_after=5)

        data = youtube.search_video(query)
        search_result = ''
        for i, item in enumerate(data, start=1):
            _id = item[1]
            url = _id if "://" in _id else f"https://youtu.be/{_id}"
            val = f"**{i}. [{item[0]}]({url})**"
            search_result += val + "\n\n"

        return await ctx.send(embed=discord.Embed(
            title="Search results!",
            description=search_result,
            color=discord.Color.magenta()
        ))

    @commands.command(name='play', aliases=['p'])
    async def _play(self, ctx: commands.Context, *, search: str):
        """Plays a song.
        If there are songs in the queue, this will be queued until the
        other songs finished playing.
        This command automatically searches from various sites if no URL is provided.
        A list of these sites can be found here: https://rg3.github.io/youtube-dl/supportedsites.html
        """

        ctx.voice_state = self.get_voice_state(ctx)
        if not ctx.voice_state.voice:
            await ctx.invoke(self._join)

        async with ctx.typing():
            source = await YTDLSource.create_source(ctx, search)
            song = Song(source, timer())

            await ctx.voice_state.songs.put(song)
            embed = discord.Embed(
                title='Enqueued!',
                description='[{0.source.title}]({0.source.url})'.format(song),
                color=discord.Color.magenta()
            )
            await ctx.send(embed=embed)

    @_join.before_invoke
    @_play.before_invoke
    async def ensure_voice_state(self, ctx: commands.Context):

        ctx.voice_state = self.get_voice_state(ctx)
        if not ctx.author.voice or not ctx.author.voice.channel:
            embed = discord.Embed(
                title="You are not connected to a voice channel!",
                description='',
                color=discord.Color.magenta()
            )
            await ctx.send(embed=embed)
            raise commands.CommandError('You are not connected to any voice channel.')

        if ctx.voice_client:
            if ctx.voice_client.channel != ctx.author.voice.channel:
                raise commands.CommandError('Bot is already in a voice channel.')


async def setup(bot: commands.Bot):
    await bot.add_cog(Music(bot))
