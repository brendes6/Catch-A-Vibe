# Catch A Vibe – An NLP-Powered Playlist Generator

## Project Overview

Catch A Vibe is a full-stack machine learning web app that generates Spotify song recommendations based purely on vibe-based text input. Users can type in a phrase like “late-night drive with the windows down” and instantly receive a curated list of fitting tracks based on playlist-style semantic similarity.

The app leverages FastEmbed embeddings to capture user intent and match it against a custom Spotify track dataset with pre-computed playlist vibe vectors.

## Motivation

Spotify’s personalized “mixes” inspired this project. I wanted to build a system that could generate playlists from any phrase — even abstract ones — without requiring a seed song or genre. The idea: reverse-engineer Spotify’s magic by letting users describe a vibe, and using machine learning to fill in the music that matches it.

What started as an offline NLP experiment turned into a full-stack app, complete with a containerized FastAPI backend and a React frontend. My focus was on building a system that was fast, flexible, and fun - something that made vibe discovery feel like magic.

## Tech Stack & Highlights

- Stack: React, FastAPI, Docker, FastEmbed, Spotify Web API
- Frontend: React + Material UI for a clean, responsive interface
- Backend: FastAPI containerized via Docker and deployed independently
- Embedding Model: FastEmbed (BAAI/bge-small-en-v1.5) embeddings of user input vs averaged playlist titles
- Custom Dataset: 3K+ songs mapped to playlist-level vibe embeddings
- Live Demo: Accepts free-text input and returns real-time Spotify-style song recommendations

##  Key Features

- Recommend 20+ songs based solely on a text vibe (e.g., “gritty cowboy dusk ride”)
- Fully deployed React + FastAPI app, communicating via REST API
- Fast, local embedding generation and semantic similarity search
- Spotify OAuth integration planned (future addition)

## Try It Live
https://catch-a-vibe-six.vercel.app/

Note: First call may take a few seconds while backend spins up.
