# Catch A Vibe – An NLP-Powered Personalized Playlist Generator

## Project Overview

This project is a full-stack NLP-based web app that generates Spotify song recommendations based on a combination of user query embeddings, popularity and user personalization as part of a multi-stage recommendation pipeline. Users can authenticate with Spotify and type phrases like "late night drive", "hype workout mix", or "throwback party bangers" and quickly receive a list of songs that match the title the user inputs as well as their own personal taste.

This project utilizes a wide variety of tools to deliver personalized recommendations. Spotify OAuth is used to pull data on which artists a user listens to often, which is eventually used as part of a multi-stage retrieval of songs for personalized recs. FastEmbed and Qdrant vector databases are used to embed playlist titles and reliably store+query embeddings. The database contains 600k+ songs-embedding associations. FastAPI, Docker and Google Cloud Run are used to keep the recommendation service up for the app to constantly service personalized recommendations.

## Motivation

My inspiration for this project came from a weakness I noticed in Spotify's song recommendations for newly created playlists. Often, when you create a playlist, the initial recommendations to add don't fully capture the vibe of the playlist based on the title. Thus, I had the idea to leverage NLP embeddings and vector database queries alongside the Spotify API for personalization to build an app that quickly matches playlist titles to personalized, vibe-based song recommendations.

## Tech Stack and Highlights

The foundation of this project is the Spotify Million Playlist Dataset (https://www.aicrowd.com/challenges/spotify-million-playlist-dataset-challenge), which is a dataset containing, as the name suggests, 1 million spotify playlists with associated data such as playlist title and a list of tracks. Using this dataset alongside the **FastEmbed** embedding model and a Qdrant vector database, I was able to process this dataset to create a mapping of songs directly to the **average embedding of playlist titles they appear on**. This embedding creates a relationship between a playlist title and the songs we can expect to appear on it.

I used this foundation to build a recommendation service that provides song picks based on a multi-stage retrieval and ranking process. The first step is to pull candidates from the entire database based on the input query, and then also pull candidates from the database using the input query but also **filtered based on the user's top artists**. These candidates are merged and then passed into the second stage of the pipeline, which first provides a boost to popular songs (based on number of playlists they appear in on Spotify MPD Dataset), and then boosts songs that are either **directly from top user artists** or **share a very similar embedding to a user's top artists's average embedding**. For example, if Drake is in a user's top 50 artists, Drake songs get a flat 1.0 boost during reranking, whereas 21 Savage songs may get a 0.7 boost due to the average embeddings of both artists being similar. The final ranking is based on a composite scoring:

 - 50% pure query embedding match
 - 15% popularity score
 - 35% artist similarity/match ranking

The project is a full-stack web application featuring the following tools to build it:

 - Frontend: React + Material UI for a clean, responsive interface
 - Backend: FastAPI endpoints integrating with Spotify API and Qdrant
 - Embedding Model: FastEmbed (BAAI/bge-small-en-v1.5) embeddings of user input vs averaged playlist titles
 - Dataset: 600k+ songs mapped to playlist-level vibe embeddings in Qdrant
 - OAuth: Spotify OAuth2.0 used for authorization

## Try It Live
https://catch-a-vibe-six.vercel.app/