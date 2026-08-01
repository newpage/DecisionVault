type MetricCardProps = {
  label: string;
  value: number;
  suffix?: string;
  source: "calculated" | "demo";
  status: "good" | "watch" | "attention";
};

export default function MetricCard({
  label,
  value,
  suffix = "",
  source,
  status,
}: MetricCardProps) {
  return (
    <article className={`workspace-metric workspace-metric-${status}`}>
      <div className="workspace-metric-top">
        <span>{label}</span>
        <span className="metric-source">{source}</span>
      </div>
      <strong>
        {value}
        {suffix}
      </strong>
    </article>
  );
}
