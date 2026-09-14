import { useEffect, useState } from "react";
import { ArrowUpRight, Building2, CircleCheck, Clock3, Home, Wrench } from "lucide-react";

import { LoadingBlock, PageHeader } from "../components/PageHeader";
import { api } from "../lib/api";
import type { DashboardSummary, Organization, Property, WorkOrder } from "../types";

export function DashboardPage({ organization }: { organization: Organization }) {
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [properties, setProperties] = useState<Property[]>([]);
  const [workOrders, setWorkOrders] = useState<WorkOrder[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    void load();
  }, [organization.id]);

  async function load() {
    setError("");
    try {
      const [nextSummary, nextProperties, nextWorkOrders] = await Promise.all([
        api.request<DashboardSummary>("/dashboard/summary", {}, organization.id),
        api.request<Property[]>("/properties", {}, organization.id),
        api.request<WorkOrder[]>("/work-orders", {}, organization.id),
      ]);
      setSummary(nextSummary);
      setProperties(nextProperties);
      setWorkOrders(nextWorkOrders.slice(0, 5));
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Dashboard unavailable");
    }
  }

  if (!summary && !error) return <LoadingBlock />;

  const metrics = summary
    ? [
        {
          label: "Properties",
          value: summary.properties,
          detail: `${summary.units} units`,
          icon: Building2,
        },
        {
          label: "Active leases",
          value: summary.active_leases,
          detail: "Current tenancies",
          icon: Home,
        },
        {
          label: "Open repairs",
          value: summary.open_work_orders,
          detail: "Need attention",
          icon: Wrench,
        },
        {
          label: "Unread updates",
          value: summary.unread_notifications,
          detail: "For your account",
          icon: Clock3,
        },
      ]
    : [];

  return (
    <>
      <PageHeader
        eyebrow="Portfolio command centre"
        title={`Good day. Here’s ${organization.name}.`}
        description="A live view of the work, occupancy, and operational health across your portfolio."
        action={
          <span className="status-pill">
            <span /> Systems operational
          </span>
        }
      />
      {error && <div className="inline-alert">{error}</div>}
      <section className="metric-grid">
        {metrics.map((metric) => {
          const Icon = metric.icon;
          return (
            <article className="metric-card" key={metric.label}>
              <div className="metric-icon">
                <Icon size={19} />
              </div>
              <span>{metric.label}</span>
              <strong>{metric.value}</strong>
              <small>{metric.detail}</small>
            </article>
          );
        })}
      </section>
      <section className="dashboard-grid">
        <article className="panel activity-panel">
          <div className="panel-heading">
            <div>
              <span className="eyebrow">Priority queue</span>
              <h2>Recent maintenance</h2>
            </div>
            <Wrench size={20} />
          </div>
          {workOrders.length === 0 ? (
            <div className="quiet-success">
              <CircleCheck size={24} />
              <div>
                <strong>No maintenance queue</strong>
                <span>New work orders will appear here.</span>
              </div>
            </div>
          ) : (
            <div className="work-list compact">
              {workOrders.map((order) => (
                <div className="work-row" key={order.id}>
                  <span className={`priority-dot ${order.priority}`} />
                  <div>
                    <strong>{order.title}</strong>
                    <span>{order.status.replaceAll("_", " ")}</span>
                  </div>
                  <span className={`tag ${order.status}`}>{order.priority}</span>
                </div>
              ))}
            </div>
          )}
        </article>
        <article className="panel portfolio-panel">
          <div className="panel-heading">
            <div>
              <span className="eyebrow">Portfolio</span>
              <h2>Property footprint</h2>
            </div>
            <ArrowUpRight size={20} />
          </div>
          {properties.length === 0 ? (
            <p className="muted">Add your first property to begin tracking operations.</p>
          ) : (
            <div className="property-stack">
              {properties.slice(0, 4).map((property, index) => (
                <div key={property.id}>
                  <span className="property-number">0{index + 1}</span>
                  <div>
                    <strong>{property.name}</strong>
                    <span>
                      {property.city}, {property.country_code}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
          <div className="plan-strip">
            <span>Current plan</span>
            <strong>{summary?.subscription_plan}</strong>
            <small>{summary?.subscription_status}</small>
          </div>
        </article>
      </section>
    </>
  );
}
