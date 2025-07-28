import { useState } from 'react';
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
} from '@mui/material';
import MusicNoteIcon from '@mui/icons-material/MusicNote';
import { getRecs } from './components/Call.jsx';

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

function App() {
  const [vibeQuery, setVibeQuery] = useState("");
  const [songPredictions, setSongPredictions] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

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
      const result = await getRecs(vibeQuery);
      if (!result || !result.songs || result.songs.length === 0) {
        throw new Error("No songs found for this vibe. Try another one!");
      }
      setSongPredictions(result.songs);
    } catch (err) {
      setError(err.message || "Failed to fetch recommendations. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <ThemeProvider theme={darkTheme}>
      <CssBaseline />
      <Container
        component="main"
        maxWidth="lg"
        sx={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          minHeight: '100vh',
          py: 4, // Use vertical padding
        }}
      >
        <Box sx={{ textAlign: 'center', mb: 4 }}>
          <Typography variant="h2" component="h1" gutterBottom sx={{ fontWeight: 'bold' }}>
            Catch A Vibe
          </Typography>
          <Typography variant="h5" color="text.secondary">
            Input your "vibe" to get instant song recommendations!
          </Typography>
        </Box>

        <Box component="form" onSubmit={handleSearch} sx={{ display: 'flex', justifyContent: 'center', gap: 1, mb: 4, width: '100%', maxWidth: '700px' }}>
          <TextField
            label="What's the vibe?"
            variant="outlined"
            value={vibeQuery}
            onChange={(e) => setVibeQuery(e.target.value)}
            sx={{ width: '100%' }}
            disabled={loading}
          />
          <Button type="submit" variant="contained" size="large" disabled={loading}>
            Get Recs
          </Button>
        </Box>

        {loading && <CircularProgress sx={{ my: 4 }} />}

        {error && <Alert severity="error" sx={{ mt: 2, justifyContent: 'center', width: '100%', maxWidth: '700px' }}>{error}</Alert>}

        {songPredictions && (
          <Grid container spacing={2} sx={{ mt: 2, width: '100%', maxWidth: '900px' }}>
            {songPredictions.map((song, index) => (
              <Grid item xs={12} sm={6} key={`${song}-${index}`}>
                <Paper sx={{ p: 2, display: 'flex', alignItems: 'center', height: '100%' }}>
                  <ListItemIcon>
                    <MusicNoteIcon color="primary" />
                  </ListItemIcon>
                  <ListItemText primary={song} />
                </Paper>
              </Grid>
            ))}
          </Grid>
        )}
      </Container>
    </ThemeProvider>
  );
}

export default App;
