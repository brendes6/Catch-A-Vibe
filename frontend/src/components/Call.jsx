export const getRecs = async (vibe) => {
  try {
    const response = await fetch(
      `https://spotify-app-658487049469.us-central1.run.app/recs?vibe_input=${encodeURIComponent(vibe)}`
    );

    if (!response.ok) {
      throw new Error("API error: " + response.statusText);
    }

    const data = await response.json();
    return data;
  } catch (error) {
    console.error("Error fetching prediction:", error);
    return null;
  }
};