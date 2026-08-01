import {Calculator} from "lucide-react";

type ScoreFactor = {
  key: string;
  label: string;
  achieved: number;
  possible: number;
  explanation: string;
};

type ScoreExplanationProps = {
  label: string;
  score: number;
  rating: "strong" | "developing" | "needs_attention";
  formula: string;
  factors: ScoreFactor[];
};

export default function ScoreExplanation({
  label,
  score,
  rating,
  formula,
  factors,
}: ScoreExplanationProps) {
  return (
    <section className="card score-explanation">
      <div className="section-title">
        <Calculator size={18} />
        <div>
          <h2>Why this score is {score}%</h2>
          <div className="muted small-text">{label}: {formula}</div>
        </div>
        <span className={`score-rating score-rating-${rating}`}>
          {rating.replace("_", " ")}
        </span>
      </div>

      <div className="score-factor-list">
        {factors.map((factor) => {
          const width = factor.possible
            ? Math.round((factor.achieved / factor.possible) * 100)
            : 0;
          return (
            <div className="score-factor" key={factor.key}>
              <div className="row between">
                <strong>{factor.label}</strong>
                <span>{factor.achieved} / {factor.possible} points</span>
              </div>
              <div className="score-track">
                <span style={{width: `${width}%`}} />
              </div>
              <p>{factor.explanation}</p>
            </div>
          );
        })}
      </div>
    </section>
  );
}
