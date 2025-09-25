# Catch A Vibe – An NLP-Powered Playlist Generator

## Project Overview

Catch A Vibe is a full-stack machine learning web app that generates Spotify song recommendations based purely on vibe-based text input. Users can type in a phrase like “late-night drive with the windows down” and instantly receive a curated list of fitting tracks based on playlist-style semantic similarity.

The app leverages FastEmbed embeddings to capture user intent, and a Qdrant cloud vector database to allow instant song recommendations.

The backend is deployed on Google Cloud Run, allowing fast, scalable API calls.

## Motivation

My inspiration for this project came from a weakness I noticed in Spotify's song recommendations for newly created playlists. Often, when you create a playlist, the initial recommendations to add don't fully capture the vibe of the playlist based on the title. Thus, I had the idea to leverage NLP embeddings and vector database queries to quickly match playlist titles to song recommendations.

What started as an offline NLP experiment turned into a full-stack app, complete with a containerized FastAPI backend deployed to Google Cloud Run and a React frontend. My focus was on building a system that was fast, flexible, and fun, showing the product-oriented benefits of deploying an embedding-based recommender.

## Tech Stack & Highlights

- Stack: React, FastAPI, Qdrant, Docker, FastEmbed, Spotify Web API
- Frontend: React + Material UI for a clean, responsive interface
- Backend: FastAPI containerized via Docker and deployed on Google Cloud Run
- Embedding Model: FastEmbed (BAAI/bge-small-en-v1.5) embeddings of user input vs averaged playlist titles
- Custom Dataset: 3K+ songs mapped to playlist-level vibe embeddings
- Live Demo: Accepts free-text input and returns real-time Spotify-style song recommendations

##  Key Features

- Recommend 20+ songs based solely on a text vibe (e.g., “gritty cowboy dusk ride”)
- Fully deployed React + FastAPI app, communicating via REST API on GCR
- Fast, local embedding generation and vector DB similarity search
- Spotify OAuth integration planned (future addition)

## Try It Live
https://catch-a-vibe-six.vercel.app/