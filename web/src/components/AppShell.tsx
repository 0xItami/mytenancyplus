import type { ReactNode } from "react";
import {
  Bell,
  Building2,
  ChevronDown,
  FileText,
  Gauge,
  LogOut,
  Settings,
  Wrench,
} from "lucide-react";

import type { Organization, User } from "../types";

export type PageId =
  "dashboard" | "properties" | "maintenance" | "documents" | "notifications" | "settings";

const navigation = [
  { id: "dashboard" as const, label: "Overview", icon: Gauge },
  { id: "properties" as const, label: "Properties", icon: Building2 },
  { id: "maintenance" as const, label: "Maintenance", icon: Wrench },
  { id: "documents" as const, label: "Documents", icon: FileText },
  { id: "notifications" as const, label: "Notifications", icon: Bell },
  { id: "settings" as const, label: "Workspace", icon: Settings },
];

interface AppShellProps {
  page: PageId;
  onPageChange: (page: PageId) => void;
  user: User;
  organization: Organization;
  organizations: Organization[];
  onOrganizationChange: (id: string) => void;
  onLogout: () => Promise<void>;
  children: ReactNode;
}

export function AppShell({
  page,
  onPageChange,
  user,
  organization,
  organizations,
  onOrganizationChange,
  onLogout,
  children,
}: AppShellProps) {
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand-lockup brand-lockup-sidebar">
          <span className="brand-mark">M+</span>
          <span>MyTenancyPlus</span>
        </div>
        <div className="organization-select-wrap">
          <span className="organization-avatar">{organization.name.slice(0, 1).toUpperCase()}</span>
          <select
            aria-label="Current organization"
            value={organization.id}
            onChange={(event) => onOrganizationChange(event.target.value)}
          >
            {organizations.map((item) => (
              <option key={item.id} value={item.id}>
                {item.name}
              </option>
            ))}
          </select>
          <ChevronDown size={15} />
        </div>
        <nav className="primary-nav">
          {navigation.map((item) => {
            const Icon = item.icon;
            return (
              <button
                key={item.id}
                className={page === item.id ? "active" : ""}
                onClick={() => onPageChange(item.id)}
              >
                <Icon size={18} />
                <span>{item.label}</span>
              </button>
            );
          })}
        </nav>
        <div className="sidebar-account">
          <span className="user-avatar">
            {user.full_name
              .split(" ")
              .map((part) => part[0])
              .join("")
              .slice(0, 2)
              .toUpperCase()}
          </span>
          <div>
            <strong>{user.full_name}</strong>
            <span>{organization.role}</span>
          </div>
          <button aria-label="Sign out" onClick={() => void onLogout()}>
            <LogOut size={17} />
          </button>
        </div>
      </aside>
      <div className="workspace">
        <header className="mobile-header">
          <div className="brand-lockup">
            <span className="brand-mark">M+</span>
            <span>MyTenancyPlus</span>
          </div>
          <span className="user-avatar">{user.full_name.slice(0, 1)}</span>
        </header>
        <main className="workspace-content">{children}</main>
        <nav className="mobile-nav">
          {navigation.slice(0, 5).map((item) => {
            const Icon = item.icon;
            return (
              <button
                key={item.id}
                className={page === item.id ? "active" : ""}
                onClick={() => onPageChange(item.id)}
                aria-label={item.label}
              >
                <Icon size={19} />
                <span>{item.label}</span>
              </button>
            );
          })}
        </nav>
      </div>
    </div>
  );
}
