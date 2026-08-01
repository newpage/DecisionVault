type DecisionVaultMarkProps = {
  size?: "small" | "large";
};

export default function DecisionVaultMark({
  size = "small",
}: DecisionVaultMarkProps) {
  return (
    <div
      className={`dv-product-mark dv-product-mark-${size}`}
      aria-hidden="true"
    >
      <span className="dv-product-mark-cap" />
      <span className="dv-product-mark-vault">
        <span className="dv-product-mark-core" />
      </span>
    </div>
  );
}
