"use client";

import Link from "next/link";
import {useEffect, useMemo, useState} from "react";
import {
  AlertTriangle,
  BookOpen,
  Boxes,
  BrainCircuit,
  Building2,
  Clock3,
  FileCheck2,
  RefreshCw,
  Scale,
  ShieldCheck,
} from "lucide-react";
import Shell from "@/components/Shell";
import {api} from "@/lib/api";
import ActivityFeed, {
  DashboardActivity,
} from "@/components/dashboard/ActivityFeed";
import {
  ChartDatum,
  DistributionBars,
  HorizontalBars,
  TrendChart,
  TrendDatum,
} from "@/components/dashboard/AnalyticsCharts";
import DashboardWidget from "@/components/dashboard/DashboardWidget";
import ExecutiveMetric from "@/components/dashboard/ExecutiveMetric";
import styles from "./Dashboard.module.css";

type Insight = {
  tone: "positive" | "attention" | "neutral";
  title: string;
  description: string;
};

type Alert = {
  severity: "critical" | "high" | "medium";
  title: string;
  description: string;
  href: string;
};

type DashboardResponse = {
  summary: {
    open_decisions: number;
    pending_approval: number;
    high_risk: number;
    overdue: number;
    average_readiness: number;
    knowledge_cards: number;
    business_concepts: number;
    evidence_sources: number;
    workspaces: number;
    governance_score: number;
    ai_confidence: number;
    published_knowledge: number;
  };
  briefing: {
    title: string;
    summary: string;
    generated_at: string;
    method: string;
  };
  charts: {
    decision_status: ChartDatum[];
    risk_distribution: ChartDatum[];
    readiness_distribution: ChartDatum[];
    decision_trend: TrendDatum[];
    business_units: ChartDatum[];
  };
  alerts: Alert[];
  insights: Insight[];
  activity: DashboardActivity[];
  cache_ttl_seconds: number;
};

function greeting() {
  const hour = new Date().getHours();
  if (hour < 12) return "Good morning";
  if (hour < 18) return "Good afternoon";
  return "Good evening";
}

