import { useState, useEffect, useRef, useMemo } from 'react';
import {
  Search,
  MapPin,
  Download,
  Play,
  Loader2,
  CheckCircle2,
  AlertCircle,
  Zap,
  Layers,
  Mail,
  Globe,
  Target,
  TrendingUp,
  Square,
} from 'lucide-react';

const API_URL = import.meta.env.VITE_API_URL || (import.meta.env.PROD ? '' : 'http://localhost:5000');
const STORAGE_KEY = 'lead-engine-session';
const XLSX_MIME = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet';

function loadSession() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

function saveSession(data) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
  } catch (err) {
    console.warn('Failed to save session:', err.message);
  }
}

function getDownloadUrl() {
  return API_URL ? `${API_URL}/download` : '/download';
}

function isSameOriginDownload() {
  const url = getDownloadUrl();
  if (url.startsWith('/')) return true;
  try {
    return new URL(url).origin === window.location.origin;
  } catch {
    return false;
  }
}

const initialSession = loadSession();

const STATUS_CHIPS = [
  { key: 'idle', label: 'Ready' },
  { key: 'scraping', label: 'Scraping' },
  { key: 'completed', label: 'Completed' },
  { key: 'error', label: 'Error' },
];

const hasValue = (v) => v && v !== 'N/A';

