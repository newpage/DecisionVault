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

type DecisionReview = {
  id: string;
  sequence: number;
  review_type: string;
  assigned_reviewer_membership_id: string;
  assigned_reviewer_name: string;
  assigned_reviewer_email: string;
  assigned_reviewer_organization: string;
  status: string;
  conclusion: string | null;
  summary: string;
  freshness_status: string;
  submitted_at: string | null;
  evidence_ids: string[];
};

type ReviewerCandidate = {
  membership_id: string;
  display_name: string;
  email: string;
  organization_name: string;
  role_labels: string[];
  responsibility: "decision_reviewer";
};

type ReviewerCandidatePage = {
  items: ReviewerCandidate[];
  offset: number;
  limit: number;
  total: number;
};

type ReviewFinding = {
  id: string;
  review_id: string;
  title: string;
  description: string;
  severity: string;
  required_response: boolean;
  status: string;
};

type ApprovalCondition = {
  id: string;
  condition_text: string;
  responsible_party: string;
  due_date: string | null;
  status: string;
};

type ReviewWorkspace = {
  reviews: DecisionReview[];
  findings: ReviewFinding[];
  approval_actions: {id: string; action: string; rationale: string; created_at: string}[];
  conditions: ApprovalCondition[];
  capabilities: Record<string, boolean>;
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
  const [reviewWorkspace, setReviewWorkspace] = useState<ReviewWorkspace>();
  const [reviewBusy, setReviewBusy] = useState(false);
  const [reviewerCandidates, setReviewerCandidates] = useState<ReviewerCandidate[]>([]);
  const [selectedMembershipId, setSelectedMembershipId] = useState("");
  const [candidateQuery, setCandidateQuery] = useState("");
  const [candidateLoading, setCandidateLoading] = useState(false);
  const [candidateMessage, setCandidateMessage] = useState("");
  const [reviewType, setReviewType] = useState("final_approval");
  const [assignmentRationale, setAssignmentRationale] = useState("");
  const [reviewRationale, setReviewRationale] = useState("");
  const [findingTitle, setFindingTitle] = useState("");
  const [findingDescription, setFindingDescription] = useState("");
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
        setReviewWorkspace(
          await api<ReviewWorkspace>(
            `/decisions/${params.id}/review-workspace`,
          ),
        );
      } catch {
        setReviewWorkspace(undefined);
      }
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

  async function reviewAction(
    path: string,
    body?: object,
    method = "POST",
  ) {
    setReviewBusy(true);
    try {
      setError("");
      await api(`/decisions/${params.id}${path}`, {
        method,
        body: body ? JSON.stringify(body) : undefined,
      });
      await load();
    } catch (caught) {
      setError(
        caught instanceof Error
          ? caught.message
          : "Unable to update the governed review workflow.",
      );
    } finally {
      setReviewBusy(false);
    }
  }

  async function loadReviewerCandidates() {
    setCandidateLoading(true);
    setCandidateMessage("");
    try {
      const page = await api<ReviewerCandidatePage>(
        `/decisions/${params.id}/reviewer-candidates?responsibility=decision_reviewer&limit=20&query=${encodeURIComponent(candidateQuery.trim())}`,
      );
      setReviewerCandidates(page.items);
      if (!page.items.length) {
        setCandidateMessage("No eligible reviewers match this search.");
      }
    } catch (caught) {
      setReviewerCandidates([]);
      setCandidateMessage(
        caught instanceof Error
          ? caught.message
          : "Unable to load eligible reviewers.",
      );
    } finally {
      setCandidateLoading(false);
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
          <span className={styles.statusBadge}>
            {decision.status.replaceAll("_", " ")}
          </span>
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
            onClick={() => {
              setActiveTab(tab);
              if (tab === "Approvals" && reviewWorkspace?.capabilities.assign) {
                void loadReviewerCandidates();
              }
            }}
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

      {activeTab === "Approvals" ? (
        <section className={styles.approvalWorkspace}>
          {!reviewWorkspace ? (
            <DashboardWidget
              eyebrow="Access controlled"
              title="Review workspace"
            >
              <div className={styles.emptyPanel}>
                You do not have permission to view review and approval records.
              </div>
            </DashboardWidget>
          ) : (
            <>
              <DashboardWidget
                eyebrow="Governed workflow"
                title="Review controls"
              >
                <div className={styles.approvalControls}>
                  {reviewWorkspace.capabilities.assign ? (
                    <div className={styles.controlGroup}>
                      <strong>Assign a reviewer</strong>
                      <span className={styles.helperText}>
                        Eligible tenant members with governed Decision and evidence access.
                      </span>
                      <div className={styles.candidateSearch}>
                        <input
                          aria-label="Search eligible reviewers"
                          placeholder="Search by name, email, or organization"
                          value={candidateQuery}
                          onChange={(event) => setCandidateQuery(event.target.value)}
                          onKeyDown={(event) => {
                            if (event.key === "Enter") void loadReviewerCandidates();
                          }}
                        />
                        <button
                          disabled={candidateLoading}
                          onClick={() => void loadReviewerCandidates()}
                        >
                          {candidateLoading ? "Searching…" : "Search"}
                        </button>
                      </div>
                      {reviewerCandidates.length ? (
                        <div className={styles.candidateList} role="listbox" aria-label="Eligible reviewers">
                          {reviewerCandidates.map((candidate) => (
                            <button
                              key={candidate.membership_id}
                              type="button"
                              role="option"
                              aria-selected={selectedMembershipId === candidate.membership_id}
                              className={selectedMembershipId === candidate.membership_id ? styles.selectedCandidate : ""}
                              onClick={() => setSelectedMembershipId(candidate.membership_id)}
                            >
                              <strong>{candidate.display_name}</strong>
                              <span>{candidate.email}</span>
                              <span>{candidate.organization_name} · {candidate.role_labels.join(", ")}</span>
                            </button>
                          ))}
                        </div>
                      ) : (
                        <span className={styles.helperText}>
                          {candidateLoading ? "Loading eligible reviewers…" : candidateMessage || "Search to select an eligible reviewer."}
                        </span>
                      )}
                      <select
                        aria-label="Review type"
                        value={reviewType}
                        onChange={(event) => setReviewType(event.target.value)}
                      >
                        <option value="business">Business</option>
                        <option value="risk">Risk</option>
                        <option value="compliance">Compliance</option>
                        <option value="final_approval">Final approval</option>
                      </select>
                      <textarea
                        aria-label="Assignment rationale"
                        placeholder="Why is this member appropriate for this review?"
                        value={assignmentRationale}
                        onChange={(event) => setAssignmentRationale(event.target.value)}
                      />
                      <button
                        disabled={reviewBusy || !selectedMembershipId || assignmentRationale.trim().length < 3}
                        onClick={() =>
                          void reviewAction("/reviews", {
                            membership_id: selectedMembershipId,
                            review_type: reviewType,
                            rationale: assignmentRationale,
                          })
                        }
                      >
                        Assign review
                      </button>
                    </div>
                  ) : null}
                  {reviewWorkspace.capabilities.manage &&
                  decision.status === "evidence_collection" ? (
                    <button
                      className={styles.primaryAction}
                      disabled={reviewBusy}
                      onClick={() => void reviewAction("/submit-review")}
                    >
                      Submit for review
                    </button>
                  ) : null}
                  <div className={styles.controlGroup}>
                    <strong>Approval rationale</strong>
                    <textarea
                      aria-label="Approval rationale"
                      placeholder="Record the decision authority's rationale"
                      value={reviewRationale}
                      onChange={(event) =>
                        setReviewRationale(event.target.value)
                      }
                    />
                    <div className={styles.actionRow}>
                      {reviewWorkspace.capabilities.return_for_changes &&
                      decision.status === "in_review" ? (
                        <button
                          disabled={reviewBusy || reviewRationale.length < 3}
                          onClick={() =>
                            void reviewAction("/return-for-changes", {
                              rationale: reviewRationale,
                            })
                          }
                        >
                          Return for changes
                        </button>
                      ) : null}
                      {reviewWorkspace.capabilities.approve &&
                      ["in_review", "conditionally_approved"].includes(
                        decision.status,
                      ) ? (
                        <button
                          disabled={reviewBusy || reviewRationale.length < 3}
                          onClick={() =>
                            void reviewAction("/approve", {
                              rationale: reviewRationale,
                            })
                          }
                        >
                          Approve
                        </button>
                      ) : null}
                      {reviewWorkspace.capabilities.conditionally_approve &&
                      decision.status === "in_review" ? (
                        <button
                          disabled={reviewBusy || reviewRationale.length < 3}
                          onClick={() =>
                            void reviewAction("/conditionally-approve", {
                              rationale: reviewRationale,
                              conditions: [
                                {condition_text: reviewRationale},
                              ],
                            })
                          }
                        >
                          Approve with condition
                        </button>
                      ) : null}
                      {reviewWorkspace.capabilities.reject &&
                      decision.status === "in_review" ? (
                        <button
                          disabled={reviewBusy || reviewRationale.length < 3}
                          onClick={() =>
                            void reviewAction("/reject", {
                              rationale: reviewRationale,
                            })
                          }
                        >
                          Reject
                        </button>
                      ) : null}
                    </div>
                  </div>
                </div>
              </DashboardWidget>

              <DashboardWidget
                eyebrow="Assigned accountability"
                title={`Reviews (${reviewWorkspace.reviews.length})`}
              >
                <div className={styles.reviewList}>
                  {reviewWorkspace.reviews.map((review) => (
                    <article className={styles.reviewCard} key={review.id}>
                      <div className={styles.reviewHeader}>
                        <div>
                          <strong>
                            Review {review.sequence}: {review.review_type.replaceAll("_", " ")}
                          </strong>
                          <span>
                            Reviewer {review.assigned_reviewer_name} · {review.assigned_reviewer_organization}
                          </span>
                          <span>{review.assigned_reviewer_email}</span>
                        </div>
                        <div className={styles.evidenceBadges}>
                          <span>{review.status.replaceAll("_", " ")}</span>
                          <span>{review.freshness_status}</span>
                          <span>{review.evidence_ids.length} evidence</span>
                        </div>
                      </div>
                      {review.summary ? <p>{review.summary}</p> : null}
                      {reviewWorkspace.capabilities.assign && review.status === "assigned" ? (
                        <button
                          disabled={reviewBusy || !selectedMembershipId || assignmentRationale.trim().length < 3 || selectedMembershipId === review.assigned_reviewer_membership_id}
                          onClick={() => void reviewAction(
                            `/reviews/${review.id}/assignment`,
                            {membership_id: selectedMembershipId, rationale: assignmentRationale},
                            "PATCH",
                          )}
                        >
                          Reassign selected reviewer
                        </button>
                      ) : null}
                      {reviewWorkspace.capabilities.perform &&
                      review.status === "assigned" &&
                      review.submitted_at ? (
                        <button
                          disabled={reviewBusy}
                          onClick={() =>
                            void reviewAction(`/reviews/${review.id}/start`)
                          }
                        >
                          Start review
                        </button>
                      ) : null}
                      {reviewWorkspace.capabilities.perform &&
                      review.status === "in_progress" ? (
                        <div className={styles.findingControls}>
                          <input
                            aria-label="Finding title"
                            placeholder="Finding title"
                            value={findingTitle}
                            onChange={(event) => setFindingTitle(event.target.value)}
                          />
                          <textarea
                            aria-label="Finding description"
                            placeholder="Finding description"
                            value={findingDescription}
                            onChange={(event) => setFindingDescription(event.target.value)}
                          />
                          <button
                            disabled={reviewBusy || findingTitle.length < 3 || findingDescription.length < 3}
                            onClick={() => void reviewAction(`/reviews/${review.id}/findings`, {
                              finding_type: "comment",
                              severity: "medium",
                              title: findingTitle,
                              description: findingDescription,
                              required_response: false,
                            })}
                          >
                            Record finding
                          </button>
                          <button
                            disabled={reviewBusy || reviewRationale.length < 3}
                            onClick={() => void reviewAction(`/reviews/${review.id}/complete`, {
                              conclusion: "recommend_approve",
                              summary: reviewRationale,
                            })}
                          >
                            Complete and recommend approval
                          </button>
                        </div>
                      ) : null}
                    </article>
                  ))}
                </div>
              </DashboardWidget>

              <DashboardWidget
                eyebrow="Tracked exceptions"
                title={`Findings and conditions (${reviewWorkspace.findings.length + reviewWorkspace.conditions.length})`}
              >
                <div className={styles.reviewList}>
                  {reviewWorkspace.findings.map((finding) => (
                    <article className={styles.reviewCard} key={finding.id}>
                      <strong>{finding.title}</strong>
                      <span>{finding.severity} · {finding.status}</span>
                      <p>{finding.description}</p>
                      {finding.status === "open" && reviewWorkspace.capabilities.perform ? (
                        <button disabled={reviewBusy || reviewRationale.length < 3} onClick={() => void reviewAction(
                          `/reviews/${finding.review_id}/findings/${finding.id}`,
                          {status: "accepted", response: reviewRationale},
                          "PATCH",
                        )}>Accept finding</button>
                      ) : null}
                    </article>
                  ))}
                  {reviewWorkspace.conditions.map((condition) => (
                    <article className={styles.reviewCard} key={condition.id}>
                      <strong>{condition.condition_text}</strong>
                      <span>{condition.status} · {condition.responsible_party || "Unassigned"}</span>
                      {condition.status === "open" && reviewWorkspace.capabilities.manage ? (
                        <button disabled={reviewBusy || reviewRationale.length < 3} onClick={() => void reviewAction(
                          `/conditions/${condition.id}/satisfy`,
                          {response: reviewRationale},
                        )}>Mark satisfied</button>
                      ) : null}
                    </article>
                  ))}
                </div>
              </DashboardWidget>
            </>
          )}
        </section>
      ) : null}

      {["AI Analysis", "Reports"].includes(activeTab) ? (
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
