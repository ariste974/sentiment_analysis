import pandas as pd
from googleapiclient.discovery import build
from dotenv import load_dotenv
import os
# === CONFIGURATION ===
load_dotenv()  # lit le .env dans le répertoire courant
API_KEY = os.getenv("API_KEY")
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
    Retourne un DataFrame d'une seule ligne
    """
    try:
        # Récupération des détails de la vidéo
        request = youtube.videos().list(
            part="snippet,statistics,contentDetails",
            id=video_id
        )
        response = request.execute()

        if not response.get('items'):
            return pd.DataFrame()  # vide si pas trouvé

        video_data = response['items'][0]
        
        # Extraction des données
        stats = {
            'video_id': video_data['id'],
            'title': video_data['snippet']['title'],
            'channel_name': video_data['snippet']['channelTitle'],
            'publication_date': video_data['snippet']['publishedAt'],
            'view_count': int(video_data['statistics'].get('viewCount', 0)),
            'like_count': int(video_data['statistics'].get('likeCount', 0)),
            'comment_count': int(video_data['statistics'].get('commentCount', 0)),
            'duration': video_data['contentDetails']['duration'],
            'description': video_data['snippet']['description']
        }
        
        return pd.DataFrame([stats])  # <-- une ligne

    except Exception as e:
        print(f"Erreur lors de la récupération des statistiques: {str(e)}")
        return pd.DataFrame()

def get_channel_videos_by_title(channel_title, max_results=None):
    """
    Récupère les vidéos d'une chaîne YouTube via sa playlist 'uploads'
    Retourne un pandas.DataFrame avec les colonnes: video_id, title, published_at, description
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
                    return pd.DataFrame(videos[:max_results])

            next_page_token = playlist_items.get("nextPageToken")
            if not next_page_token:
                break

        print(f"Total vidéos trouvées: {len(videos)}")
        return pd.DataFrame(videos)

    except Exception as e:
        print(f"Erreur: {str(e)}")
        return pd.DataFrame()
def merge_datasets(channel_title, max_results=10):
    """
    Fusionne les DataFrames des vidéos et des statistiques sur 'video_id'
    """
    videos = get_channel_videos_by_title(channel_title, max_results=max_results)
    # initialiser un DataFrame vide avec les colonnes attendues
    stat = pd.DataFrame(columns=[
            'video_id','title','channel_name','publication_date',
            'view_count','like_count','comment_count','duration','description'
        ])
    # récupérer et concaténer correctement
    for vid_id in videos.get('video_id', []):
        row = get_video_stats(vid_id)
        if not row.empty:
            stat = pd.concat([stat, row], ignore_index=True)
    data_final = pd.merge(videos, stat, on=['video_id'])
    data_final=data_final.drop(columns=['title_y','description_y'])
    data_final=data_final.rename(columns={'title_x':'title','description_x':'description'})
    return data_final
# === UTILISATION ===
if __name__ == "__main__":
    channel_title = "Squeezie"  # Exemple avec le titre de la chaîne
    data_final = merge_datasets(channel_title, max_results=5)
    print(data_final.columns)  # Affiche les statistiques de la première vidéo
