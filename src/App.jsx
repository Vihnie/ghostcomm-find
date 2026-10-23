import { useEffect, useMemo, useState } from 'react'
import {
  Search, Plus, ShieldCheck, Sparkles, MapPin,
  Clock, Package, Menu, X
} from 'lucide-react'
import './App.css'
import { createApi } from './api'
import Modal from './components/Modal'
import AuthForm from './components/AuthForm'
import ReportForm from './components/ReportForm'
import ItemDetail from './components/ItemDetail'
import Inbox from './components/Inbox'

export default function App() {
  const [token, setToken] = useState(() => sessionStorage.getItem('ghostcomm-token') || '')
  const [user, setUser] = useState(null)
  const [items, setItems] = useState([])
  const [search, setSearch] = useState('')
  const [filter, setFilter] = useState('All')
  const [mine, setMine] = useState(false)
  const [status, setStatus] = useState('open')
  const [page, setPage] = useState(0)
  const [menu, setMenu] = useState(false)
  const [modal, setModal] = useState(null)
  const [pending, setPending] = useState(null)
  const [selected, setSelected] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [revision, setRevision] = useState(0)
  const [aiBusy, setAiBusy] = useState(false)
  const [aiResults, setAiResults] = useState(null)
  const api = useMemo(() => createApi(token, () => {
    setToken('')
    setModal('auth')
    setError('Your session expired. Please sign in again.')
  }), [token])
  useEffect(() => {
    if (token) sessionStorage.setItem('ghostcomm-token', token)
    else sessionStorage.removeItem('ghostcomm-token')
  }, [token])
  useEffect(() => {
    if (!token) { setUser(null); setItems([]); setAiResults(null); return }
    const controller = new AbortController()
    api('/auth/me', { signal: controller.signal }).then(setUser).catch(error => {
      if (error.name !== 'AbortError') setError(error.message)
    })
    return () => controller.abort()
  }, [api, token])
  useEffect(() => {
    if (!token) return
    const controller = new AbortController()
    setLoading(true)
    setError('')
    const timer = setTimeout(async () => {
      try {
        const params = new URLSearchParams({ offset: String(page * 20), limit: '20', status })
        if (filter !== 'All') params.set('kind', filter.toLowerCase())
        if (search.trim()) params.set('q', search.trim())
        if (mine) params.set('mine', 'true')
        const reports = await api(`/items?${params}`, { signal: controller.signal })
        setItems(reports)
        setAiResults(null)
      } catch (error) {
        if (error.name !== 'AbortError') setError(error.message)
      } finally {
        if (!controller.signal.aborted) setLoading(false)
      }
    }, 250)
    return () => { clearTimeout(timer); controller.abort() }
  }, [api, token, page, status, filter, search, mine, revision])
  function openProtected(view) {
    setMenu(false)
    if (!token) { setPending(view); setModal('auth') }
    else setModal(view)
  }
  function openItem(item) { setSelected(item); setModal('detail') }
  function signOut() {
    setToken('')
    setUser(null)
    setSelected(null)
    setPending(null)
    setModal(null)
  }
  async function aiSearch() {
    setError('')
    setAiBusy(true)
    try {
      const hits = await api('/search/ai', { method: 'POST', body: {
        description: search.trim(), kind: filter === 'Lost' ? 'lost' : 'found',
      } })
      const reports = await Promise.all(hits.map(async hit => ({
        ...await api(`/items/${hit.target_id}`), match: hit,
      })))
      setAiResults(reports)
    } catch (error) { setError(error.message) } finally { setAiBusy(false) }
  }
  const visibleItems = aiResults || items
  return (
    <div className="app">
      <div className="topbar">
        <ShieldCheck size={16} />
        <span>GHOSTCOMM FIND</span>
        <span className="motto">PRIVACY IS A RIGHT, NOT A PRIVILEGE.</span>
      </div>

      <header className="navbar">
        <a href="#home" className="logo">
          <span className="logo-icon"><Search size={25} /></span>
          <span>GHOSTCOMM<small>FIND</small></span>
        </a>

        <button className="menu-toggle" aria-label="Toggle navigation" onClick={() => setMenu(!menu)}>
          {menu ? <X /> : <Menu />}
        </button>

        <nav className={menu ? 'nav-links open' : 'nav-links'}>
          <a href="#browse" onClick={() => setMenu(false)}>Browse items</a>
          <a href="#how" onClick={() => setMenu(false)}>How it works</a>
          {token ? <>
            <button className="nav-button" onClick={() => openProtected('inbox')}>Messages</button>
            <button className="nav-button" onClick={signOut}>Sign out{user ? ` (${user.name})` : ''}</button>
          </> : <button className="nav-button" onClick={() => openProtected(null)}>Sign in</button>}
          <button className="button primary" onClick={() => openProtected('report')}>
            <Plus size={17} /> Report an item
          </button>
        </nav>
      </header>

      <main id="home">
        <section className="hero">
          <div className="hero-content">
            <span className="eyebrow">
              <span className="dot" /> YOUR CAMPUS. YOUR COMMUNITY.
            </span>

            <h1>Lost something?<br /><span>Let's find it.</span></h1>

            <p>
              Lost belongings shouldn't stay lost. Discover reported items,
              report what you've misplaced, and help your campus community
              reconnect with what matters.
            </p>

            <div className="hero-buttons">
              <a href="#browse" className="button primary">
                Find an item <Search size={17} />
              </a>
              <button className="button secondary" onClick={() => openProtected('report')}>
                <Plus size={17} /> Report lost or found
              </button>
            </div>

            <div className="trust">
              <ShieldCheck size={18} />
              Community-powered. Privacy-conscious.
            </div>
          </div>

          <div className="hero-visual">
            <div className="visual-card">
              <div className="visual-icon"><Search size={48} /></div>
              <span>GHOSTCOMM TECHNOLOGY</span>
              <h2>Lost. Found.<br />Reconnected.</h2>
              <div className="red-line" />
            </div>
            <div className="floating-card">
              <Sparkles size={19} />
              <div><strong>AI-assisted matching</strong><small>Helping items find their owners</small></div>
            </div>
          </div>
        </section>

        <section className="browse section" id="browse">
          <div className="section-heading">
            <div>
              <span className="eyebrow">THE COMMUNITY BOARD</span>
              <h2>Find what you're looking for</h2>
            </div>
            <span className="preview-tag">{token ? "CAMPUS REPORTS" : "MEMBERS ONLY"}</span>
          </div>

          <div className="search-row">
            <label className="search-input">
              <Search size={20} />
              <input
                value={search}
                onChange={e => { setSearch(e.target.value); setPage(0) }}
                aria-label="Search reports"
                maxLength={200}
                placeholder="Search keys, books, electronics..."
              />
            </label>

            <div className="filters">
              {['All', 'Lost', 'Found'].map(option => (
                <button
                  key={option}
                  className={filter === option ? 'filter active' : 'filter'}
                  onClick={() => { setFilter(option); setPage(0) }}
                >
                  {option}
                </button>
              ))}
            </div>
          </div>

          {token && <div className="board-controls">
            <label><input type="checkbox" checked={mine} onChange={event => { setMine(event.target.checked); setPage(0) }} /> My reports</label>
            <label>Status <select value={status} onChange={event => { setStatus(event.target.value); setPage(0) }}>
              <option value="open">Open</option><option value="resolved">Resolved</option>
            </select></label>
            <button className="button secondary" disabled={aiBusy || loading || search.trim().length < 10} onClick={aiSearch}>
              <Sparkles size={16} />{aiBusy ? 'Searching...' : `AI search ${filter === 'Lost' ? 'lost' : 'found'} reports`}
            </button>
            {aiResults && <button className="details-link" onClick={() => setAiResults(null)}>Back to regular search</button>}
          </div>}
          {error && <p className="error-message" role="alert">{error}</p>}
          {!token ? <div className="empty"><p>Sign in to view real reports from your campus community.</p>
            <button className="button primary" onClick={() => openProtected(null)}>Sign in or create an account</button></div> : <>
            {loading && <p role="status">Loading campus reports...</p>}
            <p className="result-count">Showing {visibleItems.length} {aiResults ? 'AI suggestions' : 'reports'}</p>
            <div className="item-grid">
              {visibleItems.map(item => <article className="item-card" key={item.id}>
                <div className="item-image"><Package size={42} />
                  <span className={`status ${item.kind}`}>{item.kind === 'lost' ? 'Lost' : 'Found'}</span>
                </div>
                <div className="item-details">
                  <span className="category">{item.category}{item.owner_id === user?.id ? ' - Your report' : ''}</span>
                  <h3>{item.title}</h3>
                  <div className="item-meta">
                    <span><MapPin size={15} /> {item.location}</span>
                    <span><Clock size={15} /> {item.occurred_at.slice(0, 10)}</span>
                  </div>
                  {item.match && <p>{Math.round(item.match.score * 100)}% similarity: {item.match.reason}</p>}
                  <button className="details-link" onClick={() => openItem(item)}>View details</button>
                </div>
              </article>)}
            </div>
            {!loading && !error && visibleItems.length === 0 && <p className="empty">No reports found. Try another search or report an item.</p>}
            {!aiResults && <div className="action-row pagination">
              <button className="button secondary" disabled={page === 0 || loading} onClick={() => setPage(page - 1)}>Previous</button>
              <span>Page {page + 1}</span>
              <button className="button secondary" disabled={items.length < 20 || loading} onClick={() => setPage(page + 1)}>Next</button>
            </div>}
            <p className="disclaimer">AI suggestions help narrow the search. Verify ownership before handing over an item. AI searches send report descriptions and pictures to Gemini.</p>
          </>}
        </section>

        <section className="how section" id="how">
          <div className="section-heading centered">
            <span className="eyebrow">SIMPLE BY DESIGN</span>
            <h2>Three steps. One less worry.</h2>
          </div>

          <div className="steps">
            <article><span>01</span><Search /><h3>Search</h3><p>Search reported lost and found items.</p></article>
            <article><span>02</span><Plus /><h3>Report</h3><p>Share information about an item you've lost or found.</p></article>
            <article><span>03</span><Sparkles /><h3>Reconnect</h3><p>Compare possible matches and privately contact the reporter.</p></article>
          </div>
        </section>
      </main>

      <footer>
        <a href="#home" className="footer-logo">GHOSTCOMM <span>FIND</span></a>
        <p>Helping lost things find their way home.</p>
        <small>© {new Date().getFullYear()} GhostComm Find</small>
        <strong>PRIVACY IS A RIGHT, NOT A PRIVILEGE.</strong>
      </footer>

      {modal === 'auth' && <Modal title="Welcome to GhostComm Find" onClose={() => setModal(null)}>
        <AuthForm onLogin={value => { setToken(value); setPage(0); setError(''); setModal(pending); setPending(null) }} />
      </Modal>}
      {modal === 'report' && token && <Modal title="Report a lost or found item" onClose={() => setModal(null)}>
        <ReportForm api={api} onSaved={item => { setRevision(value => value + 1); openItem(item) }} />
      </Modal>}
      {modal === 'detail' && selected && token && user && <Modal title="Item report" onClose={() => setModal(null)}>
        <ItemDetail key={selected.id} initialItem={selected} api={api} userId={user.id}
          onChanged={() => setRevision(value => value + 1)} onOpenItem={openItem}
          onDeleted={() => { setModal(null); setRevision(value => value + 1) }} />
      </Modal>}
      {modal === 'inbox' && token && user && <Modal title="Your messages" onClose={() => setModal(null)}>
        <Inbox api={api} userId={user.id} />
      </Modal>}
    </div>
  )
}
