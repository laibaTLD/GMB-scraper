import { ExternalLink } from 'lucide-react';

const RESULT_FIELDS = [
  { key: 'name', label: 'Name', minWidth: 160 },
  { key: 'phone', label: 'Phone', minWidth: 120 },
  { key: 'email', label: 'Email', minWidth: 160 },
  { key: 'facebook', label: 'Facebook', minWidth: 140 },
  { key: 'instagram', label: 'Instagram', minWidth: 140 },
  { key: 'twitter', label: 'Twitter', minWidth: 140 },
  { key: 'linkedin', label: 'LinkedIn', minWidth: 140 },
  { key: 'youtube', label: 'YouTube', minWidth: 140 },
  { key: 'tiktok', label: 'TikTok', minWidth: 140 },
  { key: 'website', label: 'Website', minWidth: 160 },
  { key: 'address', label: 'Address', minWidth: 200 },
  { key: 'rating', label: 'Rating', minWidth: 80 },
  { key: 'reviews', label: 'Reviews', minWidth: 80 },
  { key: 'category', label: 'Category', minWidth: 120 },
  { key: 'hours', label: 'Hours', minWidth: 180 },
  { key: 'files_url', label: 'Map URL', minWidth: 160 },
];

const URL_FIELDS = new Set([
  'website', 'facebook', 'instagram', 'twitter', 'linkedin', 'youtube', 'tiktok', 'files_url',
]);

const hasValue = (v) => v && v !== 'N/A';

function shortenUrl(url) {
  try {
    const { hostname, pathname } = new URL(url);
    const path = pathname.length > 20 ? `${pathname.slice(0, 20)}…` : pathname;
    return `${hostname}${path === '/' ? '' : path}`;
  } catch {
    return url.length > 36 ? `${url.slice(0, 36)}…` : url;
  }
}

function CellValue({ field, value }) {
  if (!hasValue(value)) {
    return <span className="text-[var(--text-subtle)]">—</span>;
  }

  if (URL_FIELDS.has(field)) {
    return (
      <a
        href={value}
        target="_blank"
        rel="noopener noreferrer"
        className="preview-link"
        title={value}
      >
        <span className="truncate">{shortenUrl(value)}</span>
        <ExternalLink className="w-3 h-3 shrink-0 opacity-60" />
      </a>
    );
  }

  if (field === 'rating') {
    return <span className="text-[var(--primary)] whitespace-nowrap">★ {value}</span>;
  }

  if (field === 'phone') {
    return <span className="font-mono text-[11px] whitespace-nowrap">{value}</span>;
  }

  return (
    <span className="block truncate max-w-[220px]" title={value}>
      {value}
    </span>
  );
}

export default function ResultsPreview({ data }) {
  if (!data.length) {
    return (
      <div className="h-full flex flex-col items-center justify-center gap-2 text-[var(--text-muted)]">
        <p className="text-[12px]">No results to preview.</p>
      </div>
    );
  }

  return (
    <div className="h-full min-h-0 overflow-auto">
      <table className="preview-table w-full">
        <thead className="sticky top-0 z-10">
          <tr>
            <th className="preview-table-index">#</th>
            {RESULT_FIELDS.map(({ key, label, minWidth }) => (
              <th key={key} style={{ minWidth }}>{label}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.map((row, idx) => (
            <tr key={idx}>
              <td className="preview-table-index text-[var(--text-muted)] tabular-nums">
                {idx + 1}
              </td>
              {RESULT_FIELDS.map(({ key }) => (
                <td key={key}>
                  <CellValue field={key} value={row[key]} />
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
