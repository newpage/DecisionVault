import styles from "./DecisionHealth.module.css";

type DecisionHealthProps = {
  decisions: number;
  workspaces: number;
  sources: number;
  knowledgeCards: number;
};

export default function DecisionHealth({
  decisions,
  workspaces,
  sources,
  knowledgeCards,
}: DecisionHealthProps) {
  const rows = [
    {
      label: "Decision activity",
      value: decisions,
      max: Math.max(decisions, 5),
    },
    {
      label: "Governed workspaces",
      value: workspaces,
      max: Math.max(workspaces, 4),
    },
    {
      label: "Evidence sources",
      value: sources,
      max: Math.max(sources, 8),
    },
    {
      label: "Knowledge coverage",
      value: knowledgeCards,
      max: Math.max(knowledgeCards, 12),
    },
  ];

  return (
    <div className={styles.health}>
      {rows.map((row) => {
        const percentage = Math.max(
          row.value > 0 ? 12 : 0,
          Math.min(100, Math.round((row.value / row.max) * 100)),
        );

        return (
          <div className={styles.row} key={row.label}>
            <div className={styles.label}>
              <span>{row.label}</span>
              <strong>{row.value}</strong>
            </div>
            <div className={styles.track}>
              <span style={{width: `${percentage}%`}} />
            </div>
          </div>
        );
      })}
    </div>
  );
}
