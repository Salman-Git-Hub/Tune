import sys

from googleapiclient.discovery import build

sys.path.append('utils')
from utils.env import YOUTUBE_API_KEY, MAX_PLAYLIST_ITEM

youtube = build("youtube", 'v3', developerKey=YOUTUBE_API_KEY)


def get_playlist(playlistId):
    request = youtube.playlistItems().list(
        part='id, snippet',
        maxResults=MAX_PLAYLIST_ITEM,
        playlistId=playlistId
    )
    r = request.execute()
    playlist_list_dict = []
    for item in r['items']:
        snippet = item.get('snippet')
        title = snippet.get('title')
        videoId = snippet.get("resourceId").get("videoId")
        playlist_list_dict.append(
            {
                'title': title,
                'id': f'https://www.youtube.com/watch?v={videoId}'
            }
        )
    return playlist_list_dict


