"use client";

import Link from "next/link";
import {useParams} from "next/navigation";
import {useEffect, useState} from "react";
import {
  AlertTriangle,
  ArrowLeft,
  BookOpen,
  Building2,
  CalendarDays,
  CheckCircle2,
  Clock3,
  FileCheck2,
  MapPin,
  RefreshCw,
  Scale,
  ShieldCheck,
  UserRound,
} from "lucide-react";
import Shell from "@/components/Shell";
import DashboardWidget from "@/components/dashboard/DashboardWidget";
import DecisionScoreCard from "@/components/decision/DecisionScoreCard";
import ReadinessBreakdown from "@/components/decision/ReadinessBreakdown";
import {api} from "@/lib/api";
import styles from "./DecisionWorkspace.module.css";

type Decision = {
  id: string;
  title: string;
  question: string;
  status: string;
  recommendation: string;
  confidence: number;
  supplier_name: string;
  supplier_category: string;
  supplier_location: string;
  owner_name: string;
  due_date: string | null;
  priority: string;
  risk_level: string;
  decision_type: string;
  business_unit: string;
  readiness_score: number;
  readiness_status: string;
  created_at: string;
  updated_at: string;
};

type KnowledgeCard = {
  id: string;
  knowledge_card_id: string;
  relationship_type: string;
  selection_rationale: string;
  snapshot_title: string;
  snapshot_content: string;
  snapshot_knowledge_type: string;
  snapshot_approval_status: string;
  snapshot_authority_level: string;
  snapshot_trust_score: number;
  snapshot_ai_usage_allowed: boolean;
  selected_at: string;
  removed_at: string | null;
  removal_rationale: string | null;
};

type AvailableEvidence = {
  id: string;
  title: string;
  summary: string;
  knowledge_type: string;
  authority_level: string;
  trust_score: number;
  ai_usage_allowed: boolean;
  selected: boolean;
  chunks: {id: string; chunk_index: number; content: string}[];
};

type AuditEvent = {
  id: string;
  event_type: string;
  description: string;
  created_at: string;
};

type WorkspaceResponse = {
  decision: Decision;
  business_concept: {
    id: string;
    name: string;
    description: string;
  } | null;
  evidence: KnowledgeCard[];
  activity: AuditEvent[];
  workspace_summary: {
    evidence_count: number;
    approved_count: number;
    trusted_count: number;
    governed_count: number;
    confidence_percent: number;
    missing_information: string[];
    control_areas: string[];
    calculation: Record<
      string,
      {points: number; possible: number; count: number}
    >;
    allowed_transitions: string[];
  };
};

const tabs = [
  "Overview",
  "Evidence",
  "Timeline",
  "AI Analysis",
  "Approvals",
  "Reports",
] as const;

