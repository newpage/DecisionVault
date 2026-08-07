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

type ExpectedOutcome = {
  id: string; title: string; description: string; measurement_type: string;
  baseline_value: number | null; target_value: number | null;
  target_min_value: number | null; target_max_value: number | null;
  target_boolean: boolean | null; unit: string; target_direction: string;
  target_date: string | null; weight: number; is_critical: boolean;
  success_criteria: string; revision: number; frozen_at: string | null;
};
type OutcomeObservation = {
  id: string; expected_outcome_id: string; observation_date: string;
  numeric_value: number | null; boolean_value: boolean | null;
  observed_status: string; narrative: string; provenance: string;
  verification_status: string; recorded_by_membership_id: string;
};
type EffectivenessAssessment = {
  id: string; status: string; classification: string; rationale: string;
  assessment_date: string; calculation_details: Record<string, unknown>;
};
type EffectivenessWorkspace = {
  outcomes: ExpectedOutcome[]; observations: OutcomeObservation[];
  calculations: Record<string, {assessable: boolean; target_met: boolean | null; explanation: string; actual_value: unknown; target_value: unknown}>;
  aggregate: {classification: string; weighted_target_met_ratio: number | null; missing_count: number; critical_failure: boolean};
  assessments: EffectivenessAssessment[];
  lessons: {id: string; lesson_type: string; description: string; business_impact: string}[];
  conditions: ApprovalCondition[]; capabilities: Record<string, boolean>;
};

type SimilarityComponent = {score: number; weighted_points: number; available: boolean; explanation: string};
type HistoricalDecision = {
  id: string; title: string; created_at: string; business_concept_name: string | null;
  final_status: string; approval_result: string | null; effectiveness_classification: string | null;
  evidence_count: number | null; evidence_types: string[] | null;
  material_conditions: string[] | null; material_findings: string[] | null; lessons: string[] | null;
};
type PrecedentResult = {
  historical_decision: HistoricalDecision; overall_similarity: number; relevance: string;
  algorithm_version: string; similarity_components: Record<string, SimilarityComponent>;
  shared_characteristics: string[]; different_characteristics: string[];
  observed_usage: {decision: {referenced_count: number; evaluated_count: number; classification_counts: Record<string, number>}; lessons: Record<string, {adopted_count: number; rejected_count: number; evaluated_count: number; classification_counts: Record<string, number>}>} | null;
};
type PrecedentWorkspace = {algorithm_version: string; items: PrecedentResult[]; considered_count: number; returned_count: number};
type DecisionComparison = PrecedentResult & {
  current_decision: Record<string, string | null>; historical_governance: Record<string, unknown> | null;
  historical_outcome: Record<string, unknown> | null; historical_lessons: {id: string; type: string; description: string; business_impact: string}[] | null;
};
type GovernedPrecedent = {id: string; historical_decision_id: string; relationship_type: string; rationale: string; similarity_score: number; similarity_algorithm_version: string; snapshot_historical_title: string; snapshot_historical_status: string; snapshot_outcome_classification: string | null; referenced_by_membership_id: string; referenced_at: string};
type LessonAdoption = {id: string; historical_lesson_id: string; status: string; rationale: string; snapshot_lesson_type: string; snapshot_lesson_description: string; acted_by_membership_id: string; acted_at: string};
type DecisionLearning = {precedent_evaluations: {id: string; precedent_reference_id: string; classification: string; rationale: string; current_effectiveness_snapshot: string; evaluated_at: string; superseded_at: string | null}[]; lesson_evaluations: {id: string; lesson_adoption_id: string; classification: string; rationale: string; was_applied: boolean | null; evaluated_at: string; superseded_at: string | null}[]};

