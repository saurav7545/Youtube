import { useState } from 'react'
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
  const [isSearching, setIsSearching] = useState(false)

  const qualityList = downloadType === 'video' ? videoQualities : audioQualities

  const handleTypeChange = (nextType) => {
    const nextQualityList = nextType === 'video' ? videoQualities : audioQualities
    setDownloadType(nextType)
    setQuality(nextQualityList[0] || QUALITY_OPTIONS[nextType][0])
  }

  const handleSearch = async (event) => {
    event.preventDefault()

    const cleanUrl = videoUrl.trim()
    if (!cleanUrl) {
      setStatus('Please paste a valid YouTube URL first.')
      return
    }

    setIsSearching(true)
    setStatus('Searching video details...')

    try {
      const response = await fetch(
        `${apiUrl('/api/yt/info')}?url=${encodeURIComponent(cleanUrl)}`,
      )
      const payload = await response.json().catch(() => ({}))

      if (!response.ok) {
        throw new Error(payload.error || 'Unable to fetch video details.')
      }

      const nextVideoQualities =
        payload.videoQualities?.length > 0
          ? payload.videoQualities
          : QUALITY_OPTIONS.video
      const nextAudioQualities =
        payload.audioQualities?.length > 0
          ? payload.audioQualities
          : QUALITY_OPTIONS.audio

      setVideoId(payload.videoId || '')
      setVideoTitle(payload.title || 'YouTube Video')
      setThumbnailUrl(payload.thumbnail || '')
      setVideoQualities(nextVideoQualities)
      setAudioQualities(nextAudioQualities)
      setDownloadType('video')
      setQuality(nextVideoQualities[0] || QUALITY_OPTIONS.video[0])
      setStatus('Thumbnail loaded. Select format and quality.')
    } catch (error) {
      setVideoId('')
      setVideoTitle('')
      setThumbnailUrl('')
      setStatus(error.message || 'Failed to load thumbnail.')
    } finally {
      setIsSearching(false)
    }
  }

  const handleDownload = () => {
    const cleanUrl = videoUrl.trim()
    if (!videoId || !cleanUrl) {
      setStatus('Paste link and click search first.')
      return
    }

    const params = new URLSearchParams({
      url: cleanUrl,
      type: downloadType,
      quality,
    })
    const downloadEndpoint = `${apiUrl('/api/yt/download')}?${params.toString()}`

    window.open(downloadEndpoint, '_blank', 'noopener')
    setStatus(`Starting ${downloadType} download in ${quality}...`)
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
              >
                Download
              </button>
            </div>
          </div>
        )}

        <p className="download-status" aria-live="polite">
          {status || 'Paste a YouTube link and click search.'}
        </p>
      </form>
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
