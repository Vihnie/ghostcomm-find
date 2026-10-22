import { useState } from 'react'
import {
  Search, Plus, ShieldCheck, Sparkles, MapPin,
  Clock, Laptop, KeyRound, BookOpen, Menu, X
} from 'lucide-react'
import './App.css'

const items = [
  { id: 1, name: 'Black laptop sleeve', type: 'Found', category: 'Electronics', location: 'Main Library', date: 'Today', icon: Laptop },
  { id: 2, name: 'Set of keys', type: 'Lost', category: 'Personal items', location: 'Main Gate', date: 'Yesterday', icon: KeyRound },
  { id: 3, name: 'Business textbook', type: 'Found', category: 'Books', location: 'Lecture Block', date: '2 days ago', icon: BookOpen },
]

export default function App() {
  const [search, setSearch] = useState('')
  const [filter, setFilter] = useState('All')
  const [menu, setMenu] = useState(false)
  const [modal, setModal] = useState(false)

  const filteredItems = items.filter(item => {
    const matchesFilter = filter === 'All' || item.type === filter
    const matchesSearch =
      `${item.name} ${item.category} ${item.location}`
        .toLowerCase()
        .includes(search.toLowerCase())

    return matchesFilter && matchesSearch
  })

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

        <button className="menu-toggle" onClick={() => setMenu(!menu)}>
          {menu ? <X /> : <Menu />}
        </button>

        <nav className={menu ? 'nav-links open' : 'nav-links'}>
          <a href="#browse" onClick={() => setMenu(false)}>Browse items</a>
          <a href="#how" onClick={() => setMenu(false)}>How it works</a>
          <button className="button primary" onClick={() => setModal(true)}>
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
              <button className="button secondary" onClick={() => setModal(true)}>
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
            <span className="preview-tag">DEMO LISTINGS</span>
          </div>

          <div className="search-row">
            <label className="search-input">
              <Search size={20} />
              <input
                value={search}
                onChange={e => setSearch(e.target.value)}
                placeholder="Search keys, books, electronics..."
              />
            </label>

            <div className="filters">
              {['All', 'Lost', 'Found'].map(option => (
                <button
                  key={option}
                  className={filter === option ? 'filter active' : 'filter'}
                  onClick={() => setFilter(option)}
                >
                  {option}
                </button>
              ))}
            </div>
          </div>

          <p className="result-count">
            Showing {filteredItems.length} sample {filteredItems.length === 1 ? 'item' : 'items'}
          </p>

          <div className="item-grid">
            {filteredItems.map(item => {
              const ItemIcon = item.icon
              return (
                <article className="item-card" key={item.id}>
                  <div className="item-image">
                    <ItemIcon size={42} />
                    <span className={`status ${item.type.toLowerCase()}`}>
                      {item.type}
                    </span>
                  </div>
                  <div className="item-details">
                    <span className="category">{item.category}</span>
                    <h3>{item.name}</h3>
                    <div className="item-meta">
                      <span><MapPin size={15} /> {item.location}</span>
                      <span><Clock size={15} /> {item.date}</span>
                    </div>
                    <button className="details-link" onClick={() => setModal(true)}>
                      View details →
                    </button>
                  </div>
                </article>
              )
            })}
          </div>

          {filteredItems.length === 0 && (
            <p className="empty">No items match your search. Try another keyword.</p>
          )}

          <p className="disclaimer">
            These are sample listings for the frontend preview, not live backend records.
          </p>
        </section>

        <section className="how section" id="how">
          <div className="section-heading centered">
            <span className="eyebrow">SIMPLE BY DESIGN</span>
            <h2>Three steps. One less worry.</h2>
          </div>

          <div className="steps">
            <article><span>01</span><Search /><h3>Search</h3><p>Search reported lost and found items.</p></article>
            <article><span>02</span><Plus /><h3>Report</h3><p>Share information about an item you've lost or found.</p></article>
            <article><span>03</span><Sparkles /><h3>Reconnect</h3><p>Work toward smarter matching and secure recovery.</p></article>
          </div>
        </section>
      </main>

      <footer>
        <a href="#home" className="footer-logo">GHOSTCOMM <span>FIND</span></a>
        <p>Helping lost things find their way home.</p>
        <small>© {new Date().getFullYear()} GhostComm Find</small>
        <strong>PRIVACY IS A RIGHT, NOT A PRIVILEGE.</strong>
      </footer>

      {modal && (
        <div className="modal-overlay" onClick={() => setModal(false)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <button className="modal-close" onClick={() => setModal(false)}><X /></button>
            <ShieldCheck size={36} />
            <h2>GhostComm Find</h2>
            <p>
              This interface is a frontend preview. We need to connect it to
              your existing FastAPI routes before reports, login, or item
              details can use real data.
            </p>
            <button className="button primary" onClick={() => setModal(false)}>Got it</button>
          </div>
        </div>
      )}
    </div>
  )
}
