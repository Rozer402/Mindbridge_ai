"use client";

import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

interface MoodPoint {
  logged_at: string;
  mood_score: number;
}

export function MoodChart({ data }: { data: MoodPoint[] }) {
  const chartData = data.map((d) => ({
    date: new Date(d.logged_at).toLocaleDateString("en-IN", { month: "short", day: "numeric" }),
    score: d.mood_score,
  }));

  if (!chartData.length) {
    return (
      <div className="flex h-48 items-center justify-center text-sm text-slate-400">
        Log your mood to see trends
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={220}>
      <AreaChart data={chartData}>
        <defs>
          <linearGradient id="moodGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#8b5cf6" stopOpacity={0.3} />
            <stop offset="95%" stopColor="#8b5cf6" stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
        <XAxis dataKey="date" tick={{ fontSize: 11 }} />
        <YAxis domain={[1, 10]} tick={{ fontSize: 11 }} />
        <Tooltip />
        <Area type="monotone" dataKey="score" stroke="#7c3aed" fill="url(#moodGrad)" strokeWidth={2} />
      </AreaChart>
    </ResponsiveContainer>
  );
}