export default function DecisionWorkspace() {
  const params = useParams<{id: string}>();
  const [data, setData] = useState<WorkspaceResponse>();
  const [activeTab, setActiveTab] =
    useState<(typeof tabs)[number]>("Overview");
  const [error, setError] = useState("");
  const [refreshing, setRefreshing] = useState(false);
  const [updatingStatus, setUpdatingStatus] = useState(false);
  const [available, setAvailable] = useState<AvailableEvidence[]>([]);
  const [history, setHistory] = useState<KnowledgeCard[]>([]);
  const [evidenceBusy, setEvidenceBusy] = useState(false);
  const [removingEvidence, setRemovingEvidence] = useState<string>();
  const [removalRationale, setRemovalRationale] = useState("");
  const [drafts, setDrafts] = useState<
    Record<string, {relationship: string; rationale: string}>
  >({});

  async function load() {
    setRefreshing(true);
    try {
      setError("");
      const [workspace, eligible] = await Promise.all([
        api<WorkspaceResponse>(`/decisions/${params.id}`),
        api<AvailableEvidence[]>(
          `/decisions/${params.id}/available-evidence`,
        ),
      ]);
      setData(workspace);
      setAvailable(eligible);
      try {
        setHistory(
          await api<KnowledgeCard[]>(
            `/decisions/${params.id}/evidence/history`,
          ),
        );
      } catch {
        setHistory([]);
      }
    } catch (caught) {
      setError(
        caught instanceof Error
          ? caught.message
          : "Unable to load the decision workspace.",
      );
    } finally {
      setRefreshing(false);
    }
  }

  useEffect(() => {
    void load();
  }, [params.id]);

  async function changeStatus(status: string) {
    setUpdatingStatus(true);
    try {
      await api(`/decisions/${params.id}/status`, {
        method: "PATCH",
        body: JSON.stringify({status}),
      });
      await load();
    } catch (caught) {
      setError(
        caught instanceof Error
          ? caught.message
          : "Unable to update decision status.",
      );
    } finally {
      setUpdatingStatus(false);
    }
  }

  async function selectEvidence(card: AvailableEvidence) {
    const draft = drafts[card.id] || {
      relationship: "supporting",
      rationale: "",
    };
    if (draft.rationale.trim().length < 3) {
      setError("Explain why this evidence applies before selecting it.");
      return;
    }
    setEvidenceBusy(true);
    try {
      setError("");
      await api(`/decisions/${params.id}/evidence`, {
        method: "POST",
        body: JSON.stringify({
          knowledge_card_id: card.id,
          relationship_type: draft.relationship,
          rationale: draft.rationale,
        }),
      });
      await load();
    } catch (caught) {
      setError(
        caught instanceof Error
          ? caught.message
          : "Unable to select decision evidence.",
      );
    } finally {
      setEvidenceBusy(false);
    }
  }

  async function removeEvidence(evidence: KnowledgeCard) {
    if (removalRationale.trim().length < 3) {
      setError("Explain why this evidence should be removed.");
      return;
    }
    setEvidenceBusy(true);
    try {
      setError("");
      await api(`/decisions/${params.id}/evidence/${evidence.id}`, {
        method: "DELETE",
        body: JSON.stringify({rationale: removalRationale}),
      });
      setRemovingEvidence(undefined);
      setRemovalRationale("");
      await load();
    } catch (caught) {
      setError(
        caught instanceof Error
          ? caught.message
          : "Unable to remove decision evidence.",
      );
    } finally {
      setEvidenceBusy(false);
    }
  }

  if (!data && !error) {
    return (
      <Shell>
        <div className={styles.loading}>
          <RefreshCw className={styles.spin} size={22} />
          Loading decision workspace
        </div>
      </Shell>
    );
  }

  if (!data) {
    return (
      <Shell>
        <Link href="/decisions" className={styles.backLink}>
          <ArrowLeft size={15} />
          Back to Decision Center
        </Link>
        <div className={styles.error}>{error}</div>
      </Shell>
    );
  }

  const {decision, workspace_summary: summary} = data;
  const overdue =
    decision.due_date &&
    new Date(`${decision.due_date}T23:59:59`) < new Date() &&
    !["approved", "rejected", "closed"].includes(decision.status);

  const readinessTone =
    decision.readiness_score >= 80
      ? "positive"
      : decision.readiness_score >= 50
      ? "warning"
      : "critical";

  const riskTone = ["critical", "high"].includes(decision.risk_level)
    ? "critical"
    : decision.risk_level === "medium"
    ? "warning"
    : "positive";

  return (
    <Shell>
      <Link href="/decisions" className={styles.backLink}>
        <ArrowLeft size={15} />
        Back to Decision Center
      </Link>

      <header className={styles.hero}>
        <div className={styles.heroIdentity}>
          <div className={styles.supplierIcon}>
            <Building2 size={25} strokeWidth={1.7} />
          </div>
          <div>
            <div className={styles.eyebrow}>
              {decision.supplier_category}
            </div>
            <h1>{decision.supplier_name || decision.title}</h1>
            <p>{decision.title}</p>
          </div>
        </div>

        <div className={styles.heroActions}>
          <button
            className={styles.refreshButton}
            onClick={() => void load()}
            disabled={refreshing}
          >
            <RefreshCw
              size={15}
              className={refreshing ? styles.spin : ""}
            />
            Refresh
          </button>
          <select
            value={decision.status}
            onChange={(event) =>
              void changeStatus(event.target.value)
            }
            disabled={updatingStatus}
            className={styles.statusSelect}
            aria-label="Decision status"
          >
            <option value={decision.status}>
              {decision.status.replaceAll("_", " ")}
            </option>
            {summary.allowed_transitions.map((status) => (
              <option value={status} key={status}>
                {status.replaceAll("_", " ")}
              </option>
            ))}
          </select>
        </div>
      </header>

      {error ? <div className={styles.error}>{error}</div> : null}

      <section className={styles.scoreGrid}>
        <DecisionScoreCard
          label="Decision readiness"
          value={`${decision.readiness_score}%`}
          detail={decision.readiness_status.replaceAll("_", " ")}
          icon={FileCheck2}
          tone={readinessTone}
        />
        <DecisionScoreCard
          label="Risk level"
          value={decision.risk_level.toUpperCase()}
          detail={`${decision.priority} priority`}
          icon={AlertTriangle}
          tone={riskTone}
        />
        <DecisionScoreCard
          label="Confidence"
          value={`${summary.confidence_percent}%`}
          detail="Recorded decision confidence"
          icon={ShieldCheck}
          tone={
            summary.confidence_percent >= 80 ? "positive" : "neutral"
          }
        />
        <DecisionScoreCard
          label="Evidence"
          value={String(summary.evidence_count)}
          detail={`${summary.approved_count} approved`}
          icon={BookOpen}
          tone={summary.evidence_count >= 4 ? "positive" : "warning"}
        />
      </section>

      <section className={styles.metaBar}>
        <div>
          <UserRound size={15} />
          <span>
            <b>Owner</b>
            {decision.owner_name || "Unassigned"}
          </span>
        </div>
        <div>
          <CalendarDays size={15} />
          <span>
            <b>Due date</b>
            {decision.due_date || "Not scheduled"}
          </span>
        </div>
        <div>
          <MapPin size={15} />
          <span>
            <b>Location</b>
            {decision.supplier_location || "Not provided"}
          </span>
        </div>
        <div>
          <Scale size={15} />
          <span>
            <b>Business unit</b>
            {decision.business_unit}
          </span>
        </div>
        {overdue ? (
          <div className={styles.overdue}>
            <Clock3 size={15} />
            <span>
              <b>Attention</b>
              Review is overdue
            </span>
          </div>
        ) : null}
      </section>

      <nav className={styles.tabs} aria-label="Decision workspace sections">
        {tabs.map((tab) => (
          <button
            key={tab}
            className={activeTab === tab ? styles.activeTab : ""}
            onClick={() => setActiveTab(tab)}
          >
            {tab}
          </button>
        ))}
      </nav>

      {activeTab === "Overview" ? (
        <section className={styles.workspaceGrid}>
          <div className={styles.mainColumn}>
            <DashboardWidget
              eyebrow="Decision context"
              title="Decision question"
            >
              <p className={styles.question}>{decision.question}</p>
            </DashboardWidget>

            <DashboardWidget
              eyebrow="Governed recommendation"
              title="Executive recommendation"
            >
              <div className={styles.recommendation}>
                <ShieldCheck size={20} />
                <p>{decision.recommendation}</p>
              </div>
            </DashboardWidget>

            <DashboardWidget
              eyebrow="Evidence baseline"
              title="Readiness calculation"
            >
              <ReadinessBreakdown calculation={summary.calculation} />
            </DashboardWidget>
          </div>

          <aside className={styles.sideColumn}>
            <DashboardWidget
              eyebrow="Decision attention"
              title="Missing information"
            >
              {summary.missing_information.length ? (
                <div className={styles.findingList}>
                  {summary.missing_information.map((item) => (
                    <div className={styles.finding} key={item}>
                      <AlertTriangle size={15} />
                      <span>{item}</span>
                    </div>
                  ))}
                </div>
              ) : (
                <div className={styles.clearState}>
                  <CheckCircle2 size={21} />
                  <strong>Evidence baseline complete</strong>
                  <span>No missing information is currently recorded.</span>
                </div>
              )}
            </DashboardWidget>

            <DashboardWidget
              eyebrow="Expected coverage"
              title="Control areas"
            >
              <div className={styles.controlList}>
                {summary.control_areas.map((item) => (
                  <div key={item}>
                    <CheckCircle2 size={14} />
                    <span>{item}</span>
                  </div>
                ))}
              </div>
            </DashboardWidget>

            <DashboardWidget
              eyebrow="Business classification"
              title="Decision profile"
            >
              <dl className={styles.profile}>
                <div>
                  <dt>Decision type</dt>
                  <dd>{decision.decision_type.replaceAll("_", " ")}</dd>
                </div>
                <div>
                  <dt>Business concept</dt>
                  <dd>{data.business_concept?.name || "Not assigned"}</dd>
                </div>
                <div>
                  <dt>Created</dt>
                  <dd>
                    {new Date(decision.created_at).toLocaleDateString()}
                  </dd>
                </div>
                <div>
                  <dt>Last updated</dt>
                  <dd>
                    {new Date(decision.updated_at).toLocaleString()}
                  </dd>
                </div>
              </dl>
            </DashboardWidget>
          </aside>
        </section>
      ) : null}

      {activeTab === "Evidence" ? (
        <section className={styles.evidenceWorkspace}>
          <DashboardWidget
            eyebrow="Immutable snapshots"
            title={`Active decision evidence (${data.evidence.length})`}
          >
            {data.evidence.length ? (
              <div className={styles.evidenceList}>
                {data.evidence.map((card) => (
                  <article className={styles.evidenceCard} key={card.id}>
                    <div className={styles.evidenceHeader}>
                      <div>
                        <strong>{card.snapshot_title}</strong>
                        <span>
                          {card.snapshot_knowledge_type.replaceAll("_", " ")}
                        </span>
                      </div>
                      <div className={styles.evidenceBadges}>
                        <span>{card.relationship_type}</span>
                        <span>
                          {Math.round(card.snapshot_trust_score * 100)}% trust
                        </span>
                      </div>
                    </div>
                    <p>{card.snapshot_content}</p>
                    <p className={styles.rationale}>
                      <b>Selection rationale:</b> {card.selection_rationale}
                    </p>
                    <div className={styles.evidenceMeta}>
                      <span>
                        Selected {new Date(card.selected_at).toLocaleString()}
                      </span>
                      <button
                        className={styles.removeEvidence}
                        disabled={evidenceBusy}
                        onClick={() => {
                          setRemovingEvidence(card.id);
                          setRemovalRationale("");
                        }}
                      >
                        Remove
                      </button>
                    </div>
                    {removingEvidence === card.id ? (
                      <div className={styles.removalControls}>
                        <input
                          autoFocus
                          value={removalRationale}
                          placeholder="Why should this evidence be removed?"
                          aria-label={`Removal rationale for ${card.snapshot_title}`}
                          onChange={(event) =>
                            setRemovalRationale(event.target.value)
                          }
                        />
                        <button
                          disabled={evidenceBusy}
                          onClick={() => void removeEvidence(card)}
                        >
                          Confirm removal
                        </button>
                        <button
                          disabled={evidenceBusy}
                          onClick={() => setRemovingEvidence(undefined)}
                        >
                          Cancel
                        </button>
                      </div>
                    ) : null}
                  </article>
                ))}
              </div>
            ) : (
              <div className={styles.emptyPanel}>
                Select governed knowledge below to establish the evidence
                supporting this Decision.
              </div>
            )}
          </DashboardWidget>

          <DashboardWidget
            eyebrow="Available governed knowledge"
            title={`Eligible evidence (${available.length})`}
          >
            <div className={styles.evidenceList}>
              {available.map((card) => {
                const draft = drafts[card.id] || {
                  relationship: "supporting",
                  rationale: "",
                };
                return (
                  <article className={styles.evidenceCard} key={card.id}>
                    <div className={styles.evidenceHeader}>
                      <div>
                        <strong>{card.title}</strong>
                        <span>{card.knowledge_type.replaceAll("_", " ")}</span>
                      </div>
                      <div className={styles.evidenceBadges}>
                        <span>{Math.round(card.trust_score * 100)}% trust</span>
                        {card.selected ? <span>Selected</span> : null}
                      </div>
                    </div>
                    <p>{card.summary}</p>
                    {!card.selected ? (
                      <div className={styles.selectionControls}>
                        <select
                          value={draft.relationship}
                          aria-label={`Relationship for ${card.title}`}
                          onChange={(event) =>
                            setDrafts((current) => ({
                              ...current,
                              [card.id]: {
                                ...draft,
                                relationship: event.target.value,
                              },
                            }))
                          }
                        >
                          {[
                            "supporting",
                            "opposing",
                            "contextual",
                            "risk",
                            "constraint",
                          ].map((relationship) => (
                            <option key={relationship} value={relationship}>
                              {relationship}
                            </option>
                          ))}
                        </select>
                        <input
                          value={draft.rationale}
                          placeholder="Why is this evidence relevant?"
                          aria-label={`Selection rationale for ${card.title}`}
                          onChange={(event) =>
                            setDrafts((current) => ({
                              ...current,
                              [card.id]: {
                                ...draft,
                                rationale: event.target.value,
                              },
                            }))
                          }
                        />
                        <button
                          disabled={evidenceBusy}
                          onClick={() => void selectEvidence(card)}
                        >
                          Select evidence
                        </button>
                      </div>
                    ) : null}
                  </article>
                );
              })}
            </div>
          </DashboardWidget>

          {history.some((item) => item.removed_at) ? (
            <DashboardWidget
              eyebrow="Retained history"
              title="Removed evidence"
            >
              <div className={styles.evidenceList}>
                {history
                  .filter((item) => item.removed_at)
                  .map((item) => (
                    <article className={styles.evidenceCard} key={item.id}>
                      <div className={styles.evidenceHeader}>
                        <strong>{item.snapshot_title}</strong>
                        <div className={styles.evidenceBadges}>
                          <span>Removed</span>
                          <span>{item.relationship_type}</span>
                        </div>
                      </div>
                      <p>{item.removal_rationale}</p>
                      <div className={styles.evidenceMeta}>
                        Removed {new Date(item.removed_at!).toLocaleString()}
                      </div>
                    </article>
                  ))}
              </div>
            </DashboardWidget>
          ) : null}
        </section>
      ) : null}

      {activeTab === "Timeline" ? (
        <DashboardWidget
          eyebrow="Permanent audit trail"
          title={`Decision timeline (${data.activity.length})`}
        >
          {data.activity.length ? (
            <div className={styles.timeline}>
              {data.activity.map((event) => (
                <article key={event.id}>
                  <span className={styles.timelineDot} />
                  <div>
                    <strong>
                      {event.event_type
                        .replace(/([a-z])([A-Z])/g, "$1 $2")
                        .replaceAll("_", " ")}
                    </strong>
                    <p>{event.description}</p>
                    <time>
                      {new Date(event.created_at).toLocaleString()}
                    </time>
                  </div>
                </article>
              ))}
            </div>
          ) : (
            <div className={styles.emptyPanel}>
              Timeline events will appear as the decision progresses.
            </div>
          )}
        </DashboardWidget>
      ) : null}

      {["AI Analysis", "Approvals", "Reports"].includes(activeTab) ? (
        <DashboardWidget
          eyebrow="Release 0.5 roadmap"
          title={`${activeTab} workspace`}
        >
          <div className={styles.futurePanel}>
            <ShieldCheck size={24} />
            <strong>{activeTab} foundation is ready</strong>
            <p>
              This section is reserved in the unified workspace and will be
              activated in the next Release 0.5 increments.
            </p>
          </div>
        </DashboardWidget>
      ) : null}
    </Shell>
  );
}
