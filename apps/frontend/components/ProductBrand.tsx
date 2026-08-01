import DecisionVaultMark from "@/components/DecisionVaultMark";

type ProductBrandProps = {
  large?: boolean;
};

export default function ProductBrand({
  large = false,
}: ProductBrandProps) {
  return (
    <div className={`dv-product-brand${large ? " large" : ""}`}>
      <DecisionVaultMark size={large ? "large" : "small"} />
      <div>
        <div className="dv-product-name">
          Decision<span>Vault</span>
        </div>
        <div className="dv-product-tagline">
          Enterprise Decision Intelligence
        </div>
      </div>
    </div>
  );
}
