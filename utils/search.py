from googleapiclient.discovery import build
from utils.env import YOUTUBE_API_KEY, MAX_SEARCH_ITEM
import sys
sys.path.append('utils')

youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)


def search_video(query):
    request = youtube.search().list(
        part='id,snippet',
        q=query,
        maxResults=MAX_SEARCH_ITEM,
        type='video'
    )
    response = request.execute()
    search_results = []
    for item in response['items']:
        title = item['snippet']['title']
        video_id = item['id']['videoId']
        video = [title, video_id]
        search_results.append(video)
    return search_results
