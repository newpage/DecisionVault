import DecisionVaultMark from "@/components/DecisionVaultMark";

type ProductBrandProps = {
  large?: boolean;
  trademark?: boolean;
};

export default function ProductBrand({
  large = false,
  trademark = false,
}: ProductBrandProps) {
  return (
    <div className={`dv-product-brand${large ? " large" : ""}`}>
      <DecisionVaultMark size={large ? "large" : "small"} />
      <div>
        <div className="dv-product-name">
          Decision<span>Vault</span>{trademark ? <sup>™</sup> : null}
        </div>
        <div className="dv-product-tagline">
          Enterprise Decision Intelligence
        </div>
      </div>
    </div>
  );
}
