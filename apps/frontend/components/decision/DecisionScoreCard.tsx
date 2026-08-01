import {LucideIcon} from "lucide-react";
import styles from "./DecisionScoreCard.module.css";

type Props = {
  label: string;
  value: string;
  detail: string;
  icon: LucideIcon;
  tone?: "positive" | "warning" | "critical" | "neutral";
};

export default function DecisionScoreCard({
  label,
  value,
  detail,
  icon: Icon,
  tone = "neutral",
}: Props) {
  return (
    <article className={`${styles.card} ${styles[tone]}`}>
      <div className={styles.top}>
        <span>{label}</span>
        <Icon size={17} strokeWidth={1.8} />
      </div>
      <strong>{value}</strong>
      <small>{detail}</small>
    </article>
  );
}
