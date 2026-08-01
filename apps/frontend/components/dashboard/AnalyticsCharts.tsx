import styles from "./AnalyticsCharts.module.css";

export type ChartDatum = {
  label: string;
  value: number;
};

export type TrendDatum = {
  label: string;
  created: number;
  completed: number;
};

export function HorizontalBars({
  data,
  tone = "cyan",
}: {
  data: ChartDatum[];
  tone?: "cyan" | "risk" | "blue";
}) {
  const maximum = Math.max(...data.map((item) => item.value), 1);

  return (
    <div className={styles.horizontalBars}>
      {data.map((item) => (
        <div className={styles.horizontalRow} key={item.label}>
          <div className={styles.horizontalLabel}>
            <span>{item.label.replaceAll("_", " ")}</span>
            <strong>{item.value}</strong>
          </div>
          <div className={styles.track}>
            <span
              className={styles[tone]}
              style={{width: `${Math.round(item.value / maximum * 100)}%`}}
            />
          </div>
        </div>
      ))}
    </div>
  );
}

export function DistributionBars({data}: {data: ChartDatum[]}) {
  const maximum = Math.max(...data.map((item) => item.value), 1);

  return (
    <div className={styles.distribution}>
      {data.map((item) => (
        <div className={styles.distributionColumn} key={item.label}>
          <div className={styles.distributionValue}>{item.value}</div>
          <div className={styles.distributionTrack}>
            <span
              style={{
                height: `${Math.max(
                  item.value > 0 ? 12 : 0,
                  Math.round(item.value / maximum * 100),
                )}%`,
              }}
            />
          </div>
          <small>{item.label}</small>
        </div>
      ))}
    </div>
  );
}

export function TrendChart({data}: {data: TrendDatum[]}) {
  const maximum = Math.max(
    ...data.flatMap((item) => [item.created, item.completed]),
    1,
  );

  return (
    <div className={styles.trend}>
      <div className={styles.legend}>
        <span><i className={styles.createdDot} />Created</span>
        <span><i className={styles.completedDot} />Completed</span>
      </div>
      <div className={styles.trendGrid}>
        {data.map((item) => (
          <div className={styles.trendMonth} key={item.label}>
            <div className={styles.trendBars}>
              <span
                className={styles.createdBar}
                style={{
                  height: `${Math.max(
                    item.created > 0 ? 10 : 0,
                    item.created / maximum * 100,
                  )}%`,
                }}
                title={`${item.created} created`}
              />
              <span
                className={styles.completedBar}
                style={{
                  height: `${Math.max(
                    item.completed > 0 ? 10 : 0,
                    item.completed / maximum * 100,
                  )}%`,
                }}
                title={`${item.completed} completed`}
              />
            </div>
            <small>{item.label}</small>
          </div>
        ))}
      </div>
    </div>
  );
}
