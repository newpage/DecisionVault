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
        width={compact ? 118 : 210}
        height={compact ? 34 : 60}
        priority
      />
      <span>DiscoverA.ai Technology</span>
    </div>
  );
}
