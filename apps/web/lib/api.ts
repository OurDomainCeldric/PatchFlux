export interface NewsItem {
  id: string;
  title: string;
  publishedAt: string;
  sourceId: string;
  sourceName: string;
  author: string | null;
  url: string;
  products: string[];
  tags: string[];
  language: "de" | "en";
}

export interface NewsResponse {
  items: NewsItem[];
  count: number;
}

export interface SourceHealth {
  sourceId: string;
  lastFetchAt: string | null;
  lastStatus: string | null;
  lastError: string | null;
}

export interface SourcesResponse {
  sources: SourceHealth[];
}

/**
 * Base URL of the Azure Functions HTTP API. In production on Azure Static Web
 * Apps the linked Functions are exposed under `/api/*` by default.
 *
 * Override via `NEXT_PUBLIC_API_BASE_URL` for local development (e.g.
 * `http://localhost:7071/api`).
 */
const API_BASE = (process.env.NEXT_PUBLIC_API_BASE_URL ?? "/api").replace(/\/$/, "");

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      Accept: "application/json",
      ...init?.headers,
    },
  });
  if (!response.ok) {
    throw new Error(`Request to ${path} failed with ${response.status}`);
  }
  return (await response.json()) as T;
}

export function fetchNews(params: {
  source?: string;
  product?: string;
  limit?: number;
} = {}): Promise<NewsResponse> {
  const search = new URLSearchParams();
  if (params.source) search.set("source", params.source);
  if (params.product) search.set("product", params.product);
  if (params.limit) search.set("limit", String(params.limit));
  const qs = search.toString();
  return request<NewsResponse>(`/news${qs ? `?${qs}` : ""}`);
}

export function fetchSources(): Promise<SourcesResponse> {
  return request<SourcesResponse>("/sources");
}
