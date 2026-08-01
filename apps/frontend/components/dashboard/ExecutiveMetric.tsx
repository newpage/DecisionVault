import {LucideIcon} from "lucide-react";
import styles from "./ExecutiveMetric.module.css";

type ExecutiveMetricProps = {
  label: string;
  value: string | number;
  detail: string;
  icon: LucideIcon;
  tone?: "neutral" | "positive" | "warning" | "critical";
};

export default function ExecutiveMetric({
  label,
  value,
  detail,
  icon: Icon,
  tone = "neutral",
}: ExecutiveMetricProps) {
  return (
    <article className={`${styles.metric} ${styles[tone]}`}>
      <div className={styles.top}>
        <span>{label}</span>
        <span className={styles.icon}>
          <Icon size={17} strokeWidth={1.8} />
        </span>
      </div>
      <strong>{value}</strong>
      <small>{detail}</small>
    </article>
  );
}
