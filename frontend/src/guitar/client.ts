/**
 * Django Guitar TypeScript Client
 * Auto-generated - do not edit manually
 */

export interface GuitarConfig {
  baseUrl: string;
  credentials?: RequestCredentials;
  headers?: Record<string, string>;
  fetch?: typeof fetch;
}

let config: GuitarConfig = {
  baseUrl: '/guitar/',
  credentials: 'include',
};

export const configure = (newConfig: Partial<GuitarConfig>): void => {
  config = { ...config, ...newConfig };
};

export const getConfig = (): GuitarConfig => config;

export class GuitarError extends Error {
  constructor(
    public status: number,
    public detail: string,
    public fields?: Record<string, string[]>,
  ) {
    super(detail);
    this.name = 'GuitarError';
  }
}

export class NotFoundError extends GuitarError {
  constructor(detail: string = 'Not found') {
    super(404, detail);
    this.name = 'NotFoundError';
  }
}

export class PermissionDeniedError extends GuitarError {
  constructor(detail: string = 'Permission denied') {
    super(403, detail);
    this.name = 'PermissionDeniedError';
  }
}

export class ValidationError extends GuitarError {
  constructor(detail: string, fields?: Record<string, string[]>) {
    super(400, detail, fields);
    this.name = 'ValidationError';
  }
}

const handleResponse = async <T>(response: Response): Promise<T> => {
  if (!response.ok) {
    let detail = 'An error occurred';
    let fields: Record<string, string[]> | undefined;
    
    try {
      const data = await response.json();
      detail = data.detail || JSON.stringify(data);
      if (typeof data === 'object' && !data.detail) {
        fields = data;
      }
    } catch {
      detail = response.statusText;
    }
    
    if (response.status === 404) {
      throw new NotFoundError(detail);
    } else if (response.status === 403) {
      throw new PermissionDeniedError(detail);
    } else if (response.status === 400) {
      throw new ValidationError(detail, fields);
    }
    
    throw new GuitarError(response.status, detail, fields);
  }
  
  if (response.status === 204) {
    return undefined as T;
  }
  
  return response.json();
};

export const guitarFetch = async <T>(
  endpoint: string,
  options: RequestInit = {},
): Promise<T> => {
  const url = `${config.baseUrl.replace(/\/$/, '')}${endpoint}`;
  
  const fetchFn = config.fetch || fetch;
  
  const response = await fetchFn(url, {
    ...options,
    credentials: config.credentials,
    headers: {
      'Content-Type': 'application/json',
      ...config.headers,
      ...options.headers,
    },
  });
  
  return handleResponse<T>(response);
};

export interface QueryParams {
  [key: string]: string | number | boolean | null | undefined | (string | number)[];
}

export const buildQueryString = (params: QueryParams): string => {
  const searchParams = new URLSearchParams();
  
  for (const [key, value] of Object.entries(params)) {
    if (value === null || value === undefined) {
      continue;
    }
    
    if (Array.isArray(value)) {
      searchParams.set(key, value.join(','));
    } else {
      searchParams.set(key, String(value));
    }
  }
  
  const queryString = searchParams.toString();
  return queryString ? `?${queryString}` : '';
};

export interface PaginatedResponse<T> {
  results: T[];
  count: number;
  next_cursor?: string;
  has_more: boolean;
}

export type FilterLookup<T> = {
  [K in keyof T]?: T[K];
} & {
  [key: `${string}__${string}`]: unknown;
};

export abstract class GuitarManager<
  TRead,
  TCreate,
  TUpdate,
  TFilter = FilterLookup<TRead>,
