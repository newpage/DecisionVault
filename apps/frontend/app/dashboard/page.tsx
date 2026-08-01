"use client";

import Link from "next/link";
import {useEffect, useMemo, useState} from "react";
import {
  AlertTriangle,
  BookOpen,
  Boxes,
  FileCheck2,
  FolderKanban,
  RefreshCw,
  Scale,
} from "lucide-react";
import Shell from "@/components/Shell";
import {api} from "@/lib/api";
import ActivityFeed, {
  DashboardActivity,
} from "@/components/dashboard/ActivityFeed";
import DashboardWidget from "@/components/dashboard/DashboardWidget";
import DecisionHealth from "@/components/dashboard/DecisionHealth";
import ExecutiveBriefing from "@/components/dashboard/ExecutiveBriefing";
import ExecutiveMetric from "@/components/dashboard/ExecutiveMetric";
import styles from "./Dashboard.module.css";

type DashboardResponse = {
  metrics: {
    workspaces?: number;
    knowledge_cards?: number;
    published?: number;
    pending_review?: number;
    sources?: number;
    decisions?: number;
  };
  activity: DashboardActivity[];
};

const EMPTY_DASHBOARD: DashboardResponse = {
  metrics: {},
  activity: [],
};

function greeting() {
  const hour = new Date().getHours();
  if (hour < 12) return "Good morning";
  if (hour < 18) return "Good afternoon";
  return "Good evening";
}

export default function Dashboard() {
  const [data, setData] = useState<DashboardResponse>(EMPTY_DASHBOARD);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");

  async function load(isRefresh = false) {
    if (isRefresh) setRefreshing(true);
    else setLoading(true);

    setError("");

    try {
      const response = await api<DashboardResponse>("/dashboard");
      setData(response);
    } catch (caught) {
      setError(
        caught instanceof Error
          ? caught.message
          : "Unable to load the executive dashboard.",
      );
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }

  useEffect(() => {
    void load();
  }, []);

  const metrics = data.metrics ?? {};
  const decisions = metrics.decisions ?? 0;
  const knowledgeCards = metrics.knowledge_cards ?? 0;
  const published = metrics.published ?? 0;
  const pendingReview = metrics.pending_review ?? 0;
  const workspaces = metrics.workspaces ?? 0;
  const sources = metrics.sources ?? 0;

  const publicationRate = useMemo(
    () =>
      knowledgeCards > 0
        ? Math.round((published / knowledgeCards) * 100)
        : 0,
    [knowledgeCards, published],
  );

  const statusRows = [
    {
      label: "Published knowledge",
      value: published,
      total: Math.max(knowledgeCards, published, 1),
      tone: "good",
    },
    {
      label: "Pending review",
      value: pendingReview,
      total: Math.max(knowledgeCards, pendingReview, 1),
      tone: "watch",
    },
    {
      label: "Evidence sources",
      value: sources,
      total: Math.max(sources, knowledgeCards, 1),
      tone: "neutral",
    },
  ];

  return (
    <Shell>
      <header className={styles.pageHeader}>
        <div>
          <div className={styles.eyebrow}>Enterprise overview</div>
          <h1>Decision Intelligence</h1>
          <p>
            {greeting()}. Review organizational decisions, governed knowledge,
            evidence, and readiness from one executive workspace.
          </p>
        </div>

        <div className={styles.headerActions}>
          <span>
            {new Date().toLocaleDateString(undefined, {
              weekday: "long",
              month: "long",
              day: "numeric",
              year: "numeric",
            })}
          </span>
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

      {loading ? (
        <div className={styles.loadingGrid}>
          {Array.from({length: 6}).map((_, index) => (
            <div className={styles.loadingCard} key={index} />
          ))}
        </div>
      ) : (
        <>
          <ExecutiveBriefing
            openDecisions={decisions}
            pendingReview={pendingReview}
            publishedKnowledge={published}
            totalKnowledge={knowledgeCards}
          />

          <section className={styles.metricGrid}>
            <ExecutiveMetric
              label="Open decisions"
              value={decisions}
              detail="Tracked decision records"
              icon={Scale}
              tone={decisions > 0 ? "warning" : "neutral"}
            />
            <ExecutiveMetric
              label="Pending review"
              value={pendingReview}
              detail="Knowledge awaiting approval"
              icon={AlertTriangle}
              tone={pendingReview > 0 ? "critical" : "positive"}
            />
            <ExecutiveMetric
              label="Knowledge cards"
              value={knowledgeCards}
              detail={`${published} published`}
              icon={BookOpen}
              tone="positive"
            />
            <ExecutiveMetric
              label="Publication rate"
              value={`${publicationRate}%`}
              detail="Approved knowledge coverage"
              icon={FileCheck2}
              tone={publicationRate >= 80 ? "positive" : "warning"}
            />
            <ExecutiveMetric
              label="Evidence sources"
              value={sources}
              detail="Connected source documents"
              icon={Boxes}
              tone="neutral"
            />
            <ExecutiveMetric
              label="Workspaces"
              value={workspaces}
              detail="Governed operating areas"
              icon={FolderKanban}
              tone="neutral"
            />
          </section>

          <section className={styles.dashboardGrid}>
            <DashboardWidget
              title="Decision and knowledge health"
              eyebrow="Operating picture"
              className={styles.healthWidget}
            >
              <DecisionHealth
                decisions={decisions}
                workspaces={workspaces}
                sources={sources}
                knowledgeCards={knowledgeCards}
              />
            </DashboardWidget>

            <DashboardWidget
              title="Governance posture"
              eyebrow="Content lifecycle"
              className={styles.governanceWidget}
            >
              <div className={styles.statusList}>
                {statusRows.map((row) => {
                  const width = Math.max(
                    row.value > 0 ? 8 : 0,
                    Math.min(100, Math.round((row.value / row.total) * 100)),
                  );

                  return (
                    <div className={styles.statusRow} key={row.label}>
                      <div>
                        <span>{row.label}</span>
                        <strong>{row.value}</strong>
                      </div>
                      <div className={styles.statusTrack}>
                        <span
                          className={styles[row.tone]}
                          style={{width: `${width}%`}}
                        />
                      </div>
                    </div>
                  );
                })}
              </div>
            </DashboardWidget>

            <DashboardWidget
              title="Recent activity"
              eyebrow="Audit stream"
              action={
                <Link href="/governance" className={styles.widgetLink}>
                  View governance
                </Link>
              }
              className={styles.activityWidget}
            >
              <ActivityFeed activity={data.activity ?? []} />
            </DashboardWidget>

            <DashboardWidget
              title="Executive actions"
              eyebrow="Next steps"
              className={styles.actionsWidget}
            >
              <div className={styles.actionList}>
                <Link href="/decisions">
                  <Scale size={17} />
                  <span>
                    <strong>Review decision portfolio</strong>
                    <small>
                      Open supplier and enterprise decision records.
                    </small>
                  </span>
                </Link>
                <Link href="/governance">
                  <FileCheck2 size={17} />
                  <span>
                    <strong>Resolve review queue</strong>
                    <small>
                      Approve or return governed knowledge items.
                    </small>
                  </span>
                </Link>
                <Link href="/sources">
                  <Boxes size={17} />
                  <span>
                    <strong>Add trusted evidence</strong>
                    <small>
                      Connect source documentation to DecisionVault.
                    </small>
                  </span>
                </Link>
              </div>
            </DashboardWidget>
          </section>
        </>
      )}
    </Shell>
  );
}
