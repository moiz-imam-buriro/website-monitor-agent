import { CartesianGrid, ComposedChart, Line, ResponsiveContainer, Scatter, Tooltip, XAxis, YAxis } from "recharts";
import { useTheme } from "@/hooks/useTheme";
import { formatExact } from "@/lib/format";
import { EmptyState } from "@/components/ui/Layout";
import type { CheckRead } from "@/types";

const PALETTE = {
  light: { line: "#0b6bcb", failed: "#b91c1c", axis: "#475569", grid: "#e3e6eb", tooltipBg: "#ffffff", tooltipBorder: "#e3e6eb" },
  dark: { line: "#6cb2ff", failed: "#f87171", axis: "#a7b1bf", grid: "#243041", tooltipBg: "#121822", tooltipBorder: "#243041" },
};

interface ChartPoint {
  time: number;
  ms: number | null;
}

function toPoints(checks: CheckRead[]): { line: ChartPoint[]; failed: ChartPoint[] } {
  const sorted = [...checks].sort((a, b) => Date.parse(a.checked_at) - Date.parse(b.checked_at));
  const line: ChartPoint[] = [];
  const failed: ChartPoint[] = [];
  for (const check of sorted) {
    const time = Date.parse(check.checked_at);
    if (Number.isNaN(time)) continue;
    line.push({ time, ms: check.ok ? check.response_time_ms : null });
    if (!check.ok) failed.push({ time, ms: 0 });
  }
  return { line, failed };
}

function formatTick(value: number): string {
  return new Date(value).toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" });
}

export function ResponseChart({ checks }: { checks: CheckRead[] }) {
  const { theme } = useTheme();
  const colors = PALETTE[theme];
  const { line, failed } = toPoints(checks);

  if (line.length === 0) {
    return <EmptyState title="No checks in this period" description="Results appear here after the first check runs." />;
  }

  return (
    <div className="flex min-w-0 flex-col gap-3">
      <div className="h-[240px] w-full min-w-0 sm:h-[280px]">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
            <CartesianGrid stroke={colors.grid} vertical={false} />
            <XAxis
              dataKey="time"
              type="number"
              domain={["dataMin", "dataMax"]}
              tickFormatter={formatTick}
              tick={{ fill: colors.axis, fontSize: 12 }}
              stroke={colors.grid}
              minTickGap={24}
            />
            <YAxis
              dataKey="ms"
              width={56}
              domain={[0, "auto"]}
              tickFormatter={(value: number) => `${Math.round(value)} ms`}
              tick={{ fill: colors.axis, fontSize: 12 }}
              stroke={colors.grid}
            />
            <Tooltip
              labelFormatter={(label) => formatExact(new Date(Number(label)).toISOString())}
              contentStyle={{ background: colors.tooltipBg, border: `1px solid ${colors.tooltipBorder}`, borderRadius: 8, fontSize: 12 }}
            />
            <Line
              name="Response time"
              data={line}
              dataKey="ms"
              stroke={colors.line}
              strokeWidth={2}
              dot={false}
              connectNulls={false}
              type="monotone"
              isAnimationActive={false}
            />
            <Scatter name="Failed check" data={failed} dataKey="ms" fill={colors.failed} isAnimationActive={false} />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
      <p className="text-xs text-muted">Red dots mark checks that failed. Gaps mean no response time was recorded.</p>
    </div>
  );
}
