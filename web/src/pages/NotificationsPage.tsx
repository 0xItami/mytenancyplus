import { useEffect, useState } from "react";
import { Bell, Check, Wrench } from "lucide-react";

import { EmptyState, LoadingBlock, PageHeader } from "../components/PageHeader";
import { api } from "../lib/api";
import type { Notification, Organization } from "../types";

export function NotificationsPage({ organization }: { organization: Organization }) {
  const [notifications, setNotifications] = useState<Notification[] | null>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    void load();
  }, [organization.id]);

  async function load() {
    try {
      setNotifications(await api.request<Notification[]>("/notifications", {}, organization.id));
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Notifications unavailable");
    }
  }

  async function markRead(notification: Notification) {
    try {
      await api.request(
        `/notifications/${notification.id}/read`,
        { method: "PATCH" },
        organization.id,
      );
      await load();
    } catch (requestError) {
      setError(
        requestError instanceof Error ? requestError.message : "Could not update notification",
      );
    }
  }

  if (!notifications && !error) return <LoadingBlock />;
  return (
    <>
      <PageHeader
        eyebrow="Personal inbox"
        title="Notifications"
        description="The operational updates that need your attention, without the noise."
      />
      {error && <div className="inline-alert">{error}</div>}
      {notifications?.length === 0 ? (
        <EmptyState>
          <Bell size={30} />
          <h2>You’re all caught up</h2>
          <p>Assignments and important workflow events will appear here.</p>
        </EmptyState>
      ) : (
        <section className="panel notification-list">
          {notifications?.map((notification) => (
            <article className={notification.read_at ? "read" : ""} key={notification.id}>
              <span className="notification-icon">
                <Wrench size={18} />
              </span>
              <div>
                <span className="eyebrow">{notification.category}</span>
                <h2>{notification.title}</h2>
                <p>{notification.body}</p>
                <time>{new Date(notification.created_at).toLocaleString()}</time>
              </div>
              {notification.read_at ? (
                <span className="read-label">
                  <Check size={14} /> Read
                </span>
              ) : (
                <button
                  className="button button-secondary"
                  onClick={() => void markRead(notification)}
                >
                  Mark as read
                </button>
              )}
            </article>
          ))}
        </section>
      )}
    </>
  );
}
