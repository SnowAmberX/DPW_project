export function parseCsv(text) {
  if (!text || !text.trim()) {
    return [];
  }

  const rows = [];
  let current = "";
  let record = [];
  let inQuotes = false;

  const pushCell = () => {
    record.push(current);
    current = "";
  };

  const pushRecord = () => {
    if (record.length || current.length) {
      pushCell();
      rows.push(record);
      record = [];
    }
  };

  for (let index = 0; index < text.length; index += 1) {
    const char = text[index];
    const next = text[index + 1];

    if (char === '"') {
      if (inQuotes && next === '"') {
        current += '"';
        index += 1;
      } else {
        inQuotes = !inQuotes;
      }
      continue;
    }

    if (char === "," && !inQuotes) {
      pushCell();
      continue;
    }

    if ((char === "\n" || char === "\r") && !inQuotes) {
      if (char === "\r" && next === "\n") {
        index += 1;
      }
      pushRecord();
      continue;
    }

    current += char;
  }

  pushRecord();

  if (!rows.length) {
    return [];
  }

  const [headerRow, ...bodyRows] = rows;
  const headers = headerRow.map((header) => header.trim());

  return bodyRows
    .filter((row) => row.some((cell) => String(cell || "").trim().length))
    .map((row) =>
      headers.reduce((entry, header, headerIndex) => {
        entry[header] = (row[headerIndex] ?? "").trim();
        return entry;
      }, {})
    );
}

export async function loadCsvFromCandidates(candidates, basePath = "/overview") {
  for (const candidate of candidates) {
    const sanitized = candidate.startsWith("/") ? candidate : `${basePath}/${candidate}`;

    try {
      const response = await fetch(sanitized);
      if (!response.ok) {
        continue;
      }

      const text = await response.text();
      return {
        rows: parseCsv(text),
        source: sanitized,
        error: null
      };
    } catch (error) {
      // Try the next candidate instead of failing the whole page.
    }
  }

  return {
    rows: [],
    source: null,
    error: `Missing CSV: ${candidates.join(", ")}`
  };
}

export function pickField(row, candidates, fallback = "") {
  if (!row) {
    return fallback;
  }

  const normalizedMap = Object.keys(row).reduce((map, key) => {
    map[normalizeFieldName(key)] = row[key];
    return map;
  }, {});

  for (const candidate of candidates) {
    if (candidate in row && row[candidate] !== "") {
      return row[candidate];
    }

    const normalized = normalizeFieldName(candidate);
    if (normalized in normalizedMap && normalizedMap[normalized] !== "") {
      return normalizedMap[normalized];
    }
  }

  return fallback;
}

export function toNumber(value, fallback = null) {
  if (value === null || value === undefined || value === "") {
    return fallback;
  }

  const numeric = Number(value);
  return Number.isFinite(numeric) ? numeric : fallback;
}

export function normalizeFieldName(value) {
  return String(value || "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "");
}

export function parseDateValue(value) {
  const timestamp = Date.parse(value);
  return Number.isFinite(timestamp) ? timestamp : null;
}

export function unique(values) {
  return Array.from(new Set(values));
}

export function groupBy(list, getKey) {
  return list.reduce((groups, item) => {
    const key = getKey(item);
    if (!groups[key]) {
      groups[key] = [];
    }
    groups[key].push(item);
    return groups;
  }, {});
}

export function formatDateLabel(value) {
  const timestamp = parseDateValue(value);
  if (timestamp === null) {
    return value || "";
  }

  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric"
  }).format(new Date(timestamp));
}

export function formatMonthLabel(timestamp) {
  if (!Number.isFinite(timestamp)) {
    return "";
  }

  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    year: "2-digit"
  }).format(new Date(timestamp));
}

export function formatPercent(value, digits = 1) {
  if (!Number.isFinite(value)) {
    return "N/A";
  }

  return `${value.toFixed(digits)}%`;
}

export function formatCompactNumber(value, digits = 1) {
  if (!Number.isFinite(value)) {
    return "N/A";
  }

  return new Intl.NumberFormat("en-US", {
    notation: "compact",
    maximumFractionDigits: digits
  }).format(value);
}

export function formatSignedPercent(value, digits = 1) {
  if (!Number.isFinite(value)) {
    return "N/A";
  }

  const prefix = value > 0 ? "+" : "";
  return `${prefix}${value.toFixed(digits)} pts`;
}

export function getLineTicks(min, max, count = 5) {
  if (!Number.isFinite(min) || !Number.isFinite(max)) {
    return [];
  }

  if (min === max) {
    return [min];
  }

  const step = (max - min) / Math.max(count - 1, 1);
  return Array.from({ length: count }, (_, index) => min + step * index);
}

export function clampNumber(value, min, max) {
  return Math.min(Math.max(value, min), max);
}
