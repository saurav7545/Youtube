import { useEffect, useState } from 'react'
import './App.css'

function HomeText() {
  return (
    <main className="page-content" id="home">
      <section className="hero-copy">
        <h1>Download YouTube Videos Instantly</h1>
        <p>
          Download YouTube videos instantly with our free tool. No signup, no
          ads, no waiting.
        </p>
        <p>
          Your ultimate YouTube video, audio, and playlist downloader. Fast,
          free, unlimited.
        </p>
      </section>
    </main>
  )
}

const QUALITY_OPTIONS = {
  video: ['144p', '240p', '360p', '480p', '720p', '1080p'],
  audio: ['64 kbps', '128 kbps', '192 kbps', '320 kbps'],
}

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '')
const apiUrl = (path) => `${API_BASE_URL}${path}`
const GITHUB_REPO_URL = 'https://github.com/saurav7545/Youtube'
const API_NOTE_URL = `${GITHUB_REPO_URL}/blob/main/API_NOTE.md`
const AUTH_ERROR_MARKERS = [
  "sign in to confirm you're not a bot",
  '--cookies-from-browser',
  '--cookies',
  'requirescookies',
  'youtube authentication',
  'cookies.txt',
  'login required',
]
const QUALITY_PATTERN = {
  video: /^(\d{3,4})p$/i,
  audio: /^(\d{2,3})\s*kbps$/i,
}

const normalizeAuthText = (value = '') =>
  value.toLowerCase().replaceAll('’', "'").replace(/\s+/g, ' ').trim()

const hasAuthErrorMarker = (value = '') => {
  const normalized = normalizeAuthText(value)
  return AUTH_ERROR_MARKERS.some((marker) => normalized.includes(marker))
}

const isAuthRequiredPayload = (payload = {}, fallbackMessage = '') => {
  if (payload.requiresCookies) {
    return true
  }

  return hasAuthErrorMarker(
    [payload.error, payload.details, fallbackMessage].filter(Boolean).join(' '),
  )
}

const extractErrorMessage = (payload = {}, fallbackMessage = '') =>
  payload.error || payload.details || fallbackMessage

const getDisplayErrorMessage = (error, fallbackMessage) => {
  if (error instanceof TypeError) {
    return 'Cannot reach API server. Check backend/proxy or VITE_API_BASE_URL in .env.local.'
  }
  return error?.message || fallbackMessage
}

const parseQualityRank = (quality, type) => {
  const match = quality?.trim().match(QUALITY_PATTERN[type])
  return match ? Number(match[1]) : null
}

const normalizeQualityList = (values, type) => {
  const fallback = QUALITY_OPTIONS[type]
  const sorted = [...new Set((values || []).map((item) => item?.trim()).filter(Boolean))]
    .filter((item) => QUALITY_PATTERN[type].test(item))
    .sort((left, right) => {
      const leftRank = parseQualityRank(left, type) ?? 0
      const rightRank = parseQualityRank(right, type) ?? 0
      return rightRank - leftRank
    })

  return sorted.length > 0 ? sorted : fallback
}

const getFilenameFromDisposition = (contentDisposition) => {
  if (!contentDisposition) {
    return ''
  }

  const utf8Match = contentDisposition.match(/filename\*=UTF-8''([^;]+)/i)
  if (utf8Match?.[1]) {
    return decodeURIComponent(utf8Match[1].trim())
  }

  const simpleMatch = contentDisposition.match(/filename="?([^";]+)"?/i)
  return simpleMatch?.[1]?.trim() || ''
}

