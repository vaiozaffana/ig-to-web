import { useCallback, useEffect, useMemo, useState } from 'react'
import type { FormEvent } from 'react'
import './App.css'

type WorkflowStatus =
  | 'instagram_collected'
  | 'asset_downloaded'
  | 'draft_generating'
  | 'draft_generated'
  | 'waiting_review'
  | 'approved'
  | 'publishing'
  | 'published'
  | 'rejected'
  | 'needs_revision'
  | 'fetch_failed'
  | 'generation_failed'
  | 'notification_failed'
  | 'publish_failed'

type MediaItem = {
  id: string
  media_url: string
  media_type: string
  thumbnail_url: string | null
  permalink: string | null
}

type Draft = {
  id: number
  instagram_post_id: number
  title: string
  slug: string
  summary: string
  content_markdown: string
  content_html: string
  meta_title: string
  meta_description: string
  category: string
  tags: string[]
  image_alt_text: string
  source_instagram_url: string
  source_media_url: string | null
  source_media_type: string | null
  source_media_items: MediaItem[]
  status: WorkflowStatus
  approved_by: string | null
  approved_at: string | null
  published_at: string | null
  error_message: string | null
  created_at: string
  updated_at: string
}

type SyncResult = {
  created_posts?: number
  skipped_duplicates?: number
  enqueued_generation?: number
  task_id?: string
  status?: string
}

type IntegrationStatus = {
  ok: boolean
  provider: string
  account_id: string | null
  username: string | null
  message: string
}

type View = 'queue' | 'articles'

const QUEUE_STATUSES: WorkflowStatus[] = [
  'waiting_review',
  'needs_revision',
  'approved',
  'generation_failed',
  'notification_failed',
  'publish_failed',
]

function statusLabel(status: WorkflowStatus) {
  return status.replaceAll('_', ' ')
}

function formatDate(value: string | null) {
  if (!value) return '-'
  return new Intl.DateTimeFormat('id-ID', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value))
}

function isVideoMedia(mediaType: string | null) {
  return mediaType?.toLowerCase().includes('video') ?? false
}

function mediaDisplayUrl(media: MediaItem) {
  return media.media_url || media.thumbnail_url || ''
}

function mediaTypeLabel(mediaType: string) {
  return mediaType.replaceAll('_', ' ')
}

