import { useState } from 'react'
import reactLogo from './assets/react.svg'
import viteLogo from '/vite.svg'
import './App.css'
import Rec from './components/Rec.jsx'
import { getRecs } from './components/Call.jsx'



function App() {
  const [vibeQuery, setVibeQuery] = useState("");
  const [songPredictions, setSongPrediction] = useState(null);

  const handleSearch = async (e) => {
    e.preventDefault();

    setSongPrediction(null);
    try {
      const result = await getRecs(vibeQuery);
      if (!result) throw new Error();
      setSongPrediction(result.songs);
    } catch (err) {
    } finally {
    }
  }

  return (
    <>
      <h1>Catch A Vibe - input your "vibe" to get instant song recommendations!</h1>
      <form onSubmit={handleSearch}>
        <input type="text" value={vibeQuery} onChange={(e) => setVibeQuery(e.target.value)}></input>
      </form>
      {songPredictions && (
        <div>
          {songPredictions.map((song) => {
            return <p key={song}>{song}</p>
          })}
        </div>
      )}
    </>
  )
}

export default App
