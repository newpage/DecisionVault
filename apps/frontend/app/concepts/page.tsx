"use client";

import {
  BadgeCheck,
  CircleDot,
  GitPullRequest,
  GraduationCap,
  Network,
  Search,
  ShieldCheck,
  TriangleAlert,
} from "lucide-react";
import Link from "next/link";
import {useEffect, useMemo, useState} from "react";
import Shell from "@/components/Shell";
import {Card, PageHeader} from "@/components/Page";
import {api} from "@/lib/api";

type BusinessConcept = {
  id: string;
  name: string;
  slug: string;
  description: string;
  category: string;
  icon: string;
  color: string;
  status: string;
  knowledge_count: number;
  updated_at: string;
};

const iconMap = {
  BadgeCheck,
  CircleDot,
  GitPullRequest,
  GraduationCap,
  Network,
  ShieldCheck,
  TriangleAlert,
} as const;

export default function BusinessConceptsPage() {
  const [concepts, setConcepts] = useState<BusinessConcept[]>([]);
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function load(nextQuery = query) {
    setLoading(true);
    setError("");
    try {
      const suffix = nextQuery.trim()
        ? `?q=${encodeURIComponent(nextQuery.trim())}`
        : "";
      setConcepts(await api<BusinessConcept[]>(`/business-concepts${suffix}`));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to load concepts");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load("");
  }, []);

  const totalKnowledge = useMemo(
    () => concepts.reduce((sum, concept) => sum + concept.knowledge_count, 0),
    [concepts],
  );

  return (
    <Shell>
      <PageHeader
        eyebrow="Business Knowledge Model"
        title="Business Concepts"
        description="Navigate trusted knowledge through the business topics, processes, risks, and responsibilities your organization understands."
      />

      <div className="grid metrics" style={{marginBottom: 16}}>
        <Card className="metric">
          <span className="muted">Active concepts</span>
          <strong>{concepts.length}</strong>
        </Card>
        <Card className="metric">
          <span className="muted">Connected knowledge</span>
          <strong>{totalKnowledge}</strong>
        </Card>
        <Card className="metric">
          <span className="muted">Knowledge model status</span>
          <strong className="status">Active</strong>
        </Card>
      </div>

      <Card>
        <div className="concept-toolbar">
          <div style={{position: "relative", flex: 1}}>
            <Search
              size={17}
              style={{position: "absolute", left: 13, top: 13, color: "#91a2ba"}}
            />
            <input
              className="input"
              style={{paddingLeft: 40}}
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter") void load();
              }}
              placeholder="Search concepts, categories, or business topics"
            />
          </div>
          <button className="btn primary" onClick={() => void load()}>
            Search
          </button>
        </div>
      </Card>

      {error ? <Card className="danger" style={{marginTop: 16}}>{error}</Card> : null}

      {loading ? (
        <Card className="empty-state" style={{marginTop: 16}}>
          <div className="muted">Loading business knowledge model…</div>
        </Card>
      ) : concepts.length === 0 ? (
        <Card className="empty-state" style={{marginTop: 16}}>
          <Network size={34} style={{marginBottom: 12}} />
          <h2>No matching concepts</h2>
          <div className="muted">Try a broader search term.</div>
        </Card>
      ) : (
        <div className="concept-grid" style={{marginTop: 16}}>
          {concepts.map((concept) => {
            const Icon = iconMap[concept.icon as keyof typeof iconMap] ?? Network;
            return (
              <Link href={`/concepts/${concept.id}`} key={concept.id}>
                <Card className="concept-card">
                  <div
                    className="concept-accent"
                    style={{background: concept.color}}
                  />
                  <div>
                    <div className="row between">
                      <div
                        className="concept-icon"
                        style={{color: concept.color}}
                      >
                        <Icon size={22} />
                      </div>
                      <span className="category-pill">{concept.category}</span>
                    </div>
                    <h2>{concept.name}</h2>
                    <p>{concept.description}</p>
                  </div>
                  <div className="concept-meta">
                    <span>
                      <span className="concept-count">{concept.knowledge_count}</span>
                      {" "}Knowledge Cards
                    </span>
                    <span className="status">{concept.status}</span>
                  </div>
                </Card>
              </Link>
            );
          })}
        </div>
      )}
    </Shell>
  );
}
