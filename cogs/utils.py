import discord
from discord.ext import commands
import os


class UtilsCogs(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.is_owner()
    @commands.command(name='reload')
    async def _reload(self, ctx: commands.Context, cog: str = None):
        if cog is None:
            await ctx.message.delete()
            return await ctx.send("Cog name needed!", delete_after=5)
        cogs = [file[:-3] for file in os.listdir("./cogs") if file.endswith(".py")]
        if cog not in cogs:
            await ctx.message.delete()
            return await ctx.send(f"Cog `{cog}` does not exists!")
        embed = discord.Embed(
            title="Reloading Extension!",
            description=f"**Cog: {cog}**",
            color=discord.Color.brand_red()
        )
        await ctx.message.delete()
        msg = await ctx.send(embed=embed)
        try:
            await self.bot.reload_extension(f"cogs.{cog}")
        except Exception as e:
            if isinstance(e, commands.ExtensionNotLoaded) or isinstance(e, commands.ExtensionNotFound):
                print(cog)
                await self.bot.load_extension(f"cogs.{cog}")
        await msg.add_reaction("👍")
        await msg.delete(delay=5)
        return



async def setup(bot):
    await bot.add_cog(UtilsCogs(bot))

