"use client";

import Link from "next/link";
import {useEffect, useState} from "react";
import {
  AlertTriangle,
  ArrowRight,
  Building2,
  CheckCircle2,
  Cpu,
  Plus,
  ShieldCheck,
} from "lucide-react";
import Shell from "@/components/Shell";
import {Card, PageHeader} from "@/components/Page";
import {api} from "@/lib/api";

type Workspace = {id: string; name: string};
type Concept = {id: string; name: string; slug: string};

type Decision = {
  id: string;
  title: string;
  question: string;
  status: string;
  recommendation: string;
  supplier_name: string;
  supplier_category: string;
  supplier_location: string;
  owner_name: string;
  due_date: string | null;
  priority: string;
  risk_level: string;
  readiness_score: number;
  readiness_status: string;
  evidence_summary: {missing_information?: string[]};
};

const paymentsDemo =
  process.env.NEXT_PUBLIC_DEMO_TENANT === "global-payments";

const defaults = {
title: paymentsDemo ? "Review merchant acquiring application" : "",
  question: paymentsDemo
    ? "Should this merchant be approved, conditionally approved, restricted, or rejected for merchant acquiring?"
    : "",
  supplier_name: paymentsDemo ? "Northstar Digital Commerce LLC" : "",
  supplier_category: paymentsDemo ? "Card-not-present merchant" : "",
  supplier_location: paymentsDemo ? "Austin, Texas" : "",
  owner_name: paymentsDemo ? "Merchant Risk Committee" : "",
  due_date: "",
  priority: "high",
  risk_level: "high",
  decision_type: "initial_qualification",
  business_unit: paymentsDemo ? "Merchant Acquiring Risk" : "",
};

