import Link from "next/link";
import {Network} from "lucide-react";

type RelatedConcept = {
  id: string;
  name: string;
  category: string;
  color: string;
};

export default function RelatedConcepts({
  concepts,
}: {
  concepts: RelatedConcept[];
}) {
  return (
    <section className="card workspace-panel">
      <div className="section-title">
        <Network size={18} />
        <h2>Related Concepts</h2>
      </div>
      <div className="related-list">
        {concepts.map((concept) => (
          <Link
            href={`/concepts/${concept.id}`}
            className="related-item"
            key={concept.id}
          >
            <span
              className="related-dot"
              style={{background: concept.color}}
            />
            <span>
              <strong>{concept.name}</strong>
              <small>{concept.category}</small>
            </span>
          </Link>
        ))}
      </div>
    </section>
  );
}