async function api<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`/api${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  })

  if (!response.ok) {
    const body = await response.json().catch(() => null)
    throw new Error(body?.detail ?? `Request failed with ${response.status}`)
  }

  return response.json() as Promise<T>
}

function App() {
  const [view, setView] = useState<View>('queue')
  const [drafts, setDrafts] = useState<Draft[]>([])
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [loading, setLoading] = useState(false)
  const [busyAction, setBusyAction] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const queueDrafts = useMemo(
    () => drafts.filter((draft) => QUEUE_STATUSES.includes(draft.status)),
    [drafts],
  )

  const publishedDrafts = useMemo(
    () => drafts.filter((draft) => draft.status === 'published'),
    [drafts],
  )

  const visibleDrafts = view === 'queue' ? queueDrafts : publishedDrafts

  const selected = useMemo(
    () => visibleDrafts.find((draft) => draft.id === selectedId) ?? visibleDrafts[0] ?? null,
    [selectedId, visibleDrafts],
  )

  const selectedMedia = useMemo(() => {
    if (!selected) return []
    const mediaItems = selected.source_media_items ?? []
    if (mediaItems.length > 0) return mediaItems
    if (!selected.source_media_url) return []
    return [
      {
        id: `${selected.instagram_post_id}-primary`,
        media_url: selected.source_media_url,
        media_type: selected.source_media_type ?? 'image',
        thumbnail_url: null,
        permalink: selected.source_instagram_url,
      },
    ]
  }, [selected])

  const loadDrafts = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await api<Draft[]>('/admin/articles/drafts')
      setDrafts(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load drafts')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    const timeoutId = window.setTimeout(() => {
      void loadDrafts()
    }, 0)
    return () => window.clearTimeout(timeoutId)
  }, [loadDrafts])

  async function runAction(label: string, action: () => Promise<unknown>) {
    setBusyAction(label)
    setNotice(null)
    setError(null)
    try {
      await action()
      setNotice(label)
      await loadDrafts()
    } catch (err) {
      setError(err instanceof Error ? err.message : `${label} failed`)
    } finally {
      setBusyAction(null)
    }
  }

  function syncInstagram() {
    void runAction('Sync task queued', async () => {
      const status = await api<IntegrationStatus>('/admin/integrations/instagram/status')
      if (!status.ok || status.account_id === 'fake') {
        throw new Error(status.message)
      }
      const result = await api<SyncResult>('/admin/sync-instagram/task', {
        method: 'POST',
      })
      setNotice(
        result.task_id
          ? `Sync masuk Celery queue: ${result.task_id}`
          : `Sync selesai, ${result.enqueued_generation ?? 0} draft diproses`,
      )
    })
  }

  function checkInstagram() {
    void runAction('Instagram credential checked', async () => {
      const result = await api<IntegrationStatus>('/admin/integrations/instagram/status')
      if (!result.ok) {
        throw new Error(result.message)
      }
      setNotice(
        result.username
          ? `Instagram connected: ${result.username}`
          : 'Instagram credential valid',
      )
    })
  }

  function approveDraft(draft: Draft) {
    void runAction('Draft approved', () =>
      api(`/admin/articles/drafts/${draft.id}/approve`, { method: 'POST' }),
    )
  }

  function publishDraft(draft: Draft) {
    void runAction('Draft published', () =>
      api(`/admin/articles/drafts/${draft.id}/publish`, { method: 'POST' }),
    )
  }

  function rejectDraft(draft: Draft) {
    void runAction('Draft rejected', () =>
      api(`/admin/articles/drafts/${draft.id}/reject`, {
        method: 'POST',
        body: JSON.stringify({ comment: 'Rejected from frontend test UI' }),
      }),
    )
  }

  function reviseDraft(event: FormEvent<HTMLFormElement>, draft: Draft) {
    event.preventDefault()
    const form = new FormData(event.currentTarget)
    const comment = String(form.get('comment') || '').trim()
    if (!comment) {
      setError('Catatan revisi wajib diisi')
      return
    }
    void runAction('Revision requested', () =>
      api(`/admin/articles/drafts/${draft.id}/revise`, {
        method: 'POST',
        body: JSON.stringify({ comment }),
      }),
    )
    event.currentTarget.reset()
  }

  return (
    <main className="app-shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">Instagram Article Automation</p>
          <h1>Review Draft Artikel</h1>
        </div>
        <div className="topbar-actions">
          <button type="button" className="secondary-button" onClick={() => void loadDrafts()}>
            Refresh
          </button>
          <button type="button" className="secondary-button" onClick={checkInstagram}>
            Check Instagram
          </button>
          <button type="button" className="primary-button" onClick={syncInstagram}>
            Sync Instagram
          </button>
        </div>
      </header>

      <nav className="tabs" aria-label="Main view">
        <button
          type="button"
          className={view === 'queue' ? 'active' : ''}
          onClick={() => setView('queue')}
        >
          Antrian <span>{queueDrafts.length}</span>
        </button>
        <button
          type="button"
          className={view === 'articles' ? 'active' : ''}
          onClick={() => setView('articles')}
        >
          Articles <span>{publishedDrafts.length}</span>
        </button>
      </nav>

      {(notice || error || busyAction) && (
        <section className="status-strip" aria-live="polite">
          {busyAction && <span className="loading">Processing: {busyAction}</span>}
          {notice && <span className="success">{notice}</span>}
          {error && <span className="error">{error}</span>}
        </section>
      )}

      <section className="workspace">
        <aside className="draft-list" aria-label={view === 'queue' ? 'Antrian' : 'Articles'}>
          <div className="panel-header">
            <h2>{view === 'queue' ? 'Antrian' : 'Published Articles'}</h2>
            {loading && <span>Loading</span>}
          </div>

          {visibleDrafts.length === 0 ? (
            <div className="empty-state">
              {view === 'queue'
                ? 'Belum ada draft di antrian. Jalankan sync untuk membuat draft.'
                : 'Belum ada artikel published.'}
            </div>
          ) : (
            <ul>
              {visibleDrafts.map((draft) => (
                <li key={draft.id}>
                  <button
                    type="button"
                    className={selected?.id === draft.id ? 'selected' : ''}
                    onClick={() => setSelectedId(draft.id)}
                  >
                    <span className="draft-title">{draft.title}</span>
                    <span className={`badge ${draft.status}`}>{statusLabel(draft.status)}</span>
                    <span className="draft-date">{formatDate(draft.updated_at)}</span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </aside>

        <section className="detail-panel">
          {!selected ? (
            <div className="empty-detail">Pilih draft untuk review.</div>
          ) : (
            <article>
              <div className="detail-meta">
                <span className={`badge ${selected.status}`}>{statusLabel(selected.status)}</span>
                <span>Updated {formatDate(selected.updated_at)}</span>
                <span>Post #{selected.instagram_post_id}</span>
              </div>

              <h2>{selected.title}</h2>
              <p className="summary">{selected.summary}</p>

              {selectedMedia.length > 0 && (
                <div className="media-gallery" aria-label="Instagram media">
                  {selectedMedia.map((media, index) => {
                    const displayUrl = mediaDisplayUrl(media)
                    if (!displayUrl) return null
                    return (
                      <figure key={`${media.id}-${index}`} className="media-preview">
                        {isVideoMedia(media.media_type) ? (
                          <video
                            src={media.media_url || media.thumbnail_url || undefined}
                            poster={media.thumbnail_url ?? undefined}
                            controls
                            preload="metadata"
                          />
                        ) : (
                          <img
                            src={displayUrl}
                            alt={`${selected.image_alt_text} ${index + 1}`}
                          />
                        )}
                        {selectedMedia.length > 1 && (
                          <figcaption>
                            {index + 1}/{selectedMedia.length} · {mediaTypeLabel(media.media_type)}
                          </figcaption>
                        )}
                      </figure>
                    )
                  })}
                </div>
              )}

              <dl className="meta-grid">
                <div>
                  <dt>Category</dt>
                  <dd>{selected.category}</dd>
                </div>
                <div>
                  <dt>Slug</dt>
                  <dd>{selected.slug}</dd>
                </div>
                <div>
                  <dt>Meta title</dt>
                  <dd>{selected.meta_title}</dd>
                </div>
                <div>
                  <dt>Published</dt>
                  <dd>{formatDate(selected.published_at)}</dd>
                </div>
              </dl>

              {selected.error_message && (
                <div className="inline-error">{selected.error_message}</div>
              )}

              <div className="tag-row">
                {selected.tags.map((tag) => (
                  <span key={tag}>{tag}</span>
                ))}
              </div>

              <div className="content-preview">
                <h3>Content</h3>
                <pre>{selected.content_markdown}</pre>
              </div>

              <div className="source-row">
                <a href={selected.source_instagram_url} target="_blank" rel="noreferrer">
                  Open Instagram source
                </a>
              </div>

              {view === 'queue' && (
                <div className="review-actions">
                  <button
                    type="button"
                    className="secondary-button"
                    onClick={() => approveDraft(selected)}
                    disabled={!['waiting_review', 'needs_revision'].includes(selected.status)}
                  >
                    Approve
                  </button>
                  <button
                    type="button"
                    className="primary-button"
                    onClick={() => publishDraft(selected)}
                    disabled={selected.status !== 'approved'}
                  >
                    Publish
                  </button>
                  <button
                    type="button"
                    className="danger-button"
                    onClick={() => rejectDraft(selected)}
                    disabled={selected.status === 'published'}
                  >
                    Reject
                  </button>
                </div>
              )}

              {view === 'queue' && (
                <form className="revision-box" onSubmit={(event) => reviseDraft(event, selected)}>
                  <label htmlFor="comment">Catatan revisi</label>
                  <textarea
                    id="comment"
                    name="comment"
                    placeholder="Contoh: ringkas paragraf kedua dan gunakan judul lebih formal"
                    rows={3}
                  />
                  <button
                    type="submit"
                    className="secondary-button"
                    disabled={!['waiting_review', 'needs_revision'].includes(selected.status)}
                  >
                    Request Revision
                  </button>
                </form>
              )}
            </article>
          )}
        </section>
      </section>
    </main>
  )
}

export default App
