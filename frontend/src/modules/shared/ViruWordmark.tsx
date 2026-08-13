import Image from "next/image";

type ViruWordmarkProps = {
  readonly className?: string;
};

export default function ViruWordmark({ className = "" }: ViruWordmarkProps) {
  return (
    <span className={`viru-wordmark${className ? ` ${className}` : ""}`}>
      <Image
        src="/brand/viru-wordmark.png"
        alt=""
        width={2172}
        height={724}
        sizes="(max-width: 768px) 104px, 136px"
      />
    </span>
  );
}
