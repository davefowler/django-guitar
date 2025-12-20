/**
 * Chart model
 * Auto-generated - do not edit manually
 */

import { GuitarManager } from '../client';

export interface Chart {
  readonly id: number;
  dashboard_id: number;
  name: string;
  chart_type: string;
  query: string;
  config: Record<string, unknown>;
  position: number;
  readonly created_at: string;
  readonly updated_at: string;
  readonly created_by_id: number | null;
}

export interface ChartCreate {
  dashboard_id: number;
  name: string;
  chart_type?: string;
  query?: string;
  config?: Record<string, unknown>;
  position?: number;
}

export interface ChartUpdate {
  dashboard_id?: number;
  name?: string;
  chart_type?: string;
  query?: string;
  config?: Record<string, unknown>;
  position?: number;
}

export interface ChartFilter {
  id?: unknown;
  dashboard_id?: unknown;
  name?: unknown;
  chart_type?: unknown;
  query?: unknown;
  config?: unknown;
  position?: unknown;
  created_at?: unknown;
  updated_at?: unknown;
  created_by_id?: unknown;
  [key: `${string}__${string}`]: unknown;
}

class ChartManager extends GuitarManager<
  Chart,
  ChartCreate,
  ChartUpdate,
  ChartFilter
> {
  protected endpoint = 'chart';
}

export const Chart = {
  objects: new ChartManager(),
};

export default Chart;
