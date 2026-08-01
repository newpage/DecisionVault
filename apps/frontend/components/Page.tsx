import type {
  HTMLAttributes,
  ReactNode,
} from "react";

type PageHeaderProps = {
  eyebrow: string;
  title: string;
  description: string;
  action?: ReactNode;
};

export function PageHeader({
  eyebrow,
  title,
  description,
  action,
}: PageHeaderProps) {
  return (
    <div className="top">
      <div>
        <div className="eyebrow">{eyebrow}</div>
        <h1>{title}</h1>
        <div className="muted">{description}</div>
      </div>
      {action}
    </div>
  );
}

type CardProps = HTMLAttributes<HTMLElement> & {
  children: ReactNode;
};

export function Card({
  children,
  className = "",
  ...sectionProps
}: CardProps) {
  return (
    <section
      className={`card ${className}`.trim()}
      {...sectionProps}
    >
      {children}
    </section>
  );
}