> {
  protected abstract endpoint: string;
  
  private _filters: Record<string, unknown> = {};
  private _ordering: string[] = [];
  private _limit?: number;
  private _offset?: number;
  private _only?: string[];
  private _defer?: string[];
  private _expand?: string[];
  
  protected _clone(): this {
    const cloned = Object.create(Object.getPrototypeOf(this));
    cloned.endpoint = this.endpoint;
    cloned._filters = { ...this._filters };
    cloned._ordering = [...this._ordering];
    cloned._limit = this._limit;
    cloned._offset = this._offset;
    cloned._only = this._only ? [...this._only] : undefined;
    cloned._defer = this._defer ? [...this._defer] : undefined;
    cloned._expand = this._expand ? [...this._expand] : undefined;
    return cloned;
  }
  
  filter(lookup: Partial<TFilter>): this {
    const cloned = this._clone();
    cloned._filters = { ...cloned._filters, ...lookup };
    return cloned;
  }
  
  exclude(lookup: Partial<TFilter>): this {
    // For now, just use filter - proper exclude would need backend support
    return this.filter(lookup);
  }
  
  order_by(...fields: string[]): this {
    const cloned = this._clone();
    cloned._ordering = fields;
    return cloned;
  }
  
  limit(count: number): this {
    const cloned = this._clone();
    cloned._limit = count;
    return cloned;
  }
  
  offset(count: number): this {
    const cloned = this._clone();
    cloned._offset = count;
    return cloned;
  }
  
  only(...fields: string[]): this {
    const cloned = this._clone();
    cloned._only = fields;
    return cloned;
  }
  
  defer(...fields: string[]): this {
    const cloned = this._clone();
    cloned._defer = fields;
    return cloned;
  }
  
  select_related(...relations: string[]): this {
    const cloned = this._clone();
    cloned._expand = relations;
    return cloned;
  }
  
  prefetch_related(...relations: string[]): this {
    return this.select_related(...relations);
  }
  
  private _buildQueryParams(): QueryParams {
    const params: QueryParams = { ...this._filters };
    
    if (this._ordering.length > 0) {
      params._order = this._ordering.join(',');
    }
    if (this._limit !== undefined) {
      params._limit = this._limit;
    }
    if (this._offset !== undefined) {
      params._offset = this._offset;
    }
    if (this._only) {
      params._only = this._only.join(',');
    }
    if (this._defer) {
      params._defer = this._defer.join(',');
    }
    if (this._expand) {
      params._expand = this._expand.join(',');
    }
    
    return params;
  }
  
  async all(): Promise<TRead[]> {
    const queryString = buildQueryString(this._buildQueryParams());
    return guitarFetch<TRead[]>(`${this.endpoint}/${queryString}`);
  }
  
  async get(lookup: Partial<TFilter>): Promise<TRead> {
    if ('id' in lookup && typeof lookup.id === 'number') {
      return guitarFetch<TRead>(`${this.endpoint}/${lookup.id}/`);
    }
    
    const results = await this.filter(lookup).limit(2).all();
    
    if (results.length === 0) {
      throw new NotFoundError();
    }
    if (results.length > 1) {
      throw new GuitarError(400, 'get() returned more than one result');
    }
    
    return results[0];
  }
  
  async first(): Promise<TRead | null> {
    const results = await this.limit(1).all();
    return results.length > 0 ? results[0] : null;
  }
  
  async last(): Promise<TRead | null> {
    // Would need backend support for proper implementation
    const results = await this.all();
    return results.length > 0 ? results[results.length - 1] : null;
  }
  
  async count(): Promise<number> {
    const results = await this.all();
    return results.length;
  }
  
  async exists(): Promise<boolean> {
    const results = await this.limit(1).all();
    return results.length > 0;
  }
  
  async create(data: TCreate): Promise<TRead> {
    return guitarFetch<TRead>(`${this.endpoint}/`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }
  
  async update(data: TUpdate): Promise<TRead[]> {
    const items = await this.all();
    const results: TRead[] = [];
    
    for (const item of items) {
      const id = (item as Record<string, unknown>).id;
      const updated = await guitarFetch<TRead>(`${this.endpoint}/${id}/`, {
        method: 'PATCH',
        body: JSON.stringify(data),
      });
      results.push(updated);
    }
    
    return results;
  }
  
  async delete(): Promise<void> {
    const items = await this.all();
    
    for (const item of items) {
      const id = (item as Record<string, unknown>).id;
      await guitarFetch<void>(`${this.endpoint}/${id}/`, {
        method: 'DELETE',
      });
    }
  }
}
