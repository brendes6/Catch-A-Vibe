function Header({ isLoggedIn, onLogin, onLogout }) {
  return (
    <header className="site-header">
      <a className="site-title" href="/" aria-current="page"><span className="site-title-mark" aria-hidden="true">●</span> Catch A Vibe</a>
      <div className="header-tools">
        <span className="metadata">by Brendan Desjardins</span>
        {isLoggedIn ? (
          <>
            <span className="metadata" aria-label="Spotify connection status">Spotify connected</span>
            <button className="text-button" type="button" onClick={onLogout}>Log out</button>
          </>
        ) : (
          <button className="text-button connect-button" type="button" onClick={onLogin}>Connect Spotify</button>
        )}
      </div>
    </header>
  );
}

export default Header;
