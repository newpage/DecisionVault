"use client";

import {useState} from "react";
import {Info} from "lucide-react";

type MetricCardProps = {
  label: string;
  value: number;
  suffix?: string;
  source: "calculated" | "demo";
  status: "good" | "watch" | "attention";
  explanation: string;
};

export default function MetricCard({
  label,
  value,
  suffix = "",
  source,
  status,
  explanation,
}: MetricCardProps) {
  const [open, setOpen] = useState(false);

  return (
    <article className={`workspace-metric workspace-metric-${status}`}>
      <div className="workspace-metric-top">
        <span>{label}</span>
        <button
          className="metric-info-button"
          type="button"
          onClick={() => setOpen((current) => !current)}
          aria-label={`Explain ${label}`}
        >
          <Info size={14} />
        </button>
      </div>
      <strong>
        {value}
        {suffix}
      </strong>
      <span className="metric-source">{source}</span>
      {open ? (
        <div className="metric-explanation">
          <strong>How this is calculated</strong>
          <p>{explanation}</p>
        </div>
      ) : null}
    </article>
  );
}
