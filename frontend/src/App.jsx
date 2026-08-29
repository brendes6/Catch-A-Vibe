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
  Snackbar,
  Chip,
} from '@mui/material';
import MusicNoteIcon from '@mui/icons-material/MusicNote';
import { getRecs, loginSpotify, savePlaylist } from './components/Call.jsx';
import SpotifyCallback from './components/SpotifyCallback.jsx';

// Clean, utilitarian dark theme
const darkTheme = createTheme({
  palette: {
    mode: 'dark',
    primary: { main: '#1DB954' },
    background: { default: '#101010', paper: '#1A1A1A' },
  },
  typography: {
    fontFamily: '"Inter", "Roboto", "Helvetica", "Arial", sans-serif',
    h2: { fontWeight: 800, letterSpacing: '-0.03em' },
    h6: { fontWeight: 600 },
  },
  shape: { borderRadius: 8 },
});

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
    const sessionId = localStorage.getItem('session_id');
    setIsLoggedIn(!!sessionId);
  }, []);

  const handleSearch = async (e) => {
    if (e) e.preventDefault();
    if (!vibeQuery.trim()) {
      setError("Please enter a vibe!");
      return;
    }

    setLoading(true);
    setError(null);
    setSongPredictions(null);

    try {
      const result = await getRecs(vibeQuery);
      if (!result || !result.results || result.results.length === 0) {
        throw new Error("No songs found for this vibe. Try another one!");
      }
      setSongPredictions(result.results);
      setLastSearchedVibe(vibeQuery);
    } catch (err) {
      setError(err.message || "Failed to fetch recommendations. Please try again.");
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
    const trackUris = songPredictions.filter((s) => s.track_uri).map((s) => s.track_uri);
    if (trackUris.length === 0) {
      setSnackbar({ open: true, message: 'No tracks with URIs to save.' });
      return;
    }
    setSaving(true);
    try {
      const result = await savePlaylist(trackUris, `Catch A Vibe: ${vibeQuery}`);
      if (result.playlist_url) {
        setSnackbar({ open: true, message: 'Playlist saved! Opening Spotify...' });
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
    <Container maxWidth="lg" sx={{ py: 4, minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      <Box sx={{ display: 'flex', justifyContent: 'flex-end', mb: 2 }}>
        {isLoggedIn ? (
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Chip label="Spotify Connected" color="primary" variant="outlined" size="small" />
            <Button size="small" onClick={handleLogout} color="inherit">Logout</Button>
          </Box>
        ) : (
          <Button variant="outlined" color="primary" size="small" onClick={handleLogin}>Connect Spotify</Button>
        )}
      </Box>

      <Box sx={{ textAlign: 'center', mb: 6 }}>
        <Typography variant="h2" component="h1" gutterBottom color="primary">
          Catch A Vibe
        </Typography>
        <Typography variant="h6" color="text.secondary" sx={{ fontWeight: 400 }}>
          A fast, personalized playlist recommendation engine
        </Typography>
      </Box>

      <Box component="form" onSubmit={handleSearch} sx={{ display: 'flex', justifyContent: 'center', gap: 1, mb: 4 }}>
        <TextField
          placeholder="e.g. late night driving, crying in bed, hype workout"
          variant="outlined"
          value={vibeQuery}
          onChange={(e) => setVibeQuery(e.target.value)}
          disabled={loading}
          sx={{ width: '100%', maxWidth: 500 }}
          InputProps={{ sx: { borderRadius: 2 } }}
        />
        <Button type="submit" variant="contained" size="large" disabled={loading || !vibeQuery.trim()} sx={{ px: 4, borderRadius: 2, fontWeight: 'bold' }}>
          Search
        </Button>
      </Box>

      {loading && <Box sx={{ display: 'flex', justifyContent: 'center', my: 4 }}><CircularProgress /></Box>}

      {error && (
        <Alert severity="error" sx={{ mb: 4, mx: 'auto', maxWidth: 600 }}>{error}</Alert>
      )}

      {songPredictions && (
        <Box sx={{ width: '100%' }}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3, borderBottom: '1px solid #333', pb: 2 }}>
            <Typography variant="h5" sx={{ fontWeight: 'bold' }}>
              Results for "{lastSearchedVibe}"
            </Typography>
            <Box sx={{ display: 'flex', gap: 2 }}>
              {isLoggedIn && (
                <Button variant="contained" color="primary" onClick={handleSavePlaylist} disabled={saving} sx={{ borderRadius: 2, fontWeight: 'bold' }}>
                  {saving ? 'Saving...' : 'Save Playlist'}
                </Button>
              )}
            </Box>
          </Box>

          <Grid container spacing={2}>
            {songPredictions.map((song, index) => (
                <Grid item xs={12} sm={6} md={4} key={`${song.song_id}-${index}`}>
                  <Paper 
                    elevation={0}
                    sx={{ 
                      p: 2, 
                      display: 'flex', 
                      alignItems: 'center', 
                      height: '100%',
                      border: '1px solid',
                      borderColor: 'divider',
                      backgroundColor: 'background.paper',
                      transition: 'all 0.2s ease',
                      '&:hover': {
                          borderColor: 'text.disabled'
                      }
                    }}
                  >
                    <ListItemIcon sx={{ minWidth: 40 }}>
                      <MusicNoteIcon sx={{ opacity: 0.7 }} />
                    </ListItemIcon>
                    <ListItemText
                      primary={song.track}
                      secondary={song.artist}
                      primaryTypographyProps={{ fontWeight: 500, noWrap: true }}
                      secondaryTypographyProps={{ noWrap: true }}
                      sx={{ overflow: 'hidden' }}
                    />
                  </Paper>
                </Grid>
            ))}
          </Grid>
        </Box>
      )}

      <Snackbar
        open={snackbar.open}
        autoHideDuration={4000}
        onClose={() => setSnackbar({ open: false, message: '' })}
        message={snackbar.message}
      />
    </Container>
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
