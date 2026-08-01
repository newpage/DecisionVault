import Image from "next/image";

type DiscoverABrandProps = {
  compact?: boolean;
};

export default function DiscoverABrand({
  compact = false,
}: DiscoverABrandProps) {
  return (
    <div className={`discovera-signature${compact ? " compact" : ""}`}>
      <Image
        src="/branding/discovera-logo.svg"
        alt="DiscoverA.ai"
        width={compact ? 132 : 210}
        height={compact ? 38 : 60}
        priority
      />
      <span>A DiscoverA.ai Technology</span>
    </div>
  );
}
