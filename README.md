# 📊 YouTube Analytics & Sentiment Dashboard

## 🚀 Overview

Ce projet consiste à construire un **dashboard analytique interactif** permettant d’analyser les performances d’une chaîne YouTube ainsi que le **sentiment des commentaires** à l’aide du **NLP (FinBERT)**.

L’objectif est de mettre en œuvre une **chaîne complète Data Engineer** :
- ingestion de données via API
- transformation et enrichissement
- analyse NLP à grande échelle
- visualisation dans un dashboard dynamique

---

## 🧠 Features

### 🔹 YouTube Analytics
- Recherche dynamique d’une chaîne YouTube
- Récupération automatique :
  - vues
  - likes
  - nombre de commentaires
  - durée des vidéos
  - date de publication
- Visualisation de **plusieurs métriques sur une seule page**
- Graphiques interactifs (Plotly)

### 🔹 Analyse de sentiment (NLP)
- Analyse automatique des commentaires YouTube
- Modèle utilisé :
  - **FinBERT – yiyanghkust/finbert-tone**
- Classification en **3 catégories** :
  - 👍 Positif  
  - 😐 Neutre  
  - 👎 Négatif
- Résultats affichés :
  - Compteurs par sentiment
  - Diagramme circulaire

### 🔹 Dashboard
- Interface construite avec **Dash**
- Thème sombre (dark mode)
- Sélection de vidéo via dropdown
- Tout le dashboard sur **une seule page (no scroll)**

---

## 🧱 Architecture

```text
YouTube API
    ↓
Extraction (Python)
    ↓
Transformation & normalisation
    ↓
NLP Sentiment Analysis (FinBERT)
    ↓
Dashboard interactif (Dash + Plotly)
