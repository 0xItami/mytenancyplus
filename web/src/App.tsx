import { useEffect, useState } from "react";

import { AppShell, type PageId } from "./components/AppShell";
import { AuthScreen } from "./components/AuthScreen";
import { api } from "./lib/api";
import { DashboardPage } from "./pages/DashboardPage";
import { DocumentsPage } from "./pages/DocumentsPage";
import { MaintenancePage } from "./pages/MaintenancePage";
import { NotificationsPage } from "./pages/NotificationsPage";
import { PropertiesPage } from "./pages/PropertiesPage";
import { SettingsPage } from "./pages/SettingsPage";
import type { Organization, User } from "./types";

const ORGANIZATION_KEY = "mytenancyplus.organization";

export function App() {
  const [authenticated, setAuthenticated] = useState(api.isAuthenticated());
  const [user, setUser] = useState<User | null>(null);
  const [organizations, setOrganizations] = useState<Organization[]>([]);
  const [organizationId, setOrganizationId] = useState(
    localStorage.getItem(ORGANIZATION_KEY) ?? "",
  );
  const [page, setPage] = useState<PageId>("dashboard");
  const [loading, setLoading] = useState(authenticated);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!authenticated) return;
    void loadWorkspace();
  }, [authenticated]);

  async function loadWorkspace() {
    setLoading(true);
    setError("");
    try {
      const currentUser = await api.request<User>("/auth/me");
      const invitationToken = new URLSearchParams(window.location.search).get("invitation");
      if (invitationToken) {
        await api.request("/organizations/invitations/accept", {
          method: "POST",
          body: JSON.stringify({ token: invitationToken }),
        });
        window.history.replaceState({}, "", window.location.pathname);
      }
      const availableOrganizations = await api.request<Organization[]>("/organizations");
      setUser(currentUser);
      setOrganizations(availableOrganizations);
      const selected = availableOrganizations.find((item) => item.id === organizationId);
      if (!selected && availableOrganizations[0]) selectOrganization(availableOrganizations[0].id);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Could not load workspace");
      if (!api.isAuthenticated()) setAuthenticated(false);
    } finally {
      setLoading(false);
    }
  }

  function selectOrganization(id: string) {
    setOrganizationId(id);
    localStorage.setItem(ORGANIZATION_KEY, id);
  }

  async function createOrganization(name: string) {
    const created = await api.request<Organization>("/organizations", {
      method: "POST",
      body: JSON.stringify({ name }),
    });
    setOrganizations((current) => [...current, created]);
    selectOrganization(created.id);
  }

  async function logout() {
    await api.logout();
    setAuthenticated(false);
    setUser(null);
    setOrganizations([]);
  }

  if (!authenticated) {
    return <AuthScreen onAuthenticated={() => setAuthenticated(true)} />;
  }

  if (loading) {
    return (
      <main className="loading-screen">
        <span className="brand-mark">M+</span>
        <p>Opening your operations workspace…</p>
      </main>
    );
  }

  if (!user) {
    return (
      <main className="loading-screen">
        <p>{error || "Your workspace could not be loaded."}</p>
        <button className="button button-primary" onClick={() => void loadWorkspace()}>
          Try again
        </button>
      </main>
    );
  }

  if (organizations.length === 0) {
    return <OrganizationSetup user={user} onCreate={createOrganization} onLogout={logout} />;
  }

  const organization = organizations.find((item) => item.id === organizationId) ?? organizations[0];

  return (
    <AppShell
      page={page}
      onPageChange={setPage}
      user={user}
      organization={organization}
      organizations={organizations}
      onOrganizationChange={selectOrganization}
      onLogout={logout}
    >
      {error && <div className="inline-alert">{error}</div>}
      {page === "dashboard" && <DashboardPage organization={organization} />}
      {page === "properties" && <PropertiesPage organization={organization} />}
      {page === "maintenance" && <MaintenancePage organization={organization} />}
      {page === "documents" && <DocumentsPage organization={organization} />}
      {page === "notifications" && <NotificationsPage organization={organization} />}
      {page === "settings" && <SettingsPage organization={organization} />}
    </AppShell>
  );
}

interface OrganizationSetupProps {
  user: User;
  onCreate: (name: string) => Promise<void>;
  onLogout: () => Promise<void>;
}

function OrganizationSetup({ user, onCreate, onLogout }: OrganizationSetupProps) {
  const [name, setName] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      await onCreate(name);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Could not create workspace");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="setup-screen">
      <section className="setup-card">
        <span className="eyebrow">Welcome, {user.full_name.split(" ")[0]}</span>
        <h1>Create your property workspace</h1>
        <p>Keep every building, tenancy, repair, and document under one accountable operation.</p>
        <form onSubmit={(event) => void submit(event)}>
          <label>
            Workspace name
            <input
              autoFocus
              minLength={2}
              maxLength={160}
              placeholder="e.g. Northstar Property Group"
              required
              value={name}
              onChange={(event) => setName(event.target.value)}
            />
          </label>
          {error && <p className="form-error">{error}</p>}
          <button className="button button-primary" disabled={busy}>
            {busy ? "Creating…" : "Create workspace"}
          </button>
        </form>
        <button className="text-button" onClick={() => void onLogout()}>
          Sign out
        </button>
      </section>
    </main>
  );
}
