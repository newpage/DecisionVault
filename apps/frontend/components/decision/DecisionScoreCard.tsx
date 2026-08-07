import {LucideIcon} from "lucide-react";
import styles from "./DecisionScoreCard.module.css";

type Props = {
  label: string;
  value: string;
  detail: string;
  icon: LucideIcon;
  tone?: "positive" | "warning" | "critical" | "neutral";
  onClick?: () => void;
  actionLabel?: string;
};

export default function DecisionScoreCard({
  label,
  value,
  detail,
  icon: Icon,
  tone = "neutral",
  onClick,
  actionLabel,
}: Props) {
  return (
    <button
      type="button"
      className={`${styles.card} ${styles[tone]}`}
      onClick={onClick}
      aria-label={actionLabel ? `${label}: ${actionLabel}` : label}
    >
      <div className={styles.top}>
        <span>{label}</span>
        <Icon size={17} strokeWidth={1.8} />
      </div>
      <strong>{value}</strong>
      <small>{detail}</small>
      {actionLabel ? <span className={styles.action}>{actionLabel} →</span> : null}
    </button>
  );
}
