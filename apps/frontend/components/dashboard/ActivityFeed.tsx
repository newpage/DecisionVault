import {Clock3} from "lucide-react";
import styles from "./ActivityFeed.module.css";

export type DashboardActivity = {
  id: string;
  event_type: string;
  description: string;
  created_at: string;
};

type ActivityFeedProps = {
  activity: DashboardActivity[];
};

function readableEventType(value: string) {
  return value
    .replace(/([a-z])([A-Z])/g, "$1 $2")
    .replaceAll("_", " ");
}

export default function ActivityFeed({activity}: ActivityFeedProps) {
  if (!activity.length) {
    return (
      <div className={styles.empty}>
        <Clock3 size={20} />
        <span>Activity will appear as decisions and knowledge evolve.</span>
      </div>
    );
  }

  return (
    <div className={styles.feed}>
      {activity.map((item) => (
        <article className={styles.item} key={item.id}>
          <span className={styles.dot} />
          <div>
            <div className={styles.row}>
              <strong>{readableEventType(item.event_type)}</strong>
              <time>
                {new Date(item.created_at).toLocaleString(undefined, {
                  month: "short",
                  day: "numeric",
                  hour: "numeric",
                  minute: "2-digit",
                })}
              </time>
            </div>
            <p>{item.description}</p>
          </div>
        </article>
      ))}
    </div>
  );
}
