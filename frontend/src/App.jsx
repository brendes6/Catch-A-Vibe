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
  IconButton,
} from '@mui/material';
import MusicNoteIcon from '@mui/icons-material/MusicNote';
import ThumbUpIcon from '@mui/icons-material/ThumbUp';
import ThumbDownIcon from '@mui/icons-material/ThumbDown';
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
  
  // Rocchio Feedback State
  const [likedSongs, setLikedSongs] = useState([]);
  const [dislikedSongs, setDislikedSongs] = useState([]);

  useEffect(() => {
    const sessionId = localStorage.getItem('session_id');
    setIsLoggedIn(!!sessionId);
  }, []);

  const handleSearch = async (e, isRefine = false) => {
    if (e) e.preventDefault();
    if (!vibeQuery.trim()) {
      setError("Please enter a vibe!");
      return;
    }

    setLoading(true);
    setError(null);
    
    // Clear feedback if this is a fresh search, not a refinement
    let currentLiked = likedSongs;
    let currentDisliked = dislikedSongs;
    
    if (!isRefine) {
      currentLiked = [];
      currentDisliked = [];
      setLikedSongs([]);
      setDislikedSongs([]);
      setSongPredictions(null);
    }

    try {
      const result = await getRecs(vibeQuery, currentLiked, currentDisliked);
      if (!result || !result.results || result.results.length === 0) {
        throw new Error("No songs found for this vibe. Try another one!");
      }
      setSongPredictions(result.results);
      setLastSearchedVibe(vibeQuery);
      // Clear feedback after a successful refinement so they can refine again from the new set
      if (isRefine) {
          setLikedSongs([]);
          setDislikedSongs([]);
      }
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
  
  const toggleLike = (songId) => {
      if (likedSongs.includes(songId)) {
          setLikedSongs(likedSongs.filter(id => id !== songId));
      } else {
          setLikedSongs([...likedSongs, songId]);
          setDislikedSongs(dislikedSongs.filter(id => id !== songId));
      }
  };

  const toggleDislike = (songId) => {
      if (dislikedSongs.includes(songId)) {
          setDislikedSongs(dislikedSongs.filter(id => id !== songId));
      } else {
          setDislikedSongs([...dislikedSongs, songId]);
          setLikedSongs(likedSongs.filter(id => id !== songId));
      }
  };

  const hasFeedback = likedSongs.length > 0 || dislikedSongs.length > 0;

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
          Vector Search Recommendation Engine
        </Typography>
      </Box>

      <Box component="form" onSubmit={(e) => handleSearch(e, false)} sx={{ display: 'flex', justifyContent: 'center', gap: 1, mb: 4 }}>
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
              <Button 
                variant="outlined" 
                color="primary"
                onClick={() => handleSearch(null, true)}
                disabled={!hasFeedback || loading}
                sx={{ 
                  borderRadius: 2, 
                  opacity: hasFeedback ? 1 : 0.5,
                  transition: 'all 0.2s',
                  borderWidth: 2,
                  '&:hover': { borderWidth: 2 }
                }}
              >
                Refine Vibe
              </Button>
              {isLoggedIn && (
                <Button variant="contained" color="primary" onClick={handleSavePlaylist} disabled={saving} sx={{ borderRadius: 2, fontWeight: 'bold' }}>
                  {saving ? 'Saving...' : 'Save Playlist'}
                </Button>
              )}
            </Box>
          </Box>

          <Grid container spacing={2}>
            {songPredictions.map((song, index) => {
              const isLiked = likedSongs.includes(song.song_id);
              const isDisliked = dislikedSongs.includes(song.song_id);
              
              return (
                <Grid item xs={12} sm={6} md={4} key={`${song.song_id}-${index}`}>
                  <Paper 
                    elevation={0}
                    sx={{ 
                      p: 2, 
                      display: 'flex', 
                      alignItems: 'center', 
                      height: '100%',
                      border: '1px solid',
                      borderColor: isLiked ? 'primary.main' : isDisliked ? 'error.main' : 'divider',
                      backgroundColor: isLiked ? 'rgba(29, 185, 84, 0.08)' : isDisliked ? 'rgba(244, 67, 54, 0.05)' : 'background.paper',
                      transition: 'all 0.2s ease',
                      opacity: isDisliked ? 0.6 : 1,
                      '&:hover': {
                          borderColor: isLiked ? 'primary.main' : isDisliked ? 'error.main' : 'text.disabled'
                      }
                    }}
                  >
                    <ListItemIcon sx={{ minWidth: 40 }}>
                      <MusicNoteIcon color={isLiked ? "primary" : "inherit"} sx={{ opacity: 0.7 }} />
                    </ListItemIcon>
                    <ListItemText
                      primary={song.track}
                      secondary={song.artist}
                      primaryTypographyProps={{ fontWeight: 500, noWrap: true }}
                      secondaryTypographyProps={{ noWrap: true }}
                      sx={{ overflow: 'hidden' }}
                    />
                    <Box sx={{ display: 'flex', ml: 1 }}>
                        <IconButton 
                          size="small" 
                          onClick={() => toggleLike(song.song_id)}
                          color={isLiked ? "primary" : "default"}
                        >
                            <ThumbUpIcon fontSize="small" />
                        </IconButton>
                        <IconButton 
                          size="small" 
                          onClick={() => toggleDislike(song.song_id)}
                          color={isDisliked ? "error" : "default"}
                        >
                            <ThumbDownIcon fontSize="small" />
                        </IconButton>
                    </Box>
                  </Paper>
                </Grid>
              );
            })}
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
