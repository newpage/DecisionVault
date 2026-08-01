import {ReactNode} from "react";
import styles from "./DashboardWidget.module.css";

type DashboardWidgetProps = {
  title: string;
  eyebrow?: string;
  action?: ReactNode;
  className?: string;
  children: ReactNode;
};

export default function DashboardWidget({
  title,
  eyebrow,
  action,
  className = "",
  children,
}: DashboardWidgetProps) {
  return (
    <section className={`${styles.widget} ${className}`}>
      <header className={styles.header}>
        <div>
          {eyebrow ? <div className={styles.eyebrow}>{eyebrow}</div> : null}
          <h2>{title}</h2>
        </div>
        {action ? <div className={styles.action}>{action}</div> : null}
      </header>
      <div className={styles.body}>{children}</div>
    </section>
  );
}
