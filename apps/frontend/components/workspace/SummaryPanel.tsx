import {Sparkles} from "lucide-react";

type SummaryPanelProps = {
  summary: string;
  confidence: number;
  source: "curated" | "ai";
};

export default function SummaryPanel({
  summary,
  confidence,
  source,
}: SummaryPanelProps) {
  return (
    <section className="card insight-panel">
      <div className="row between">
        <div className="row">
          <div className="insight-icon">
            <Sparkles size={20} />
          </div>
          <div>
            <div className="eyebrow">Decision Intelligence Summary</div>
            <h2>What this concept means</h2>
          </div>
        </div>
        <div className="confidence-badge">{confidence}% confidence</div>
      </div>
      <p>{summary}</p>
      <div className="muted small-text">
        Source: {source === "ai" ? "AI generated" : "Curated business context"}
      </div>
    </section>
  );
}
