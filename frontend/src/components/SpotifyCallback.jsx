import { useEffect, useState } from 'react';
import { Box, Typography, CircularProgress } from '@mui/material';

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8080';

function SpotifyCallback() {
  const [status, setStatus] = useState('Connecting to Spotify...');

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const code = params.get('code');
    const state = params.get('state');
    if (params.get('error')) {
      setStatus('Spotify login was cancelled.');
      return;
    }
    if (!code || !state) {
      setStatus('Invalid Spotify authorization response.');
      return;
    }

    fetch(`${API_BASE}/api/auth/callback`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ code, state }),
    })
      .then((res) => {
        if (!res.ok) throw new Error('Auth failed');
        return res.json();
      })
      .then((data) => {
        localStorage.setItem('session_id', data.session_id);
        localStorage.setItem(
          'has_taste_profile',
          String(data.has_taste_profile)
        );
        setStatus('Connected! Redirecting...');
        window.location.href = '/';
      })
      .catch((err) => {
        console.error('Callback error:', err);
        setStatus('Failed to connect. Please try again.');
      });
  }, []);

  return (
    <Box
      sx={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        flexDirection: 'column',
        gap: 2,
      }}
    >
      <CircularProgress color="primary" />
      <Typography variant="h6">{status}</Typography>
    </Box>
  );
}

export default SpotifyCallback;
