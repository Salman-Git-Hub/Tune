import discord
from discord.ext import commands
from discord.ext.commands import CommandNotFound, MissingPermissions, \
            MissingRequiredArgument, BotMissingPermissions, NotOwner
import logging

logger = logging.getLogger("discord")


class ErrorCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.img = 'https://c.tenor.com/fzCt8ROqlngAAAAM/error-error404.gif'

    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error: commands.CommandError):
        if isinstance(error, CommandNotFound):
            cmd_name = error.args[0].replace('Command "', '').replace('" is not found', '')
            embed = discord.Embed(
                title='Command Error  ❌',
                description=f"Command `{cmd_name}` does not exists!\n\n**Try `'help`**",
                color=discord.Color.red()
            )
            embed.set_thumbnail(url=self.img)
            await ctx.message.delete()
            return await ctx.send(embed=embed, delete_after=10)

        elif isinstance(error, MissingRequiredArgument):
            param = error.param
            embed = discord.Embed(
                title='Missing Argument  ❌',
                description=f"Missing argument `{param.name}`",
                color=discord.Color.red()
            )
            embed.set_thumbnail(url=self.img)
            await ctx.message.delete()
            return await ctx.send(embed=embed, delete_after=10)

        elif isinstance(error, MissingPermissions):
            perms = ", ".join(error.missing_perms)
            embed = discord.Embed(
                title='Missing Permissions  ❌',
                description=f"You're don't have `{perms}` permission",
                color=discord.Color.red()
            )
            embed.set_thumbnail(url=self.img)
            await ctx.message.delete()
            return await ctx.send(embed=embed, delete_after=10)

        elif isinstance(error, BotMissingPermissions):
            perms = ', '.join(error.missing_perms)
            embed = discord.Embed(
                title='Missing Permissions  ❌',
                description=f"Bot doesn't have`{perms}` permission",
                color=discord.Color.red()
            )
            embed.set_thumbnail(url=self.img)
            await ctx.message.delete()
            return await ctx.send(embed=embed, delete_after=10)

        elif isinstance(error, NotOwner):
            embed = discord.Embed(
                title='Owner command!  ❌',
                description='This command can only be used by the owner',
                color=discord.Color.red()
            )
            embed.set_thumbnail(url=self.img)
            await ctx.message.delete()
            return await ctx.send(embed=embed, delete_after=10)
        logger.error(error)


async def setup(bot):
    await bot.add_cog(ErrorCog(bot))
