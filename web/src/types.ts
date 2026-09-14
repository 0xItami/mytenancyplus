export type MembershipRole = "owner" | "admin" | "manager" | "viewer";

export interface SessionTokens {
  access_token: string;
  refresh_token: string;
  token_type: "bearer";
  expires_in: number;
}

export interface User {
  id: string;
  email: string;
  full_name: string;
}

export interface Organization {
  id: string;
  name: string;
  slug: string;
  created_at: string;
  role: MembershipRole;
}

export interface Member {
  organization_id: string;
  user_id: string;
  email: string;
  full_name: string;
  role: MembershipRole;
  status: "active" | "suspended";
}

export interface Invitation {
  id: string;
  email: string;
  role: MembershipRole;
  expires_at: string;
  delivery_token: string | null;
}

export interface DashboardSummary {
  properties: number;
  units: number;
  active_leases: number;
  open_work_orders: number;
  unread_notifications: number;
  subscription_plan: "starter" | "growth" | "scale";
  subscription_status: "trialing" | "active" | "past_due" | "cancelled";
}

export interface Property {
  id: string;
  organization_id: string;
  name: string;
  address_line: string;
  city: string;
  country_code: string;
  created_at: string;
}

export type WorkOrderStatus =
  "open" | "triaged" | "in_progress" | "resolved" | "closed" | "cancelled";

export interface WorkOrder {
  id: string;
  organization_id: string;
  property_id: string;
  unit_id: string | null;
  title: string;
  description: string;
  priority: "low" | "normal" | "high" | "urgent";
  status: WorkOrderStatus;
  reported_by_id: string;
  assigned_to_id: string | null;
  due_at: string | null;
  resolved_at: string | null;
  closed_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface Notification {
  id: string;
  category: string;
  title: string;
  body: string;
  resource_type: string | null;
  resource_id: string | null;
  read_at: string | null;
  created_at: string;
}

export interface DocumentRecord {
  id: string;
  organization_id: string;
  file_name: string;
  content_type: string;
  size_bytes: number;
  checksum_sha256: string;
  resource_type: string;
  resource_id: string;
  uploaded_by_id: string;
  created_at: string;
}

export interface Subscription {
  id: string;
  organization_id: string;
  provider: string;
  plan: "starter" | "growth" | "scale";
  status: "trialing" | "active" | "past_due" | "cancelled";
  current_period_end: string | null;
  cancel_at_period_end: boolean;
}
