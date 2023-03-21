import asyncio
import datetime
import itertools
import json
import logging
import math
import random
from sqlite3 import OperationalError
import discord
import yt_dlp
from async_timeout import timeout
from discord.ext import commands

import pafy
from db.music import *
from utils.playlist import get_playlist
from utils.search import search_video

bot = commands.Bot(command_prefix="'", help_command=None, intents=discord.Intents.all())


class VoiceError(Exception):
    pass


class YTDLError(Exception):
    pass


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
        'default_search': 'ytsearch',
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

        with cls.ytdlp as ytdl:
            info = ytdl.sanitize_info(ytdl.extract_info(search, download=False))

        if 'entries' in info:
            info = info['entries'][0]

        opt = cls.FFMPEG_OPTIONS
        opt['options'] = f'-vn -ss {time}'
        # opt['options'] = f'-vn -ss {time} -af "{filter}" -b:a 320k'
        return cls(ctx, discord.FFmpegPCMAudio(source=info['url'], **opt), data=info)

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
    __slots__ = ('source', 'requester')

    def __init__(self, source: YTDLSource):
        self.source = source
        self.requester = source.requester

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


class SongItem:
    def __init__(self, ctx, value, id: str = None, time: int = 0):
        self.time = time
        self.ctx = ctx
        self.name = value
        self.id = id

    def __str__(self):
        return '**{0.name}**'.format(self)

    async def create_song(self) -> Song:
        source = await YTDLSource.create_source(self.ctx, self.name, time=self.time)
        return Song(source)


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
        self.start = datetime.datetime.now()
        self.end = 0
        self.voice = None
        self.next = asyncio.Event()
        self.songs = SongQueue()

        self._loop = False
        self._volume = 0.5

        self.audio_player = bot.loop.create_task(self.audio_player_task())

        self.song_item = None

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

    async def audio_player_task(self):
        while True:
            self.next.clear()

            if not self.loop:
                # Try to get the next song within 3 minutes.
                # If no song will be added to the queue in time,
                # the player will disconnect due to performance
                # reasons.
                try:
                    async with timeout(60):  # 1(3) minutes
                        self.song_item = await self.songs.get()
                        self.current = await self.song_item.create_song()
                except asyncio.TimeoutError:

                    self.bot.loop.create_task(self.stop())
                    return
            else:
                await self.songs.put(self.song_item)
                self.song_item = await self.songs.get()
                self.current = await self.song_item.create_song()
            self.current.source.volume = self._volume
            self.voice.play(self.current.source, after=self.play_next_song)
            self.end = self.current.source.int_duration
            self.start = datetime.datetime.now()
            await self.current.source.channel.send(embed=self.current.create_embed())

            await self.next.wait()

    def play_next_song(self, error=None):

        if error:
            logging.error(error)

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


class Context(commands.Context):
    voice_state: VoiceState = None


async def import_playlist(ctx: commands.Context, attach: discord.Attachment):
    playlists = get_playlists(ctx.guild.id)
    await attach.save(f"tmp/playlist.{ctx.guild.id}.1.json")
    with open(f"tmp/playlist.{ctx.guild.id}.1.json", 'r') as f:
        data = json.load(f)
    pl_name = data['playlist_name']
    if playlists is not None:
        if pl_name in playlists:
            return await ctx.send(
                embed=discord.Embed(title=f"Playlist with name: **{pl_name.capitalize()}** already exists!",
                                    color=discord.Color.magenta()))
    try:
        create_playlist(ctx.guild.id, pl_name)
    except OperationalError:
        create_guild_playlist(ctx.guild.id)
        create_playlist(ctx.guild.id, pl_name)
    for key in data.keys():
        if key == "playlist_name":
            continue
        tmp = data[key]
        name, url = tmp["name"], tmp["url"]

        insert_playlist_data(ctx.guild.id, pl_name, [name, url])
    os.remove(f"tmp/playlist.{ctx.guild.id}.1.json")
    await ctx.send(embed=discord.Embed(title=f"Imported playlist: **{pl_name.capitalize()}**",
                                       color=discord.Color.magenta()))


