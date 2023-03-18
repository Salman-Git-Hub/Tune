from aiohttp import request


waifu_base_url = "https://api.waifu.pics/"
api_bi_base_url = "https://pic.re/"


async def get_waifu_api_image(endpoint):
    async with request("GET", waifu_base_url + "sfw/" + endpoint, headers={}) as response:
        r = await response.json()
        return r.get("url")


async def get_api_bi_image():
    async with request("POST", api_bi_base_url + "image", headers={}) as response:
        r = await response.json()
        return r


waifu_endpoints = {
    "sfw": [
        "waifu", "neko", "shinobu", "megumin", "bully",
        "cuddle", "cry", "hug", "awoo", "kiss", "lick",
        "pat", "smug", "bonk", "yeet", "blush", "smile",
        "wave", "highfive", "handhold", "nom", "bite",
        "glomp", "slap", "kill", "kick", "happy", "wink",
        "poke", "dance", "cringe"
    ]
}


async def get_anime_image(endpoint):
    if endpoint in waifu_endpoints['sfw']:
        return await get_waifu_api_image(endpoint)
    return None
