export interface NewsItem {
  id: string;
  title: string;
  publishedAt: string;
  sourceId: string;
  sourceName: string;
  sourceTier: 1 | 2 | 3;
  author: string | null;
  url: string;
  products: string[];
  tags: string[];
  language: "de" | "en";
  priority: 0 | 1 | 2;
  topics: string[];
}

export interface NewsResponse {
  items: NewsItem[];
  count: number;
  nextCursor: string | null;
}

export interface HotResponse {
  items: NewsItem[];
  count: number;
}

export interface SourceHealth {
  sourceId: string;
  sourceName?: string;
  state:
    | "ok"
    | "not_modified"
    | "error"
    | "stale"
    | "timer_not_firing"
    | "disabled"
    | "never";
  lastAttemptAt: string | null;
  lastFetchAt: string | null;
  lastSuccessAt: string | null;
  lastStatus: string | null;
  lastError: string | null;
  itemsLastRun?: number;
}

export interface SourcesResponse {
  sources: SourceHealth[];
}

export interface ProductCount {
  id: string;
  count: number;
}

export interface ProductsResponse {
  products: ProductCount[];
}

export interface TopicCount {
  id: string;
  count: number;
}

export interface TopicsResponse {
  topics: TopicCount[];
  windowDays: number;
}

export interface HealthResponse {
  status: "ok" | "degraded";
  storage: boolean;
  sourcesStale: string[];
  sourceCounts: {
    disabled: number;
    error: number;
    never: number;
    notModified: number;
    ok: number;
    stale: number;
    timerNotFiring: number;
  };
  sourcesByState: {
    disabled: string[];
    error: string[];
    never: string[];
    notModified: string[];
    ok: string[];
    stale: string[];
    timerNotFiring: string[];
  };
  checkedAt: string;
}

export interface IngestResponse {
  written: Record<string, number>;
}

export interface VisitCountsResponse {
  today: number;
  allTime: number;
  dayKey: string;
  timezone: string;
}

export interface NewsFilters {
  source?: string;
  product?: string;
  lang?: "de" | "en";
  since?: string;
  q?: string;
  limit?: number;
  cursor?: string;
  deduped?: boolean;
  minPriority?: 1 | 2;
  hot?: boolean;
  topics?: string[];
  excludeTopics?: string[];
  /** true = Community tab (tier 3 only); false = News & Blogs (tier 1+2 only) */
  community?: boolean;
}

const API_BASE = (process.env.NEXT_PUBLIC_API_BASE_URL ?? "/api").replace(/\/$/, "");

function joinUrl(path: string, search: URLSearchParams): string {
  const qs = search.toString();
  return `${API_BASE}${path}${qs ? `?${qs}` : ""}`;
}

async function request<T>(
  path: string,
  search: URLSearchParams,
  init?: RequestInit,
): Promise<T> {
  const response = await fetch(joinUrl(path, search), {
    ...init,
    headers: { Accept: "application/json", ...init?.headers },
  });
  if (!response.ok) {
    throw new Error(`Request to ${path} failed with ${response.status}`);
  }
  return (await response.json()) as T;
}

function buildNewsQuery(params: NewsFilters): URLSearchParams {
  const search = new URLSearchParams();
  if (params.source) search.set("source", params.source);
  if (params.product) search.set("product", params.product);
  if (params.lang) search.set("lang", params.lang);
  if (params.since) search.set("since", params.since);
  if (params.q) search.set("q", params.q);
  if (params.limit) search.set("limit", String(params.limit));
  if (params.cursor) search.set("cursor", params.cursor);
  if (params.deduped) search.set("deduped", "1");
  if (params.minPriority) search.set("min_priority", String(params.minPriority));
  if (params.hot) search.set("hot", "1");
  if (params.topics && params.topics.length > 0)
    search.set("topics", params.topics.join(","));
  if (params.excludeTopics && params.excludeTopics.length > 0)
    search.set("exclude_topics", params.excludeTopics.join(","));
  if (params.community !== undefined)
    search.set("community", params.community ? "1" : "0");
  return search;
}

export function fetchNews(params: NewsFilters = {}): Promise<NewsResponse> {
  return request<NewsResponse>("/news", buildNewsQuery(params));
}

export function fetchHot(
  params: { limit?: number; days?: number; lang?: "de" | "en" } = {},
): Promise<HotResponse> {
  const search = new URLSearchParams();
  if (params.limit) search.set("limit", String(params.limit));
  if (params.days) search.set("days", String(params.days));
  if (params.lang) search.set("lang", params.lang);
  return request<HotResponse>("/hot", search);
}

export function fetchSources(includeCounts = false): Promise<SourcesResponse> {
  const search = new URLSearchParams();
  if (includeCounts) search.set("include_counts", "1");
  return request<SourcesResponse>("/sources", search);
}

export function fetchProducts(months = 3): Promise<ProductsResponse> {
  const search = new URLSearchParams({ months: String(months) });
  return request<ProductsResponse>("/products", search);
}

export function fetchTopics(days = 14): Promise<TopicsResponse> {
  const search = new URLSearchParams({ days: String(days) });
  return request<TopicsResponse>("/topics", search);
}

export function fetchHealth(): Promise<HealthResponse> {
  return request<HealthResponse>("/health", new URLSearchParams());
}

export async function triggerIngest(
  adminKey: string,
  sourceId?: string,
): Promise<IngestResponse> {
  const search = new URLSearchParams({ code: adminKey });
  if (sourceId) search.set("source", sourceId);
  const response = await fetch(joinUrl("/ingest", search), {
    method: "POST",
    headers: { Accept: "application/json" },
  });
  if (!response.ok) {
    throw new Error(`Ingest trigger failed with ${response.status}`);
  }
  return (await response.json()) as IngestResponse;
}

export function fetchVisitCounts(): Promise<VisitCountsResponse> {
  return request<VisitCountsResponse>("/visits", new URLSearchParams());
}

export async function trackVisit(): Promise<VisitCountsResponse> {
  const response = await fetch(joinUrl("/visits/track", new URLSearchParams()), {
    method: "POST",
    headers: { Accept: "application/json" },
  });
  if (!response.ok) {
    throw new Error(`Visit tracking failed with ${response.status}`);
  }
  return (await response.json()) as VisitCountsResponse;
}
