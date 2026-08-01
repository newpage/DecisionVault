import styles from "./ReadinessBreakdown.module.css";

type Factor = {
  points: number;
  possible: number;
  count: number;
};

type Props = {
  calculation: Record<string, Factor>;
};

function label(value: string) {
  return value
    .replaceAll("_", " ")
    .replace(/\w/g, (character) => character.toUpperCase());
}

export default function ReadinessBreakdown({calculation}: Props) {
  const rows = Object.entries(calculation);

  if (!rows.length) {
    return (
      <div className={styles.empty}>
        Readiness factors are not available for this decision.
      </div>
    );
  }

  return (
    <div className={styles.list}>
      {rows.map(([key, factor]) => {
        const percentage =
          factor.possible > 0
            ? Math.round(factor.points / factor.possible * 100)
            : 0;

        return (
          <div className={styles.factor} key={key}>
            <div className={styles.heading}>
              <span>{label(key)}</span>
              <strong>
                {factor.points}/{factor.possible}
              </strong>
            </div>
            <div className={styles.track}>
              <span style={{width: `${percentage}%`}} />
            </div>
            <small>{factor.count} supporting item(s)</small>
          </div>
        );
      })}
    </div>
  );
}
