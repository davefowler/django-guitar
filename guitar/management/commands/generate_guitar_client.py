"""
Management command to generate TypeScript client from Guitar models.
"""

import os
from typing import Any, Dict, List, Optional, Type
from django.core.management.base import BaseCommand, CommandError
from django.apps import apps
from django.db import models
from django.conf import settings

from guitar.models import GuitarModel


# Django field type to TypeScript type mapping
DJANGO_TO_TS_TYPE: Dict[type, str] = {
    models.AutoField: 'number',
    models.BigAutoField: 'number',
    models.IntegerField: 'number',
    models.BigIntegerField: 'number',
    models.SmallIntegerField: 'number',
    models.PositiveIntegerField: 'number',
    models.PositiveSmallIntegerField: 'number',
    models.FloatField: 'number',
    models.DecimalField: 'number',
    models.CharField: 'string',
    models.TextField: 'string',
    models.EmailField: 'string',
    models.URLField: 'string',
    models.SlugField: 'string',
    models.UUIDField: 'string',
    models.BooleanField: 'boolean',
    models.NullBooleanField: 'boolean | null',
    models.DateField: 'string',
    models.DateTimeField: 'string',
    models.TimeField: 'string',
    models.JSONField: 'Record<string, unknown>',
    models.ForeignKey: 'number',
}


