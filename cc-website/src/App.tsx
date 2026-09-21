import { useEffect, useMemo, useState } from 'react'
import { partners, type Leader, type Partner } from './data/partners'
import './App.css'

const focusAreas = [
  'All partners',
  'FY25 VSUW funded',
  'Not FY25 VSUW funded',
  'ASU alumni',
]

const getInitials = (name: string) =>
  name
    .split(' ')
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0])
    .join('')

const assetUrl = (url: string) =>
  url.startsWith('/') ? `${import.meta.env.BASE_URL}${url.slice(1)}` : url

const paragraphs = (content: string) =>
  content
    .split('\n\n')
    .map((item) => item.trim())
    .filter(Boolean)

const statusLabel = (partner: Partner) =>
  partner.funded
    ? 'FY25 VSUW funded'
    : partner.status.toLowerCase().includes('not available')
      ? 'FY25 VSUW status unavailable'
      : 'Not FY25 VSUW funded'

const isAsuAlum = (partner: Partner) => partner.asuAlum.toLowerCase() === 'yes'
const alumLabel = (partner: Partner) =>
  isAsuAlum(partner) ? '🔱 ASU alum' : partner.asuAlum ? 'Not ASU alum' : 'Alum status needed'

function LeaderPhoto({ leader, large = false }: { leader: Leader; large?: boolean }) {
  if (leader.photo) {
    return (
      <img
        className={large ? 'leader-photo large' : 'leader-photo'}
        src={assetUrl(leader.photo)}
        alt={leader.name}
      />
    )
  }

  return <div className={large ? 'avatar large' : 'avatar'}>{getInitials(leader.name)}</div>
}

