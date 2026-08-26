const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8080';

export const getRecs = async (query) => {
  const sessionId = localStorage.getItem('session_id');

  const response = await fetch(`${API_BASE}/recommend`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      query,
      session_id: sessionId,
    }),
  });

  if (!response.ok) {
    throw new Error('API error: ' + response.statusText);
  }

  return await response.json();
};

export const loginSpotify = async () => {
  const response = await fetch(`${API_BASE}/api/auth/login`);
  const { url } = await response.json();
  window.location.href = url;
};

export const savePlaylist = async (trackUris, name = 'Catch A Vibe Playlist') => {
  const sessionId = localStorage.getItem('session_id');
  if (!sessionId) throw new Error('Not logged in');

  const response = await fetch(`${API_BASE}/api/save-playlist`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      session_id: sessionId,
      track_uris: trackUris,
      name,
    }),
  });

  if (!response.ok) {
    throw new Error('Failed to save playlist');
  }

  return await response.json();
};