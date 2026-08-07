import {LucideIcon} from "lucide-react";
import Link from "next/link";
import styles from "./ExecutiveMetric.module.css";

type ExecutiveMetricProps = {
  label: string;
  value: string | number;
  detail: string;
  icon: LucideIcon;
  tone?: "neutral" | "positive" | "warning" | "critical";
  href: string;
  actionLabel: string;
};

export default function ExecutiveMetric({
  label,
  value,
  detail,
  icon: Icon,
  tone = "neutral",
  href,
  actionLabel,
}: ExecutiveMetricProps) {
  return (
    <Link
      className={`${styles.metric} ${styles[tone]}`}
      href={href}
      aria-label={`${label}: ${actionLabel}`}
    >
      <div className={styles.top}>
        <span>{label}</span>
        <span className={styles.icon}>
          <Icon size={17} strokeWidth={1.8} />
        </span>
      </div>
      <strong>{value}</strong>
      <small>{detail}</small>
      <span className={styles.action}>{actionLabel} →</span>
    </Link>
  );
}