function App() {
  const [activeFilter, setActiveFilter] = useState(focusAreas[0])
  const [selected, setSelected] = useState<Partner | null>(null)
  const [imageViewer, setImageViewer] = useState<Leader | null>(null)
  const [detailMode, setDetailMode] = useState<'organization' | 'leader'>('organization')
  const [query, setQuery] = useState('')

  useEffect(() => {
    document.body.style.overflow = selected ? 'hidden' : ''
    return () => {
      document.body.style.overflow = ''
    }
  }, [selected])

  const filteredPartners = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase()

    return partners.filter((partner) => {
      const matchesFilter =
        activeFilter === 'All partners' ||
        (activeFilter === 'FY25 VSUW funded' && partner.funded) ||
        (activeFilter === 'Not FY25 VSUW funded' && !partner.funded) ||
        (activeFilter === 'ASU alumni' && isAsuAlum(partner))
      const matchesSearch =
        !normalizedQuery ||
        partner.organization.toLowerCase().includes(normalizedQuery) ||
        partner.leader.toLowerCase().includes(normalizedQuery) ||
        partner.asuAlumDetails.toLowerCase().includes(normalizedQuery)

      return matchesFilter && matchesSearch
    })
  }, [activeFilter, query])

  const fundedCount = partners.filter((partner) => partner.funded).length
  const asuAlumCount = partners.filter(isAsuAlum).length
  const selectedLeader =
    selected?.leadership.find((leader) => leader.name === selected.leader) ??
    selected?.leadership[0]

  const openPartner = (partner: Partner, mode: 'organization' | 'leader') => {
    setSelected(partner)
    setDetailMode(mode)
  }

  return (
    <main className="app-shell">
      <header className="hero">
        <div className="hero-copy">
          <span className="eyebrow">ASU Community Council</span>
          <h1>Community partner portfolio</h1>
          <p>
            Browse organization profiles, executive leadership, source links, and
            FY25 Valley of the Sun United Way funded partner status.
          </p>
        </div>
        <div className="hero-panel" aria-label="Portfolio summary">
          <div>
            <span>Total partners</span>
            <strong>{partners.length}</strong>
          </div>
          <div>
            <span>FY25 VSUW funded</span>
            <strong>{fundedCount}</strong>
          </div>
          <div>
            <span>🔱 ASU alumni</span>
            <strong>{asuAlumCount}</strong>
          </div>
        </div>
      </header>

      <section className="toolbar" aria-label="Directory controls">
        <label className="search">
          <span>Search</span>
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Organization or leader"
          />
        </label>
        <div className="segments" role="tablist" aria-label="Partner status filter">
          {focusAreas.map((filter) => (
            <button
              className={filter === activeFilter ? 'active' : ''}
              key={filter}
              onClick={() => setActiveFilter(filter)}
              type="button"
            >
              {filter}
            </button>
          ))}
        </div>
      </section>

      <section className="directory-wrap">
        <div className="section-heading">
          <div>
            <h2>Partner directory</h2>
            <p>{filteredPartners.length} organizations visible</p>
          </div>
        </div>

        <section className="directory" aria-label="Partner directory">
          {filteredPartners.map((partner) => {
            const leader = partner.leader
              ? partner.leadership.find((person) => person.name === partner.leader) ??
                partner.leadership[0] ?? { name: partner.leader, title: partner.position, photo: '' }
              : null

            return (
              <article
                className="partner-card"
                key={partner.organization}
                onClick={() => openPartner(partner, 'organization')}
              >
                <div className="card-top">
                  {leader ? (
                    <button
                      className="photo-button"
                      aria-label={`View ${leader.name}'s full picture`}
                      onClick={(event) => {
                        event.stopPropagation()
                        openPartner(partner, 'leader')
                      }}
                      type="button"
                    >
                      <LeaderPhoto leader={leader} />
                    </button>
                  ) : (
                    <div className="avatar blank" aria-hidden="true" />
                  )}
                  <div className="badge-stack">
                    <span className={partner.funded ? 'badge funded' : 'badge'}>
                      {partner.funded ? 'FY25 VSUW funded' : 'Not FY25 VSUW funded'}
                    </span>
                    <span className={isAsuAlum(partner) ? 'badge gold' : 'badge'}>
                      {alumLabel(partner)}
                    </span>
                  </div>
                </div>
                <button className="org-button" type="button">
                  {partner.organization}
                </button>
                {leader ? (
                  <>
                    <button
                      className="leader-button"
                      onClick={(event) => {
                        event.stopPropagation()
                        openPartner(partner, 'leader')
                      }}
                      type="button"
                    >
                      {partner.leader}
                    </button>
                    <p>{partner.position}</p>
                  </>
                ) : null}
              </article>
            )
          })}
        </section>
      </section>

      {selected ? (
        <div
          className="modal-backdrop"
          onClick={() => setSelected(null)}
          role="presentation"
        >
              <section
            className="profile-modal"
            aria-label={`${selected.organization} profile`}
            onClick={(event) => event.stopPropagation()}
          >
            <div className="modal-rail">
              {selectedLeader ? (
                <button className="modal-photo-button" aria-label={`View ${selectedLeader.name}'s full picture`} onClick={() => setImageViewer(selectedLeader)} type="button">
                  <LeaderPhoto leader={selectedLeader} large />
                </button>
              ) : null}
              <span
                className={selected.funded ? 'badge funded' : 'badge'}
                title={selected.status}
              >
                {statusLabel(selected)}
              </span>
              <span
                className={isAsuAlum(selected) ? 'badge gold' : 'badge'}
                title={selected.asuAlumDetails || alumLabel(selected)}
              >
                {alumLabel(selected)}
              </span>
              <h2>{selected.organization}</h2>
              {selected.leader ? <p>{selected.leader}</p> : null}
              {selected.position ? <p>{selected.position}</p> : null}
              <div className="modal-actions">
                <a href={selected.website} target="_blank" rel="noreferrer">
                  Website
                </a>
                {selected.linkedin ? (
                  <a href={selected.linkedin} target="_blank" rel="noreferrer">
                    LinkedIn
                  </a>
                ) : null}
                {selected.collaboratory ? (
                  <a href={selected.collaboratory} target="_blank" rel="noreferrer">
                    Collaboratory
                  </a>
                ) : null}
                {selected.googleDrive ? (
                  <a href={selected.googleDrive} target="_blank" rel="noreferrer">
                    Google Drive
                  </a>
                ) : null}
              </div>
            </div>

            <div className="modal-main">
              <div className="modal-header">
                <div className={selected.leader ? 'detail-tabs' : 'detail-tabs single'}>
                  <button
                    className={detailMode === 'organization' ? 'active' : ''}
                    onClick={() => setDetailMode('organization')}
                    type="button"
                  >
                    Organization
                  </button>
                  {selected.leader ? (
                    <button
                      className={detailMode === 'leader' ? 'active' : ''}
                      onClick={() => setDetailMode('leader')}
                      type="button"
                    >
                      Leader
                    </button>
                  ) : null}
                </div>
                <button className="close-button" onClick={() => setSelected(null)} type="button">
                  Close
                </button>
              </div>

              <div className="modal-scroll">
                {detailMode === 'organization' ? (
                <div className="profile-content">
                  <section>
                    <h3>About</h3>
                    {paragraphs(selected.about).map((paragraph) => (
                      <p key={paragraph}>{paragraph}</p>
                    ))}
                  </section>
                  <section>
                    <h3>Mission & Vision</h3>
                    {paragraphs(selected.missionVision).map((paragraph) => (
                      <p key={paragraph}>{paragraph}</p>
                    ))}
                  </section>
                  {selected.leadership.length ? (
                    <section>
                      <h3>Leadership</h3>
                      <div className="leadership-grid">
                        {selected.leadership.map((leader) => (
                          <article className="leader-tile" key={`${leader.name}-${leader.title}`}>
                            <LeaderPhoto leader={leader} />
                            <div>
                              <strong>{leader.name}</strong>
                              <span>{leader.title}</span>
                            </div>
                          </article>
                        ))}
                      </div>
                    </section>
                  ) : null}
                </div>
                ) : (
                <div className="profile-content">
                  <section className="person-focus">
                    {selectedLeader ? <LeaderPhoto leader={selectedLeader} large /> : null}
                    <div>
                      <span className="badge gold">Executive deep dive</span>
                      <h3>{selected.leader}</h3>
                      <p>
                        {selected.leader} is listed as {selected.position} for{' '}
                        {selected.organization}. This profile is connected to the
                        organization's public profile, funding status, and source notes.
                      </p>
                      {selected.linkedin ? (
                        <a
                          className="profile-link"
                          href={selected.linkedin}
                          target="_blank"
                          rel="noreferrer"
                        >
                          LinkedIn
                        </a>
                      ) : null}
                    </div>
                  </section>
                  {isAsuAlum(selected) ? (
                    <section>
                      <h3>🔱 ASU Alum Details</h3>
                      <p>{selected.asuAlumDetails || 'Listed as an ASU alum.'}</p>
                    </section>
                  ) : null}
                  <section>
                    <h3>Organization Context</h3>
                    <p>{paragraphs(selected.about)[0]}</p>
                  </section>
                </div>
                )}

              </div>
            </div>
          </section>
        </div>
      ) : null}

      {imageViewer ? (
        <div className="image-viewer-backdrop" onClick={() => setImageViewer(null)} role="presentation">
          <section className="image-viewer" aria-label={`${imageViewer.name} full picture`} onClick={(event) => event.stopPropagation()}>
            <button className="image-viewer-close" onClick={() => setImageViewer(null)} type="button">Close</button>
            {imageViewer.photo ? <img src={assetUrl(imageViewer.photo)} alt={imageViewer.name} /> : <div className="image-viewer-fallback">{getInitials(imageViewer.name)}</div>}
            <strong>{imageViewer.name}</strong>
            <span>{imageViewer.title}</span>
          </section>
        </div>
      ) : null}
    </main>
  )
}

export default App
