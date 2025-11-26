import dash
from dash import html, dcc
import plotly.express as px
import pandas as pd

from youtube_api import (
    get_channel_videos_by_title,
    get_video_comments,
    get_video_stats,
    merge_datasets
)

channel_title = "Squeezie"  # Exemple avec le titre de la chaîne
data_final = merge_datasets(channel_title, max_results=5)

# --- Create simple charts ---
fig_views = px.bar(data_final, x='title', y='view_count', title='Vues par vidéo')
fig_likes = px.bar(data_final, x='title', y='like_count', title='Likes par vidéo')
#fig_time = px.line(data_final.sort_values('published_at'), x='published_at', y='view_count', title='Évolution des vues')


# --- Dashboard ---
app = dash.Dash(__name__)
app.layout = html.Div([
html.H1("Dashboard YouTube Analytics", style={"textAlign": "center"}),


dcc.Graph(id="views_graph", figure=fig_views),
dcc.Graph(id="likes_graph", figure=fig_likes),
#dcc.Graph(id="time_graph", figure=fig_time)
])


if __name__ == '__main__':
    app.run(debug=True)