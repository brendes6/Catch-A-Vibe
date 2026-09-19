function Footer() {
  return (
    <footer className="site-footer">
      <span>© {new Date().getFullYear()} Brendan Desjardins</span>
      <nav className="footer-links" aria-label="Footer">
        <a className="footer-link" href="https://brendandesjardins.fyi" target="_blank" rel="noreferrer">Portfolio ↗</a>
        <a className="footer-link" href="https://github.com/brendes6" target="_blank" rel="noreferrer">GitHub ↗</a>
        <a className="footer-link" href="mailto:brendes6@gmail.com">Email</a>
      </nav>
    </footer>
  );
}

export default Footer;
