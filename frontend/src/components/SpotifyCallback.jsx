import { useEffect, useState } from 'react';
import { Box, Typography, CircularProgress } from '@mui/material';

const API_BASE = 'http://127.0.0.1:8080';

function SpotifyCallback() {
  const [status, setStatus] = useState('Connecting to Spotify...');

  useEffect(() => {
    const code = new URLSearchParams(window.location.search).get('code');
    if (!code) {
      setStatus('No authorization code found.');
      return;
    }

    fetch(`${API_BASE}/api/auth/callback`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ code }),
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
