import { useEffect, useState } from "react";
import { Building2, MapPin, Plus, X } from "lucide-react";

import { EmptyState, LoadingBlock, PageHeader } from "../components/PageHeader";
import { api } from "../lib/api";
import type { Organization, Property } from "../types";

export function PropertiesPage({ organization }: { organization: Organization }) {
  const [properties, setProperties] = useState<Property[] | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    void load();
  }, [organization.id]);

  async function load() {
    try {
      setProperties(await api.request<Property[]>("/properties", {}, organization.id));
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Properties unavailable");
    }
  }

  if (!properties && !error) return <LoadingBlock />;

  return (
    <>
      <PageHeader
        eyebrow="Portfolio register"
        title="Properties"
        description="The physical places your team operates and remains accountable for."
        action={
          <button className="button button-primary" onClick={() => setShowForm(true)}>
            <Plus size={17} /> Add property
          </button>
        }
      />
      {error && <div className="inline-alert">{error}</div>}
      {properties?.length === 0 ? (
        <EmptyState>
          <Building2 size={30} />
          <h2>No properties yet</h2>
          <p>Add your first building to unlock units, leases, maintenance, and documents.</p>
        </EmptyState>
      ) : (
        <section className="property-grid">
          {properties?.map((property) => (
            <article className="property-card" key={property.id}>
              <div className="property-card-art">
                <span>{property.name.slice(0, 2).toUpperCase()}</span>
              </div>
              <div className="property-card-copy">
                <span className="eyebrow">Active property</span>
                <h2>{property.name}</h2>
                <p>
                  <MapPin size={15} /> {property.address_line}, {property.city}
                </p>
              </div>
              <footer>
                <span>{property.country_code}</span>
                <span>Added {new Date(property.created_at).toLocaleDateString()}</span>
              </footer>
            </article>
          ))}
        </section>
      )}
      {showForm && (
        <PropertyForm
          organization={organization}
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

function PropertyForm({
  organization,
  onClose,
  onCreated,
}: {
  organization: Organization;
  onClose: () => void;
  onCreated: () => Promise<void>;
}) {
  const [form, setForm] = useState({ name: "", address_line: "", city: "", country_code: "NG" });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      await api.request<Property>(
        "/properties",
        { method: "POST", body: JSON.stringify(form) },
        organization.id,
      );
      await onCreated();
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Could not add property");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="modal-backdrop" role="presentation">
      <section className="modal" role="dialog" aria-modal="true" aria-label="Add a property">
        <button className="modal-close" onClick={onClose} aria-label="Close">
          <X size={19} />
        </button>
        <span className="eyebrow">Portfolio expansion</span>
        <h2>Add a property</h2>
        <p className="muted">Create the operational record now. Units and tenancies can follow.</p>
        <form onSubmit={(event) => void submit(event)}>
          <label>
            Property name
            <input
              required
              minLength={2}
              value={form.name}
              onChange={(event) => setForm({ ...form, name: event.target.value })}
              placeholder="Marina Court"
            />
          </label>
          <label>
            Street address
            <input
              required
              value={form.address_line}
              onChange={(event) => setForm({ ...form, address_line: event.target.value })}
              placeholder="8 Harbour Road"
            />
          </label>
          <div className="form-row">
            <label>
              City
              <input
                required
                value={form.city}
                onChange={(event) => setForm({ ...form, city: event.target.value })}
                placeholder="Lagos"
              />
            </label>
            <label>
              Country code
              <input
                required
                minLength={2}
                maxLength={2}
                value={form.country_code}
                onChange={(event) =>
                  setForm({ ...form, country_code: event.target.value.toUpperCase() })
                }
              />
            </label>
          </div>
          {error && <p className="form-error">{error}</p>}
          <div className="modal-actions">
            <button type="button" className="button button-secondary" onClick={onClose}>
              Cancel
            </button>
            <button className="button button-primary" disabled={busy}>
              {busy ? "Adding…" : "Add property"}
            </button>
          </div>
        </form>
      </section>
    </div>
  );
}
