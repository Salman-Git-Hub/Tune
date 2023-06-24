import os
from typing import Optional, Literal
import psutil
import humanize
import discord
from discord.ext import commands


class UtilCogs(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def load_ext(self, extension: list[str]):
        for ext in extension:
            try:
                await self.bot.reload_extension(f"cogs.{ext}")
            except Exception as e:
                if isinstance(e, commands.ExtensionNotLoaded) or isinstance(e, commands.ExtensionNotFound):
                    await self.bot.load_extension(f"cogs.{ext}")

    @commands.is_owner()
    @commands.command(name='reload')
    async def _reload(self, ctx: commands.Context, cog: str = None):
        await ctx.message.delete()
        if cog is None:
            return await ctx.send("Cog name needed!", delete_after=5)
        cogs = [file[:-3] for file in os.listdir("./cogs") if file.endswith(".py")]
        if cog not in cogs and cog != "all":
            return await ctx.send(f"Cog `{cog}` does not exists!", delete_after=5)

        embed = discord.Embed(
            title="Reloading...",
            description=f"Extension: **{cog if cog != 'all' else ', '.join(cogs)}**",
            color=discord.Color.brand_red()
        )
        msg = await ctx.send(embed=embed)
        if cog == "all":
            await self.load_ext(cogs)
        else:
            await self.load_ext([cog])
        await msg.add_reaction("👍")
        await msg.delete(delay=5)
        return

    @commands.hybrid_command(name='usage', aliases=['u', 'status', 'stat'])
    async def usage_(self, ctx: commands.Context):
        freq = psutil.cpu_freq().current
        cpu_u = psutil.cpu_percent()
        ram_u = psutil.virtual_memory().percent
        ram_t = psutil.virtual_memory().total
        embed = discord.Embed(
            title='Tune Status',
            description='',
            color=discord.Color.green()
        )
        embed.add_field(name='CPU Usage', value=f"{cpu_u:.2f}%", inline=True)
        embed.add_field(name='CPU Frequency', value=f"{freq:.2f} Hz", inline=False)
        embed.add_field(name='RAM Usage', value=f"{ram_u:.2f}" + "/100 %", inline=True)
        embed.add_field(name='Total RAM', value=humanize.naturalsize(ram_t), inline=False)
        embed.set_thumbnail(url="https://img.icons8.com/external-kmg-design-flat-kmg-design/64/undefined/external"
                                "-statistics-marketing-kmg-design-flat-kmg-design.png")

        return await ctx.send(embed=embed)

    @commands.is_owner()
    @commands.guild_only()
    @commands.hybrid_command(name='sync')
    async def _sync_commands(self, ctx: commands.Context, guilds: commands.Greedy[discord.Guild],
                             mode: Optional[Literal['~', '*', '^']] = None):
        if not guilds:
            if mode == '~':
                await ctx.bot.tree.sync(guild=ctx.guild)
                msg = "Synced current server!"
            elif mode == '*':
                await ctx.bot.tree.sync()
                ctx.bot.tree.copy_global_to(guild=ctx.guild)
                msg = 'Copied commands to current server!'
            elif mode == '^':
                ctx.bot.tree.clear_commands(guild=ctx.guild)
                await ctx.bot.tree.sync(guild=ctx.guild)
                msg = "Cleared all commands and synced!"
            else:
                await ctx.bot.tree.sync()
                msg = "Global Sync!"
            return await ctx.send(msg, ephemeral=True)
        for guild in guilds:
            try:
                await ctx.bot.tree.sync(guild=guild)
            except discord.HTTPException:
                pass
        return await ctx.send("Synced commands in given servers!")


async def setup(bot):
    await bot.add_cog(UtilCogs(bot))
