import type { SessionTokens } from "../types";

const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000/api/v1";
const SESSION_KEY = "mytenancyplus.session";

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
  }
}

function readSession(): SessionTokens | null {
  const value = localStorage.getItem(SESSION_KEY);
  if (!value) return null;
  try {
    return JSON.parse(value) as SessionTokens;
  } catch {
    localStorage.removeItem(SESSION_KEY);
    return null;
  }
}

async function errorMessage(response: Response): Promise<string> {
  try {
    const body = (await response.json()) as { detail?: string };
    return body.detail ?? `Request failed with status ${response.status}`;
  } catch {
    return `Request failed with status ${response.status}`;
  }
}

class ApiClient {
  private session = readSession();

  isAuthenticated(): boolean {
    return this.session !== null;
  }

  saveSession(session: SessionTokens): void {
    this.session = session;
    localStorage.setItem(SESSION_KEY, JSON.stringify(session));
  }

  clearSession(): void {
    this.session = null;
    localStorage.removeItem(SESSION_KEY);
  }

  async login(email: string, password: string): Promise<void> {
    const body = new URLSearchParams({ username: email, password });
    const response = await fetch(`${API_URL}/auth/token`, { method: "POST", body });
    if (!response.ok) throw new ApiError(await errorMessage(response), response.status);
    this.saveSession((await response.json()) as SessionTokens);
  }

  async register(fullName: string, email: string, password: string): Promise<void> {
    await this.request("/auth/register", {
      method: "POST",
      body: JSON.stringify({ full_name: fullName, email, password }),
    });
    await this.login(email, password);
  }

  async logout(): Promise<void> {
    if (this.session) {
      try {
        await fetch(`${API_URL}/auth/logout`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ refresh_token: this.session.refresh_token }),
        });
      } finally {
        this.clearSession();
      }
    }
  }

  async request<T>(path: string, init: RequestInit = {}, organizationId?: string): Promise<T> {
    const response = await this.send(path, init, organizationId);
    if (response.status === 401 && this.session && !path.startsWith("/auth/")) {
      const refreshed = await this.refresh();
      if (refreshed) return this.parse<T>(await this.send(path, init, organizationId));
    }
    return this.parse<T>(response);
  }

  async download(path: string, organizationId: string): Promise<Blob> {
    const response = await this.send(path, {}, organizationId);
    if (!response.ok) throw new ApiError(await errorMessage(response), response.status);
    return response.blob();
  }

  private async refresh(): Promise<boolean> {
    if (!this.session) return false;
    const response = await fetch(`${API_URL}/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: this.session.refresh_token }),
    });
    if (!response.ok) {
      this.clearSession();
      return false;
    }
    this.saveSession((await response.json()) as SessionTokens);
    return true;
  }

  private send(path: string, init: RequestInit, organizationId?: string): Promise<Response> {
    const headers = new Headers(init.headers);
    if (!(init.body instanceof FormData)) headers.set("Content-Type", "application/json");
    if (this.session) headers.set("Authorization", `Bearer ${this.session.access_token}`);
    if (organizationId) headers.set("X-Organization-ID", organizationId);
    return fetch(`${API_URL}${path}`, { ...init, headers });
  }

  private async parse<T>(response: Response): Promise<T> {
    if (!response.ok) throw new ApiError(await errorMessage(response), response.status);
    if (response.status === 204) return undefined as T;
    return response.json() as Promise<T>;
  }
}

export const api = new ApiClient();
