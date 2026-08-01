"use client";

import {ArrowLeft, BookOpen, ChevronRight} from "lucide-react";
import Link from "next/link";
import {useEffect, useState} from "react";
import {useParams} from "next/navigation";
import Shell from "@/components/Shell";
import {Card} from "@/components/Page";
import ActivityFeed from "@/components/workspace/ActivityFeed";
import FindingsPanel from "@/components/workspace/FindingsPanel";
import MetricCard from "@/components/workspace/MetricCard";
import RelatedConcepts from "@/components/workspace/RelatedConcepts";
import ScoreExplanation from "@/components/workspace/ScoreExplanation";
import SummaryPanel from "@/components/workspace/SummaryPanel";
import {api} from "@/lib/api";

type Workspace = {
  id: string;
  name: string;
  slug: string;
  description: string;
  category: string;
  icon: string;
  color: string;
  status: string;
  updated_at: string;
  insight: {
    summary: string;
    confidence: number;
    source: "curated" | "ai";
  };
  metrics: Array<{
    key: string;
    label: string;
    value: number;
    source: "calculated" | "demo";
    status: "good" | "watch" | "attention";
    explanation: string;
  }>;
  score_explanation: {
    label: string;
    score: number;
    rating: "strong" | "developing" | "needs_attention";
    formula: string;
    factors: Array<{
      key: string;
      label: string;
      achieved: number;
      possible: number;
      explanation: string;
    }>;
  };
  findings: Array<{
    id: string;
    finding_type: string;
    severity: "high" | "medium" | "low";
    title: string;
    description: string;
    recommended_action: string;
    affected_count: number;
  }>;
  knowledge: Array<{
    id: string;
    title: string;
    summary: string;
    lifecycle_status: string;
    approval_status: string;
    trust_score: number;
    ai_usage_allowed: boolean;
    updated_at: string;
  }>;
  activity: Array<{
    id: string;
    event_type: string;
    description: string;
    created_at: string;
  }>;
  related_concepts: Array<{
    id: string;
    name: string;
    slug: string;
    category: string;
    icon: string;
    color: string;
  }>;
};

export default function BusinessConceptWorkspacePage() {
  const params = useParams<{id: string}>();
  const [workspace, setWorkspace] = useState<Workspace | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    async function load() {
      try {
        setWorkspace(
          await api<Workspace>(`/business-concepts/${params.id}`),
        );
      } catch (caught) {
        setError(
          caught instanceof Error ? caught.message : "Unable to load workspace",
        );
      }
    }
    void load();
  }, [params.id]);

  return (
    <Shell>
      <Link href="/concepts" className="back-link">
        <ArrowLeft size={16} />
        Business Concepts
      </Link>

      {error ? <Card className="danger">{error}</Card> : null}

      {!workspace ? (
        <Card className="empty-state">
          <div className="muted">Loading Business Concept workspace…</div>
        </Card>
      ) : (
        <>
          <header className="workspace-hero">
            <div
              className="workspace-hero-icon"
              style={{color: workspace.color}}
            >
              <BookOpen size={27} />
            </div>
            <div>
              <div className="eyebrow">{workspace.category}</div>
              <h1>{workspace.name}</h1>
              <p>{workspace.description}</p>
            </div>
            <span className="status">{workspace.status}</span>
          </header>

          <div className="workspace-metrics">
            {workspace.metrics.map((metric) => (
              <MetricCard
                key={metric.key}
                label={metric.label}
                value={metric.value}
                suffix={
                  metric.key === "readiness" || metric.key === "health"
                    ? "%"
                    : ""
                }
                source={metric.source}
                status={metric.status}
                explanation={metric.explanation}
              />
            ))}
          </div>

          <SummaryPanel
            summary={workspace.insight.summary}
            confidence={workspace.insight.confidence}
            source={workspace.insight.source}
          />

          <div className="workspace-intelligence-grid">
            <ScoreExplanation {...workspace.score_explanation} />
            <FindingsPanel findings={workspace.findings} />
          </div>

          <div className="workspace-columns">
            <section className="card workspace-panel workspace-knowledge">
              <div className="section-title">
                <BookOpen size={18} />
                <h2>Connected Knowledge</h2>
              </div>
              {workspace.knowledge.length === 0 ? (
                <div className="muted">
                  No Knowledge Cards are connected to this concept yet.
                </div>
              ) : (
                <div className="knowledge-list">
                  {workspace.knowledge.map((item) => (
                    <Link
                      href="/knowledge"
                      key={item.id}
                      className="knowledge-item"
                    >
                      <div>
                        <strong>{item.title}</strong>
                        <p>{item.summary}</p>
                        <div className="row">
                          <span className="badge">{item.lifecycle_status}</span>
                          <span className="badge">{item.approval_status}</span>
                          <span className="muted small-text">
                            Trust {Math.round(item.trust_score * 100)}%
                          </span>
                          {!item.ai_usage_allowed ? (
                            <span className="badge">AI restricted</span>
                          ) : null}
                        </div>
                      </div>
                      <ChevronRight size={18} />
                    </Link>
                  ))}
                </div>
              )}
            </section>

            <div className="workspace-side">
              <ActivityFeed items={workspace.activity} />
              <RelatedConcepts concepts={workspace.related_concepts} />
            </div>
          </div>
        </>
      )}
    </Shell>
  );
}
