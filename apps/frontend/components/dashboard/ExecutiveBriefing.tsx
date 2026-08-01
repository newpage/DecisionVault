import {ArrowRight, Sparkles} from "lucide-react";
import Link from "next/link";
import styles from "./ExecutiveBriefing.module.css";

type ExecutiveBriefingProps = {
  openDecisions: number;
  pendingReview: number;
  publishedKnowledge: number;
  totalKnowledge: number;
};

export default function ExecutiveBriefing({
  openDecisions,
  pendingReview,
  publishedKnowledge,
  totalKnowledge,
}: ExecutiveBriefingProps) {
  const coverage =
    totalKnowledge > 0
      ? Math.round((publishedKnowledge / totalKnowledge) * 100)
      : 0;

  return (
    <section className={styles.briefing}>
      <div className={styles.icon}>
        <Sparkles size={19} strokeWidth={1.8} />
      </div>
      <div className={styles.copy}>
        <div className={styles.eyebrow}>Executive briefing</div>
        <h2>Decision operations are ready for focused review.</h2>
        <p>
          DecisionVault is tracking <strong>{openDecisions}</strong> active
          decision record{openDecisions === 1 ? "" : "s"}.{" "}
          <strong>{pendingReview}</strong> knowledge item
          {pendingReview === 1 ? "" : "s"} require review, while published
          knowledge coverage is currently <strong>{coverage}%</strong>.
        </p>
      </div>
      <Link href="/decisions" className={styles.link}>
        Open Decision Center
        <ArrowRight size={15} />
      </Link>
    </section>
  );
}
