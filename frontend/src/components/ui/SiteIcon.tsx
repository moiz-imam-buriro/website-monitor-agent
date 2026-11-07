import { useState } from "react";
import { cn } from "@/lib/cn";

interface SiteIconProps {
  url: string;
  name: string;
  size?: number;
}

function faviconSource(url: string): string | null {
  try {
    return `${new URL(url).origin}/favicon.ico`;
  } catch {
    return null;
  }
}

function LetterIcon({ name, size }: { name: string; size: number }) {
  return (
    <span
      aria-hidden="true"
      style={{ width: size, height: size }}
      className="inline-flex shrink-0 items-center justify-center rounded-md border border-line bg-hover text-xs font-medium uppercase text-ink"
    >
      {name.trim().charAt(0) || "?"}
    </span>
  );
}

function FaviconImage({ src, name, size }: { src: string; name: string; size: number }) {
  const [failed, setFailed] = useState(false);
  if (failed) return <LetterIcon name={name} size={size} />;
  return (
    <img
      src={src}
      alt=""
      width={size}
      height={size}
      loading="lazy"
      onError={() => setFailed(true)}
      style={{ width: size, height: size }}
      className={cn("shrink-0 rounded-md border border-line bg-card object-contain p-0.5")}
    />
  );
}

export function SiteIcon({ url, name, size = 32 }: SiteIconProps) {
  const src = faviconSource(url);
  if (!src) return <LetterIcon name={name} size={size} />;
  return <FaviconImage key={src} src={src} name={name} size={size} />;
}
