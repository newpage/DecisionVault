"use client";

import {useEffect, useState} from "react";
import Shell from "@/components/Shell";
import {Card, PageHeader} from "@/components/Page";
import {api} from "@/lib/api";

type StructuredExtraction = {
  extraction_mode?: string;
  facts?: string[];
  provenance?: string;
  review_status?: string;
};

function extraction(body: string): StructuredExtraction | null {
  try {
    const value = JSON.parse(body);
    return value && typeof value === "object" ? value : null;
  } catch {
    return null;
  }
}

export default function Knowledge() {
  const [cards, setCards] = useState<any[]>([]);
  const [query, setQuery] = useState("");
  const load = () =>
    api<any[]>(`/knowledge${query ? `?q=${encodeURIComponent(query)}` : ""}`).then(
      setCards,
    );

  useEffect(() => {
    void load();
  }, []);

  return (
    <Shell>
      <PageHeader
        eyebrow="AI moment 1 · Document intelligence"
        title="Payments Knowledge Cards"
        description="Structured, reviewable facts extracted from synthetic merchant, KYC/KYB, fraud, chargeback, AML, sanctions, and policy documents."
      />
      <Card>
        <div className="row between">
          <div>
            <strong>Deterministic synthetic extraction</strong>
            <p className="muted">
              Pre-seeded for presentation reliability. Every card remains governed,
              cited, reviewable, and human-published.
            </p>
          </div>
          <span className="badge">No live model dependency</span>
        </div>
        <div className="row">
          <input
            className="input"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search payments Knowledge Cards"
          />
          <button className="btn primary" onClick={load}>Search</button>
        </div>
      </Card>
      <div className="list" style={{marginTop: 16}}>
        {cards.map((card) => {
          const structured = extraction(card.body);
          return (
            <Card key={card.id} className="knowledge-detail-card">
              <div className="row between">
                <strong>{card.title}</strong>
                <span className="badge">{card.lifecycle_status}</span>
              </div>
              <p className="knowledge-summary">{card.summary}</p>
              <div className="row">
                <span className="badge">{card.authority_level.replaceAll("_", " ")}</span>
                <span className="badge">Trust {Math.round(card.trust_score * 100)}%</span>
                <span className="badge">AI retrieval allowed</span>
              </div>
              {structured ? (
                <div className="notice">
                  <div className="row between">
                    <strong>Reviewable structured extraction</strong>
                    <span className="badge">{structured.extraction_mode}</span>
                  </div>
                  <ul>{structured.facts?.map((fact) => <li key={fact}>{fact}</li>)}</ul>
                  <p><b>Provenance:</b> {structured.provenance}</p>
                  <p><b>Governance:</b> {structured.review_status}</p>
                </div>
              ) : null}
              {card.decision_lesson_provenance ? (
                <div className="notice">
                  <strong>Immutable Decision-learning provenance</strong>
                  <p>Source Decision: {card.decision_lesson_provenance.source_decision?.title}</p>
                  <p>Observed evaluation: {card.decision_lesson_provenance.evaluation?.classification?.replaceAll("_", " ")}</p>
                  <p><b>Applicability:</b> {card.decision_lesson_provenance.applicability}</p>
                  <p><b>Limitations:</b> {card.decision_lesson_provenance.limitations}</p>
                  <p>Observed usefulness supports reuse consideration but does not prove universal applicability.</p>
                </div>
              ) : null}
            </Card>
          );
        })}
      </div>
    </Shell>
  );
}
