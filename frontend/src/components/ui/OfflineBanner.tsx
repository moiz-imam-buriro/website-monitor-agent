import { WifiOff } from "lucide-react";
import { useOnline } from "@/hooks/useOnline";

export function OfflineBanner() {
  const online = useOnline();
  if (online) return null;
  return (
    <div role="status" className="flex items-center gap-2 border-b border-line bg-degraded-tint px-4 py-2.5 text-sm text-degraded sm:px-6 lg:px-8">
      <WifiOff size={16} aria-hidden="true" className="shrink-0" />
      <span>You are offline. The data below is the last one loaded and will refresh when you reconnect.</span>
    </div>
  );
}
