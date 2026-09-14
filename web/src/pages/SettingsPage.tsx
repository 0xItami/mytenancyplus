import { useEffect, useState } from "react";
import {
  CheckCircle2,
  Copy,
  Database,
  KeyRound,
  Layers3,
  Send,
  ShieldCheck,
  Users,
} from "lucide-react";

import { LoadingBlock, PageHeader } from "../components/PageHeader";
import { api } from "../lib/api";
import type { Invitation, Member, MembershipRole, Organization, Subscription } from "../types";

export function SettingsPage({ organization }: { organization: Organization }) {
  const [subscription, setSubscription] = useState<Subscription | null | undefined>(undefined);
  const [members, setMembers] = useState<Member[]>([]);
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteRole, setInviteRole] = useState<MembershipRole>("manager");
  const [invitationLink, setInvitationLink] = useState("");
  const [inviteBusy, setInviteBusy] = useState(false);
  const [error, setError] = useState("");
  useEffect(() => {
    void load();
  }, [organization.id]);

  async function load() {
    try {
      const [nextSubscription, nextMembers] = await Promise.all([
        api.request<Subscription | null>("/billing/subscription", {}, organization.id),
        api.request<Member[]>("/organizations/members", {}, organization.id),
      ]);
      setSubscription(nextSubscription);
      setMembers(nextMembers);
    } catch (requestError) {
      setError(
        requestError instanceof Error ? requestError.message : "Workspace details unavailable",
      );
    }
  }

  async function invite(event: React.FormEvent) {
    event.preventDefault();
    setInviteBusy(true);
    setInvitationLink("");
    setError("");
    try {
      const invitation = await api.request<Invitation>(
        "/organizations/invitations",
        {
          method: "POST",
          body: JSON.stringify({ email: inviteEmail, role: inviteRole }),
        },
        organization.id,
      );
      setInviteEmail("");
      setInvitationLink(
        invitation.delivery_token
          ? `${window.location.origin}/?invitation=${encodeURIComponent(invitation.delivery_token)}`
          : "queued",
      );
    } catch (requestError) {
      setError(
        requestError instanceof Error ? requestError.message : "Invitation could not be sent",
      );
    } finally {
      setInviteBusy(false);
    }
  }
  if (subscription === undefined && !error) return <LoadingBlock />;
  const plan = subscription?.plan ?? "starter";
  const status = subscription?.status ?? "trialing";
  return (
    <>
      <PageHeader
        eyebrow="Workspace governance"
        title={organization.name}
        description="Membership context, service plan, and platform safeguards for this organization."
      />
      {error && <div className="inline-alert">{error}</div>}
      <section className="settings-grid">
        <article className="panel plan-card">
          <span className="eyebrow">Current service plan</span>
          <div className="plan-title">
            <h2>{plan}</h2>
            <span className={`tag ${status}`}>{status}</span>
          </div>
          <p>Your subscription state is synchronized through signed, idempotent billing events.</p>
          <ul>
            <li>
              <CheckCircle2 size={17} /> Property and tenancy operations
            </li>
            <li>
              <CheckCircle2 size={17} /> Maintenance workflows and notifications
            </li>
            <li>
              <CheckCircle2 size={17} /> Document evidence library
            </li>
          </ul>
        </article>
        <article className="panel governance-card">
          <span className="eyebrow">Organization context</span>
          <h2>Access and isolation</h2>
          <div>
            <ShieldCheck size={19} />
            <span>
              <strong>Your role</strong>
              <small>{organization.role}</small>
            </span>
          </div>
          <div>
            <KeyRound size={19} />
            <span>
              <strong>Workspace ID</strong>
              <small>{organization.id}</small>
            </span>
          </div>
          <div>
            <Database size={19} />
            <span>
              <strong>Data boundary</strong>
              <small>Organization isolated</small>
            </span>
          </div>
          <div>
            <Layers3 size={19} />
            <span>
              <strong>Audit trail</strong>
              <small>Operational writes recorded</small>
            </span>
          </div>
        </article>
      </section>
      <section className="panel team-panel">
        <div className="panel-heading">
          <div>
            <span className="eyebrow">Team membership</span>
            <h2>People with workspace access</h2>
          </div>
          <Users size={20} />
        </div>
        <div className="member-list">
          {members.map((member) => (
            <div className="member-row" key={member.user_id}>
              <span className="user-avatar">
                {member.full_name
                  .split(" ")
                  .map((part) => part[0])
                  .join("")
                  .slice(0, 2)
                  .toUpperCase()}
              </span>
              <div>
                <strong>{member.full_name}</strong>
                <span>{member.email}</span>
              </div>
              <span className={`tag ${member.status}`}>{member.status}</span>
              <strong className="member-role">{member.role}</strong>
            </div>
          ))}
        </div>
        {organization.role === "owner" || organization.role === "admin" ? (
          <form className="invite-form" onSubmit={(event) => void invite(event)}>
            <label>
              Invite by email
              <input
                type="email"
                required
                value={inviteEmail}
                onChange={(event) => setInviteEmail(event.target.value)}
                placeholder="teammate@company.com"
              />
            </label>
            <label>
              Role
              <select
                value={inviteRole}
                onChange={(event) => setInviteRole(event.target.value as MembershipRole)}
              >
                <option value="admin">Admin</option>
                <option value="manager">Manager</option>
                <option value="viewer">Viewer</option>
              </select>
            </label>
            <button className="button button-primary" disabled={inviteBusy}>
              <Send size={16} /> {inviteBusy ? "Inviting…" : "Invite member"}
            </button>
          </form>
        ) : null}
        {invitationLink && (
          <div className="invitation-result">
            <div>
              <strong>Invitation created</strong>
              <span>
                {invitationLink === "queued"
                  ? "The delivery event is queued."
                  : "Copy this local invitation link for the teammate."}
              </span>
            </div>
            {invitationLink !== "queued" && (
              <button
                className="button button-secondary"
                onClick={() => void navigator.clipboard.writeText(invitationLink)}
              >
                <Copy size={15} /> Copy link
              </button>
            )}
          </div>
        )}
      </section>
    </>
  );
}
