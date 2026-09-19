import { useEffect, useState } from 'react';
import { Routes, Route } from 'react-router-dom';
import { getRecs, loginSpotify, savePlaylist } from './components/Call.jsx';
import SpotifyCallback from './components/SpotifyCallback.jsx';
import Header from './components/layout/Header.jsx';
import Footer from './components/layout/Footer.jsx';
import './App.css';

function HomePage() {
  const [vibeQuery, setVibeQuery] = useState('');
  const [lastSearchedVibe, setLastSearchedVibe] = useState('');
  const [songPredictions, setSongPredictions] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [saving, setSaving] = useState(false);
  const [snackbar, setSnackbar] = useState({ open: false, message: '' });

  useEffect(() => {
    setIsLoggedIn(Boolean(localStorage.getItem('session_id')));
  }, []);

  useEffect(() => {
    if (!snackbar.open) return undefined;
    const timeout = window.setTimeout(() => setSnackbar({ open: false, message: '' }), 4000);
    return () => window.clearTimeout(timeout);
  }, [snackbar]);

  const handleSearch = async (event) => {
    event.preventDefault();
    if (!vibeQuery.trim()) {
      setError('Please enter a vibe.');
      return;
    }
    setLoading(true);
    setError(null);
    setSongPredictions(null);
    try {
      const result = await getRecs(vibeQuery);
      if (!result?.results?.length) throw new Error('No songs found for this vibe. Try another one.');
      setSongPredictions(result.results);
      setLastSearchedVibe(vibeQuery);
    } catch (err) {
      setError(err.message || 'Failed to fetch recommendations. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleLogin = async () => {
    try { await loginSpotify(); } catch { setError('Failed to start Spotify login.'); }
  };

  const handleLogout = () => {
    localStorage.removeItem('session_id');
    localStorage.removeItem('has_taste_profile');
    setIsLoggedIn(false);
  };

  const handleSavePlaylist = async () => {
    if (!songPredictions) return;
    const trackUris = songPredictions.filter((song) => song.track_uri).map((song) => song.track_uri);
    if (!trackUris.length) {
      setSnackbar({ open: true, message: 'No tracks with URIs to save.' });
      return;
    }
    setSaving(true);
    try {
      const result = await savePlaylist(trackUris, `Catch A Vibe: ${vibeQuery}`);
      if (result.playlist_url) {
        setSnackbar({ open: true, message: 'Playlist saved. Opening Spotify…' });
        window.open(result.playlist_url, '_blank', 'noopener,noreferrer');
      } else {
        setSnackbar({ open: true, message: 'Failed to save playlist.' });
      }
    } catch (err) {
      setSnackbar({ open: true, message: err.message });
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="site-shell">
      <Header isLoggedIn={isLoggedIn} onLogin={handleLogin} onLogout={handleLogout} />
      <main className="main-content" id="main">
        <section className="intro" aria-labelledby="page-title">
          <p className="eyebrow">Music discovery / personalized playlist generator</p>
          <h1 className="page-title" id="page-title">Catch A Vibe</h1>
          <p className="intro-copy">A personalized, NLP-based playlist generator. Optionally log in with Spotify and type a playlist title to get started.</p>
        </section>

        <form className="vibe-form" onSubmit={handleSearch}>
          <label className="sr-only" htmlFor="vibe-query">Describe a vibe</label>
          <input className="vibe-input" id="vibe-query"
            placeholder="late night driving, crying in bed, hype workout"
            value={vibeQuery} onChange={(event) => setVibeQuery(event.target.value)} disabled={loading} />
          <button className="action-button" type="submit" disabled={loading || !vibeQuery.trim()}>
            {loading ? 'Searching…' : 'Find songs'}
          </button>
        </form>

        {loading && <p className="status-message" role="status">Finding songs for this vibe…</p>}
        {error && <p className="status-message status-error" role="alert">{error}</p>}

        {songPredictions && (
          <section aria-labelledby="results-title">
            <div className="section-heading">
              <div>
                <p className="eyebrow">Recommendations</p>
                <h2 className="section-title" id="results-title">Results for “{lastSearchedVibe}”</h2>
              </div>
              {isLoggedIn && (
                <div className="results-actions">
                  <span className="metadata">{songPredictions.length} tracks</span>
                  <button className="text-button" type="button" onClick={handleSavePlaylist} disabled={saving}>
                    {saving ? 'Saving…' : 'Save playlist'}
                  </button>
                </div>
              )}
            </div>
            <div className="results-grid">
              {songPredictions.map((song, index) => (
                <article className="song-row" key={`${song.song_id}-${index}`}>
                  <span className="song-index">{String(index + 1).padStart(2, '0')}</span>
                  <div className="song-info">
                    <div className="song-title">{song.track}</div>
                    <div className="song-artist">{song.artist}</div>
                  </div>
                </article>
              ))}
            </div>
          </section>
        )}
      </main>
      <Footer />
      {snackbar.open && <div className="status-message" role="status">{snackbar.message}</div>}
    </div>
  );
}

function App() {
  return (
    <Routes>
      <Route path="/" element={<HomePage />} />
      <Route path="/callback" element={<SpotifyCallback />} />
    </Routes>
  );
}

export default App;
