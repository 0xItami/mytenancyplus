import { useState } from "react";
import { Building2, CheckCircle2, ShieldCheck, Wrench } from "lucide-react";

import { api } from "../lib/api";

interface AuthScreenProps {
  onAuthenticated: () => void;
}

export function AuthScreen({ onAuthenticated }: AuthScreenProps) {
  const [mode, setMode] = useState<"login" | "register">("login");
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      if (mode === "register") await api.register(fullName, email, password);
      else await api.login(email, password);
      onAuthenticated();
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Authentication failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="auth-layout">
      <section className="auth-story">
        <div className="brand-lockup">
          <span className="brand-mark">M+</span>
          <span>MyTenancyPlus</span>
        </div>
        <div className="auth-story-copy">
          <span className="eyebrow">Property operations, made accountable</span>
          <h1>A calmer command centre for every tenancy.</h1>
          <p>
            One secure workspace for properties, leases, repairs, documents, and the people
            responsible for moving them forward.
          </p>
          <ul className="feature-list">
            <li>
              <Building2 size={18} /> Portfolio-wide operational visibility
            </li>
            <li>
              <Wrench size={18} /> Structured maintenance workflows
            </li>
            <li>
              <ShieldCheck size={18} /> Organization-level access controls
            </li>
          </ul>
        </div>
        <div className="trust-note">
          <CheckCircle2 size={16} /> Built for focused property teams
        </div>
      </section>

      <section className="auth-panel">
        <div className="auth-card">
          <span className="eyebrow">
            {mode === "login" ? "Welcome back" : "Start your workspace"}
          </span>
          <h2>{mode === "login" ? "Sign in to continue" : "Create your account"}</h2>
          <p className="muted">
            {mode === "login"
              ? "Your portfolio is ready when you are."
              : "Set up your organization in less than a minute."}
          </p>
          <form onSubmit={(event) => void submit(event)}>
            {mode === "register" && (
              <label>
                Full name
                <input
                  autoComplete="name"
                  required
                  minLength={2}
                  value={fullName}
                  onChange={(event) => setFullName(event.target.value)}
                  placeholder="Amara Okafor"
                />
              </label>
            )}
            <label>
              Email address
              <input
                autoComplete="email"
                type="email"
                required
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                placeholder="you@company.com"
              />
            </label>
            <label>
              Password
              <input
                autoComplete={mode === "login" ? "current-password" : "new-password"}
                type="password"
                required
                minLength={12}
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                placeholder="At least 12 characters"
              />
            </label>
            {error && <p className="form-error">{error}</p>}
            <button className="button button-primary button-wide" disabled={busy}>
              {busy ? "Please wait…" : mode === "login" ? "Sign in" : "Create account"}
            </button>
          </form>
          <p className="auth-switch">
            {mode === "login" ? "New to MyTenancyPlus?" : "Already have an account?"}{" "}
            <button
              className="text-button"
              onClick={() => {
                setMode(mode === "login" ? "register" : "login");
                setError("");
              }}
            >
              {mode === "login" ? "Create an account" : "Sign in"}
            </button>
          </p>
        </div>
      </section>
    </main>
  );
}