class Command(BaseCommand):
    help = 'Generate TypeScript client from Guitar models'
    
    def add_arguments(self, parser) -> None:
        parser.add_argument(
            '--output',
            '-o',
            type=str,
            default='./frontend/src/guitar/',
            help='Output directory for generated TypeScript files',
        )
        parser.add_argument(
            '--base-url',
            type=str,
            default='/guitar/',
            help='Base URL for API endpoints',
        )
    
    def handle(self, *args: Any, **options: Any) -> None:
        output_dir = options['output']
        base_url = options['base_url']
        
        # Get from settings if available
        guitar_settings = getattr(settings, 'GUITAR', {})
        if not options.get('output'):
            output_dir = guitar_settings.get('TYPESCRIPT_OUTPUT', output_dir)
        if not options.get('base_url'):
            base_url = guitar_settings.get('BASE_URL', base_url)
        
        # Find all Guitar models
        guitar_models = self._find_guitar_models()
        
        if not guitar_models:
            self.stdout.write(self.style.WARNING('No Guitar models found.'))
            return
        
        self.stdout.write(f'Found {len(guitar_models)} Guitar models')
        
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        os.makedirs(os.path.join(output_dir, 'models'), exist_ok=True)
        
        # Generate files
        self._generate_client(output_dir, base_url)
        self._generate_types(output_dir)
        
        for model_class in guitar_models:
            self._generate_model_file(model_class, output_dir, base_url)
        
        self._generate_index(guitar_models, output_dir)
        
        self.stdout.write(
            self.style.SUCCESS(f'Generated TypeScript client in {output_dir}')
        )
    
    def _find_guitar_models(self) -> List[Type[models.Model]]:
        """Find all models that inherit from GuitarModel."""
        guitar_models = []
        
        for app_config in apps.get_app_configs():
            for model in app_config.get_models():
                if issubclass(model, GuitarModel) and model is not GuitarModel:
                    guitar_models.append(model)
        
        return guitar_models
    
    def _get_ts_type(self, field: models.Field) -> str:
        """Get TypeScript type for a Django field."""
        field_type = type(field)
        ts_type = DJANGO_TO_TS_TYPE.get(field_type, 'unknown')
        
        # Handle nullable fields
        is_nullable = getattr(field, 'null', False)
        if is_nullable and '| null' not in ts_type:
            ts_type = f'{ts_type} | null'
        
        return ts_type
    
    def _generate_client(self, output_dir: str, base_url: str) -> None:
        """Generate the base client file."""
        client_code = f'''/**
 * Django Guitar TypeScript Client
 * Auto-generated - do not edit manually
 */

export interface GuitarConfig {{
  baseUrl: string;
  credentials?: RequestCredentials;
  headers?: Record<string, string>;
  fetch?: typeof fetch;
}}

let config: GuitarConfig = {{
  baseUrl: '{base_url}',
  credentials: 'include',
}};

export const configure = (newConfig: Partial<GuitarConfig>): void => {{
  config = {{ ...config, ...newConfig }};
}};

export const getConfig = (): GuitarConfig => config;

export class GuitarError extends Error {{
  constructor(
    public status: number,
    public detail: string,
    public fields?: Record<string, string[]>,
  ) {{
    super(detail);
    this.name = 'GuitarError';
  }}
}}

export class NotFoundError extends GuitarError {{
  constructor(detail: string = 'Not found') {{
    super(404, detail);
    this.name = 'NotFoundError';
  }}
}}

export class PermissionDeniedError extends GuitarError {{
  constructor(detail: string = 'Permission denied') {{
    super(403, detail);
    this.name = 'PermissionDeniedError';
  }}
}}

export class ValidationError extends GuitarError {{
  constructor(detail: string, fields?: Record<string, string[]>) {{
    super(400, detail, fields);
    this.name = 'ValidationError';
  }}
}}

const handleResponse = async <T>(response: Response): Promise<T> => {{
  if (!response.ok) {{
    let detail = 'An error occurred';
    let fields: Record<string, string[]> | undefined;
    
    try {{
      const data = await response.json();
      detail = data.detail || JSON.stringify(data);
      if (typeof data === 'object' && !data.detail) {{
        fields = data;
      }}
    }} catch {{
      detail = response.statusText;
    }}
    
    if (response.status === 404) {{
      throw new NotFoundError(detail);
    }} else if (response.status === 403) {{
      throw new PermissionDeniedError(detail);
    }} else if (response.status === 400) {{
      throw new ValidationError(detail, fields);
    }}
    
    throw new GuitarError(response.status, detail, fields);
  }}
  
  if (response.status === 204) {{
    return undefined as T;
  }}
  
  return response.json();
}};

export const guitarFetch = async <T>(
  endpoint: string,
  options: RequestInit = {{}},
): Promise<T> => {{
  const url = `${{config.baseUrl.replace(/\\/$/, '')}}${{endpoint}}`;
  
  const fetchFn = config.fetch || fetch;
  
  const response = await fetchFn(url, {{
    ...options,
    credentials: config.credentials,
    headers: {{
      'Content-Type': 'application/json',
      ...config.headers,
      ...options.headers,
    }},
  }});
  
  return handleResponse<T>(response);
}};

export interface QueryParams {{
  [key: string]: string | number | boolean | null | undefined | (string | number)[];
}}

export const buildQueryString = (params: QueryParams): string => {{
  const searchParams = new URLSearchParams();
  
  for (const [key, value] of Object.entries(params)) {{
    if (value === null || value === undefined) {{
      continue;
    }}
    
    if (Array.isArray(value)) {{
      searchParams.set(key, value.join(','));
    }} else {{
      searchParams.set(key, String(value));
    }}
  }}
  
  const queryString = searchParams.toString();
  return queryString ? `?${{queryString}}` : '';
}};

export interface PaginatedResponse<T> {{
  results: T[];
  count: number;
  next_cursor?: string;
  has_more: boolean;
}}

export type FilterLookup<T> = {{
  [K in keyof T]?: T[K];
}} & {{
  [key: `${{string}}__${{string}}`]: unknown;
}};

export abstract class GuitarManager<
  TRead,
  TCreate,
  TUpdate,
  TFilter = FilterLookup<TRead>,
> {{
  protected abstract endpoint: string;
  
  private _filters: Record<string, unknown> = {{}};
  private _exclude?: Record<string, unknown>;
  private _ordering: string[] = [];
  private _limit?: number;
  private _offset?: number;
  private _only?: string[];
  private _defer?: string[];
  private _expand?: string[];
  
  protected _clone(): this {{
    const cloned = Object.create(Object.getPrototypeOf(this));
    cloned.endpoint = this.endpoint;
    cloned._filters = {{ ...this._filters }};
    cloned._exclude = this._exclude ? {{ ...this._exclude }} : undefined;
    cloned._ordering = [...this._ordering];
    cloned._limit = this._limit;
    cloned._offset = this._offset;
    cloned._only = this._only ? [...this._only] : undefined;
    cloned._defer = this._defer ? [...this._defer] : undefined;
    cloned._expand = this._expand ? [...this._expand] : undefined;
    return cloned;
  }}
  
  filter(lookup: Partial<TFilter>): this {{
    const cloned = this._clone();
    cloned._filters = {{ ...cloned._filters, ...lookup }};
    return cloned;
  }}
  
  exclude(lookup: Partial<TFilter>): this {{
    const cloned = this._clone();
    // Store exclude filters separately
    if (!cloned._exclude) {{
      cloned._exclude = {{}};
    }}
    cloned._exclude = {{ ...cloned._exclude, ...lookup }};
    return cloned;
  }}
  
  order_by(...fields: string[]): this {{
    const cloned = this._clone();
    cloned._ordering = fields;
    return cloned;
  }}
  
  limit(count: number): this {{
    const cloned = this._clone();
    cloned._limit = count;
    return cloned;
  }}
  
  offset(count: number): this {{
    const cloned = this._clone();
    cloned._offset = count;
    return cloned;
  }}
  
  only(...fields: string[]): this {{
    const cloned = this._clone();
    cloned._only = fields;
    return cloned;
  }}
  
  defer(...fields: string[]): this {{
    const cloned = this._clone();
    cloned._defer = fields;
    return cloned;
  }}
  
  select_related(...relations: string[]): this {{
    const cloned = this._clone();
    cloned._expand = relations;
    return cloned;
  }}
  
  prefetch_related(...relations: string[]): this {{
    return this.select_related(...relations);
  }}
  
  private _buildQueryParams(): QueryParams {{
    const params: QueryParams = {{ ...this._filters }};
    
    if (this._ordering.length > 0) {{
      params._order = this._ordering.join(',');
    }}
    if (this._limit !== undefined) {{
      params._limit = this._limit;
    }}
    if (this._offset !== undefined) {{
      params._offset = this._offset;
    }}
    if (this._only) {{
      params._only = this._only.join(',');
    }}
    if (this._defer) {{
      params._defer = this._defer.join(',');
    }}
    if (this._expand) {{
      params._expand = this._expand.join(',');
    }}
    if (this._exclude) {{
      // Convert exclude filters to comma-separated field=value format
      const excludeParts: string[] = [];
      for (const [key, value] of Object.entries(this._exclude)) {{
        excludeParts.push(`${{key}}=${{value}}`);
      }}
      params._exclude = excludeParts.join(',');
    }}
    
    return params;
  }}
  
  async all(): Promise<TRead[]> {{
    const queryString = buildQueryString(this._buildQueryParams());
    return guitarFetch<TRead[]>(`${{this.endpoint}}/${{queryString}}`);
  }}
  
  async get(lookup: Partial<TFilter>): Promise<TRead> {{
    if ('id' in lookup && typeof lookup.id === 'number') {{
      return guitarFetch<TRead>(`${{this.endpoint}}/${{lookup.id}}/`);
    }}
    
    const results = await this.filter(lookup).limit(2).all();
    
    if (results.length === 0) {{
      throw new NotFoundError();
    }}
    if (results.length > 1) {{
      throw new GuitarError(400, 'get() returned more than one result');
    }}
    
    return results[0];
  }}
  
  async first(): Promise<TRead | null> {{
    const results = await this.limit(1).all();
    return results.length > 0 ? results[0] : null;
  }}
  
  async last(): Promise<TRead | null> {{
    // Would need backend support for proper implementation
    const results = await this.all();
    return results.length > 0 ? results[results.length - 1] : null;
  }}
  
  async count(): Promise<number> {{
    const queryString = buildQueryString(this._buildQueryParams());
    return guitarFetch<number>(`${{this.endpoint}}/_count/${{queryString}}`);
  }}
  
  async exists(): Promise<boolean> {{
    const results = await this.limit(1).all();
    return results.length > 0;
  }}
  
  async create(data: TCreate): Promise<TRead> {{
    return guitarFetch<TRead>(`${{this.endpoint}}/`, {{
      method: 'POST',
      body: JSON.stringify(data),
    }});
  }}
  
  async update(data: TUpdate): Promise<TRead[]> {{
    const items = await this.all();
    const results: TRead[] = [];
    
    for (const item of items) {{
      const id = (item as Record<string, unknown>).id;
      const updated = await guitarFetch<TRead>(`${{this.endpoint}}/${{id}}/`, {{
        method: 'PATCH',
        body: JSON.stringify(data),
      }});
      results.push(updated);
    }}
    
    return results;
  }}
  
  async delete(): Promise<void> {{
    const items = await this.all();
    
    for (const item of items) {{
      const id = (item as Record<string, unknown>).id;
      await guitarFetch<void>(`${{this.endpoint}}/${{id}}/`, {{
        method: 'DELETE',
      }});
    }}
  }}
  
  async bulk_create(data: TCreate[]): Promise<TRead[]> {{
    return guitarFetch<TRead[]>(`${{this.endpoint}}/_bulk/`, {{
      method: 'POST',
      body: JSON.stringify(data),
    }});
  }}
  
  async bulk_update(data: TUpdate): Promise<TRead[]> {{
    const queryString = buildQueryString(this._buildQueryParams());
    return guitarFetch<TRead[]>(`${{this.endpoint}}/_bulk/${{queryString}}`, {{
      method: 'PATCH',
      body: JSON.stringify(data),
    }});
  }}
}}
'''
        
        with open(os.path.join(output_dir, 'client.ts'), 'w') as f:
            f.write(client_code)
    
    def _generate_types(self, output_dir: str) -> None:
        """Generate shared types file."""
        types_code = '''/**
 * Shared types for Django Guitar
 * Auto-generated - do not edit manually
 */

export type { 
  GuitarConfig,
  GuitarError,
  NotFoundError,
  PermissionDeniedError,
  ValidationError,
  QueryParams,
  PaginatedResponse,
  FilterLookup,
} from './client';
'''
        
        with open(os.path.join(output_dir, 'types.ts'), 'w') as f:
            f.write(types_code)
    
    def _generate_model_file(
        self,
        model_class: Type[models.Model],
        output_dir: str,
        base_url: str,
    ) -> None:
        """Generate TypeScript file for a single model."""
        model_name = model_class.__name__
        meta = model_class._get_guitar_meta()
        endpoint_name = model_class._get_endpoint_name()
        
        exposed_fields = model_class._get_exposed_fields()
        writable_fields = model_class._get_writable_fields()
        read_only_fields = list(meta.read_only_fields) + ['id']
        
        # Build interface fields
        read_fields = []
        create_fields = []
        update_fields = []
        
        for field_name in exposed_fields:
            # Handle FK _id fields
            if field_name.endswith('_id'):
                base_name = field_name[:-3]
                try:
                    field = model_class._meta.get_field(base_name)
                    if isinstance(field, models.ForeignKey):
                        is_nullable = getattr(field, 'null', False)
                        ts_type = 'number | null' if is_nullable else 'number'
                        readonly = 'readonly ' if field_name in read_only_fields else ''
                        read_fields.append(f'  {readonly}{field_name}: {ts_type};')
                        
                        if field_name in writable_fields:
                            create_fields.append(f'  {field_name}: {ts_type};')
                            update_fields.append(f'  {field_name}?: {ts_type};')
                        continue
                except:
                    pass
            
            try:
                field = model_class._meta.get_field(field_name)
                ts_type = self._get_ts_type(field)
                readonly = 'readonly ' if field_name in read_only_fields else ''
                read_fields.append(f'  {readonly}{field_name}: {ts_type};')
                
                if field_name in writable_fields and field_name not in read_only_fields:
                    is_nullable = getattr(field, 'null', False) or getattr(field, 'blank', False)
                    has_default = field.has_default() or getattr(field, 'auto_now', False) or getattr(field, 'auto_now_add', False)
                    
                    if is_nullable or has_default:
                        create_fields.append(f'  {field_name}?: {ts_type};')
                    else:
                        create_fields.append(f'  {field_name}: {ts_type};')
                    
                    update_fields.append(f'  {field_name}?: {ts_type};')
            except:
                # Property or computed field
                read_fields.append(f'  readonly {field_name}: unknown;')
        
        # Build filter fields (include lookup variants)
        filter_fields = []
        for field_name in exposed_fields:
            filter_fields.append(f'  {field_name}?: unknown;')
        
        # Generate the file
        model_code = f'''/**
 * {model_name} model
 * Auto-generated - do not edit manually
 */

import {{ GuitarManager }} from '../client';

export interface {model_name} {{
{chr(10).join(read_fields)}
}}

export interface {model_name}Create {{
{chr(10).join(create_fields) if create_fields else '  // No writable fields'}
}}

export interface {model_name}Update {{
{chr(10).join(update_fields) if update_fields else '  // No writable fields'}
}}

export interface {model_name}Filter {{
{chr(10).join(filter_fields)}
  [key: `${{string}}__${{string}}`]: unknown;
}}

class {model_name}Manager extends GuitarManager<
  {model_name},
  {model_name}Create,
  {model_name}Update,
  {model_name}Filter
> {{
  protected endpoint = '{endpoint_name}';
}}

export const {model_name} = {{
  objects: new {model_name}Manager(),
}};

export default {model_name};
'''
        
        with open(os.path.join(output_dir, 'models', f'{model_name}.ts'), 'w') as f:
            f.write(model_code)
    
    def _generate_index(
        self,
        guitar_models: List[Type[models.Model]],
        output_dir: str,
    ) -> None:
        """Generate the index.ts file that exports all models."""
        imports = []
        exports = []
        
        for model_class in guitar_models:
            model_name = model_class.__name__
            imports.append(f"import {{ {model_name} }} from './models/{model_name}';")
            exports.append(model_name)
        
        # Also export from client
        imports.append("export * from './client';")
        imports.append("export * from './types';")
        
        index_code = f'''/**
 * Django Guitar TypeScript Client
 * Auto-generated - do not edit manually
 */

{chr(10).join(imports)}

export {{
  {', '.join(exports)},
}};
'''
        
        with open(os.path.join(output_dir, 'index.ts'), 'w') as f:
            f.write(index_code)
