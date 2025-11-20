import pandas as pd
from googleapiclient.discovery import build


# === CONFIGURATION ===
API_KEY = "AIzaSyAiZhA317VKGvADdoSblIany73s_icMB9g"
VIDEO_ID = "0aR9xvrRP2g"  # ex: "dQw4w9WgXcQ"
MAX_RESULTS = 100  # nombre max de commentaires par page (max 100)

# === INITIALISATION DU SERVICE ===
youtube = build('youtube', 'v3', developerKey=API_KEY)

# === FONCTION POUR RÉCUPÉRER LES COMMENTAIRES ===
def get_video_comments(video_id):
    comments = []
    next_page_token = None

    while True:
        request = youtube.commentThreads().list(
            part="snippet",
            videoId=video_id,
            maxResults=MAX_RESULTS,
            textFormat="plainText",
            pageToken=next_page_token
        )
        response = request.execute()

        for item in response["items"]:
            comment = item["snippet"]["topLevelComment"]["snippet"]
            author = comment["authorDisplayName"]
            text = comment["textDisplay"]
            like_count = comment["likeCount"]
            published_at = comment["publishedAt"]

            comments.append({
                "author": author,
                "text": text,
                "likes": like_count,
                "date": published_at
            })

        # Gestion de la pagination
        next_page_token = response.get("nextPageToken")
        if not next_page_token:
            break

    return comments

def get_video_stats(video_id):
    """
    Récupère les statistiques détaillées d'une vidéo YouTube
    Retourne un dictionnaire contenant les vues, likes, date de publication, etc.
    """
    try:
        # Récupération des détails de la vidéo
        request = youtube.videos().list(
            part="snippet,statistics,contentDetails",
            id=video_id
        )
        response = request.execute()

        if not response.get('items'):
            return None

        video_data = response['items'][0]
        
        # Extraction des données
        stats = {
            'title': video_data['snippet']['title'],
            'channel_name': video_data['snippet']['channelTitle'],
            'publication_date': video_data['snippet']['publishedAt'],
            'view_count': int(video_data['statistics'].get('viewCount', 0)),
            'like_count': int(video_data['statistics'].get('likeCount', 0)),
            'comment_count': int(video_data['statistics'].get('commentCount', 0)),
            'duration': video_data['contentDetails']['duration'],
            'description': video_data['snippet']['description']
        }
        
        return stats
    except Exception as e:
        print(f"Erreur lors de la récupération des statistiques: {str(e)}")
        return None
def get_channel_videos_by_title(channel_title, max_results=None):
    """
    Récupère les vidéos d'une chaîne YouTube via sa playlist 'uploads'
    """
    try:
        # 1. Trouver la chaîne
        channel_response = youtube.search().list(
            part="snippet",
            q=channel_title,
            type="channel",
            maxResults=1
        ).execute()

        if not channel_response.get("items"):
            raise ValueError(f"Chaîne non trouvée: {channel_title}")

        # 2. Récupérer l'ID de la chaîne
        channel_id = channel_response["items"][0]["id"]["channelId"]
        channel_found = channel_response["items"][0]["snippet"]["channelTitle"]
        print(f"Chaîne trouvée: {channel_found}")

        # 3. Obtenir l'ID de la playlist 'uploads' de la chaîne
        playlist_response = youtube.channels().list(
            part="contentDetails",
            id=channel_id
        ).execute()
        
        uploads_playlist_id = playlist_response["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]

        # 4. Récupérer les vidéos de la playlist 'uploads'
        videos = []
        next_page_token = None

        while True:
            playlist_items = youtube.playlistItems().list(
                part="snippet",
                playlistId=uploads_playlist_id,
                maxResults=50,  # Maximum par requête
                pageToken=next_page_token
            ).execute()

            for item in playlist_items["items"]:
                video = {
                    "video_id": item["snippet"]["resourceId"]["videoId"],
                    "title": item["snippet"]["title"],
                    "published_at": item["snippet"]["publishedAt"],
                    "description": item["snippet"]["description"],
                }
                videos.append(video)
                print(f"Vidéo trouvée: {video['title']}")  # Pour suivre la progression

                if max_results and len(videos) >= max_results:
                    return videos[:max_results]

            next_page_token = playlist_items.get("nextPageToken")
            if not next_page_token:
                break

        print(f"Total vidéos trouvées: {len(videos)}")
        return videos

    except Exception as e:
        print(f"Erreur: {str(e)}")
        return []
# === UTILISATION ===
if __name__ == "__main__":
    channel_title = "Squeezie"  # Exemple avec le titre de la chaîne
    videos = get_channel_videos_by_title(channel_title, max_results=10)
    
    print(f"\n=== VIDÉOS DE {channel_title} ===")
    for video in videos:
        print(f"\nTitre: {video['title']}")
        print(f"ID: {video['video_id']}")
        print(f"Date: {video['published_at']}")
        print("-" * 50)
