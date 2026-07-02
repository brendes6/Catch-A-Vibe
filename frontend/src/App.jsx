import { useState, useEffect } from 'react';
import { Routes, Route } from 'react-router-dom';
import {
  Container,
  TextField,
  Button,
  Typography,
  Box,
  CircularProgress,
  Alert,
  CssBaseline,
  ThemeProvider,
  createTheme,
  ListItemIcon,
  Grid,
  Paper,
  ListItemText,
  ToggleButton,
  ToggleButtonGroup,
  Snackbar,
  Chip,
} from '@mui/material';
import MusicNoteIcon from '@mui/icons-material/MusicNote';
import { getRecs, loginSpotify, savePlaylist } from './components/Call.jsx';
import SpotifyCallback from './components/SpotifyCallback.jsx';

// A dark theme for a better vibe
const darkTheme = createTheme({
  palette: {
    mode: 'dark',
    primary: {
      main: '#1DB954', // A Spotify-like green
    },
    background: {
      default: '#121212',
      paper: '#282828',
    },
  },
});

function HomePage() {
  const [vibeQuery, setVibeQuery] = useState('');
  const [songPredictions, setSongPredictions] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [direction, setDirection] = useState(null);
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [saving, setSaving] = useState(false);
  const [snackbar, setSnackbar] = useState({ open: false, message: '' });

  useEffect(() => {
    const sessionId = localStorage.getItem('session_id');
    setIsLoggedIn(!!sessionId);
  }, []);

  const handleSearch = async (e) => {
    e.preventDefault();
    if (!vibeQuery.trim()) {
      setError("Please enter a vibe!");
      return;
    }

    setLoading(true);
    setError(null);
    setSongPredictions(null);

    try {
      const result = await getRecs(vibeQuery, direction);
      if (!result || !result.results || result.results.length === 0) {
        throw new Error("No songs found for this vibe. Try another one!");
      }
      setSongPredictions(result.results);
    } catch (err) {
      setError(err.message || "Failed to fetch recommendations. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const handleLogin = async () => {
    try {
      await loginSpotify();
    } catch (err) {
      setError('Failed to start Spotify login.');
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('session_id');
    localStorage.removeItem('has_taste_profile');
    setIsLoggedIn(false);
  };

  const handleSavePlaylist = async () => {
    if (!songPredictions) return;

    const trackUris = songPredictions
      .filter((s) => s.track_uri)
      .map((s) => s.track_uri);

    if (trackUris.length === 0) {
      setSnackbar({ open: true, message: 'No tracks with URIs to save.' });
      return;
    }

    setSaving(true);
    try {
      const result = await savePlaylist(trackUris, `Catch A Vibe: ${vibeQuery}`);
      if (result.playlist_url) {
        setSnackbar({
          open: true,
          message: 'Playlist saved! Opening Spotify...',
        });
        window.open(result.playlist_url, '_blank');
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
    <>
      <Box
        sx={{
          minHeight: '30vh',
          width: '100vw',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          flexDirection: 'column',
          gap: 1,
        }}
      >
        {/* Spotify auth button */}
        <Box sx={{ position: 'absolute', top: 16, right: 24 }}>
          {isLoggedIn ? (
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <Chip label="Spotify Connected" color="primary" variant="outlined" />
              <Button size="small" onClick={handleLogout} color="inherit">
                Logout
              </Button>
            </Box>
          ) : (
            <Button variant="outlined" color="primary" onClick={handleLogin}>
              Connect Spotify
            </Button>
          )}
        </Box>

        <Typography variant="h2" component="h1" gutterBottom sx={{ fontWeight: 'bold' }}>
          Catch A Vibe
        </Typography>
        <Typography variant="h5" color="text.secondary">
          Input your playlist title or "vibe" to get instant song recommendations!
        </Typography>
      </Box>

      <Box
        component="form"
        onSubmit={handleSearch}
        sx={{
          minHeight: '10vh',
          width: '100vw',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          flexDirection: 'column',
          gap: 2,
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <TextField
            label="What's the vibe?"
            variant="outlined"
            value={vibeQuery}
            onChange={(e) => setVibeQuery(e.target.value)}
            disabled={loading}
          />
          <Button type="submit" variant="contained" size="large" disabled={loading}>
            Get Recs
          </Button>
        </Box>

        {/* Direction selector */}
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Typography variant="body2" color="text.secondary">
            Steer:
          </Typography>
          <ToggleButtonGroup
            value={direction}
            exclusive
            onChange={(e, val) => setDirection(val)}
            size="small"
          >
            <ToggleButton value="energy">Energy ⚡</ToggleButton>
            <ToggleButton value="mood">Mood 😊</ToggleButton>
            <ToggleButton value="intensity">Intensity 🔥</ToggleButton>
          </ToggleButtonGroup>
        </Box>
      </Box>

      {loading && <CircularProgress sx={{ mx: 100, width: '100%', maxWidth: '1000px' }} />}

      {error && (
        <Alert severity="error" sx={{ mt: 2, justifyContent: 'center', width: '100%', maxWidth: '700px' }}>
          {error}
        </Alert>
      )}

      {songPredictions && (
        <>
          {/* Save to Spotify button */}
          {isLoggedIn && (
            <Box sx={{ mt: 2, display: 'flex', justifyContent: 'center' }}>
              <Button
                variant="contained"
                color="primary"
                onClick={handleSavePlaylist}
                disabled={saving}
              >
                {saving ? 'Saving...' : 'Save to Spotify'}
              </Button>
            </Box>
          )}

          <Grid
            container
            spacing={2}
            sx={{
              mt: 2,
              width: '100%',
              alignItems: 'center',
              justifyContent: 'center',
              maxWidth: '1900px',
            }}
          >
            {songPredictions.map((song, index) => (
              <Grid item xs={12} sm={6} key={`${song.track}-${index}`}>
                <Paper sx={{ p: 2, display: 'flex', alignItems: 'center', height: '100%' }}>
                  <ListItemIcon>
                    <MusicNoteIcon color="primary" />
                  </ListItemIcon>
                  <ListItemText
                    primary={song.track}
                    secondary={song.artist}
                  />
                </Paper>
              </Grid>
            ))}
          </Grid>
        </>
      )}

      <Snackbar
        open={snackbar.open}
        autoHideDuration={4000}
        onClose={() => setSnackbar({ open: false, message: '' })}
        message={snackbar.message}
      />
    </>
  );
}

function App() {
  return (
    <ThemeProvider theme={darkTheme}>
      <CssBaseline />
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/callback" element={<SpotifyCallback />} />
      </Routes>
    </ThemeProvider>
  );
}

export default App;