function App() {
  const [query, setQuery] = useState(initialSession?.query ?? '');
  const [location, setLocation] = useState(initialSession?.location ?? '');
  const [limit, setLimit] = useState(initialSession?.limit ?? 50);
  const [scrapingMode, setScrapingMode] = useState(initialSession?.scrapingMode ?? 'detailed');
  const [isScraping, setIsScraping] = useState(false);
  const [status, setStatus] = useState(initialSession?.status ?? 'idle');
  const [results, setResults] = useState((initialSession?.allResults ?? []).slice(0, 50));
  const [allResults, setAllResults] = useState(initialSession?.allResults ?? []);
  const [progress, setProgress] = useState(
    initialSession?.progress ?? { count: 0, target: 0, status: '', is_active: false, download_ready: false }
  );
  const [error, setError] = useState(null);
  const pollingRef = useRef(null);

  useEffect(() => {
    saveSession({ query, location, limit, scrapingMode, status, allResults, progress });
  }, [query, location, limit, scrapingMode, status, allResults, progress]);

  useEffect(() => {
    (async () => {
      try {
        const progressRes = await fetch(`${API_URL}/progress`);
        if (!progressRes.ok) return;
        const progressData = await progressRes.json();
        setProgress(progressData);

        if (progressData.is_active) {
          setIsScraping(true);
          setStatus('scraping');
        } else if (progressData.download_ready) {
          setStatus('completed');
        }

        const resultsRes = await fetch(`${API_URL}/results?limit=1000`);
        if (!resultsRes.ok) return;
        const resultsData = await resultsRes.json();
        if (Array.isArray(resultsData) && resultsData.length > 0) {
          setAllResults(resultsData);
          setResults(resultsData.slice(0, 50));
        }
      } catch (err) {
        console.warn('Backend sync failed:', err.message);
      }
    })();
  }, []);

  const isActive = status === 'scraping';
  const progressPercent = progress.target > 0
    ? Math.min(100, Math.round((progress.count / progress.target) * 100))
    : 0;

  const stats = useMemo(() => {
    const emails = allResults.filter((r) => hasValue(r.email)).length;
    const websites = allResults.filter((r) => hasValue(r.website)).length;
    const records = progress.count ?? 0;
    const successRate = progress.target > 0
      ? Math.round((records / progress.target) * 100)
      : 0;
    return { records, emails, websites, successRate };
  }, [allResults, progress.count, progress.target]);

  useEffect(() => {
    if (isScraping) {
      pollingRef.current = setInterval(itemsFetcher, 2000);
    } else if (pollingRef.current) {
      clearInterval(pollingRef.current);
    }
    return () => {
      if (pollingRef.current) clearInterval(pollingRef.current);
    };
  }, [isScraping]);

  const itemsFetcher = async () => {
    try {
      const progressRes = await fetch(`${API_URL}/progress`);
      if (!progressRes.ok) throw new Error(`Progress API Error: ${progressRes.status}`);
      const progressData = await progressRes.json();
      setProgress(progressData);

      const resultsRes = await fetch(`${API_URL}/results?limit=1000`);
      if (!resultsRes.ok) throw new Error(`Results API Error: ${resultsRes.status}`);
      const resultsData = await resultsRes.json();
      if (Array.isArray(resultsData)) {
        setAllResults(resultsData);
        setResults(resultsData.slice(0, 50));
      }

      if (!progressData.is_active) {
        if (progressData.download_ready) {
          setIsScraping(false);
          setStatus('completed');
        } else if (progressData.status?.includes('Error')) {
          setIsScraping(false);
          setStatus('error');
          setError(progressData.status);
        } else if (
          progressData.target > 0 &&
          (progressData.status?.includes('Stopped') ||
            progressData.status?.includes('End of list') ||
            progressData.status?.includes('No new items') ||
            progressData.status?.includes('No results'))
        ) {
          setIsScraping(false);
          setStatus('idle');
        }
      }
    } catch (err) {
      console.warn('Polling error:', err.message);
    }
  };

  const startScraping = async () => {
    if (!query.trim()) {
      setError('Please provide a business query.');
      return;
    }
    if (limit < 1 || limit > 150) {
      setError('Max Leads must be between 1 and 150.');
      return;
    }

    setError(null);
    setIsScraping(true);
    setStatus('scraping');
    setResults([]);
    setAllResults([]);

    try {
      const response = await fetch(`${API_URL}/start-scraping`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: query.trim(),
          location: location.trim(),
          limit,
          scraping_mode: scrapingMode,
        }),
      });

      const contentType = response.headers.get('content-type');
      if (contentType && contentType.indexOf('application/json') === -1) {
        const text = await response.text();
        throw new Error(`Server returned non-JSON response: ${text.slice(0, 100)}...`);
      }

      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.error || 'Failed to start scraping');
      }
    } catch (err) {
      setError(err.message);
      setIsScraping(false);
      setStatus('error');
    }
  };

  const stopScraping = async () => {
    try {
      const response = await fetch(`${API_URL}/stop-scraping`, { method: 'POST' });
      if (response.ok) {
        setStatus('idle');
        setIsScraping(false);
      }
    } catch (err) {
      console.error('Stop error', err);
    }
  };

  const handleDownload = async () => {
    try {
      const downloadUrl = getDownloadUrl();

      if (isSameOriginDownload()) {
        const link = document.createElement('a');
        link.href = downloadUrl;
        link.style.display = 'none';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        return;
      }

      const response = await fetch(downloadUrl);
      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        throw new Error(data.error || 'Download failed');
      }
      const disposition = response.headers.get('content-disposition') || '';
      const match = disposition.match(/filename="?([^";]+)"?/);
      const filename = match?.[1] || 'google_maps_data.xlsx';
      const buffer = await response.arrayBuffer();
      const blob = new Blob([buffer], { type: XLSX_MIME });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = filename;
      link.style.display = 'none';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
    } catch (err) {
      setError(err.message);
    }
  };

  const chipClass = (key) => {
    if (status !== key) return 'status-chip';
    if (key === 'scraping') return 'status-chip status-chip-scraping';
    if (key === 'completed') return 'status-chip status-chip-completed';
    if (key === 'error') return 'status-chip status-chip-error';
    return 'status-chip status-chip-active';
  };

  const statusMessage = progress.status || (isScraping ? 'Initializing…' : 'Ready to scrape');

  return (
    <div className="dashboard">
      {/* Header — 52px */}
      <header className="dashboard-header">
        <img src="/logo.png" alt="Lead Engine" className="h-9 w-auto object-contain" />
        <div className="flex items-center gap-1.5" role="status" aria-live="polite">
          {STATUS_CHIPS.map(({ key, label }) => (
            <span key={key} className={chipClass(key)}>
              {key === 'scraping' && status === 'scraping' && (
                <span className="w-1.5 h-1.5 rounded-full bg-current animate-pulse" />
              )}
              {label}
            </span>
          ))}
        </div>
      </header>

      {/* Main — 30 / 70 grid, fills remaining viewport */}
      <main className="dashboard-main">

        {/* Left — compact control panel */}
        <aside className="flex flex-col gap-3 min-h-0">
          <div className="surface-card card-compact flex-1 min-h-0">
            <h2 className="section-heading">
              <Target className="w-3.5 h-3.5 text-[var(--primary)]" />
              Target Parameters
            </h2>

            <div className="flex flex-col flex-1 justify-evenly gap-4">
            <div className="grid gap-4">
              <div>
                <label htmlFor="query" className="field-label">Business Query</label>
                <div className="input-wrap">
                  <Search className="input-wrap-icon" />
                  <input
                    id="query"
                    type="text"
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    placeholder="Plumbers, Restaurants…"
                    className="input-compact"
                    disabled={isScraping}
                  />
                </div>
              </div>

              <div>
                <label htmlFor="location" className="field-label">Location</label>
                <div className="input-wrap">
                  <MapPin className="input-wrap-icon" />
                  <input
                    id="location"
                    type="text"
                    value={location}
                    onChange={(e) => setLocation(e.target.value)}
                    placeholder="New York, London…"
                    className="input-compact"
                    disabled={isScraping}
                  />
                </div>
              </div>

              <div>
                <label htmlFor="limit" className="field-label">Max Leads</label>
                <div className="input-wrap">
                  <span className="input-wrap-icon text-[10px] font-mono">#</span>
                  <input
                    id="limit"
                    type="number"
                    min="1"
                    max="150"
                    value={limit}
                    onChange={(e) => setLimit(Number(e.target.value))}
                    className="input-compact"
                    disabled={isScraping}
                    aria-describedby="limit-hint"
                  />
                </div>
                <span id="limit-hint" className="sr-only">Between 1 and 150</span>
              </div>
            </div>

            <div>
              <span className="field-label">Scraping Mode</span>
              <div className="segmented-toggle" role="radiogroup" aria-label="Scraping mode">
                <button
                  type="button"
                  role="radio"
                  aria-checked={scrapingMode === 'simple'}
                  disabled={isScraping}
                  onClick={() => setScrapingMode('simple')}
                  className={`segment-btn ${scrapingMode === 'simple' ? 'segment-btn-active' : ''}`}
                >
                  <Zap className="w-3 h-3" />
                  Simple
                </button>
                <button
                  type="button"
                  role="radio"
                  aria-checked={scrapingMode === 'detailed'}
                  disabled={isScraping}
                  onClick={() => setScrapingMode('detailed')}
                  className={`segment-btn ${scrapingMode === 'detailed' ? 'segment-btn-active' : ''}`}
                >
                  <Layers className="w-3 h-3" />
                  Detailed
                </button>
              </div>
            </div>

            {error && (
              <div className="alert-compact" role="alert">
                <AlertCircle className="w-3.5 h-3.5 shrink-0 mt-px" />
                <p>{error}</p>
              </div>
            )}

            <button
              onClick={isActive ? stopScraping : startScraping}
              disabled={isScraping && !isActive}
              className="btn-primary"
            >
              {isActive ? (
                <>
                  <Square className="w-3.5 h-3.5 fill-current" />
                  Stop Scraping
                </>
              ) : isScraping ? (
                <>
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  Starting…
                </>
              ) : (
                <>
                  <Play className="w-3.5 h-3.5 fill-current" />
                  Start Scraping
                </>
              )}
            </button>
            </div>

            <div className="divider" />

            <div className="flex items-center justify-between gap-2">
              <div className="min-w-0">
                <p className="text-[12px] font-medium text-[var(--text)]">Export Data</p>
                <p className="text-[10px] text-[var(--text-muted)] truncate">Excel · on demand</p>
              </div>
              <button
                onClick={handleDownload}
                disabled={!progress.download_ready}
                className="btn-ghost shrink-0"
              >
                <Download className="w-3.5 h-3.5" />
                Download
              </button>
            </div>
          </div>
        </aside>

        {/* Right — status + stats + CRM table */}
        <section className="flex flex-col gap-2.5 min-h-0 min-w-0">

          {/* Slim status banner — 40px */}
          <div className="status-banner">
            <span className="text-[10px] font-semibold uppercase tracking-wider text-[var(--primary)] shrink-0">
              Status
            </span>
            <p className="text-[12px] text-[var(--text)] truncate flex-1 min-w-0" title={statusMessage}>
              {statusMessage}
            </p>
            {progress.target > 0 && (
              <>
                <span className="text-[11px] tabular-nums text-[var(--text-muted)] shrink-0">
                  {progress.count}/{progress.target}
                </span>
                <div className="progress-slim max-w-[120px]">
                  <div className="progress-slim-fill" style={{ width: `${progressPercent}%` }} />
                </div>
              </>
            )}
          </div>

          {/* Live stats row */}
          <div className="grid grid-cols-4 gap-2 shrink-0">
            {[
              { label: 'Records Found', value: stats.records, icon: Target },
              { label: 'Emails Found', value: stats.emails, icon: Mail },
              { label: 'Websites Found', value: stats.websites, icon: Globe },
              { label: 'Success Rate', value: `${stats.successRate}%`, icon: TrendingUp },
            ].map(({ label, value, icon: Icon }) => (
              <div key={label} className="stat-cell">
                <div className="flex items-center gap-1">
                  <Icon className="w-3 h-3 text-[var(--text-muted)]" />
                  <span className="stat-label">{label}</span>
                </div>
                <div className="stat-value">{value}</div>
              </div>
            ))}
          </div>

          {/* CRM results table — fills remaining height */}
          <div className="surface-card flex flex-col flex-1 min-h-0 overflow-hidden">
            <div
              className="flex items-center justify-between px-3 shrink-0"
              style={{ height: 36, borderBottom: '1px solid var(--border)' }}
            >
              <h3 className="section-heading">
                <CheckCircle2 className="w-3.5 h-3.5 text-[var(--primary)]" />
                Live Results
              </h3>
              <span className="text-[10px] px-2 py-0.5 rounded-md text-[var(--text-muted)] bg-[var(--surface-elevated)]">
                Latest 50
              </span>
            </div>

            <div className="flex-1 min-h-0 overflow-auto">
              {results.length === 0 ? (
                <div className="h-full flex flex-col items-center justify-center gap-2 text-[var(--text-muted)]">
                  <Search className="w-6 h-6 opacity-20" />
                  <p className="text-[12px]">No results yet — configure and start scraping.</p>
                </div>
              ) : (
                <table className="crm-table w-full">
                  <thead className="sticky top-0 z-10">
                    <tr>
                      <th>Business</th>
                      <th>Rating</th>
                      <th>Phone</th>
                      <th>Email</th>
                      <th>Address</th>
                    </tr>
                  </thead>
                  <tbody>
                    {results.map((row, idx) => (
                      <tr key={idx}>
                        <td className="font-medium text-[var(--text)] max-w-[160px] truncate" title={row.name}>
                          {row.name || '—'}
                        </td>
                        <td className="whitespace-nowrap text-[var(--text-muted)]">
                          {hasValue(row.rating) ? (
                            <span className="text-[var(--primary)]">★ {row.rating}</span>
                          ) : '—'}
                        </td>
                        <td className="font-mono text-[11px] text-[var(--text-muted)] whitespace-nowrap">
                          {hasValue(row.phone) ? row.phone : '—'}
                        </td>
                        <td className="text-[11px] text-[var(--text-muted)] max-w-[140px] truncate" title={row.email}>
                          {hasValue(row.email) ? row.email : '—'}
                        </td>
                        <td className="text-[var(--text-muted)] max-w-[180px] truncate" title={row.address}>
                          {hasValue(row.address) ? row.address : '—'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}

export default App;