class Music(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.voice_states: dict[int, VoiceState] = {}

    def get_voice_state(self, ctx: Context) -> VoiceState:
        state = self.voice_states.get(ctx.guild.id)
        if not state:
            state = VoiceState(self.bot, ctx)
            self.voice_states[ctx.guild.id] = state

        return state

    def cog_unload(self):
        for state in self.voice_states.values():
            self.bot.loop.create_task(state.stop())

    def cog_check(self, ctx: Context):
        if not ctx.guild:
            raise commands.NoPrivateMessage('This command can\'t be used in DM channels.')

        return True

    async def cog_before_invoke(self, ctx: Context):
        ctx.voice_state = self.get_voice_state(ctx)

    @commands.command(name='join', invoke_without_subcommand=True, aliases=['j', 'c'])
    async def _join(self, ctx: Context):
        """Joins a voice channel."""

        try:
            destination = ctx.author.voice.channel
        except AttributeError:
            return await ctx.send(embed=discord.Embed(
                title="You're not connected to a voice channel!",
                color=discord.Color.magenta()
            ), delete_after=5)
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
    # @commands.has_permissions(manage_guild=True)
    async def _leave(self, ctx: Context):
        """Clears the queue and leaves the voice channel."""

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
    async def _volume(self, ctx: Context, *, volume: int = None):
        """Sets the volume of the player."""

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
    async def _now(self, ctx: Context):
        """Displays the currently playing song."""
        vc = ctx.voice_state
        diff = (datetime.datetime.now() - vc.start).total_seconds()
        if not ctx.voice_state.voice.is_playing:
            embed = discord.Embed(
                title="I am playing nothing!",
                description="",
                color=discord.Color.magenta()
            )
            await ctx.send(embed=embed)
        else:
            f = "🟪 "
            r = "🟥 "
            played = YTDLSource.parse_duration(diff)
            prt = round((diff / vc.end) * 100, -1) / 10
            com = f * int(prt)
            rem = r * int(10 - prt)

            embed = discord.Embed(
                title="Now Playing!",
                description='[{0.source.title}]({0.source.url})'.format(vc.current),
                color=discord.Color.blurple()
            )
            embed.add_field(name='Duration', value=vc.current.source.duration, inline=False)
            embed.add_field(name="Played", value=played, inline=False)
            embed.add_field(name="", value=com + rem, inline=False)
            embed.add_field(name='Requested by', value=vc.current.requester.mention, inline=False)
            embed.add_field(name='Uploader', value='[{0.source.uploader}]({0.source.uploader_url})'.format(vc.current),
                            inline=False)
            embed.set_thumbnail(url=vc.current.source.thumbnail)
            return await ctx.send(embed=embed)

    @commands.command(name='pause')
    # @commands.has_permissions(manage_guild=True)
    async def _pause(self, ctx: Context):
        """Pauses the currently playing song."""
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
    # @commands.has_permissions(manage_guild=True)
    async def _resume(self, ctx: Context):
        """Resumes a currently paused song."""
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
    # @commands.has_permissions(manage_guild=True)
    async def _stop(self, ctx: Context):
        """Stops playing song and clears the queue."""

        vc = ctx.voice_client

        if not vc:
            embed = discord.Embed(
                title='I am not currently playing anything!',
                description="",
                color=discord.Color.magenta()
            )
            await ctx.send(embed=embed)
            return

        if not vc.is_connected():
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
            await ctx.voice_state.stop()
            del self.voice_states[ctx.guild.id]

    @commands.command(name='seek')
    async def _seek(self, ctx: Context, t: int):
        """Seeks to the give position"""

        if not ctx.voice_state.voice.is_playing:
            embed = discord.Embed(
                title='Not playing any music right now...',
                description="",
                color=discord.Color.magenta()
            )
            await ctx.send(embed=embed)
            return

        vc = self.get_voice_state(ctx)
        vc.voice.pause()
        start_t = vc.start
        now = datetime.datetime.now()
        elapsed = now - start_t
        played_t = elapsed.total_seconds()
        new_t = played_t + t
        vc.current.source = await YTDLSource.create_source(vc._ctx, vc.current.source.url, time=new_t)
        vc.current.source.volume = vc._volume
        vc.voice.play(vc.current.source, after=vc.play_next_song)
        vc.end = vc.current.source.int_duration
        vc.start = datetime.datetime.now()
        embed = discord.Embed(
            title=f"Skipped {t} sec(s)!",
            color=discord.Color.magenta()
        )
        return await ctx.send(embed=embed)

    @commands.command(name='skip')
    async def _skip(self, ctx: Context):
        """
        Skip the current song
        """

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
    async def _clear_queue(self, ctx: Context):
        """Clears the queue"""
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
    async def _queue(self, ctx: Context, *, page: int = 1):
        """Shows the player's queue.
        You can optionally specify the page to show. Each page contains 10 elements.
        """

        if len(ctx.voice_state.songs) == 0:
            return await ctx.send('Empty queue.')

        items_per_page = 10
        pages = math.ceil(len(ctx.voice_state.songs) / items_per_page)

        start = (page - 1) * items_per_page
        end = start + items_per_page

        queue = ''
        for i, song in enumerate(ctx.voice_state.songs[start:end], start=start):
            try:
                name = song.name
                _id = song.id
                if _id is None:
                    raise AttributeError
                if "://" not in _id:
                    _id = f"https://youtu.be/{_id}"
                queue += '`{0}.` [**{1}**]({2})\n'.format(i + 1, name, _id)
            except AttributeError:
                queue += '`{0}.` **{1}**\n'.format(i + 1, song.name)

        embed = (discord.Embed(description='**{} tracks:**\n\n{}'.format(len(ctx.voice_state.songs), queue))
                 .set_footer(text='Viewing page {}/{}'.format(page, pages)))
        await ctx.send(embed=embed)

    @commands.command(name='shuffle')
    async def _shuffle(self, ctx: Context):
        """Shuffles the queue."""

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
    async def _remove(self, ctx: Context, index: int):
        """Removes a song from the queue at a given index."""

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
    async def _loop(self, ctx: Context):
        """Enable/Disable loop"""
        # Loops the currently playing song.
        # Invoke this command again to unloop the song.

        if not ctx.voice_state.voice.is_playing:
            return await ctx.send('Nothing being played at the moment.')

        # Inverse boolean value to loop and unloop.
        ctx.voice_state.loop = not ctx.voice_state.loop
        await ctx.message.add_reaction('✅')

    async def add_to_queue(self, ctx: Context, items, name: str = None):
        if ctx.voice_state.voice is None:
            return
        else:
            await ctx.invoke(self._join)
        try:
            for i, video in enumerate(items):
                try:
                    # from online playlist, keys -> title, id
                    video_name = video.get("title")
                    video_id = video.get("id")
                except AttributeError:
                    # from local database, values -> (title, id, index)
                    video_name = video[0]
                    video_id = video[1]
                song_item = SongItem(ctx, video_name, video_id)
                await ctx.voice_state.songs.put(song_item)
            new_embed = discord.Embed(
                title=f'Added playlist {name if not name is None else ""} to the queue!',
                description='',
                color=discord.Color.magenta()
            )
            await ctx.send(embed=new_embed)
            if not ctx.voice_state.voice.is_playing:
                await self.bot.loop.create_task(ctx.voice_state.audio_player_task())
        except yt_dlp.DownloadError as e:
            # await ctx.send('An error occurred while processing this request: ```{}```'.format(str(e)))
            await self.add_to_queue(ctx, items[i + 1:], name)

    @commands.command(name='pl', aliases=['playlist'])
    async def _playlist(self, ctx: Context, *, playlist: str):
        """Plays a playlist
        If a song is playing then the playlist's videos are added to the queue.
        """

        if playlist.startswith("export"):
            playlist_l = playlist.replace("export ", "")
            if len(playlist_l.strip()) == 0:
                return await ctx.send("Playlist name required!", delete_after=5)
            pl_name = playlist_l.lower()
            try:
                data = get_playlist_data(ctx.guild.id, pl_name)
            except OperationalError:
                return await ctx.send("Playlist does not exists", delete_after=5)
            if data is None:
                return await ctx.send("Empty playlist!", delete_after=5)
            exp = {"playlist_name": pl_name}
            for item in data:
                name, url, _id = item
                exp[_id] = {
                    "name": name,
                    "url": url
                }
            with open(f"tmp/playlist.{ctx.guild.id}.0.json", 'w', encoding='utf-8') as f:
                json.dump(exp, f, indent=4)
            await ctx.send(embed=discord.Embed(title="Exported playlist file!", color=discord.Color.magenta())
                           , file=discord.File(fr"./tmp/playlist.{ctx.guild.id}.0.json",
                                               filename=f"{pl_name}-export.json"))
            os.remove(f"tmp/playlist.{ctx.guild.id}.0.json")
            return

        if playlist.startswith("import"):
            attach = ctx.message.attachments
            if len(attach) == 0:
                return await ctx.send("Attach the file along with command!")

            await ctx.send(embed=discord.Embed(title="Importing playlist!",
                                               color=discord.Color.magenta()))
            for file in attach:
                self.bot.loop.create_task(import_playlist(ctx, file))
            return

        if playlist.startswith("create"):
            playlist_l = playlist.replace("create ", "")
            if len(playlist_l.strip()) == 0:
                return await ctx.send("Playlist name required!")
            name = playlist_l.lower()
            try:
                create_playlist(ctx.guild.id, name)
            except OperationalError:
                create_guild_playlist(ctx.guild.id)
                create_playlist(ctx.guild.id, name)
            embed = discord.Embed(
                title='Created playlist!',
                description=f'**{name.capitalize()}**',
                color=discord.Color.magenta()
            )
            return await ctx.send(embed=embed)

        if playlist.startswith("add"):
            playlist_list = playlist.split(" ")
            print(playlist_list)
            n = playlist_list.pop(0)
            try:
                name = playlist_list.pop()
            except IndexError:
                return await ctx.send("Playlist name missing!")
            query = " ".join(playlist_list)
            if query == " " or query == '':
                return await ctx.send("Playlist item missing!")

            if "://" in query:
                if "&" in query or "playlist" in query:
                    if "&" in query:
                        link = query.split("&")[1].replace("list=", '')
                    if "playlist" in query:
                        link = query.replace("https://youtube.com/playlist?list=", "")
                    items = get_playlist(link)
                    itms = []
                    for item in items:
                        data = [item.get('title'), item.get('id')]
                        insert_playlist_data(ctx.guild.id, name, data)
                        itms.append(data[0])
                    itm = "\n".join(itms)
                    embed = discord.Embed(
                        title=f'Added {len(itms)} to {name.capitalize()}!',
                        description=f'```{itm}```',
                        color=discord.Color.magenta()
                    )
                    await ctx.send(embed=embed)
                    return
                video = pafy.new(query)
                data = [video.title, video.videoid]
            else:
                data = search_video(query)[0]
            insert_playlist_data(ctx.guild.id, name, data)
            embed = discord.Embed(
                title=f'Added to {name.capitalize()}!',
                description=f'**{data[0]}**',
                color=discord.Color.magenta()
            )
            await ctx.send(embed=embed)
            return

        elif "://" in playlist:
            if not ctx.voice_state.voice:
                await ctx.invoke(self._join)
            if "&" in playlist:
                link = playlist.split("&")[1].replace("list=", '')
            else:
                link = playlist.replace("https://www.youtube.com/playlist?list=", "")
            items = get_playlist(link)
            embed = discord.Embed(
                title='Just a sec!',
                description="Adding playlist to the queue!",
                color=discord.Color.magenta()
            )
            tmp_embed = await ctx.send(embed=embed)
            asyncio.get_event_loop().create_task(self.add_to_queue(ctx, items))
            return

        elif playlist.startswith("guild") or playlist.startswith("server"):
            items = get_playlists(ctx.guild.id)
            embed = discord.Embed(
                title='Server Playlists!',
                description=("```" + ", ".join(items) + "```") if items is not None else ("```" + 'None' + "```"),
                color=discord.Color.magenta()
            )
            return await ctx.send(embed=embed)

        elif playlist.startswith("list"):
            playlist_list = playlist.split(" ")
            n = playlist_list.pop(0)
            name = " ".join(playlist_list)
            if name == "":
                embed = discord.Embed(
                    title='Error!',
                    description=f'Playlist name required!',
                    color=discord.Color.magenta()
                )
                return await ctx.send(embed=embed)
            try:
                items = get_playlist_items(ctx.guild.id, name)
            except OperationalError:
                embed = discord.Embed(
                    title='Error!',
                    description=f'Playlist `{name}` does not exist!',
                    color=discord.Color.magenta()
                )
                return await ctx.send(embed=embed)
            if items is None:
                embed = discord.Embed(
                    title='Empty playlist!',
                    color=discord.Color.magenta()
                )
                return await ctx.send(embed=embed)
            itm = ''
            for item in items:
                t = str(item[2]) + ". " + item[0]
                itm += t + "\n"
            embed = discord.Embed(
                title=f'{name.capitalize()} items!',
                description=f"```{itm.strip()}```",
                color=discord.Color.magenta()
            )
            return await ctx.send(embed=embed)

        elif playlist.startswith("remove"):
            playlist_list = playlist.split(" ")
            n = playlist_list.pop(0)
            try:
                index = playlist_list.pop(0)
            except IndexError:
                return await ctx.send("Item index required!")

            try:
                name = playlist_list.pop(-1)
            except IndexError:
                return await ctx.send("Playlist name required!")

            try:
                item = remove_playlist_item(ctx.guild.id, name, int(index))
            except OperationalError:
                return await ctx.send("Playlist does not exists!")
            embed = discord.Embed(
                title=f'Removed from: {name.capitalize()}',
                description=f"[{item[0]}]({item[1]})",
                color=discord.Color.magenta()
            )
            return await ctx.send(embed=embed)

        else:
            if not ctx.voice_state.voice:
                await ctx.invoke(self._join)
            try:
                items = get_playlist_data(ctx.guild.id, playlist)
            except OperationalError:
                return await ctx.send("Playlist does not exist!")
            if items is None:
                return await ctx.send("Playlist name required!")
            if ctx.voice_state.voice is not None:
                embed = discord.Embed(
                    title='Just a sec!',
                    description=f"Adding playlist {playlist.capitalize()} to the queue!",
                    color=discord.Color.magenta()
                )
                await ctx.send(embed=embed)
                self.bot.loop.create_task(self.add_to_queue(ctx, items, playlist))
            return

    # @commands.command(name='f', aliases=['filter'])
    # async def _filter(self, ctx: Context, *, filter: int):
    #     t = datetime.datetime.now() - ctx.voice_state.start
    #     e = ctx.voice_state.end
    #     if t.seconds < e:
    #         s = int(t.seconds)
    #         if filter != 10 and filter < 10:
    #             f = YTDLSource.FILTERS[filter]
    #             try:
    #                 source = await YTDLSource.create_source(ctx, ctx.voice_state.current.source.url, time=s, filter=f)
    #                 ctx.voice_state.voice.source = source

    #             except Exception as e:
    #                 print(e)
    #             return await ctx.send("Adding filter!")
    #         else:
    #             source = await YTDLSource.create_source(ctx, ctx.voice_state.current.source.url, time=s)
    #     else:
    #         embed = discord.Embed(
    #             title='Not playing any music right now...',
    #             description="",
    #             color=discord.Color.magenta()
    #         )
    #         await ctx.send(embed=embed)

    @commands.command(name='play', aliases=['p'])
    async def _play(self, ctx: Context, *, search: str):
        """Plays a song.
        If there are songs in the queue, this will be queued until the
        other songs finished playing.
        This command automatically searches from various sites if no URL is provided.
        A list of these sites can be found here: https://rg3.github.io/youtube-dl/supportedsites.html
        """

        if not ctx.voice_state.voice:
            await ctx.invoke(self._join)

        async with ctx.typing():
            # try:
            #     source = await YTDLSource.create_source(ctx, search, loop=self.bot.loop)
            # except YTDLError as e:
            #     await ctx.send('An error occurred while processing this request: {}'.format(str(e)))
            # else:
            song = SongItem(ctx, search)

            await ctx.voice_state.songs.put(song)
            embed = discord.Embed(
                title='Enqueued {}'.format(str(song)),
                description="",
                color=discord.Color.magenta()
            )
            await ctx.send(embed=embed)

    @_join.before_invoke
    @_play.before_invoke
    async def ensure_voice_state(self, ctx: Context):
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
