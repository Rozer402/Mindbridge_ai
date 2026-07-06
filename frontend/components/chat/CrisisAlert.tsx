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
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-ink/80 p-4">
      <div className="max-w-md w-full rounded-2xl border-2 border-crisis bg-parchment p-6 shadow-none">
        <div className="flex items-center gap-3 mb-4">
          <AlertTriangle className="h-8 w-8 text-crisis" />
          <h2 className="font-display text-xl text-ink">You deserve immediate support</h2>
        </div>
        <p className="font-sans text-ink/80 mb-4 text-sm leading-relaxed">
          What you&apos;re feeling is serious. Please reach out to a trained counselor right now.
        </p>
        <ul className="space-y-2 mb-6">
          {HOTLINES.map((h) => (
            <li key={h.number} className="flex items-center gap-2 text-sm">
              <Phone className="h-4 w-4 text-crisis shrink-0" />
              <span className="font-sans font-medium text-ink">{h.name}:</span>
              <a href={`tel:${h.number.replace(/-/g, "")}`} className="text-sage hover:text-ink underline transition-colors duration-300 ease-mb-ease">
                {h.number}
              </a>
            </li>
          ))}
        </ul>
        <Button className="w-full py-2.5 bg-crisis text-white hover:bg-crisis/90 rounded-full transition-colors duration-300 ease-mb-ease" onClick={onAcknowledge}>
          I understand — show me the message
        </Button>
      </div>
    </div>
  );
}
