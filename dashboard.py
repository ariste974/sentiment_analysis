import re
import dash
from dash import html, dcc, Input, Output, State
import plotly.express as px
import pandas as pd
from transformers import pipeline

from youtube_api import get_video_stats, get_channel_videos_by_title, get_video_comments, merge_datasets

# -----------------------------
# FinBERT (peut être lourd à charger)
# -----------------------------

sentiment_pipeline = pipeline("text-classification", model="tabularisai/multilingual-sentiment-analysis")


# -----------------------------
# Helpers
# -----------------------------
def parse_iso8601_duration(duration):
    """Convertit une durée ISO8601 (ex: PT1H2M3S) en secondes. Retourne None si non parsable."""
    if duration is None:
        return None
    s = str(duration)
    m = re.match(r"^PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?$", s)
    if not m:
        return None
    h = int(m.group(1)) if m.group(1) else 0
    minutes = int(m.group(2)) if m.group(2) else 0
    sec = int(m.group(3)) if m.group(3) else 0
    return h * 3600 + minutes * 60 + sec

# -----------------------------
# Dash App
# -----------------------------
app = dash.Dash(__name__)
app.title = "YouTube + tabularisai Dashboard"

app.layout = html.Div(style={"backgroundColor": "#111", "color": "white", "padding": "20px"}, children=[

    html.H1("🎥 YouTube Analytics + Sentiment (FinBERT)", style={"textAlign": "center"}),

    html.Div([
        dcc.Input(id="channel_input", type="text", placeholder="Nom de chaîne YouTube...",
                  style={"width": "40%", "padding": "10px", "fontSize": "18px"}),
        html.Button("Charger", id="load_channel", style={"marginLeft": "15px", "padding": "10px 20px"})
    ], style={"textAlign": "center"}),

    html.Br(),
    html.Div(id="charts_area"),
    html.Br(),

    html.H2("🧠 Analyse des commentaires", style={"textAlign": "center"}),
    dcc.Dropdown(id="video_selector", style={"width": "60%", "margin": "auto", "color": "black"}),
    html.Br(),
    html.Div(id="sentiment_output")
])

# -----------------------------
# Callback : charger vidéos + graphes
# -----------------------------
@app.callback(
    [Output("charts_area", "children"),
     Output("video_selector", "options"),
     Output("video_selector", "value")],
    [Input("load_channel", "n_clicks")],
    [State("channel_input", "value")]
)
def update_videos(n_clicks, channel_name):
    if not n_clicks or not channel_name:
        return [], [], None

    try:
        df = merge_datasets(channel_name, max_results=10)
    except Exception as e:
        return [html.Div(f"Erreur API : {e}", style={"color": "red"})], [], None

    if df is None or df.empty:
        return [html.H3("❌ Aucune vidéo trouvée." )], [], None

    # Normaliser/convertir colonnes numériques
    for col in ("view_count", "like_count", "comment_count"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)
        else:
            df[col] = 0

    # Parser duration (ISO8601) si présent ; sinon essayer convertir si déjà numérique
    if "duration" in df.columns:
        df["duration_sec"] = df["duration"].apply(parse_iso8601_duration)
        # si parse échoue mais duration est numérique (string), essayer cast
        df["duration_sec"] = df["duration_sec"].fillna(pd.to_numeric(df["duration"], errors="coerce"))
    else:
        df["duration_sec"] = None

    # Création figures (sécurisé avec try)
    try:
        fig_views = px.bar(df, x='title', y='view_count', title='Vues par vidéo', template="plotly_dark")
        fig_likes = px.bar(df, x='title', y='like_count', title='Likes par vidéo', template="plotly_dark")
        fig_comments = px.bar(df, x='title', y='comment_count', title='Commentaires par vidéo', template="plotly_dark")
        charts = [dcc.Graph(figure=fig_views), dcc.Graph(figure=fig_likes), dcc.Graph(figure=fig_comments)]

        if df["duration_sec"].notna().any():
            fig_duration = px.bar(df, x='title', y='duration_sec', title='Durée (sec) par vidéo', template="plotly_dark")
            charts.append(dcc.Graph(figure=fig_duration))

        for fig in charts:
            fig.figure.update_layout(xaxis_tickangle=-45)
    except Exception as e:
        return [html.Div(f"Erreur rendu graphiques : {e}", style={"color": "red"})], [], None

    # Dropdown options
    options = [{"label": row["title"], "value": row["video_id"]} for _, row in df.iterrows()]
    default_value = options[0]["value"] if options else None

    container = html.Div(style={"display": "grid", "gridTemplateColumns": "1fr 1fr", "gap": "20px"}, children=charts)
    return container, options, default_value

# -----------------------------
# Callback : analyser commentaires
# -----------------------------
@app.callback(
    Output("sentiment_output", "children"),
    Input("video_selector", "value")
)
def analyze_comments(video_id):
    if not video_id:
        return "Aucune vidéo sélectionnée."

    # get_video_comments retourne des dicts {'author','text','likes','date'} dans ton module
    comments = get_video_comments(video_id)  # récupérer la liste complète puis slice si besoin
    if not comments:
        return html.H3("❌ Pas de commentaires détectés.")

    # Extraire les textes (sécurisé)
    texts = []
    for c in comments:
        if isinstance(c, dict):
            texts.append(str(c.get("text", "")))
        else:
            texts.append(str(c))

    texts = texts[:30]  # limiter pour speed / cout API local
    print(texts[:10])
    try:
        results = sentiment_pipeline(texts)
    except Exception as e:
        return html.Div(f"Erreur pipeline sentiment : {e}", style={"color": "red"})

    pos = sum(1 for r in results if r.get("label", "").lower() == "positive")
    neu = sum(1 for r in results if r.get("label", "").lower() == "neutral")
    neg = sum(1 for r in results if r.get("label", "").lower() == "negative")

    df_sent = pd.DataFrame({"Sentiment": ["Positif", "Neutre", "Négatif"], "Count": [pos, neu, neg]})
    fig_sent = px.pie(df_sent, names="Sentiment", values="Count", title="Répartition des sentiments", template="plotly_dark")

    return html.Div([
        html.H3(f"Commentaires analysés : {len(texts)}", style={"textAlign": "center"}),
        html.P(f"👍 Positifs : {pos}  |  😐 Neutres : {neu}  |  👎 Négatifs : {neg}", style={"textAlign": "center", "fontSize": "18px"}),
        dcc.Graph(figure=fig_sent)
    ])

# -----------------------------
# Run
# -----------------------------
if __name__ == "__main__":
    app.run(debug=True)