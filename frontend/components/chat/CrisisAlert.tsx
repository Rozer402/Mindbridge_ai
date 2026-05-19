"use client";

import { AlertTriangle, Phone } from "lucide-react";
import { Button } from "@/components/ui/button";

interface Props {
  onAcknowledge: () => void;
}

const HOTLINES = [
  { name: "iCall (India)", number: "9152987821" },
  { name: "Vandrevala Foundation", number: "1860-2662-345" },
  { name: "NIMHANS Helpline", number: "080-46110007" },
  { name: "SNEHI", number: "044-24640050" },
];

export function CrisisAlert({ onAcknowledge }: Props) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      <div className="max-w-md w-full rounded-2xl border-4 border-red-500 bg-white p-6 shadow-2xl">
        <div className="flex items-center gap-3 text-red-600 mb-4">
          <AlertTriangle className="h-8 w-8" />
          <h2 className="text-xl font-bold">You deserve immediate support</h2>
        </div>
        <p className="text-slate-700 mb-4 text-sm leading-relaxed">
          What you&apos;re feeling is serious. Please reach out to a trained counselor right now.
        </p>
        <ul className="space-y-2 mb-6">
          {HOTLINES.map((h) => (
            <li key={h.number} className="flex items-center gap-2 text-sm">
              <Phone className="h-4 w-4 text-red-500 shrink-0" />
              <span className="font-medium">{h.name}:</span>
              <a href={`tel:${h.number.replace(/-/g, "")}`} className="text-brand-600 underline">
                {h.number}
              </a>
            </li>
          ))}
        </ul>
        <Button variant="destructive" className="w-full" onClick={onAcknowledge}>
          I understand — show me the message
        </Button>
      </div>
    </div>
  );
}
