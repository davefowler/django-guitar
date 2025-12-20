/**
 * DashboardMembership model
 * Auto-generated - do not edit manually
 */

import { GuitarManager } from '../client';

export interface DashboardMembership {
  readonly id: number;
  user_id: number;
  dashboard_id: number;
  role: string;
  readonly invited_at: string;
  readonly invited_by_id: number | null;
}

export interface DashboardMembershipCreate {
  user_id: number;
  dashboard_id: number;
  role: string;
}

export interface DashboardMembershipUpdate {
  user_id?: number;
  dashboard_id?: number;
  role?: string;
}

export interface DashboardMembershipFilter {
  id?: unknown;
  user_id?: unknown;
  dashboard_id?: unknown;
  role?: unknown;
  invited_at?: unknown;
  invited_by_id?: unknown;
  [key: `${string}__${string}`]: unknown;
}

class DashboardMembershipManager extends GuitarManager<
  DashboardMembership,
  DashboardMembershipCreate,
  DashboardMembershipUpdate,
  DashboardMembershipFilter
> {
  protected endpoint = 'dashboardmembership';
}

export const DashboardMembership = {
  objects: new DashboardMembershipManager(),
};

export default DashboardMembership;
