import {AlertTriangle, CheckCircle2} from "lucide-react";

type Finding = {
  id: string;
  finding_type: string;
  severity: "high" | "medium" | "low";
  title: string;
  description: string;
  recommended_action: string;
  affected_count: number;
};

export default function FindingsPanel({findings}: {findings: Finding[]}) {
  return (
    <section className="card workspace-panel findings-panel">
      <div className="section-title">
        <AlertTriangle size={18} />
        <h2>Knowledge Findings</h2>
      </div>

      {findings.length === 0 ? (
        <div className="finding-clear">
          <CheckCircle2 size={20} />
          <span>No current knowledge-quality findings.</span>
        </div>
      ) : (
        <div className="finding-list">
          {findings.map((finding) => (
            <article
              className={`finding finding-${finding.severity}`}
              key={finding.id}
            >
              <div className="row between">
                <strong>{finding.title}</strong>
                <span className="finding-severity">{finding.severity}</span>
              </div>
              <p>{finding.description}</p>
              <div className="finding-action">
                <span>Recommended action</span>
                {finding.recommended_action}
              </div>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}
