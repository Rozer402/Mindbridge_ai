"use client";

interface Props {
  suggestions: string[];
  onSelect: (text: string) => void;
}

export function QuickReplies({ suggestions, onSelect }: Props) {
  if (!suggestions.length) return null;
  return (
    <div className="flex flex-wrap gap-2 px-4 pb-2">
      {suggestions.map((s) => (
        <button
          key={s}
          type="button"
          onClick={() => onSelect(s)}
          className="rounded-full border border-brand-200 bg-brand-50 px-3 py-1 text-xs text-brand-700 hover:bg-brand-100 transition-colors"
        >
          {s}
        </button>
      ))}
    </div>
  );
}
