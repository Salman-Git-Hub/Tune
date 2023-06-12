import os

import discord
from discord.ext import commands


class UtilsCogs(commands.Cog):
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

        if cog == "all":
            await self.load_ext(cogs)
        else:
            await self.load_ext([cog])
        embed = discord.Embed(
            title="Reloading...",
            description=f"Extension: **{cog if cog != 'all' else ', '.join(cogs)}**",
            color=discord.Color.brand_red()
        )
        msg = await ctx.send(embed=embed)
        await msg.add_reaction("👍")
        await msg.delete(delay=5)
        return


async def setup(bot):
    await bot.add_cog(UtilsCogs(bot))
