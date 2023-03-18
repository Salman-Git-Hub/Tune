
help_txt = """
ping - Get the bot's latency.
info <mention/user-id> - Get a user's info.
server - Get the server's info.
usage - Get the bot's system status.
help - Get this message.
//
**For image commands, use ```'help img```**
BREAK
waifu, neko, shinobu, megumin, bully, cuddle, cry, hug, awoo, kiss, lick, pat, smug, bonk, yeet, blush, smile, wave, highfive, handhold, nom, bite, glomp, slap, kill, kick, happy, wink, poke, dance, cringe, kitsune, punch
//
```'img <endpoint>```
BREAK
join - Joins a VC.
leave - Leaves a VC.
stop - Stops the current voice activity.
play <url/name> - Plays a song/Adds it to the queue.
shuffle - Shuffles the queue.
queue <index> - Get the queue.
remove <index> - Removes a song from the queue.
pause - Pauses the current song.
resume - Resumes the current song.
skip - Skips the current song.
np - Get the current song.
clear - Clears the queue.
volume <0-100> - Set/Get the player's volume.
pl - Playlist command.
//
**For more info on pl command, use ```'help pl```**
"""


def get_help_list():
    try:
        with open("extra/help.txt", 'r') as file:
            data = file.read()
    except FileNotFoundError:
        with open("extra/help.txt", 'w') as file:
            file.write(help_txt)
            data = help_txt
    txt_help, image_help, voice_help = data.split("BREAK")
    image = image_help.split("//")
    text = txt_help.split("//")
    voice = voice_help.split("//")
    return text, image, voice
    
