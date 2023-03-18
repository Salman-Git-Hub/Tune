import discord
from discord.ext import commands
from utils.anime_img import get_anime_image


class AnimeCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='img')
    async def img(self, ctx: commands.Context, message: str = None):
        url = None
        if message is not None:
            endpoint = message.strip().lower()
            url = await get_anime_image(endpoint)
            if url is not None:
                embed = discord.Embed(
                    title="",
                    description="",
                    color=discord.Color.dark_gold()
                )
                embed.set_image(url=url)
                await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(AnimeCog(bot))
