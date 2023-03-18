import random

from aiohttp import request

waifu_base_url = "https://api.waifu.pics/"
neko_love_base_url = 'https://neko-love.xyz/api/v1/'



async def get_waifu_sfw(endpoint):
    async with request("GET", waifu_base_url + "sfw/" + endpoint, headers={}) as response:
        r = await response.json()
        return r.get("url")


async def get_neko_sfw(endpoint):
    async with request("GET", neko_love_base_url + endpoint, headers={}) as response:
        r = await response.json()
        return r.get("url")



end_points = [
    'waifu', 'neko', 'shinobu', 'megumin', 'bully', 'cuddle',
    'cry', 'hug', 'awoo', 'kiss', 'lick', 'pat', 'smug', 'bonk',
    'yeet', 'blush', 'smile', 'wave', 'highfive', 'handhold',
    'nom', 'bite', 'glomp', 'slap', 'kill', 'kick', 'happy', 'wink', 'poke', 'dance', 'cringe'
]
extra_end_points = ['kitusune', 'punch']
mp = {
    "neko": get_neko_sfw,
    "waifu": get_waifu_sfw
}


async def get_anime_image(endpoint):
    if endpoint in end_points:
        choice = random.choice(['neko', 'waifu'])
        func = mp[choice]
        return await func(endpoint)
    elif endpoint in extra_end_points:
        return await get_neko_sfw(endpoint)
    return None
