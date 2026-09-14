import { useEffect, useRef, useState } from "react";
import { Download, FileText, Paperclip, Trash2, UploadCloud } from "lucide-react";

import { EmptyState, LoadingBlock, PageHeader } from "../components/PageHeader";
import { api } from "../lib/api";
import type { DocumentRecord, Organization, Property } from "../types";

function formatBytes(value: number): string {
  if (value < 1024) return `${value} B`;
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`;
  return `${(value / (1024 * 1024)).toFixed(1)} MB`;
}

export function DocumentsPage({ organization }: { organization: Organization }) {
  const [documents, setDocuments] = useState<DocumentRecord[] | null>(null);
  const [properties, setProperties] = useState<Property[]>([]);
  const [propertyId, setPropertyId] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const input = useRef<HTMLInputElement>(null);

  useEffect(() => {
    void load();
  }, [organization.id]);

  async function load() {
    try {
      const [nextDocuments, nextProperties] = await Promise.all([
        api.request<DocumentRecord[]>("/documents", {}, organization.id),
        api.request<Property[]>("/properties", {}, organization.id),
      ]);
      setDocuments(nextDocuments);
      setProperties(nextProperties);
      setPropertyId((current) => current || nextProperties[0]?.id || "");
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Documents unavailable");
    }
  }

  async function upload(file: File) {
    if (!propertyId) return;
    setBusy(true);
    setError("");
    const form = new FormData();
    form.set("file", file);
    form.set("resource_type", "property");
    form.set("resource_id", propertyId);
    try {
      await api.request("/documents", { method: "POST", body: form }, organization.id);
      await load();
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Upload failed");
    } finally {
      setBusy(false);
      if (input.current) input.current.value = "";
    }
  }

  async function download(document: DocumentRecord) {
    try {
      const blob = await api.download(`/documents/${document.id}/content`, organization.id);
      const url = URL.createObjectURL(blob);
      const anchor = window.document.createElement("a");
      anchor.href = url;
      anchor.download = document.file_name;
      anchor.click();
      URL.revokeObjectURL(url);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Download failed");
    }
  }

  async function remove(document: DocumentRecord) {
    if (!window.confirm(`Delete ${document.file_name}? This cannot be undone.`)) return;
    try {
      await api.request(`/documents/${document.id}`, { method: "DELETE" }, organization.id);
      await load();
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Delete failed");
    }
  }

  if (!documents && !error) return <LoadingBlock />;

  return (
    <>
      <PageHeader
        eyebrow="Evidence library"
        title="Documents"
        description="Attach the records that make every property decision traceable."
      />
      {error && <div className="inline-alert">{error}</div>}
      <section className="upload-strip">
        <div>
          <UploadCloud size={24} />
          <div>
            <strong>Upload a property document</strong>
            <span>PDF, image, spreadsheet, or text up to 10 MB.</span>
          </div>
        </div>
        <div className="upload-actions">
          <select
            aria-label="Property"
            value={propertyId}
            onChange={(event) => setPropertyId(event.target.value)}
            disabled={properties.length === 0}
          >
            {properties.length === 0 && <option>Add a property first</option>}
            {properties.map((property) => (
              <option value={property.id} key={property.id}>
                {property.name}
              </option>
            ))}
          </select>
          <label className={`button button-primary ${busy || !propertyId ? "disabled" : ""}`}>
            <Paperclip size={17} />
            {busy ? "Uploading…" : "Choose file"}
            <input
              ref={input}
              type="file"
              disabled={busy || !propertyId}
              onChange={(event) => event.target.files?.[0] && void upload(event.target.files[0])}
            />
          </label>
        </div>
      </section>
      {documents?.length === 0 ? (
        <EmptyState>
          <FileText size={30} />
          <h2>No documents yet</h2>
          <p>Property evidence, agreements, and inspection records will appear here.</p>
        </EmptyState>
      ) : (
        <section className="panel document-list">
          {documents?.map((document) => (
            <div className="document-row" key={document.id}>
              <span className="file-icon">
                <FileText size={20} />
              </span>
              <div>
                <strong>{document.file_name}</strong>
                <span>
                  {properties.find((property) => property.id === document.resource_id)?.name ??
                    document.resource_type}{" "}
                  · {formatBytes(document.size_bytes)}
                </span>
              </div>
              <time>{new Date(document.created_at).toLocaleDateString()}</time>
              <button title="Download" onClick={() => void download(document)}>
                <Download size={17} />
              </button>
              <button className="danger-icon" title="Delete" onClick={() => void remove(document)}>
                <Trash2 size={17} />
              </button>
            </div>
          ))}
        </section>
      )}
    </>
  );
}