export default function Decisions() {
  const [items, setItems] = useState<Decision[]>([]);
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [concepts, setConcepts] = useState<Concept[]>([]);
  const [workspaceId, setWorkspaceId] = useState("");
  const [conceptId, setConceptId] = useState("");
  const [form, setForm] = useState(defaults);
  const [show, setShow] = useState(false);
  const [error, setError] = useState("");

  async function load() {
    const [decisions, workspaceRows, conceptRows] = await Promise.all([
      api<Decision[]>("/decisions"),
      api<Workspace[]>("/workspaces"),
      api<Concept[]>("/business-concepts"),
    ]);
    setItems(decisions);
    setWorkspaces(workspaceRows);
    setConcepts(conceptRows);

    if (!workspaceId && workspaceRows[0]) {
      setWorkspaceId(workspaceRows[0].id);
    }
    if (!conceptId) {
      if (conceptRows[0]) setConceptId(conceptRows[0].id);
    }
  }

  useEffect(() => {
    void load().catch((caught) =>
      setError(
        caught instanceof Error ? caught.message : "Unable to load",
      ),
    );
  }, []);

  function update(name: string, value: string) {
    setForm((current) => ({...current, [name]: value}));
  }

  async function create() {
    setError("");
    try {
      await api("/decisions", {
        method: "POST",
        body: JSON.stringify({
          workspace_id: workspaceId,
          business_concept_id: conceptId || null,
          ...form,
          due_date: form.due_date || null,
        }),
      });
      setShow(false);
      setForm(defaults);
      await load();
    } catch (caught) {
      setError(
        caught instanceof Error
          ? caught.message
          : "Unable to create decision",
      );
    }
  }

  return (
    <Shell>
      <PageHeader
	eyebrow={
		paymentsDemo ? "Merchant Decision Intelligence" : "Decision Intelligence"
	}
	title={paymentsDemo ? "Merchant Acquiring Decisions" : "Decisions"}
	description={
		paymentsDemo
			? "Underwrite merchants using governed fraud, chargeback, KYC/KYB, AML, sanctions, and operational-risk evidence."
			: "Make governed decisions using transparent evidence, risk, ownership, and accountable review."
	}
        action={
          <button
            className="btn primary row"
            onClick={() => setShow((current) => !current)}
          >
            <Plus size={16} />
		{paymentsDemo ? "New merchant decision" : "New decision"}
          </button>
        }
      />

      <div className="decision-summary-grid">
        <Card className="metric">
          <span className="muted">Open decisions</span>
          <strong>
            {
              items.filter(
                (item) =>
                  !["approved", "rejected", "closed"].includes(item.status),
              ).length
            }
          </strong>
        </Card>
        <Card className="metric">
          <span className="muted">High-risk reviews</span>
          <strong>
            {
              items.filter(
                (item) =>
                  ["high", "critical"].includes(item.risk_level) &&
                  !["approved", "rejected", "closed"].includes(item.status),
              ).length
            }
          </strong>
        </Card>
        <Card className="metric">
          <span className="muted">Ready for review</span>
          <strong>
            {
              items.filter((item) => item.readiness_score >= 80)
                .length
            }
          </strong>
        </Card>
      </div>

      {show ? (
        <Card className="decision-form">
          <div className="section-title">
            <Cpu size={19} />
		<h2> {paymentsDemo ? "New Merchant Acquiring Review" : "New Decision"} </h2>
          </div>

          <div className="decision-form-grid">
            {(
              [
                ["supplier_name", "Merchant legal name"],
                ["supplier_location", "Merchant location and market"],
                ["owner_name", "Decision owner"],
                ["due_date", "Due date"],
              ] as const
            ).map(([key, label]) => (
              <label key={key}>
                <span>{label}</span>
                <input
                  type={key === "due_date" ? "date" : "text"}
                  className="input"
                  value={form[key]}
                  onChange={(event) =>
                    update(key, event.target.value)
                  }
                />
              </label>
            ))}

            <label>
              <span>Priority</span>
              <select
                className="input"
                value={form.priority}
                onChange={(event) =>
                  update("priority", event.target.value)
                }
              >
                {["low", "medium", "high", "critical"].map(
                  (value) => (
                    <option key={value}>{value}</option>
                  ),
                )}
              </select>
            </label>

            <label>
              <span>Risk level</span>
              <select
                className="input"
                value={form.risk_level}
                onChange={(event) =>
                  update("risk_level", event.target.value)
                }
              >
                {["low", "medium", "high", "critical"].map(
                  (value) => (
                    <option key={value}>{value}</option>
                  ),
                )}
              </select>
            </label>

            <label>
              <span>Workspace</span>
              <select
                className="input"
                value={workspaceId}
                onChange={(event) =>
                  setWorkspaceId(event.target.value)
                }
              >
                {workspaces.map((workspace) => (
                  <option value={workspace.id} key={workspace.id}>
                    {workspace.name}
                  </option>
                ))}
              </select>
            </label>

            <label>
              <span>Business concept</span>
              <select
                className="input"
                value={conceptId}
                onChange={(event) => setConceptId(event.target.value)}
              >
                {concepts.map((concept) => (
                  <option value={concept.id} key={concept.id}>
                    {concept.name}
                  </option>
                ))}
              </select>
            </label>
          </div>

          <label>
            <span>Decision title</span>
            <input
              className="input"
              value={form.title}
              onChange={(event) =>
                update("title", event.target.value)
              }
            />
          </label>

          <label>
            <span>Decision question</span>
            <textarea
              className="input textarea"
              value={form.question}
              onChange={(event) =>
                update("question", event.target.value)
              }
            />
          </label>

          <div className="decision-control-note">
            <ShieldCheck size={18} />
            Evidence is assessed across governance, operational
            controls, risk, continuity, security, and accountability.
          </div>

          <button
            className="btn primary"
            onClick={() => void create()}
          >
            Create decision
          </button>
        </Card>
      ) : null}

      {error ? <Card className="danger">{error}</Card> : null}

      <div className="decision-list">
        {items.map((decision) => {
          const missing =
            decision.evidence_summary?.missing_information ?? [];

          return (
            <Card
              className="supplier-decision-card"
              key={decision.id}
            >
              <div className="row between decision-card-header">
                <div className="row">
                  <div className="supplier-icon">
                    <Building2 size={21} />
                  </div>
                  <div>
                    <div className="eyebrow">
                      {decision.supplier_category}
                    </div>
                    <h2>
                      {decision.supplier_name || decision.title}
                    </h2>
                    <div className="muted">{decision.title}</div>
                  </div>
                </div>

                <div
                  className={`readiness readiness-${decision.readiness_status}`}
                >
                  <strong>{decision.readiness_score}%</strong>
                  <span>Decision readiness</span>
                </div>
              </div>

              <div className="decision-meta-grid">
                <span>
                  <b>Owner</b>
                  {decision.owner_name || "Unassigned"}
                </span>
                <span>
                  <b>Status</b>
                  {decision.status.replaceAll("_", " ")}
                </span>
                <span>
                  <b>Priority</b>
                  {decision.priority}
                </span>
                <span>
                  <b>Risk</b>
                  {decision.risk_level}
                </span>
                <span>
                  <b>Location</b>
                  {decision.supplier_location || "Not provided"}
                </span>
                <span>
                  <b>Due</b>
                  {decision.due_date ?? "Not scheduled"}
                </span>
              </div>

              <p className="decision-question">
                {decision.question}
              </p>
              <p className="muted">{decision.recommendation}</p>

              {missing.length ? (
                <div className="decision-findings">
                  <div className="row">
                    <AlertTriangle size={17} />
                    <strong>Information requiring attention</strong>
                  </div>
                  {missing.map((item) => (
                    <div key={item}>• {item}</div>
                  ))}
                </div>
              ) : (
                <div className="decision-clear row">
                  <CheckCircle2 size={17} />
                  Evidence baseline is complete for formal review.
                </div>
              )}

              <div style={{marginTop: 16}}>
                <Link
                  href={`/decisions/${decision.id}`}
                  className="btn primary row"
                  style={{display: "inline-flex"}}
                >
                  Open decision workspace
                  <ArrowRight size={15} />
                </Link>
              </div>
            </Card>
          );
        })}
      </div>
    </Shell>
  );
}
