import {Clock3} from "lucide-react";

type ActivityItem = {
  id: string;
  event_type: string;
  description: string;
  created_at: string;
};

export default function ActivityFeed({items}: {items: ActivityItem[]}) {
  return (
    <section className="card workspace-panel">
      <div className="section-title">
        <Clock3 size={18} />
        <h2>Recent Activity</h2>
      </div>
      {items.length === 0 ? (
        <div className="muted">No connected activity yet.</div>
      ) : (
        <div className="activity-list">
          {items.map((item) => (
            <div className="activity-item" key={item.id}>
              <span className="activity-dot" />
              <div>
                <strong>{item.event_type}</strong>
                <p>{item.description}</p>
                <span className="muted small-text">
                  {new Date(item.created_at).toLocaleString()}
                </span>
              </div>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
