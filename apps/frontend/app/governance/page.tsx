"use client";

import {useEffect, useMemo, useState} from "react";
import {
  AlertTriangle,
  Bot,
  CheckCircle2,
  Clock3,
  FileCheck2,
  ShieldCheck,
} from "lucide-react";
import Shell from "@/components/Shell";
import {Card, PageHeader} from "@/components/Page";
import {api} from "@/lib/api";
import styles from "./governance.module.css";

type ReviewItem = {
  id: string;
  title: string;
  summary: string;
  risk_level: string;
  classification: string;
  classification_rank: number;
  trust_score: number;
  source: string;
  provenance: string;
  review_age_hours: number;
  policy_relevance: string;
  ai_eligible_if_approved: boolean;
  authority_level: string;
};

type ReviewDetail = ReviewItem & {
  extracted_facts: string[];
  conflicts: string[];
  missing_information: string[];
  sources: {filename: string; mime_type: string; locator: string; excerpt: string}[];
  access_control: string;
  intended_usage: string;
  what_changes_if_approved: string;
};

type QueueResponse = {
  summary: {
    pending_reviews: number;
    critical_items: number;
    oldest_pending_hours: number;
    ai_eligible_items: number;
  };
  reviewer: {id: string; name: string; email: string};
  review_queue: ReviewItem[];
};

const checklistLabels = {
  provenance_verified: "Provenance verified",
  classification_confirmed: "Classification confirmed",
  policy_authority_confirmed: "Policy authority confirmed",
  conflicts_reviewed: "Conflicts reviewed",
  ai_eligibility_appropriate: "AI eligibility appropriate",
};

type ChecklistKey = keyof typeof checklistLabels;
type Action = "approve_publish" | "return_correction" | "reject";

function ageLabel(hours: number) {
  if (hours < 1) return "Less than 1 hour";
  if (hours < 24) return `${hours}h`;
  return `${Math.floor(hours / 24)}d ${hours % 24}h`;
}

