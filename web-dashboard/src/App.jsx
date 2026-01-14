import { useState, useEffect, useRef } from 'react';
import {
  Search,
  MapPin,
  Download,
  Play,
  Loader2,
  Database,
  Globe,
  CheckCircle2,
  AlertCircle
} from 'lucide-react';

// API Base URL (adjust if running elsewhere, currently localhost:5001)
const API_URL = 'http://localhost:5001';

function App() {
  const [query, setQuery] = useState('');
  const [location, setLocation] = useState('');
  const [limit, setLimit] = useState(1000);
  const [isScraping, setIsScraping] = useState(false);
  const [status, setStatus] = useState('idle'); // idle, scraping, completed, error
  const [message, setMessage] = useState('');
  const [results, setResults] = useState([]);
  const [progress, setProgress] = useState({ total: 0, current: 0, status: '' });
  const [error, setError] = useState(null);
  const pollingRef = useRef(null);

  // Poll for progress when scraping
  useEffect(() => {
    if (isScraping) {
      pollingRef.current = setInterval(itemsFetcher, 2000);
    } else {
      if (pollingRef.current) clearInterval(pollingRef.current);
    }
    return () => {
      if (pollingRef.current) clearInterval(pollingRef.current);
    };
  }, [isScraping]);

  const itemsFetcher = async () => {
    try {
      // Fetch Progress
      const progressRes = await fetch(`${API_URL}/progress`);
      if (!progressRes.ok) throw new Error(`Progress API Error: ${progressRes.status}`);
      const progressData = await progressRes.json();
      setProgress(progressData);

      // Fetch Results Preview
      const resultsRes = await fetch(`${API_URL}/results?limit=10`);
      if (!resultsRes.ok) throw new Error(`Results API Error: ${resultsRes.status}`);
      const resultsData = await resultsRes.json();
      if (Array.isArray(resultsData)) {
        setResults(resultsData);
      }

      // Check if done (simple logic, backend should probably have a status flag in progress)
      // For now we assume if backend says "Done" or equivalent, or we can't really know 100% without a dedicated status endpoint vs just progress dict
      // Let's rely on the logs in progress or just keep polling. 
      // Actually, if the user stops it or it finishes, we need to know. 
      // For this v1, we'll keep polling until manual stop or error.

    } catch (err) {
      // Silent console log for polling errors to avoid spamming user UI
      console.warn("Polling error:", err.message);
    }
  };

  const startScraping = async () => {
    if (!query || !location) {
      setError("Please provide both a search term and a location.");
      return;
    }

    setError(null);
    setIsScraping(true);
    setStatus('scraping');
    setResults([]);

    try {
      const response = await fetch(`${API_URL}/start-scraping`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query, location, limit }),
      });

      const contentType = response.headers.get("content-type");
      if (contentType && contentType.indexOf("application/json") === -1) {
        const text = await response.text();
        throw new Error(`Server returned non-JSON response: ${text.slice(0, 100)}...`);
      }

      const data = await response.json();

      if (response.ok) {
        setMessage(data.message);
      } else {
        throw new Error(data.error || "Failed to start scraping");
      }
    } catch (err) {
      setError(err.message);
      setIsScraping(false);
      setStatus('error');
    }
  };

  const stopScraping = async () => {
    try {
      const response = await fetch(`${API_URL}/stop-scraping`, {
        method: 'POST',
      });
      if (response.ok) {
        setStatus('idle');
        setIsScraping(false);
        setMessage('Scraping stopped by user.');
      }
    } catch (err) {
      console.error("Stop error", err);
    }
  };

  const handleDownload = () => {
    window.open(`${API_URL}/download`, '_blank');
  };

  return (
    <div className="min-h-screen p-4 md:p-8 flex flex-col items-center" style={{ backgroundColor: 'var(--bg-dark)' }}>

      {/* Header */}
      <header className="w-full max-w-6xl mb-12 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-3 rounded-xl border" style={{ backgroundColor: 'var(--primary)20', borderColor: 'var(--primary)50' }}>
            <Globe className="w-8 h-8" style={{ color: 'var(--primary)' }} />
          </div>
          <div>
            <h1 className="text-2xl font-bold" style={{ color: 'var(--text-light)' }}>
              GMB Scraper
            </h1>
            <p className="text-sm" style={{ color: 'var(--text-medium)' }}>Business Data Intelligence</p>
          </div>
        </div>

        <div className="hidden md:flex items-center gap-4">
          <div className={`flex items-center gap-2 px-4 py-2 rounded-full border ${status === 'scraping' ? '' :
            status === 'completed' ? '' :
              ''
            }`} style={{
              backgroundColor: status === 'scraping' ? 'var(--primary)20' : status === 'completed' ? 'var(--primary)20' : 'var(--card-dark)',
              borderColor: status === 'scraping' ? 'var(--primary)50' : status === 'completed' ? 'var(--primary)50' : 'var(--text-medium)30'
            }}>
            <div className={`w-2 h-2 rounded-full ${status === 'scraping' ? 'animate-pulse' : ''}`} style={{
              backgroundColor: status === 'scraping' ? 'var(--primary)' : status === 'completed' ? 'var(--primary)' : 'var(--text-medium)'
            }} />
            <span className="text-sm font-medium capitalize" style={{ color: status === 'scraping' ? 'var(--primary)' : status === 'completed' ? 'var(--primary)' : 'var(--text-medium)' }}>{status === 'idle' ? 'Ready' : status}</span>
          </div>
        </div>
      </header>

      <main className="w-full max-w-6xl grid grid-cols-1 lg:grid-cols-3 gap-8" style={{ color: 'var(--text-light)' }}>

        {/* Left Col: Controls */}
        <div className="lg:col-span-1 space-y-6">
          <div className="glass-card p-6 space-y-6">
            <h2 className="text-xl font-semibold flex items-center gap-2" style={{ color: 'var(--text-light)' }}>
              <Search className="w-5 h-5" style={{ color: 'var(--primary)' }} />
              Target Parameters
            </h2>

            <div className="space-y-4">
              <div className="space-y-2">
                <label className="text-sm font-medium ml-1" style={{ color: 'var(--text-medium)' }}>Business Query</label>
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4" style={{ color: 'var(--text-medium)' }} />
                  <input
                    type="text"
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    placeholder="e.g. Plumbers, Restaurants..."
                    className="glass-input w-full pl-10"
                  />
                </div>
              </div>

              <div className="space-y-2">
                <label className="text-sm font-medium ml-1" style={{ color: 'var(--text-medium)' }}>Location</label>
                <div className="relative">
                  <MapPin className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4" style={{ color: 'var(--text-medium)' }} />
                  <input
                    type="text"
                    value={location}
                    onChange={(e) => setLocation(e.target.value)}
                    placeholder="e.g. New York, London..."
                    className="glass-input w-full pl-10"
                  />
                </div>
              </div>

              <div className="space-y-2">
                <label className="text-sm font-medium ml-1" style={{ color: 'var(--text-medium)' }}>Max Leads (20-1000)</label>
                <div className="relative">
                  <span className="absolute left-3 top-1/2 -translate-y-1/2 font-mono text-xs" style={{ color: 'var(--text-medium)' }}>#</span>
                  <input
                    type="number"
                    min="20"
                    max="1000"
                    value={limit}
                    onChange={(e) => setLimit(Number(e.target.value))}
                    className="glass-input w-full pl-10"
                  />
                </div>
              </div>
            </div>

            {error && (
              <div className="p-4 rounded-xl text-sm flex items-start gap-2" style={{ backgroundColor: 'var(--primary)20', border: '1px solid var(--primary)30', color: 'var(--primary)' }}>
                <AlertCircle className="w-5 h-5 shrink-0" />
                <p>{error}</p>
              </div>
            )}

            <button
              onClick={status === 'scraping' ? stopScraping : startScraping}
              disabled={isScraping && status !== 'scraping'}
              className={`w-full btn-primary ${status === 'scraping'
                ? ''
                : isScraping
                  ? 'opacity-80'
                  : ''
                }`}
              style={{
                background: status === 'scraping' ? 'var(--primary)' : 'linear-gradient(135deg, var(--primary), var(--accent))',
                boxShadow: status === 'scraping' ? '0 10px 40px -10px var(--primary)40' : '0 10px 40px -10px var(--primary)40'
              }}
            >
              {status === 'scraping' ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin" />
                  Stop Scraping
                </>
              ) : isScraping ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin" />
                  Starting...
                </>
              ) : (
                <>
                  <Play className="w-5 h-5 fill-current" />
                  Start Scraping
                </>
              )}
            </button>
          </div>

          {/* Download Card */}
          <div className="glass-card p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-semibold" style={{ color: 'var(--text-light)' }}>Export Data</h3>
              <Database className="w-5 h-5" style={{ color: 'var(--accent)' }} />
            </div>
            <p className="text-sm mb-6" style={{ color: 'var(--text-medium)' }}>
              Download the scraped data in Excel format with organized columns and formatting.
            </p>
            <button
              onClick={handleDownload}
              className="w-full btn-secondary group"
            >
              <Download className="w-5 h-5 group-hover:text-blue-400 transition-colors" style={{ color: 'var(--text-light)' }} />
              Download Excel
            </button>
          </div>
        </div>

        {/* Right Col: Live Results */}
        <div className="lg:col-span-2 space-y-6">
          {/* Progress Bar (Visible when scraping or having data) */}
          {
            (isScraping || results.length > 0) && (
              <div className="glass-card p-6 border-l-4" style={{ borderLeftColor: 'var(--primary)' }}>
                <div className="flex justify-between items-end mb-2">
                  <div>
                    <span className="text-xs font-bold uppercase tracking-wider" style={{ color: 'var(--primary)' }}>Status Console</span>
                    <p className="mt-1" style={{ color: 'var(--text-light)' }}>
                      {progress.status || (isScraping ? "Initializing scraper engine..." : "Ready")}
                    </p>
                  </div>
                  <div className="text-right">
                    <div className="text-2xl font-bold font-mono" style={{ color: 'var(--text-light)' }}>
                      {results.length}
                    </div>
                    <div className="text-xs" style={{ color: 'var(--text-medium)' }}>records found</div>
                  </div>
                </div>
              </div>
            )
          }

          {/* Results Table */}
          <div className="glass-card overflow-hidden flex flex-col h-[600px]">
            <div className="p-4 border-b flex justify-between items-center" style={{ backgroundColor: 'var(--card-dark)80', borderColor: 'var(--text-medium)20' }}>
              <h3 className="font-semibold flex items-center gap-2" style={{ color: 'var(--text-light)' }}>
                <CheckCircle2 className="w-4 h-4" style={{ color: 'var(--primary)' }} />
                Live Results
              </h3>
              <span className="text-xs px-2 py-1 rounded" style={{ color: 'var(--text-medium)', backgroundColor: 'var(--card-dark)' }}>
                Showing latest 50
              </span>
            </div>

            <div className="flex-1 overflow-auto">
              {results.length === 0 ? (
                <div className="h-full flex flex-col items-center justify-center p-8 text-center space-y-4" style={{ color: 'var(--text-medium)' }}>
                  <div className="w-16 h-16 rounded-full flex items-center justify-center" style={{ backgroundColor: 'var(--card-dark)50' }}>
                    <Search className="w-8 h-8" style={{ opacity: 0.2 }} />
                  </div>
                  <p>No results yet. Start a search to see data flow in.</p>
                </div>
              ) : (
                <table className="w-full text-left border-collapse">
                  <thead className="sticky top-0 backdrop-blur-md z-10" style={{ backgroundColor: 'var(--card-dark)80' }}>
                    <tr>
                      <th className="p-4 text-xs font-medium uppercase tracking-wider" style={{ color: 'var(--text-medium)' }}>Business Name</th>
                      <th className="p-4 text-xs font-medium uppercase tracking-wider" style={{ color: 'var(--text-medium)' }}>Rating</th>
                      <th className="p-4 text-xs font-medium uppercase tracking-wider" style={{ color: 'var(--text-medium)' }}>Phone</th>
                      <th className="p-4 text-xs font-medium uppercase tracking-wider" style={{ color: 'var(--text-medium)' }}>Address</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y" style={{ borderColor: 'var(--text-medium)20' }}>
                    {results.map((row, idx) => (
                      <tr key={idx} className="hover:bg-slate-700/20 transition-colors" style={{ color: 'var(--text-light)' }}>
                        <td className="p-4 font-medium" style={{ color: 'var(--text-light)' }}>{row.name || 'N/A'}</td>
                        <td className="p-4">
                          {row.rating ? (
                            <span className="flex items-center gap-1 text-sm" style={{ color: 'var(--primary)' }}>
                              ★ <span style={{ color: 'var(--text-light)' }}>{row.rating}</span>
                              <span className="text-xs" style={{ color: 'var(--text-medium)' }}>({row.reviews})</span>
                            </span>
                          ) : (
                            <span style={{ color: 'var(--text-medium)' }}>-</span>
                          )}
                        </td>
                        <td className="p-4 font-mono text-sm" style={{ color: 'var(--text-medium)' }}>{row.phone || '-'}</td>
                        <td className="p-4 text-sm truncate max-w-[200px]" style={{ color: 'var(--text-medium)' }} title={row.address}>
                          {row.address || '-'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}

export default App;
