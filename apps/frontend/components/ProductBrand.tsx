import DecisionVaultMark from "@/components/DecisionVaultMark";

type ProductBrandProps = {
  large?: boolean;
  trademark?: boolean;
  tagline?: string;
};

export default function ProductBrand({
  large = false,
  trademark = false,
  tagline = "Enterprise Decision Intelligence",
}: ProductBrandProps) {
  return (
    <div className={`dv-product-brand${large ? " large" : ""}`}>
      <DecisionVaultMark size={large ? "large" : "small"} />
      <div>
        <div className="dv-product-name">
          Decision<span>Vault</span>{trademark ? <sup>™</sup> : null}
        </div>
        <div className="dv-product-tagline">
          {tagline}
        </div>
      </div>
    </div>
  );
}
