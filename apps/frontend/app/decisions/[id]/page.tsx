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
  title: string;
  summary: string;
  knowledge_type: string;
  approval_status: string;
  lifecycle_status: string;
  authority_level: string;
  trust_score: number;
  ai_usage_allowed: boolean;
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

  async function load() {
    setRefreshing(true);
    try {
      setError("");
      setData(
        await api<WorkspaceResponse>(`/decisions/${params.id}`),
      );
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
        <DashboardWidget
          eyebrow="Governed knowledge"
          title={`Supporting evidence (${data.evidence.length})`}
        >
          {data.evidence.length ? (
            <div className={styles.evidenceList}>
              {data.evidence.map((card) => (
                <article className={styles.evidenceCard} key={card.id}>
                  <div className={styles.evidenceHeader}>
                    <div>
                      <strong>{card.title}</strong>
                      <span>{card.knowledge_type.replaceAll("_", " ")}</span>
                    </div>
                    <div className={styles.evidenceBadges}>
                      <span>{card.approval_status.replaceAll("_", " ")}</span>
                      <span>{Math.round(card.trust_score * 100)}% trust</span>
                    </div>
                  </div>
                  <p>{card.summary}</p>
                  <div className={styles.evidenceMeta}>
                    <span>{card.authority_level.replaceAll("_", " ")}</span>
                    <span>
                      {card.ai_usage_allowed
                        ? "Governed AI eligible"
                        : "Human review only"}
                    </span>
                  </div>
                </article>
              ))}
            </div>
          ) : (
            <div className={styles.emptyPanel}>
              No governed evidence is connected to this business concept.
            </div>
          )}
        </DashboardWidget>
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
