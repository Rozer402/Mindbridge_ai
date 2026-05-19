import Link from "next/link";
import { Brain, Shield, Clock, Sparkles, LineChart, HeartHandshake } from "lucide-react";
import { Button } from "@/components/ui/button";

const features = [
  { icon: Sparkles, title: "AI Chat", desc: "Empathetic conversations with few-shot prompting" },
  { icon: LineChart, title: "Mood Tracking", desc: "Log and visualize your emotional wellbeing" },
  { icon: HeartHandshake, title: "Crisis Support", desc: "India hotlines built into every session" },
  { icon: Shield, title: "Private & Secure", desc: "JWT auth, encrypted passwords, your data stays yours" },
  { icon: Clock, title: "24/7 Available", desc: "Support whenever you need someone to listen" },
  { icon: Brain, title: "Research-Backed", desc: "IEEE ICDSBS 2025 embedding + relevance pipeline" },
];

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-gradient-to-b from-brand-50 to-white">
      <header className="mx-auto flex max-w-6xl items-center justify-between px-6 py-6">
        <div className="flex items-center gap-2 font-bold text-brand-700 text-lg">
          <Brain className="h-7 w-7" />
          MindBridge AI
        </div>
        <div className="flex gap-3">
          <Link href="/login">
            <Button variant="ghost">Log in</Button>
          </Link>
          <Link href="/register">
            <Button>Start free</Button>
          </Link>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-6 pb-20">
        <section className="py-16 text-center">
          <h1 className="text-4xl md:text-5xl font-bold text-slate-900 tracking-tight">
            Your Mental Wellness Companion
          </h1>
          <p className="mt-4 text-lg text-slate-600 max-w-2xl mx-auto">
            MindBridge uses sentence embeddings and few-shot AI to deliver warm, contextual support — grounded in published IEEE research.
          </p>
          <div className="mt-8 flex flex-wrap justify-center gap-4">
            <Link href="/register">
              <Button size="lg">Start free</Button>
            </Link>
            <a href="#how-it-works">
              <Button size="lg" variant="outline">
                Learn how it works
              </Button>
            </a>
          </div>
        </section>

        <section className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4 py-12">
          {features.map(({ icon: Icon, title, desc }) => (
            <div key={title} className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
              <Icon className="h-8 w-8 text-brand-600 mb-3" />
              <h3 className="font-semibold text-slate-900">{title}</h3>
              <p className="mt-1 text-sm text-slate-500">{desc}</p>
            </div>
          ))}
        </section>

        <section id="how-it-works" className="py-12">
          <h2 className="text-2xl font-bold text-center mb-8">How it works</h2>
          <div className="grid md:grid-cols-3 gap-6">
            {[
              { step: "1", title: "Sign up", desc: "Create a free account in seconds" },
              { step: "2", title: "Talk to MindBridge", desc: "Share what's on your mind — AI responds with empathy" },
              { step: "3", title: "Track wellbeing", desc: "Log mood and see trends on your dashboard" },
            ].map((s) => (
              <div key={s.step} className="text-center p-6 rounded-xl bg-brand-50 border border-brand-100">
                <span className="inline-flex h-10 w-10 items-center justify-center rounded-full bg-brand-600 text-white font-bold">
                  {s.step}
                </span>
                <h3 className="mt-4 font-semibold">{s.title}</h3>
                <p className="text-sm text-slate-600 mt-1">{s.desc}</p>
              </div>
            ))}
          </div>
        </section>

        <section className="rounded-xl bg-slate-900 text-white p-8 text-center">
          <p className="text-sm text-slate-300">Built on IEEE Research · No personal data sold · India hotlines built-in</p>
          <p className="mt-4 text-xs text-slate-400">
            Crisis: iCall 9152987821 · Vandrevala 1860-2662-345 · NIMHANS 080-46110007
          </p>
        </section>
      </main>
    </div>
  );
}