export default function Dashboard() {
  const [greetingText, setGreetingText] = useState("Welcome");
  const [data, setData] = useState<DashboardResponse>();
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");
  const [lastUpdated, setLastUpdated] = useState<Date>();

  async function load(force = false) {
    if (force) setRefreshing(true);
    else if (!data) setLoading(true);

    try {
      setError("");
      const response = await api<DashboardResponse>(
        `/dashboard${force ? "?refresh=true" : ""}`,
      );
      setData(response);
      setLastUpdated(new Date());
    } catch (caught) {
      setError(
        caught instanceof Error
          ? caught.message
          : "Unable to load executive intelligence.",
      );
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }

  useEffect(() => {
    setGreetingText(greeting());
    void load();

    const interval = window.setInterval(() => {
      void load(false);
    }, 60_000);

    return () => window.clearInterval(interval);
  }, []);

  const summary = data?.summary;
  const highAndCritical = useMemo(
    () =>
      data?.charts.risk_distribution
        .filter((item) => ["high", "critical"].includes(item.label))
        .reduce((sum, item) => sum + item.value, 0) ?? 0,
    [data],
  );

  return (
    <Shell>
      <header className={styles.pageHeader}>
        <div>
          <div className={styles.eyebrow}>Executive command center</div>
          <h1>Decision Intelligence</h1>
          <p>
            {greetingText}. Monitor decision readiness, enterprise risk,
            governed evidence, and operational attention from one view.
          </p>
        </div>

        <div className={styles.headerActions}>
          <div className={styles.updateStatus}>
            <span>
              {lastUpdated
                ? `Updated ${lastUpdated.toLocaleTimeString([], {
                    hour: "numeric",
                    minute: "2-digit",
                  })}`
                : "Loading intelligence"}
            </span>
            <small>Auto-refresh every 60 seconds</small>
          </div>
          <button
            className={styles.refreshButton}
            onClick={() => void load(true)}
            disabled={refreshing}
          >
            <RefreshCw
              size={15}
              className={refreshing ? styles.spinning : ""}
            />
            Refresh
          </button>
        </div>
      </header>

      {error ? <div className={styles.error}>{error}</div> : null}

      {loading || !data || !summary ? (
        <div className={styles.loadingGrid}>
          {Array.from({length: 8}).map((_, index) => (
            <div className={styles.loadingCard} key={index} />
          ))}
        </div>
      ) : (
        <>
          <section className={styles.briefing}>
            <div className={styles.briefingIcon}>
              <BrainCircuit size={20} strokeWidth={1.8} />
            </div>
            <div>
              <div className={styles.eyebrow}>{data.briefing.title}</div>
              <h2>{data.briefing.summary}</h2>
              <p>
                Deterministic briefing generated from governed dashboard data.
                No generative model is required.
              </p>
            </div>
            <Link href="/decisions">Open Decision Center</Link>
          </section>

          <section className={styles.metricGrid}>
            <ExecutiveMetric
              label="Open decisions"
              value={summary.open_decisions}
              detail={`${summary.pending_approval} awaiting approval`}
              icon={Scale}
              tone={summary.open_decisions ? "warning" : "neutral"}
              href="/decisions"
              actionLabel="Open Decision Center"
            />
            <ExecutiveMetric
              label="High risk"
              value={summary.high_risk}
              detail={`${summary.overdue} overdue review${summary.overdue === 1 ? "" : "s"}`}
              icon={AlertTriangle}
              tone={summary.high_risk ? "critical" : "positive"}
              href="/decisions"
              actionLabel="Review high-risk decisions"
            />
            <ExecutiveMetric
              label="Average readiness"
              value={`${summary.average_readiness}%`}
              detail="Across open decisions"
              icon={FileCheck2}
              tone={summary.average_readiness >= 80 ? "positive" : "warning"}
              href="/decisions"
              actionLabel="Review decision readiness"
            />
            <ExecutiveMetric
              label="Governance score"
              value={`${summary.governance_score}%`}
              detail="Approved, trusted, AI-eligible"
              icon={ShieldCheck}
              tone={summary.governance_score >= 80 ? "positive" : "warning"}
              href="/governance"
              actionLabel="Open governance"
            />
            <ExecutiveMetric
              label="Knowledge cards"
              value={summary.knowledge_cards}
              detail={`${summary.published_knowledge} approved`}
              icon={BookOpen}
              tone="positive"
              href="/knowledge"
              actionLabel="View Knowledge Cards"
            />
            <ExecutiveMetric
              label="AI confidence"
              value={`${summary.ai_confidence}%`}
              detail="Recorded decision confidence"
              icon={BrainCircuit}
              tone={summary.ai_confidence >= 80 ? "positive" : "neutral"}
              href="/ask"
              actionLabel="Ask DecisionVault"
            />
            <ExecutiveMetric
              label="Business concepts"
              value={summary.business_concepts}
              detail="Active governed concepts"
              icon={Building2}
              tone="neutral"
              href="/concepts"
              actionLabel="View business concepts"
            />
            <ExecutiveMetric
              label="Evidence sources"
              value={summary.evidence_sources}
              detail={`${summary.workspaces} governed workspaces`}
              icon={Boxes}
              tone="neutral"
              href="/sources"
              actionLabel="View evidence sources"
            />
          </section>

          <section className={styles.chartGrid}>
            <DashboardWidget
              eyebrow="Six-month movement"
              title="Decision trend"
              className={styles.wideWidget}
            >
              <TrendChart data={data.charts.decision_trend} />
            </DashboardWidget>

            <DashboardWidget
              eyebrow="Active portfolio"
              title="Risk distribution"
            >
              <HorizontalBars
                data={data.charts.risk_distribution}
                tone="risk"
              />
            </DashboardWidget>

            <DashboardWidget
              eyebrow="Evidence maturity"
              title="Readiness distribution"
            >
              <DistributionBars data={data.charts.readiness_distribution} />
            </DashboardWidget>

            <DashboardWidget
              eyebrow="Workflow state"
              title="Decision status"
            >
              <HorizontalBars data={data.charts.decision_status} />
            </DashboardWidget>

            <DashboardWidget
              eyebrow="Operating ownership"
              title="Business units"
            >
              {data.charts.business_units.length ? (
                <HorizontalBars
                  data={data.charts.business_units}
                  tone="blue"
                />
              ) : (
                <div className={styles.emptyState}>
                  Business-unit analytics will appear as decisions are created.
                </div>
              )}
            </DashboardWidget>
          </section>

          <section className={styles.intelligenceGrid}>
            <DashboardWidget
              eyebrow="Business interpretation"
              title="Executive insights"
            >
              <div className={styles.insightList}>
                {data.insights.map((insight) => (
                  <article
                    className={`${styles.insight} ${styles[insight.tone]}`}
                    key={insight.title}
                  >
                    <strong>{insight.title}</strong>
                    <p>{insight.description}</p>
                  </article>
                ))}
              </div>
            </DashboardWidget>

            <DashboardWidget
              eyebrow="Action required"
              title="Executive alerts"
            >
              {data.alerts.length ? (
                <div className={styles.alertList}>
                  {data.alerts.map((alert) => (
                    <Link
                      className={`${styles.alert} ${styles[alert.severity]}`}
                      href={alert.href}
                      key={`${alert.severity}-${alert.title}`}
                    >
                      <AlertTriangle size={16} />
                      <span>
                        <strong>{alert.title}</strong>
                        <small>{alert.description}</small>
                      </span>
                    </Link>
                  ))}
                </div>
              ) : (
                <div className={styles.clearState}>
                  <ShieldCheck size={21} />
                  <strong>No executive alerts</strong>
                  <span>
                    There are no overdue, high-risk, or governance exceptions.
                  </span>
                </div>
              )}
            </DashboardWidget>

            <DashboardWidget
              eyebrow="Audit stream"
              title="Recent activity"
              className={styles.activityWidget}
              action={
                <Link href="/governance" className={styles.widgetLink}>
                  View governance
                </Link>
              }
            >
              <ActivityFeed activity={data.activity} />
            </DashboardWidget>

            <DashboardWidget
              eyebrow="Portfolio summary"
              title="Operating indicators"
            >
              <div className={styles.operatingList}>
                <div>
                  <Scale size={17} />
                  <span>
                    <strong>{summary.open_decisions}</strong>
                    <small>Open decisions</small>
                  </span>
                </div>
                <div>
                  <Clock3 size={17} />
                  <span>
                    <strong>{summary.overdue}</strong>
                    <small>Overdue reviews</small>
                  </span>
                </div>
                <div>
                  <AlertTriangle size={17} />
                  <span>
                    <strong>{highAndCritical}</strong>
                    <small>High or critical risk</small>
                  </span>
                </div>
                <div>
                  <FileCheck2 size={17} />
                  <span>
                    <strong>{summary.pending_approval}</strong>
                    <small>Approval-stage decisions</small>
                  </span>
                </div>
              </div>
            </DashboardWidget>
          </section>
        </>
      )}
    </Shell>
  );
}