const tabs = [
  "Overview",
  "Evidence",
  "Timeline",
  "AI Analysis",
  "Approvals",
  "Outcomes",
  "Decision Memory",
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
  const [effectiveness, setEffectiveness] = useState<EffectivenessWorkspace>();
  const [outcomeBusy, setOutcomeBusy] = useState(false);
  const [outcomeTitle, setOutcomeTitle] = useState("");
  const [outcomeTarget, setOutcomeTarget] = useState("");
  const [outcomeCriteria, setOutcomeCriteria] = useState("");
  const [observationValues, setObservationValues] = useState<Record<string, string>>({});
  const [assessmentRationale, setAssessmentRationale] = useState("");
  const [lessonText, setLessonText] = useState("");
  const [precedents, setPrecedents] = useState<PrecedentWorkspace>();
  const [memoryRelevance, setMemoryRelevance] = useState("weakly_relevant");
  const [memoryOutcome, setMemoryOutcome] = useState("");
  const [comparison, setComparison] = useState<DecisionComparison>();
  const [memoryBusy, setMemoryBusy] = useState(false);
  const [governedPrecedents, setGovernedPrecedents] = useState<GovernedPrecedent[]>([]);
  const [lessonAdoptions, setLessonAdoptions] = useState<LessonAdoption[]>([]);
  const [precedentRelationship, setPrecedentRelationship] = useState("analogous");
  const [precedentRationale, setPrecedentRationale] = useState("");
  const [lessonRationales, setLessonRationales] = useState<Record<string, string>>({});
  const [learning, setLearning] = useState<DecisionLearning>({precedent_evaluations: [], lesson_evaluations: []});
  const [learningRationales, setLearningRationales] = useState<Record<string, string>>({});
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
      try {
        setEffectiveness(await api<EffectivenessWorkspace>(`/decisions/${params.id}/effectiveness`));
      } catch {
        setEffectiveness(undefined);
      }
      try {
        setPrecedents(await api<PrecedentWorkspace>(`/decisions/${params.id}/precedents?minimum_relevance=${memoryRelevance}${memoryOutcome ? `&outcome_classification=${memoryOutcome}` : ""}`));
        setGovernedPrecedents(await api<GovernedPrecedent[]>(`/decisions/${params.id}/precedent-references`));
        setLessonAdoptions(await api<LessonAdoption[]>(`/decisions/${params.id}/lesson-adoptions`));
        setLearning(await api<DecisionLearning>(`/decisions/${params.id}/learning`));
      } catch {
        setPrecedents(undefined);
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

  async function loadPrecedents() {
    setMemoryBusy(true);
    try {
      setError("");
      setPrecedents(await api<PrecedentWorkspace>(`/decisions/${params.id}/precedents?minimum_relevance=${memoryRelevance}${memoryOutcome ? `&outcome_classification=${memoryOutcome}` : ""}`));
      setComparison(undefined);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to load Decision Memory.");
    } finally {
      setMemoryBusy(false);
    }
  }

  async function comparePrecedent(historicalDecisionId: string) {
    setMemoryBusy(true);
    try {
      setError("");
      setComparison(await api<DecisionComparison>(`/decisions/${params.id}/precedents/${historicalDecisionId}`));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to compare historical Decisions.");
    } finally {
      setMemoryBusy(false);
    }
  }

  async function attachPrecedent() {
    if (!comparison) return;
    setMemoryBusy(true);
    try {
      await api(`/decisions/${params.id}/precedent-references`, {method: "POST", body: JSON.stringify({historical_decision_id: comparison.historical_decision.id, relationship_type: precedentRelationship, rationale: precedentRationale})});
      setPrecedentRationale("");
      await load();
    } catch (caught) { setError(caught instanceof Error ? caught.message : "Unable to attach precedent."); }
    finally { setMemoryBusy(false); }
  }

  async function chooseLesson(lessonId: string, status: "adopted" | "rejected") {
    if (!comparison) return;
    setMemoryBusy(true);
    try {
      await api(`/decisions/${params.id}/lesson-adoptions`, {method: "POST", body: JSON.stringify({historical_decision_id: comparison.historical_decision.id, historical_lesson_id: lessonId, status, rationale: lessonRationales[lessonId] || ""})});
      await load();
    } catch (caught) { setError(caught instanceof Error ? caught.message : "Unable to record lesson choice."); }
    finally { setMemoryBusy(false); }
  }

  async function evaluateLearning(kind: "precedent" | "lesson", id: string, classification: string) {
    const assessment = effectiveness?.assessments.find((item) => item.status === "completed");
    if (!assessment) { setError("Complete an effectiveness assessment before evaluating learning."); return; }
    setMemoryBusy(true);
    try {
      const path = kind === "precedent" ? `/precedent-references/${id}/evaluation` : `/lesson-adoptions/${id}/evaluation`;
      await api(`/decisions/${params.id}${path}`, {method: "POST", body: JSON.stringify({effectiveness_assessment_id: assessment.id, classification, rationale: learningRationales[id] || "", was_applied: kind === "lesson" ? classification !== "not_applied" : undefined})});
      await load();
    } catch (caught) { setError(caught instanceof Error ? caught.message : "Unable to record learning evaluation."); }
    finally { setMemoryBusy(false); }
  }

  async function supersedeLearning(kind: "precedent" | "lesson", id: string, classification: string) {
    const rationale = learningRationales[`supersede-${id}`] || "";
    setMemoryBusy(true);
    try {
      const path = kind === "precedent" ? `/precedent-references/${id}/evaluation/supersede` : `/lesson-adoptions/${id}/evaluation/supersede`;
      await api(`/decisions/${params.id}${path}`, {method: "POST", body: JSON.stringify({classification, rationale, supersession_rationale: rationale})});
      await load();
    } catch (caught) { setError(caught instanceof Error ? caught.message : "Unable to supersede learning evaluation."); }
    finally { setMemoryBusy(false); }
  }

  async function outcomeAction(path: string, body?: object, method = "POST") {
    setOutcomeBusy(true);
    try {
      setError("");
      await api(`/decisions/${params.id}${path}`, {method, body: body ? JSON.stringify(body) : undefined});
      await load();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to update governed outcomes.");
    } finally {
      setOutcomeBusy(false);
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

      {activeTab === "Decision Memory" ? (
        <section className={styles.approvalWorkspace} aria-label="Decision Memory and historical comparison">
          <DashboardWidget eyebrow="Governed Decision inputs" title={`Referenced precedents (${governedPrecedents.length})`}>
            <p className={styles.helperText}>These records were deliberately relied upon. Their similarity and historical result are frozen at attachment time.</p>
            {governedPrecedents.length === 0 ? <div className={styles.emptyPanel}>No historical Decision has been attached as a governed precedent.</div> : <div className={styles.reviewList}>{governedPrecedents.map((item) => { const evaluation = learning.precedent_evaluations.find((value) => value.precedent_reference_id === item.id && !value.superseded_at); return <article className={styles.reviewCard} key={item.id}><div className={styles.reviewHeader}><strong>{item.snapshot_historical_title}</strong><span>{item.relationship_type.replaceAll("_", " ")} · {item.similarity_score}%</span></div><p>{item.rationale}</p><p className={styles.helperText}>{item.snapshot_historical_status.replaceAll("_", " ")} · attached {new Date(item.referenced_at).toLocaleString()} · {item.similarity_algorithm_version}</p>{evaluation ? <div className={styles.finding}><strong>Observed usefulness: {evaluation.classification.replaceAll("_", " ")}</strong><p>{evaluation.rationale}</p><span>Current effectiveness: {evaluation.current_effectiveness_snapshot.replaceAll("_", " ")}</span><textarea aria-label={`Correction rationale for ${item.snapshot_historical_title}`} placeholder="Why is this evaluation being corrected?" value={learningRationales[`supersede-${item.id}`] || ""} onChange={(event) => setLearningRationales((current) => ({...current, [`supersede-${item.id}`]: event.target.value}))} /><select aria-label={`Corrected usefulness for ${item.snapshot_historical_title}`} defaultValue={evaluation.classification} id={`precedent-correction-${item.id}`}><option value="highly_useful">Highly useful</option><option value="useful">Useful</option><option value="neutral">Neutral</option><option value="misleading">Misleading</option><option value="harmful">Harmful</option><option value="inconclusive">Inconclusive</option><option value="too_early">Too early</option></select><button className={styles.secondaryAction} disabled={memoryBusy || (learningRationales[`supersede-${item.id}`] || "").trim().length < 3} onClick={() => void supersedeLearning("precedent", item.id, (document.getElementById(`precedent-correction-${item.id}`) as HTMLSelectElement).value)}>Supersede evaluation</button></div> : <div className={styles.controlGroup}><textarea aria-label={`Usefulness rationale for ${item.snapshot_historical_title}`} placeholder="What happened, what matched, and why was this precedent useful or misleading?" value={learningRationales[item.id] || ""} onChange={(event) => setLearningRationales((current) => ({...current, [item.id]: event.target.value}))} /><select aria-label={`Usefulness classification for ${item.snapshot_historical_title}`} defaultValue="useful" id={`precedent-evaluation-${item.id}`}><option value="highly_useful">Highly useful</option><option value="useful">Useful</option><option value="neutral">Neutral</option><option value="misleading">Misleading</option><option value="harmful">Harmful</option><option value="inconclusive">Inconclusive</option><option value="too_early">Too early</option></select><button className={styles.primaryAction} disabled={memoryBusy || (learningRationales[item.id] || "").trim().length < 3 || !effectiveness?.assessments.some((value) => value.status === "completed")} onClick={() => { const value = (document.getElementById(`precedent-evaluation-${item.id}`) as HTMLSelectElement).value; void evaluateLearning("precedent", item.id, value); }}>Evaluate precedent</button></div>}</article>;})}</div>}
            <strong>Historical lesson choices</strong>
            {lessonAdoptions.length === 0 ? <p className={styles.helperText}>No lessons have been adopted or rejected.</p> : lessonAdoptions.map((item) => { const evaluation = learning.lesson_evaluations.find((value) => value.lesson_adoption_id === item.id && !value.superseded_at); return <div className={styles.finding} key={item.id}><strong>{item.status} · {item.snapshot_lesson_type}</strong><p>{item.snapshot_lesson_description}</p><p className={styles.helperText}>{item.rationale}</p>{evaluation ? <><p className={styles.recommendation}>Observed result: {evaluation.classification.replaceAll("_", " ")} — {evaluation.rationale}</p><textarea aria-label={`Correction rationale for lesson ${item.snapshot_lesson_description}`} placeholder="Why is this lesson evaluation being corrected?" value={learningRationales[`supersede-${item.id}`] || ""} onChange={(event) => setLearningRationales((current) => ({...current, [`supersede-${item.id}`]: event.target.value}))} /><button className={styles.secondaryAction} disabled={memoryBusy || (learningRationales[`supersede-${item.id}`] || "").trim().length < 3} onClick={() => void supersedeLearning("lesson", item.id, evaluation.classification)}>Supersede evaluation</button></> : <div className={styles.controlGroup}><textarea aria-label={`Learning rationale for ${item.snapshot_lesson_description}`} placeholder="How did this lesson choice relate to the outcome?" value={learningRationales[item.id] || ""} onChange={(event) => setLearningRationales((current) => ({...current, [item.id]: event.target.value}))} /><button className={styles.primaryAction} disabled={memoryBusy || (learningRationales[item.id] || "").trim().length < 3 || !effectiveness?.assessments.some((value) => value.status === "completed")} onClick={() => void evaluateLearning("lesson", item.id, item.status === "rejected" ? "appropriate_rejection" : "beneficial")}>Evaluate lesson choice</button></div>}</div>;})}
          </DashboardWidget>
          <div className={styles.actionRow}>
            <label className={styles.controlGroup}>Minimum relevance
              <select value={memoryRelevance} onChange={(event) => setMemoryRelevance(event.target.value)}>
                <option value="weakly_relevant">All relevance levels</option>
                <option value="somewhat_relevant">Somewhat relevant or stronger</option>
                <option value="relevant">Relevant or stronger</option>
                <option value="strongly_relevant">Strongly relevant only</option>
              </select>
            </label>
            <label className={styles.controlGroup}>Historical outcome
              <select value={memoryOutcome} onChange={(event) => setMemoryOutcome(event.target.value)}>
                <option value="">Any outcome, including missing</option>
                <option value="met">Met expectations</option>
                <option value="partially_met">Partially met</option>
                <option value="did_not_meet">Did not meet</option>
                <option value="inconclusive">Inconclusive</option>
              </select>
            </label>
            <button className={styles.primaryAction} disabled={memoryBusy} onClick={() => void loadPrecedents()}>Apply filters</button>
          </div>
          {!precedents ? <div className={styles.emptyPanel}>Decision Memory is unavailable for your current permissions.</div> : precedents.items.length === 0 ? <div className={styles.emptyPanel}><strong>No historical precedents match these filters.</strong><p>Broaden the relevance or outcome filter. Inaccessible Decisions are never counted or displayed.</p></div> : (
            <div className={styles.workspaceGrid}>
              <div className={styles.mainColumn}>
                <DashboardWidget eyebrow="Governed historical context" title={`Relevant historical Decisions (${precedents.returned_count})`}>
                  <p className={styles.helperText}>Similarity is structural, not a recommendation. Successful, failed, and rejected Decisions are ranked by the same formula.</p>
                  <div className={styles.reviewList}>
                    {precedents.items.map((precedent) => <article className={styles.reviewCard} key={precedent.historical_decision.id}>
                      <div className={styles.reviewHeader}><strong>{precedent.historical_decision.title}</strong><span>{precedent.overall_similarity}% · {precedent.relevance.replaceAll("_", " ")}</span></div>
                      <p className={styles.helperText}>{precedent.historical_decision.business_concept_name || "No Business Concept"} · {new Date(precedent.historical_decision.created_at).toLocaleDateString()} · {precedent.historical_decision.final_status.replaceAll("_", " ")}</p>
                      <div className={styles.evidenceBadges}>
                        <span>Approval: {precedent.historical_decision.approval_result?.replaceAll("_", " ") || "not available"}</span>
                        <span>Effectiveness: {precedent.historical_decision.effectiveness_classification?.replaceAll("_", " ") || "not assessed or restricted"}</span>
                      </div>
                      {precedent.observed_usage?.decision ? <p className={styles.helperText}>Observed history: referenced {precedent.observed_usage.decision.referenced_count} time(s), evaluated {precedent.observed_usage.decision.evaluated_count}. This does not affect similarity or ranking.</p> : null}
                      <div className={styles.findingList}>{Object.entries(precedent.similarity_components).filter(([, component]) => component.available && component.weighted_points > 0).map(([name, component]) => <div className={styles.finding} key={name}><strong>{name.replaceAll("_", " ")} · {Math.round(component.score * 100)}%</strong><p>{component.explanation}</p></div>)}</div>
                      {precedent.historical_decision.lessons?.slice(0, 2).map((lesson) => <p className={styles.recommendation} key={lesson}>Relevant lesson: {lesson}</p>)}
                      <button className={styles.primaryAction} disabled={memoryBusy} onClick={() => void comparePrecedent(precedent.historical_decision.id)}>Compare Decisions</button>
                    </article>)}
                  </div>
                </DashboardWidget>
              </div>
              <aside className={styles.sideColumn}>
                <DashboardWidget eyebrow="Explainable comparison" title={comparison ? comparison.historical_decision.title : "Select a precedent"}>
                  {!comparison ? <p className={styles.helperText}>Choose Compare Decisions to inspect shared characteristics, differences, governance, outcomes, and lessons.</p> : <>
                    <p className={styles.recommendation}>{comparison.overall_similarity}% similar — {comparison.relevance.replaceAll("_", " ")}</p>
                    <strong>Shared characteristics</strong>
                    <ul>{comparison.shared_characteristics.map((item) => <li key={item}>{item}</li>)}</ul>
                    <strong>Key differences</strong>
                    <ul>{comparison.different_characteristics.map((item) => <li key={item}>{item}</li>)}</ul>
                    <strong>Historical result</strong>
                    <p>{comparison.historical_decision.final_status.replaceAll("_", " ")} · effectiveness {comparison.historical_decision.effectiveness_classification?.replaceAll("_", " ") || "not assessed or restricted"}</p>
                    {comparison.observed_usage?.decision ? <p className={styles.helperText}>Observed usage: {comparison.observed_usage.decision.referenced_count} reference(s), {comparison.observed_usage.decision.evaluated_count} evaluated. Association is not causality.</p> : null}
                    <div className={styles.controlGroup}>
                      <label>Relationship type<select value={precedentRelationship} onChange={(event) => setPrecedentRelationship(event.target.value)}><option value="supporting">Supporting precedent</option><option value="cautionary">Cautionary precedent</option><option value="analogous">Analogous case</option><option value="exception">Exception case</option><option value="contrary">Contrary precedent</option></select></label>
                      <textarea aria-label="Precedent attachment rationale" placeholder="Why did this historical Decision influence the current reasoning?" value={precedentRationale} onChange={(event) => setPrecedentRationale(event.target.value)} />
                      <button className={styles.primaryAction} disabled={memoryBusy || precedentRationale.trim().length < 3} onClick={() => void attachPrecedent()}>Attach as precedent</button>
                    </div>
                    {comparison.historical_lessons?.map((lesson) => { const usage = comparison.observed_usage?.lessons?.[lesson.id]; return <div className={styles.finding} key={lesson.id}><strong>{lesson.type} lesson</strong><p>{lesson.description}</p>{usage ? <p className={styles.helperText}>Observed history: adopted {usage.adopted_count}, rejected {usage.rejected_count}, evaluated {usage.evaluated_count}.</p> : null}<textarea aria-label={`Rationale for ${lesson.description}`} placeholder="Why adopt or reject this lesson?" value={lessonRationales[lesson.id] || ""} onChange={(event) => setLessonRationales((current) => ({...current, [lesson.id]: event.target.value}))} /><div className={styles.actionRow}><button className={styles.primaryAction} disabled={memoryBusy || (lessonRationales[lesson.id] || "").trim().length < 3} onClick={() => void chooseLesson(lesson.id, "adopted")}>Adopt lesson</button><button className={styles.secondaryAction} disabled={memoryBusy || (lessonRationales[lesson.id] || "").trim().length < 3} onClick={() => void chooseLesson(lesson.id, "rejected")}>Reject lesson</button></div></div>;})}
                    <p className={styles.helperText}>Calculated with {comparison.algorithm_version}. No AI recommendation is generated.</p>
                  </>}
                </DashboardWidget>
              </aside>
            </div>
          )}
        </section>
      ) : null}

      {activeTab === "Outcomes" ? (
        <section className={styles.approvalWorkspace} aria-label="Decision outcomes and effectiveness">
          {!effectiveness ? (
            <div className={styles.emptyPanel}>Outcome tracking is unavailable for your current permissions.</div>
          ) : (
            <>
              <div className={styles.workspaceGrid}>
                <div className={styles.mainColumn}>
                  <DashboardWidget eyebrow="Expected versus actual" title={`Expected outcomes (${effectiveness.outcomes.length})`}>
                    {!effectiveness.outcomes.length ? <p className={styles.helperText}>No expected outcomes have been defined. Missing data is never treated as success.</p> : null}
                    <div className={styles.reviewList}>
                      {effectiveness.outcomes.map((outcome) => {
                        const calculation = effectiveness.calculations[outcome.id];
                        const observations = effectiveness.observations.filter((item) => item.expected_outcome_id === outcome.id);
                        return <article className={styles.reviewCard} key={outcome.id}>
                          <div className={styles.reviewHeader}>
                            <strong>{outcome.title}</strong>
                            <span>{outcome.is_critical ? "Critical · " : ""}{outcome.frozen_at ? `Frozen revision ${outcome.revision}` : "Editable before approval"}</span>
                          </div>
                          <p>{outcome.description}</p>
                          <p className={styles.helperText}>Baseline {outcome.baseline_value ?? "not set"} · Target {outcome.target_direction === "range" ? `${outcome.target_min_value}–${outcome.target_max_value}` : outcome.target_value ?? String(outcome.target_boolean ?? "governed assessment")} {outcome.unit} · {outcome.target_date || "No target date"}</p>
                          <p><strong>{calculation?.assessable ? (calculation.target_met ? "Target met" : "Target not met") : "Incomplete or too early"}</strong> — {calculation?.explanation}</p>
                          <div className={styles.findingList}>
                            {observations.map((observation) => <div className={styles.finding} key={observation.id}>
                              <strong>{observation.observation_date}: {observation.numeric_value ?? String(observation.boolean_value ?? observation.observed_status)}</strong>
                              <span>{observation.verification_status.replaceAll("_", " ")} · {observation.provenance.replaceAll("_", " ")}</span>
                              {observation.narrative ? <p>{observation.narrative}</p> : null}
                              {observation.verification_status === "unverified" && effectiveness.capabilities.verify ? <button className={styles.primaryAction} disabled={outcomeBusy} onClick={() => void outcomeAction(`/outcomes/${outcome.id}/observations/${observation.id}/verify`, {rationale: "Independently checked against the reported business record."})}>Verify observation</button> : null}
                            </div>)}
                          </div>
                          {effectiveness.capabilities.record && effectiveness.capabilities.eligible ? <div className={styles.actionRow}>
                            <input aria-label={`Actual value for ${outcome.title}`} placeholder="Observed numeric value" value={observationValues[outcome.id] || ""} onChange={(event) => setObservationValues((current) => ({...current, [outcome.id]: event.target.value}))} />
                            <button className={styles.primaryAction} disabled={outcomeBusy} onClick={() => void outcomeAction(`/outcomes/${outcome.id}/observations`, {observation_date: new Date().toISOString().slice(0, 10), numeric_value: Number(observationValues[outcome.id]), observed_status: "reported", narrative: "Recorded from the Decision workspace.", provenance: "manually_reported"})}>Record observation</button>
                          </div> : null}
                        </article>;
                      })}
                    </div>
                  </DashboardWidget>
                  {effectiveness.capabilities.define && !["rejected", "closed"].includes(decision.status) ? <DashboardWidget eyebrow="Governed expectation" title="Define expected outcome">
                    <div className={styles.controlGroup}>
                      <input aria-label="Outcome title" placeholder="Outcome title" value={outcomeTitle} onChange={(event) => setOutcomeTitle(event.target.value)} />
                      <input aria-label="Target value" placeholder="Numeric target" value={outcomeTarget} onChange={(event) => setOutcomeTarget(event.target.value)} />
                      <textarea aria-label="Success criteria" placeholder="Business description and success criteria" value={outcomeCriteria} onChange={(event) => setOutcomeCriteria(event.target.value)} />
                      <button className={styles.primaryAction} disabled={outcomeBusy || outcomeTitle.length < 3 || outcomeCriteria.length < 3} onClick={() => void outcomeAction("/outcomes", {title: outcomeTitle, description: outcomeCriteria, measurement_type: "numeric", target_value: Number(outcomeTarget), target_direction: "increase", success_criteria: outcomeCriteria})}>Create expected outcome</button>
                    </div>
                  </DashboardWidget> : null}
                </div>
                <aside className={styles.sideColumn}>
                  <DashboardWidget eyebrow="Deterministic result" title="Overall effectiveness">
                    <p className={styles.recommendation}>{effectiveness.aggregate.classification.replaceAll("_", " ")}</p>
                    <p className={styles.helperText}>{effectiveness.aggregate.weighted_target_met_ratio === null ? "No verified assessable outcomes." : `${effectiveness.aggregate.weighted_target_met_ratio}% of assessable outcome weight met.`}</p>
                    {effectiveness.aggregate.critical_failure ? <p className={styles.overdue}>A critical outcome failed; weighted success cannot override it.</p> : null}
                    {effectiveness.aggregate.missing_count ? <p className={styles.helperText}>{effectiveness.aggregate.missing_count} outcome(s) remain incomplete.</p> : null}
                  </DashboardWidget>
                  <DashboardWidget eyebrow="Approval integration" title={`Conditions (${effectiveness.conditions.length})`}>
                    {effectiveness.conditions.map((condition) => <div className={styles.finding} key={condition.id}><strong>{condition.condition_text}</strong><span>{condition.status}{condition.due_date ? ` · due ${condition.due_date}` : ""}</span></div>)}
                    {!effectiveness.conditions.length ? <p className={styles.helperText}>No approval conditions.</p> : null}
                  </DashboardWidget>
                  <DashboardWidget eyebrow="Governed judgment" title="Assessments">
                    {effectiveness.assessments.map((assessment) => <div className={styles.finding} key={assessment.id}><strong>{assessment.classification.replaceAll("_", " ")}</strong><span>{assessment.status} · {assessment.assessment_date}</span><p>{assessment.rationale}</p>{assessment.status === "draft" && effectiveness.capabilities.assess ? <button className={styles.primaryAction} onClick={() => void outcomeAction(`/effectiveness-assessments/${assessment.id}/complete`)}>Complete assessment</button> : null}</div>)}
                    {effectiveness.capabilities.assess && effectiveness.capabilities.eligible ? <div className={styles.controlGroup}><textarea aria-label="Assessment rationale" placeholder="Assessment rationale" value={assessmentRationale} onChange={(event) => setAssessmentRationale(event.target.value)} /><button className={styles.primaryAction} disabled={outcomeBusy || assessmentRationale.length < 3} onClick={() => void outcomeAction("/effectiveness-assessments", {assessment_date: new Date().toISOString().slice(0, 10), classification: effectiveness.aggregate.classification, rationale: assessmentRationale})}>Create assessment</button></div> : null}
                  </DashboardWidget>
                  <DashboardWidget eyebrow="Retained learning" title="Lessons learned">
                    {effectiveness.lessons.map((lesson) => <div className={styles.finding} key={lesson.id}><strong>{lesson.lesson_type} lesson</strong><p>{lesson.description}</p></div>)}
                    {effectiveness.capabilities.lesson && effectiveness.capabilities.eligible ? <div className={styles.controlGroup}><textarea aria-label="Lesson learned" placeholder="Lesson learned" value={lessonText} onChange={(event) => setLessonText(event.target.value)} /><button className={styles.primaryAction} disabled={outcomeBusy || lessonText.length < 3} onClick={() => void outcomeAction("/lessons", {lesson_type: "execution", description: lessonText})}>Record lesson</button></div> : null}
                  </DashboardWidget>
                </aside>
              </div>
            </>
          )}
        </section>
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
