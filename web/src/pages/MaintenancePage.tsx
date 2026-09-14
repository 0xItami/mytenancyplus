import { useEffect, useState } from "react";
import { ArrowRight, Plus, Wrench, X } from "lucide-react";

import { EmptyState, LoadingBlock, PageHeader } from "../components/PageHeader";
import { api } from "../lib/api";
import type { Organization, Property, WorkOrder, WorkOrderStatus } from "../types";

const nextStatus: Partial<Record<WorkOrderStatus, WorkOrderStatus>> = {
  open: "triaged",
  triaged: "in_progress",
  in_progress: "resolved",
  resolved: "closed",
};

export function MaintenancePage({ organization }: { organization: Organization }) {
  const [orders, setOrders] = useState<WorkOrder[] | null>(null);
  const [properties, setProperties] = useState<Property[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    void load();
  }, [organization.id]);

  async function load() {
    try {
      const [nextOrders, nextProperties] = await Promise.all([
        api.request<WorkOrder[]>("/work-orders", {}, organization.id),
        api.request<Property[]>("/properties", {}, organization.id),
      ]);
      setOrders(nextOrders);
      setProperties(nextProperties);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Maintenance unavailable");
    }
  }

  async function advance(order: WorkOrder) {
    const status = nextStatus[order.status];
    if (!status) return;
    try {
      await api.request(
        `/work-orders/${order.id}`,
        { method: "PATCH", body: JSON.stringify({ status }) },
        organization.id,
      );
      await load();
    } catch (requestError) {
      setError(
        requestError instanceof Error ? requestError.message : "Could not update work order",
      );
    }
  }

  if (!orders && !error) return <LoadingBlock />;

  return (
    <>
      <PageHeader
        eyebrow="Operational queue"
        title="Maintenance"
        description="Move every issue through a visible, controlled resolution workflow."
        action={
          <button
            className="button button-primary"
            onClick={() => setShowForm(true)}
            disabled={properties.length === 0}
          >
            <Plus size={17} /> New work order
          </button>
        }
      />
      {properties.length === 0 && (
        <div className="inline-note">Add a property before creating a work order.</div>
      )}
      {error && <div className="inline-alert">{error}</div>}
      {orders?.length === 0 ? (
        <EmptyState>
          <Wrench size={30} />
          <h2>The queue is clear</h2>
          <p>Reported issues and scheduled repairs will be tracked here.</p>
        </EmptyState>
      ) : (
        <section className="panel table-panel">
          <div className="table-head">
            <span>Issue</span>
            <span>Priority</span>
            <span>Status</span>
            <span>Opened</span>
            <span />
          </div>
          {orders?.map((order) => (
            <div className="table-row" key={order.id}>
              <div>
                <strong>{order.title}</strong>
                <span>
                  {properties.find((item) => item.id === order.property_id)?.name ?? "Property"}
                </span>
              </div>
              <span className={`tag ${order.priority}`}>{order.priority}</span>
              <span className={`tag ${order.status}`}>{order.status.replaceAll("_", " ")}</span>
              <span>{new Date(order.created_at).toLocaleDateString()}</span>
              <button
                className="row-action"
                disabled={!nextStatus[order.status]}
                onClick={() => void advance(order)}
              >
                {nextStatus[order.status] ? (
                  <>
                    <span>Advance</span>
                    <ArrowRight size={16} />
                  </>
                ) : (
                  <span>Complete</span>
                )}
              </button>
            </div>
          ))}
        </section>
      )}
      {showForm && (
        <WorkOrderForm
          organization={organization}
          properties={properties}
          onClose={() => setShowForm(false)}
          onCreated={async () => {
            setShowForm(false);
            await load();
          }}
        />
      )}
    </>
  );
}

function WorkOrderForm({
  organization,
  properties,
  onClose,
  onCreated,
}: {
  organization: Organization;
  properties: Property[];
  onClose: () => void;
  onCreated: () => Promise<void>;
}) {
  const [form, setForm] = useState({
    property_id: properties[0]?.id ?? "",
    title: "",
    description: "",
    priority: "normal",
  });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      await api.request(
        "/work-orders",
        { method: "POST", body: JSON.stringify(form) },
        organization.id,
      );
      await onCreated();
    } catch (requestError) {
      setError(
        requestError instanceof Error ? requestError.message : "Could not create work order",
      );
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="modal-backdrop">
      <section className="modal" role="dialog" aria-modal="true">
        <button className="modal-close" onClick={onClose}>
          <X size={19} />
        </button>
        <span className="eyebrow">Maintenance intake</span>
        <h2>New work order</h2>
        <p className="muted">Capture enough detail for the next person to act without guesswork.</p>
        <form onSubmit={(event) => void submit(event)}>
          <label>
            Property
            <select
              value={form.property_id}
              onChange={(event) => setForm({ ...form, property_id: event.target.value })}
            >
              {properties.map((property) => (
                <option value={property.id} key={property.id}>
                  {property.name}
                </option>
              ))}
            </select>
          </label>
          <label>
            Issue title
            <input
              required
              minLength={3}
              value={form.title}
              onChange={(event) => setForm({ ...form, title: event.target.value })}
              placeholder="Repair lobby water leak"
            />
          </label>
          <label>
            Description
            <textarea
              required
              minLength={5}
              rows={4}
              value={form.description}
              onChange={(event) => setForm({ ...form, description: event.target.value })}
              placeholder="Describe the location, impact, and what has already been checked."
            />
          </label>
          <label>
            Priority
            <select
              value={form.priority}
              onChange={(event) => setForm({ ...form, priority: event.target.value })}
            >
              <option value="low">Low</option>
              <option value="normal">Normal</option>
              <option value="high">High</option>
              <option value="urgent">Urgent</option>
            </select>
          </label>
          {error && <p className="form-error">{error}</p>}
          <div className="modal-actions">
            <button type="button" className="button button-secondary" onClick={onClose}>
              Cancel
            </button>
            <button className="button button-primary" disabled={busy}>
              {busy ? "Creating…" : "Create work order"}
            </button>
          </div>
        </form>
      </section>
    </div>
  );
}
