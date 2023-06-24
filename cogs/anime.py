import discord
from discord.ext import commands
from api.anime_img import get_anime_image, get_api_bi_image


class Image:
    def __init__(self, url, tags, source, author):
        self.source = source
        self.tags = tags
        self.url = url
        self.author = author

    @classmethod
    async def create_image(cls, data: dict):
        url = data['file_url']
        tags = ", ".join(data['tags'])
        source = data['source']
        author = data['author']
        return cls(url, tags, source, author)


class AnimeCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name='anirx')
    async def _ani_reaction(self, ctx: commands.Context, endpoint: str = None):
        url = None
        if endpoint is not None:
            endpoint = endpoint.strip().lower()
            url = await get_anime_image(endpoint)
            if url is not None:
                embed = discord.Embed(
                    title="",
                    description="",
                    color=discord.Color.dark_gold()
                )
                embed.set_image(url=url)
                await ctx.send(embed=embed)
            else:
                return await ctx.send("Invalid endpoint", delete_after=10)

    @commands.hybrid_command(name="animg")
    async def _ani_image(self, ctx: commands.Context):
        d = await get_api_bi_image()
        image = await Image.create_image(d)
        embed = discord.Embed(
            title="Anime Image",
            color=discord.Color.fuchsia()
        )
        embed.add_field(name="Source", value=f"[LINK!]({image.source or image.url})", inline=False)
        embed.add_field(name="Author", value=image.author, inline=False)
        embed.add_field(name="Tags", value=image.tags, inline=False)
        embed.set_image(url=image.url)
        return await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(AnimeCog(bot))
