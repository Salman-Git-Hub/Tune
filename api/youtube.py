import requests
from googleapiclient.discovery import build
from utils.env import YOUTUBE_API_KEY


youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)


def search_video(q: str, items: int = 5) -> list:
    request = youtube.search().list(
        part='id,snippet',
        q=q,
        maxResults=items,
        type='video'
    )
    response = request.execute()
    search_results = [
        dict(title=item['snippet']['title'], id=item['id']['videoId']) for item in response['items']
    ]
    return search_results


def video(video_id: str) -> dict:
    request = youtube.videos().list(
        part='snippet',
        id=video_id
    )
    response = request.execute()['items'][0]
    return {
        "title": response['snippet']['title'],
        "id": f"https://youtu.be/{video_id}"
    }


def video_exists(video_id: str) -> bool:
    url = "http://img.youtube.com/vi/" + video_id + "/mqdefault.jpg"
    img = requests.get(url).status_code
    if img != 200:
        return False
    return True


def playlist(playlist_id: str, items: int = 25) -> list[dict]:
    request = youtube.playlistItems().list(
        part='id,snippet',
        maxResults=items,
        playlistId=playlist_id
    )
    response = request.execute()
    playlist_dict = [
        dict(title=item['snippet']['title'], id=f"https://youtu.be/{item['snippet']['resourceId']['videoId']}")
        for item in response['items']
    ]
    return playlist_dict
