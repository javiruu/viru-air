type ViruWordmarkProps = {
  readonly className?: string;
};

export default function ViruWordmark({ className = "" }: ViruWordmarkProps) {
  return (
    <span className={`viru-wordmark${className ? ` ${className}` : ""}`} aria-hidden="true">
      <span className="viru-wordmark-mark" />
      <span className="viru-wordmark-type">viru</span>
    </span>
  );
}
