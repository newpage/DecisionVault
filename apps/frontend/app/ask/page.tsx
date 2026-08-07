"use client";

import {useState} from "react";
import {ArrowRight, MessageSquareText, Sparkles} from "lucide-react";
import Shell from "@/components/Shell";
import {Card, PageHeader} from "@/components/Page";
import {api} from "@/lib/api";
import styles from "./Ask.module.css";

const executiveQuestions = [
  "Why should Northstar not be activated?",
  "Which governed evidence supports the critical alert?",
  "What must happen before conditional approval?",
  "How does Northstar compare with failed merchants?",
  "What important information is still missing?",
];

type AskResponse = {
  mode?: string;
  confidence: number;
  answer: string;
  citations: {id: string; title: string; score: number; excerpt: string}[];
};

export default function Ask() {
  const [question, setQuestion] = useState(executiveQuestions[2]);
  const [data, setData] = useState<AskResponse>();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function run(nextQuestion = question) {
    setQuestion(nextQuestion);
    setBusy(true);
    setError("");
    try {
      setData(
        await api<AskResponse>("/ask", {
          method: "POST",
          body: JSON.stringify({question: nextQuestion}),
        }),
      );
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to analyze governed evidence.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Shell>
      <PageHeader
        eyebrow="Governed AI retrieval"
        title="Ask DecisionVault"
        description="Evidence-backed answers from approved merchant-risk knowledge only."
      />

      <Card className={styles.questionCard}>
        <div className={styles.sectionHeading}>
          <Sparkles size={19} />
          <div>
            <strong>Executive questions</strong>
            <span>Select a presentation-ready question or write your own.</span>
          </div>
        </div>
        <div className={styles.presets}>
          {executiveQuestions.map((preset) => (
            <button
              type="button"
              key={preset}
              onClick={() => void run(preset)}
              disabled={busy}
            >
              <MessageSquareText size={16} />
              <span>{preset}</span>
              <ArrowRight size={15} />
            </button>
          ))}
        </div>
        <textarea
          className="input textarea"
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          aria-label="Question for DecisionVault"
        />
        <button className="btn primary" onClick={() => void run()} disabled={busy}>
          {busy ? "Analyzing…" : "Analyze governed evidence"}
        </button>
        {error ? <p className="danger">{error}</p> : null}
      </Card>

      {data ? (
        <>
          <Card>
            <div className="row between">
              <h2>Grounded answer</h2>
              <div className="row">
                <span className="badge">{data.mode || "Deterministic fallback / local AI when available"}</span>
                <span className="badge">Confidence {data.confidence}%</span>
              </div>
            </div>
            <p className={styles.answer}>{data.answer}</p>
            <p className="muted">AI output supports review. It cannot approve, restrict, reject, or publish.</p>
          </Card>
          <h2>Evidence citations</h2>
          <div className="list">
            {data.citations.map((citation, index) => (
              <Card key={`${citation.id}-${index}`}>
                <div className="row between">
                  <strong>[{index + 1}] {citation.title}</strong>
                  <span className="badge">{citation.score}%</span>
                </div>
                <p className="citation muted">{citation.excerpt}</p>
              </Card>
            ))}
          </div>
        </>
      ) : null}
    </Shell>
  );
}
