import asyncio
import ai
import discord
import youtube_dl
import json
import requests
from discord.ext import commands

intents = discord.Intents().all()

# Suppress noise about console usage from errors
youtube_dl.utils.bug_reports_message = lambda: ''

ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0'  # bind to ipv4 since ipv6 addresses cause issues sometimes
}

ffmpeg_options = {
    'options': '-vn'
}

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)

bot = commands.Bot(command_prefix='!', intents=intents,
                   description='The best bot in the whole world!')


class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)

        self.data = data

        self.title = data.get('title')
        self.url = data.get('url')

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))

        if 'entries' in data:
            # take first item from a playlist
            data = data['entries'][0]

        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)


class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def join(self, ctx, *, channel: discord.VoiceChannel):
        """Joins a voice channel"""

        if ctx.voice_client is not None:
            return await ctx.voice_client.move_to(channel)

        await channel.connect()

    @commands.command()
    async def play(self, ctx, *, query):
        """Plays a file from the local filesystem"""

        source = discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(query))
        ctx.voice_client.play(source, after=lambda e: print('Player error: %s' % e) if e else None)

        await ctx.send('Now playing: {}'.format(query))

    @commands.command()
    async def yt(self, ctx, *, url):
        """Plays from a url (almost anything youtube_dl supports)"""

        async with ctx.typing():
            player = await YTDLSource.from_url(url, loop=self.bot.loop)
            ctx.voice_client.play(player, after=lambda e: print('Player error: %s' % e) if e else None)

        await ctx.send('Now playing: {}'.format(player.title))

    @commands.command()
    async def stream(self, ctx, *, url):
        """Streams from a url (same as yt, but doesn't predownload)"""

        async with ctx.typing():
            player = await YTDLSource.from_url(url, loop=self.bot.loop, stream=True)
            ctx.voice_client.play(player, after=lambda e: print('Player error: %s' % e) if e else None)

        await ctx.send('Now playing: {}'.format(player.title))

    @commands.command()
    async def volume(self, ctx, volume: int):
        """Changes the player's volume"""

        if ctx.voice_client is None:
            return await ctx.send('Not connected to a voice channel.')

        ctx.voice_client.source.volume = volume / 100
        await ctx.send('Changed volume to {}%'.format(volume))

    @commands.command()
    async def stop(self, ctx):
        """Stops and disconnects the bot from voice"""

        await ctx.voice_client.disconnect()

    @play.before_invoke
    @yt.before_invoke
    @stream.before_invoke
    async def ensure_voice(self, ctx):
        if ctx.voice_client is None:
            if ctx.author.voice:
                await ctx.author.voice.channel.connect()
            else:
                await ctx.send('You are not connected to a voice channel.')
                raise commands.CommandError('Author not connected to a voice channel.')
        elif ctx.voice_client.is_playing():
            ctx.voice_client.stop()


class Picture(commands.Cog):
    @commands.command()
    async def fox(self, ctx):
        """Sends random picture of fox"""
        response = requests.get('https://some-random-api.ml/img/fox')
        json_data = json.loads(response.text)

        embed = discord.Embed(color=0xff9900, title='Random Fox')
        embed.set_image(url=json_data['link'])
        await ctx.send(embed=embed)

    @commands.command()
    async def meme(self, ctx):
        """Sends random meme"""
        response = requests.get('https://some-random-api.ml/meme')
        json_data = json.loads(response.text)

        embed = discord.Embed(color=0xff9900, title=json_data['caption'])
        embed.set_image(url=json_data['image'])
        await ctx.send(embed=embed)


class Manage(commands.Cog):
    @commands.command()
    async def kick(self, ctx, member: discord.Member, *, reason=None):
        """Kicks named user"""
        await member.kick(reason=reason)
        await ctx.send(f'User {member.name} has been kicked')

    @commands.command()
    async def ban(self, ctx, member: discord.Member, *, reason=None):
        """Bans named user"""
        await member.ban(reason=reason)
        await ctx.send(f'User {member.name} has been banned')

    @commands.command()
    async def unban(self, ctx, member):
        """Unbans named user"""
        banned_users = await ctx.guild.bans()
        member_name, member_discriminator = member.split('#')

        for ban_entry in banned_users:
            user = ban_entry.user

            if (user.name, user.discriminator) == (member_name, member_discriminator):
                await ctx.guild.unban(user)
                await ctx.send(f'User {user.mention} has been unbanned')
                return

    @commands.command()
    async def mute(self, ctx, member: discord.Member, *, reason=None):
        """Mutes user"""
        guild = ctx.guild
        muted_role = discord.utils.get(guild.roles, name='Muted')

        if not muted_role:
            muted_role = await guild.create_role(name='Muted')

            for channel in guild.channels:
                await channel.set_permissions(muted_role, speak=False, send_messages=False, read_message_history=True)
        embed = discord.Embed(title='mute', description=f'{member.mention} has been muted ',
                              colour=0xff9900)
        embed.add_field(name='reason:', value=reason, inline=False)
        await ctx.send(embed=embed)
        await member.add_roles(muted_role, reason=reason)
        await member.send(f' you have been muted from: {guild.name} reason: {reason}')

    @commands.command()
    async def unmute(self, ctx, member: discord.Member, *, reason=None):
        """Unmutes muser"""
        muted_role = discord.utils.get(ctx.guild.roles, name='Muted')

        await member.remove_roles(muted_role)
        await member.send(f' you have unmuted from: {ctx.guild.name} reason: {reason}')
        embed = discord.Embed(title='unmute', description=f'{member.mention} has been unmuted',
                              colour=0xff9900)
        embed.add_field(name='reason:', value=reason, inline=False)
        await ctx.send(embed=embed)


class NeuralNetwork(commands.Cog):
    @commands.command()
    async def dialogue(self, ctx):
        """How to talk to a bot"""
        await ctx.reply('Tag me if you want to talk')


@bot.event
async def on_ready():
    print('Logged in as {0} ({0.id})'.format(bot.user))
    print('------')


@bot.event
async def on_message(message):
    if message.author.id == bot.user.id:
        return
    if message.content == 'a':
        await message.reply('boba'.format(message), mention_author=True)
    if bot.user.mentioned_in(message):
        inp = message.content
        results = ai.model.predict([ai.bag_of_words(inp, ai.words)])[0]
        results_index = ai.numpy.argmax(results)
        tag = ai.labels[results_index]

        if results[results_index] > 0.7:
            for tg in ai.data['intents']:
                if tg['tag'] == tag:
                    responses = tg['responses']

            bot_response = ai.random.choice(responses)
            await message.reply(bot_response.format(message), mention_author=True)
        else:
            await message.reply('I did not get that. Try one more time.'.format(message), mention_author=True)
    await bot.process_commands(message)


bot.add_cog(NeuralNetwork(bot))
bot.add_cog(Music(bot))
bot.add_cog(Picture(bot))
bot.add_cog((Manage(bot)))
bot.run('ODMyNjEwOTg2NDU1NDY2MDQ2.YHmTaA.hJOqvotNH2huUaTeAhgLxcOZQZI')
