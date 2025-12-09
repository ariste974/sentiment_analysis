import re
import dash
from dash import html, dcc, Input, Output, State
import plotly.express as px
import pandas as pd
from transformers import pipeline

from youtube_api import get_video_stats, get_channel_videos_by_title, get_video_comments, merge_datasets

# -----------------------------
# Sentiment Analysis (FinBERT-like)
# -----------------------------

sentiment_pipeline = pipeline("text-classification", model="tabularisai/multilingual-sentiment-analysis")

# -----------------------------
# Helpers
# -----------------------------
def parse_iso8601_duration(duration):
    """Converts an ISO8601 duration (e.g., PT1H2M3S) into seconds. Returns None if parsing fails."""
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
        dcc.Input(id="channel_input", type="text", placeholder="YouTube channel name...",
                  style={"width": "40%", "padding": "10px", "fontSize": "18px"}),
        html.Button("Load", id="load_channel", style={"marginLeft": "15px", "padding": "10px 20px"})
    ], style={"textAlign": "center"}),

    html.Br(),
    html.Div(id="charts_area"),
    html.Br(),

    html.H2("🧠 Comment Analysis", style={"textAlign": "center"}),
    dcc.Dropdown(id="video_selector", style={"width": "60%", "margin": "auto", "color": "black"}),
    html.Br(),
    html.Div(id="sentiment_output")
])

# -----------------------------
# Callback: load channel videos + charts
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
        return [html.Div(f"API Error: {e}", style={"color": "red"})], [], None

    if df is None or df.empty:
        return [html.H3("❌ No videos found.")], [], None

    # Normalize/convert numeric columns
    for col in ("view_count", "like_count", "comment_count"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)
        else:
            df[col] = 0

    # Parse duration
    if "duration" in df.columns:
        df["duration_sec"] = df["duration"].apply(parse_iso8601_duration)
        df["duration_sec"] = df["duration_sec"].fillna(pd.to_numeric(df["duration"], errors="coerce"))
    else:
        df["duration_sec"] = None

    try:
        fig_views = px.bar(df, x='title', y='view_count', title='Views per Video', template="plotly_dark")
        fig_likes = px.bar(df, x='title', y='like_count', title='Likes per Video', template="plotly_dark")
        fig_comments = px.bar(df, x='title', y='comment_count', title='Comments per Video', template="plotly_dark")
        charts = [dcc.Graph(figure=fig_views), dcc.Graph(figure=fig_likes), dcc.Graph(figure=fig_comments)]

        if df["duration_sec"].notna().any():
            fig_duration = px.bar(df, x='title', y='duration_sec', title='Duration (sec) per Video', template="plotly_dark")
            charts.append(dcc.Graph(figure=fig_duration))

        for fig in charts:
            fig.figure.update_layout(xaxis_tickangle=-45)
    except Exception as e:
        return [html.Div(f"Chart rendering error: {e}", style={"color": "red"})], [], None

    options = [{"label": row["title"], "value": row["video_id"]} for _, row in df.iterrows()]
    default_value = options[0]["value"] if options else None

    container = html.Div(style={"display": "grid", "gridTemplateColumns": "1fr 1fr", "gap": "20px"}, children=charts)
    return container, options, default_value

# -----------------------------
# Callback: sentiment analysis
# -----------------------------
@app.callback(
    Output("sentiment_output", "children"),
    Input("video_selector", "value")
)
def analyze_comments(video_id):
    if not video_id:
        return "No video selected."

    comments = get_video_comments(video_id)
    if not comments:
        return html.H3("❌ No comments found.")

    texts = []
    for c in comments:
        if isinstance(c, dict):
            texts.append(str(c.get("text", "")))
        else:
            texts.append(str(c))

    texts = texts[:30]

    try:
        results = sentiment_pipeline(texts)
    except Exception as e:
        return html.Div(f"Sentiment pipeline error: {e}", style={"color": "red"})

    pos = sum(1 for r in results if r.get("label", "").lower() in ["positive", "very positive"])
    neu = sum(1 for r in results if r.get("label", "").lower() == "neutral")
    neg = sum(1 for r in results if r.get("label", "").lower() in ["negative", "very negative"])

    df_sent = pd.DataFrame({"Sentiment": ["Positive", "Neutral", "Negative"], "Count": [pos, neu, neg]})
    fig_sent = px.pie(df_sent, names="Sentiment", values="Count", title="Sentiment Distribution", template="plotly_dark")

    return html.Div([
        html.H3(f"Comments analyzed: {len(texts)}", style={"textAlign": "center"}),
        html.P(f"👍 Positive: {pos}  |  😐 Neutral: {neu}  |  👎 Negative: {neg}",
               style={"textAlign": "center", "fontSize": "18px"}),
        dcc.Graph(figure=fig_sent)
    ])

# -----------------------------
# Run
# -----------------------------
if __name__ == "__main__":
    app.run(debug=True)
