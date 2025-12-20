/**
 * Dashboard model
 * Auto-generated - do not edit manually
 */

import { GuitarManager } from '../client';

export interface Dashboard {
  readonly id: number;
  name: string;
  description: string;
  readonly created_at: string;
  readonly updated_at: string;
}

export interface DashboardCreate {
  name: string;
  description?: string;
}

export interface DashboardUpdate {
  name?: string;
  description?: string;
}

export interface DashboardFilter {
  id?: unknown;
  name?: unknown;
  description?: unknown;
  created_at?: unknown;
  updated_at?: unknown;
  [key: `${string}__${string}`]: unknown;
}

class DashboardManager extends GuitarManager<
  Dashboard,
  DashboardCreate,
  DashboardUpdate,
  DashboardFilter
> {
  protected endpoint = 'dashboard';
}

export const Dashboard = {
  objects: new DashboardManager(),
};

export default Dashboard;