function Box() {
  const [videoUrl, setVideoUrl] = useState('')
  const [videoId, setVideoId] = useState('')
  const [videoTitle, setVideoTitle] = useState('')
  const [thumbnailUrl, setThumbnailUrl] = useState('')
  const [downloadType, setDownloadType] = useState('video')
  const [quality, setQuality] = useState('360p')
  const [videoQualities, setVideoQualities] = useState(QUALITY_OPTIONS.video)
  const [audioQualities, setAudioQualities] = useState(QUALITY_OPTIONS.audio)
  const [status, setStatus] = useState('')
  const [statusType, setStatusType] = useState('')
  const [isSearching, setIsSearching] = useState(false)
  const [isDownloading, setIsDownloading] = useState(false)
  const [isAuthPopupOpen, setIsAuthPopupOpen] = useState(false)
  const [authPopupDetails, setAuthPopupDetails] = useState('')

  const qualityList = downloadType === 'video' ? videoQualities : audioQualities

  const openAuthPopup = (payloadOrMessage = {}) => {
    if (typeof payloadOrMessage === 'string') {
      setAuthPopupDetails(payloadOrMessage)
    } else {
      setAuthPopupDetails(payloadOrMessage.details || payloadOrMessage.error || '')
    }
    setIsAuthPopupOpen(true)
  }

  const closeAuthPopup = () => {
    setIsAuthPopupOpen(false)
  }

  useEffect(() => {
    if (!isAuthPopupOpen) {
      return undefined
    }

    const handleEsc = (event) => {
      if (event.key === 'Escape') {
        setIsAuthPopupOpen(false)
      }
    }

    window.addEventListener('keydown', handleEsc)
    return () => window.removeEventListener('keydown', handleEsc)
  }, [isAuthPopupOpen])

  const handleTypeChange = (nextType) => {
    const nextQualityList = nextType === 'video' ? videoQualities : audioQualities
    setDownloadType(nextType)
    setQuality(nextQualityList[0] || QUALITY_OPTIONS[nextType][0])
  }

  const handleSearch = async (event) => {
    event.preventDefault()

    const cleanUrl = videoUrl.trim()
    if (!cleanUrl) {
      setStatusType('error')
      setStatus('Please paste a valid YouTube URL first.')
      return
    }

    setIsSearching(true)
    setStatusType('')
    setStatus('Searching video details...')

    try {
      const response = await fetch(
        `${apiUrl('/api/yt/info')}?url=${encodeURIComponent(cleanUrl)}`,
      )
      const payload = await response.json().catch(() => ({}))

      if (!response.ok) {
        const fallbackMessage = 'Unable to fetch video details.'
        if (isAuthRequiredPayload(payload, fallbackMessage)) {
          openAuthPopup(payload)
        }
        throw new Error(extractErrorMessage(payload, fallbackMessage))
      }

      const nextVideoQualities = normalizeQualityList(payload.videoQualities, 'video')
      const nextAudioQualities = normalizeQualityList(payload.audioQualities, 'audio')

      setVideoId(payload.videoId || '')
      setVideoTitle(payload.title || 'YouTube Video')
      setThumbnailUrl(payload.thumbnail || '')
      setVideoQualities(nextVideoQualities)
      setAudioQualities(nextAudioQualities)
      setDownloadType('video')
      setQuality(nextVideoQualities[0] || QUALITY_OPTIONS.video[0])
      setStatusType('success')
      setStatus('Thumbnail loaded. Select format and quality.')
    } catch (error) {
      setVideoId('')
      setVideoTitle('')
      setThumbnailUrl('')
      setStatusType('error')
      const nextMessage = getDisplayErrorMessage(error, 'Failed to load thumbnail.')
      if (hasAuthErrorMarker(nextMessage)) {
        openAuthPopup(nextMessage)
      }
      setStatus(nextMessage)
    } finally {
      setIsSearching(false)
    }
  }

  const handleDownload = async () => {
    const cleanUrl = videoUrl.trim()
    if (!videoId || !cleanUrl) {
      setStatusType('error')
      setStatus('Paste link and click search first.')
      return
    }

    setIsDownloading(true)
    setStatusType('')
    setStatus(`Preparing ${downloadType} download in ${quality}...`)

    try {
      const params = new URLSearchParams({
        url: cleanUrl,
        type: downloadType,
        quality,
      })
      const response = await fetch(`${apiUrl('/api/yt/download')}?${params.toString()}`)

      if (!response.ok) {
        const payload = await response.json().catch(() => ({}))
        const fallbackMessage = 'Unable to download file.'
        if (isAuthRequiredPayload(payload, fallbackMessage)) {
          openAuthPopup(payload)
        }
        throw new Error(extractErrorMessage(payload, fallbackMessage))
      }

      const blob = await response.blob()
      if (blob.size === 0) {
        throw new Error('The downloaded file is empty. Please try another quality.')
      }

      const contentDisposition = response.headers.get('content-disposition')
      const filename =
        getFilenameFromDisposition(contentDisposition) ||
        `${videoId}-${downloadType}-${quality.replace(/\s+/g, '').toLowerCase()}`

      const objectUrl = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = objectUrl
      link.download = filename
      document.body.appendChild(link)
      link.click()
      link.remove()
      window.URL.revokeObjectURL(objectUrl)

      setStatusType('success')
      setStatus(`Download started in ${quality}.`)
    } catch (error) {
      setStatusType('error')
      const nextMessage = getDisplayErrorMessage(
        error,
        'Download failed. Try another quality.',
      )
      if (hasAuthErrorMarker(nextMessage)) {
        openAuthPopup(nextMessage)
      }
      setStatus(nextMessage)
    } finally {
      setIsDownloading(false)
    }
  }

  return (
    <section className="download-box" id="download-history">
      <h2>Downloader Box</h2>
      <p className="download-subtitle">
        Paste link, search, preview thumbnail, then download.
      </p>

      <form className="download-form" onSubmit={handleSearch}>
        <label htmlFor="video-url" className="input-label">
          Paste YouTube Link
        </label>

        <div className="search-row">
          <input
            id="video-url"
            type="url"
            inputMode="url"
            placeholder="https://www.youtube.com/watch?v=..."
            value={videoUrl}
            onChange={(event) => setVideoUrl(event.target.value)}
            required
          />
          <button type="submit" className="search-button" disabled={isSearching}>
            {isSearching ? 'Searching...' : 'Search'}
          </button>
        </div>

        {videoId && thumbnailUrl && (
          <div className="preview-panel">
            <img
              className="thumbnail-image"
              src={thumbnailUrl}
              alt="YouTube video thumbnail preview"
            />

            <div className="download-controls">
              <p className="video-title">{videoTitle}</p>
              <p className="option-title">Audio / Video</p>
              <div className="type-buttons" role="group" aria-label="Select format">
                <button
                  type="button"
                  className={downloadType === 'video' ? 'active' : ''}
                  onClick={() => handleTypeChange('video')}
                >
                  Video
                </button>
                <button
                  type="button"
                  className={downloadType === 'audio' ? 'active' : ''}
                  onClick={() => handleTypeChange('audio')}
                >
                  Audio
                </button>
              </div>

              <p className="option-title">Quality Options</p>
              <div className="quality-buttons" role="group" aria-label="Select quality">
                {qualityList.map((option) => (
                  <button
                    type="button"
                    key={option}
                    className={quality === option ? 'active' : ''}
                    onClick={() => setQuality(option)}
                  >
                    {option}
                  </button>
                ))}
              </div>

              <button
                type="button"
                className="download-primary"
                onClick={handleDownload}
                disabled={isDownloading}
              >
                {isDownloading ? 'Downloading...' : 'Download now'}
              </button>
            </div>
          </div>
        )}

        <p
          className={`download-status${statusType ? ` ${statusType}` : ''}`}
          aria-live="polite"
        >
          {status || 'Paste a YouTube link and click search.'}
        </p>
      </form>

      {isAuthPopupOpen && (
        <div
          className="auth-modal-backdrop"
          role="presentation"
          onClick={closeAuthPopup}
        >
          <div
            className="auth-modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="auth-modal-title"
            onClick={(event) => event.stopPropagation()}
          >
            <h3 id="auth-modal-title">Sign-in Required for This Video</h3>
            <p className="auth-modal-text">
              this video downloading problem is due to backend api not working properly. please visit github repo for more information            </p>
            {authPopupDetails && <p className="auth-modal-details">{authPopupDetails}</p>}
            <div className="auth-modal-links">
              <a href={GITHUB_REPO_URL} target="_blank" rel="noreferrer">
                Open GitHub Repo
              </a>
              <a href={API_NOTE_URL} target="_blank" rel="noreferrer">
                Open api.md (API_NOTE.md)
              </a>
            </div>
            <button type="button" className="auth-modal-close" onClick={closeAuthPopup}>
              Close
            </button>
          </div>
        </div>
      )}
    </section>
  )
}

function App() {
  return (
    <>
      <header className="navbar">
        <button type="button" className="logo-button" aria-label="Go to home">
          <span className="logo-icon">YT</span>
          <span className="logo-text">YouTube</span>
        </button>

        <nav className="nav-menu" aria-label="Primary">
          <a href="#home">Home</a>
          <a href="#download-history">Download History</a>
          <a href="#about">About</a>
          <a href="#help">Help</a>
        </nav>
      </header>

      <HomeText />
      <Box />
    </>
  )
}

export default App
