from discord.ext import commands
import discord
import psutil
import humanize



class StatusCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.command(name='usage', aliases=['u', 'status', 'stat'])
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
        embed.set_thumbnail(url="https://img.icons8.com/external-kmg-design-flat-kmg-design/64/undefined/external-statistics-marketing-kmg-design-flat-kmg-design.png")
        
        return await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(StatusCog(bot))
