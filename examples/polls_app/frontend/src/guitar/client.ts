/**
 * Django Guitar API Client
 */

const BASE_URL = '/guitar'

interface RequestOptions {
  method?: string
  body?: unknown
  headers?: Record<string, string>
}

export const guitarFetch = async <T>(
  endpoint: string,
  options: RequestOptions = {}
): Promise<T> => {
  const { method = 'GET', body, headers = {} } = options

  const fetchOptions: RequestInit = {
    method,
    headers: {
      'Content-Type': 'application/json',
      ...headers,
    },
    credentials: 'include',
  }

  if (body) {
    fetchOptions.body = JSON.stringify(body)
  }

  const response = await fetch(`${BASE_URL}${endpoint}`, fetchOptions)

  if (!response.ok) {
    const errorText = await response.text()
    throw new Error(`HTTP ${response.status}: ${errorText}`)
  }

  // Handle empty responses
  const text = await response.text()
  if (!text) {
    return {} as T
  }

  return JSON.parse(text) as T
}

export class QuerySet<T, CreateT, UpdateT> {
  private endpoint: string
  private filters: Record<string, unknown> = {}
  private orderByFields: string[] = []
  private limitValue: number | null = null
  private offsetValue: number | null = null

  constructor(endpoint: string) {
    this.endpoint = endpoint
  }

  private clone(): QuerySet<T, CreateT, UpdateT> {
    const qs = new QuerySet<T, CreateT, UpdateT>(this.endpoint)
    qs.filters = { ...this.filters }
    qs.orderByFields = [...this.orderByFields]
    qs.limitValue = this.limitValue
    qs.offsetValue = this.offsetValue
    return qs
  }

  filter(conditions: Record<string, unknown>): QuerySet<T, CreateT, UpdateT> {
    const qs = this.clone()
    qs.filters = { ...qs.filters, ...conditions }
    return qs
  }

  order_by(...fields: string[]): QuerySet<T, CreateT, UpdateT> {
    const qs = this.clone()
    qs.orderByFields = fields
    return qs
  }

  limit(n: number): QuerySet<T, CreateT, UpdateT> {
    const qs = this.clone()
    qs.limitValue = n
    return qs
  }

  offset(n: number): QuerySet<T, CreateT, UpdateT> {
    const qs = this.clone()
    qs.offsetValue = n
    return qs
  }

  private buildQueryString(): string {
    const params = new URLSearchParams()

    for (const [key, value] of Object.entries(this.filters)) {
      if (value !== undefined && value !== null) {
        params.append(key, String(value))
      }
    }

    if (this.orderByFields.length > 0) {
      params.append('order_by', this.orderByFields.join(','))
    }

    if (this.limitValue !== null) {
      params.append('limit', String(this.limitValue))
    }

    if (this.offsetValue !== null) {
      params.append('offset', String(this.offsetValue))
    }

    const queryString = params.toString()
    return queryString ? `?${queryString}` : ''
  }

  async all(): Promise<T[]> {
    const response = await guitarFetch<{ results: T[] } | T[]>(
      `${this.endpoint}/${this.buildQueryString()}`
    )
    return Array.isArray(response) ? response : response.results
  }

  async get(conditions: Record<string, unknown>): Promise<T> {
    const id = conditions.id
    if (!id) {
      throw new Error('get() requires an id')
    }
    return guitarFetch<T>(`${this.endpoint}/${id}/`)
  }

  async first(): Promise<T | null> {
    const results = await this.limit(1).all()
    return results[0] || null
  }

  async create(data: CreateT): Promise<T> {
    return guitarFetch<T>(`${this.endpoint}/`, {
      method: 'POST',
      body: data,
    })
  }

  async update(conditions: Record<string, unknown>, data: UpdateT): Promise<T> {
    const id = conditions.id
    if (!id) {
      throw new Error('update() requires an id')
    }
    return guitarFetch<T>(`${this.endpoint}/${id}/`, {
      method: 'PATCH',
      body: data,
    })
  }

  async delete(conditions: Record<string, unknown>): Promise<void> {
    const id = conditions.id
    if (!id) {
      throw new Error('delete() requires an id')
    }
    await guitarFetch<void>(`${this.endpoint}/${id}/`, {
      method: 'DELETE',
    })
  }
}