export default function Governance() {
  const [data, setData] = useState<QueueResponse>();
  const [selectedId, setSelectedId] = useState("");
  const [detail, setDetail] = useState<ReviewDetail>();
  const [checklist, setChecklist] = useState<Record<ChecklistKey, boolean>>({
    provenance_verified: false,
    classification_confirmed: false,
    policy_authority_confirmed: false,
    conflicts_reviewed: false,
    ai_eligibility_appropriate: false,
  });
  const [action, setAction] = useState<Action>("approve_publish");
  const [rationale, setRationale] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [previewTimestamp, setPreviewTimestamp] = useState("");

  async function loadQueue(preferredId = "") {
    const response = await api<QueueResponse>("/governance");
    setData(response);
    const nextId = preferredId || response.review_queue[0]?.id || "";
    setSelectedId(nextId);
    if (!nextId) setDetail(undefined);
  }

  useEffect(() => {
    loadQueue().catch((caught) =>
      setError(caught instanceof Error ? caught.message : "Unable to load governance queue."),
    );
  }, []);

  useEffect(() => {
    if (!selectedId) return;
    setDetail(undefined);
    setChecklist((current) =>
      Object.fromEntries(Object.keys(current).map((key) => [key, false])) as Record<ChecklistKey, boolean>,
    );
    setRationale("");
    setMessage("");
    api<ReviewDetail>(`/governance/${selectedId}`)
      .then(setDetail)
      .catch((caught) =>
        setError(caught instanceof Error ? caught.message : "Unable to load review details."),
      );
  }, [selectedId]);

  useEffect(() => {
    setPreviewTimestamp(new Date().toLocaleString());
  }, [selectedId, action, rationale]);

  const checklistComplete = useMemo(
    () => Object.values(checklist).every(Boolean),
    [checklist],
  );

  async function submitReview() {
    if (!detail) return;
    setBusy(true);
    setError("");
    try {
      await api(`/knowledge/${detail.id}/review`, {
        method: "POST",
        body: JSON.stringify({action, rationale, checklist}),
      });
      setMessage(
        action === "approve_publish"
          ? "Knowledge Card approved and published."
          : action === "return_correction"
            ? "Knowledge Card returned for correction."
            : "Knowledge Card rejected.",
      );
      await loadQueue();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Review action failed.");
    } finally {
      setBusy(false);
    }
  }

  const summary = data?.summary;
  return (
    <Shell>
      <PageHeader
        eyebrow="Governed knowledge"
        title="Governance Review"
        description="Prioritize evidence risk, inspect provenance, and make accountable publication decisions."
      />

      <div className={styles.truthLabel}>
        <Bot size={20} />
        <div>
          <strong>Human governance boundary</strong>
          <span>AI may organize evidence and flag issues. It cannot publish governed knowledge.</span>
        </div>
      </div>

      <section className={styles.metrics} aria-label="Governance executive summary">
        <Card><span>Pending reviews</span><strong>{summary?.pending_reviews ?? "—"}</strong><FileCheck2 /></Card>
        <Card><span>Critical items</span><strong>{summary?.critical_items ?? "—"}</strong><AlertTriangle /></Card>
        <Card><span>Oldest pending item</span><strong>{summary ? ageLabel(summary.oldest_pending_hours) : "—"}</strong><Clock3 /></Card>
        <Card><span>AI-eligible items</span><strong>{summary?.ai_eligible_items ?? "—"}</strong><Bot /></Card>
      </section>

      {error ? <div className={styles.error}>{error}</div> : null}
      {message ? <div className={styles.success}>{message}</div> : null}

      <div className={styles.workspace}>
        <section className={styles.queue} aria-label="Risk-prioritized review queue">
          <div className={styles.sectionHeading}>
            <div><span>Review queue</span><h2>Risk-prioritized evidence</h2></div>
            <small>Critical first</small>
          </div>
          {data?.review_queue.map((item, index) => (
            <button
              className={`${styles.queueItem} ${selectedId === item.id ? styles.selected : ""}`}
              key={item.id}
              onClick={() => setSelectedId(item.id)}
            >
              <div className={styles.queueTop}>
                <span className={`${styles.risk} ${styles[item.risk_level]}`}>{item.risk_level}</span>
                <span>#{index + 1} priority</span>
              </div>
              <strong>{item.title}</strong>
              <p>{item.summary}</p>
              <div className={styles.queueMeta}>
                <span>{item.classification}</span>
                <span>{item.trust_score}% trust</span>
                <span>{ageLabel(item.review_age_hours)} pending</span>
                <span>{item.ai_eligible_if_approved ? "AI eligible" : "AI excluded"}</span>
              </div>
              <div className={styles.source}><b>{item.source}</b><span>{item.provenance}</span></div>
              <div className={styles.policy}>{item.policy_relevance}</div>
            </button>
          ))}
          {data?.review_queue.length === 0 ? (
            <Card><p className="muted">No Knowledge Cards currently require review.</p></Card>
          ) : null}
        </section>

        <section className={styles.detail} aria-live="polite">
          {detail ? (
            <>
              <div className={styles.detailHeader}>
                <div><span>Review details</span><h2>{detail.title}</h2></div>
                <span className={`${styles.risk} ${styles[detail.risk_level]}`}>{detail.risk_level}</span>
              </div>

              <div className={styles.controlStrip}>
                <div><span>Classification</span><strong>{detail.classification} · {detail.classification_rank}</strong></div>
                <div><span>Access</span><strong>{detail.access_control}</strong></div>
                <div><span>Authority</span><strong>{detail.authority_level.replaceAll("_", " ")}</strong></div>
              </div>

              <div className={styles.detailGrid}>
                <InfoList title="Extracted facts" values={detail.extracted_facts} tone="fact" />
                <InfoList title="Conflicts" values={detail.conflicts} tone="conflict" />
                <InfoList title="Missing information" values={detail.missing_information} tone="missing" />
              </div>

              <div className={styles.provenancePanel}>
                <h3>Provenance and source</h3>
                {detail.sources.map((source) => (
                  <div key={`${source.filename}-${source.locator}`}>
                    <strong>{source.filename}</strong><span>{source.mime_type} · {source.locator}</span><p>{source.excerpt}</p>
                  </div>
                ))}
              </div>

              <div className={styles.usageGrid}>
                <div><span>Intended Decision Intelligence usage</span><p>{detail.intended_usage}</p></div>
                <div className={styles.changePanel}><span>What changes if approved?</span><p>{detail.what_changes_if_approved}</p></div>
              </div>

              <div className={styles.reviewPanel}>
                <div>
                  <h3>Governance checklist</h3>
                  <div className={styles.checklist}>
                    {(Object.entries(checklistLabels) as [ChecklistKey, string][]).map(([key, label]) => (
                      <label key={key}><input type="checkbox" checked={checklist[key]} onChange={(event) => setChecklist({...checklist, [key]: event.target.checked})} /><span>{label}</span></label>
                    ))}
                  </div>
                </div>
                <div>
                  <h3>Governed lifecycle action</h3>
                  <label className={styles.field}>Proposed action<select value={action} onChange={(event) => setAction(event.target.value as Action)}><option value="approve_publish">Approve and publish</option><option value="return_correction">Return for correction</option><option value="reject">Reject</option></select></label>
                  <label className={styles.field}>Human rationale<textarea value={rationale} onChange={(event) => setRationale(event.target.value)} placeholder="Explain the evidence and governance basis for this action." /></label>
                </div>
              </div>

              <div className={styles.auditPreview}>
                <ShieldCheck size={22} />
                <div><span>Audit preview</span><strong>{data?.reviewer.name || "Authenticated reviewer"}</strong><p>{action.replaceAll("_", " ")} · {rationale || "Rationale required"} · {previewTimestamp || "Timestamp prepared at review"}</p></div>
              </div>
              <button className="btn primary" disabled={busy || !checklistComplete || rationale.trim().length < 10} onClick={() => void submitReview()}>
                <CheckCircle2 size={17} /> {busy ? "Recording governed action…" : "Record human review action"}
              </button>
            </>
          ) : (
            <Card><p className="muted">Select an item to inspect its governed review details.</p></Card>
          )}
        </section>
      </div>
    </Shell>
  );
}

function InfoList({title, values, tone}: {title: string; values: string[]; tone: string}) {
  return <div className={`${styles.infoList} ${styles[tone]}`}><h3>{title}</h3>{values.length ? <ul>{values.map((value) => <li key={value}>{value}</li>)}</ul> : <p>No items recorded.</p>}</div>;
}
