"use client";

import { useEffect, useRef } from "react";
import { MessageBubble } from "./MessageBubble";
import { TypingIndicator } from "./TypingIndicator";
import { ChatInput } from "./ChatInput";
import { QuickReplies } from "./QuickReplies";
import { CrisisAlert } from "./CrisisAlert";
import { useChatStore } from "@/store/chatStore";
import { chatApi } from "@/lib/api";
import type { ChatMessage } from "@/types/chat.types";

const STARTERS = [
  "I'm feeling anxious about my exams",
  "Work is overwhelming me",
  "I can't sleep at night",
  "I feel lonely lately",
];

const QUICK_REPLIES = [
  "Tell me more",
  "That helps, thank you",
  "I need coping strategies",
];

export function ChatWindow() {
  const {
    messages,
    activeSessionId,
    isTyping,
    showCrisis,
    addMessage,
    setMessages,
    setActiveSession,
    setTyping,
    setShowCrisis,
  } = useChatStore();
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isTyping]);

  const sendMessage = async (text: string) => {
    addMessage({ role: "user", content: text });
    setTyping(true);
    try {
      const { data } = await chatApi.sendMessage(text, activeSessionId || undefined);
      if (!activeSessionId) setActiveSession(data.session_id);
      addMessage({
        role: "assistant",
        content: data.response,
        relevance_score: data.relevance_score,
        is_crisis: data.is_crisis,
      });
      if (data.is_crisis) setShowCrisis(true);
    } catch {
      addMessage({
        role: "assistant",
        content: "I'm having trouble connecting right now. Please try again in a moment.",
      });
    } finally {
      setTyping(false);
    }
  };

  return (
    <div className="relative flex flex-col h-full bg-parchment">
      <div className="mb-ambient-bg" />
      <div className="flex flex-col h-full relative z-10 flex-1">
        {showCrisis && <CrisisAlert onAcknowledge={() => setShowCrisis(false)} />}

        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {messages.length === 0 ? (
            <div className="max-w-lg mx-auto text-center pt-12">
              <h2 className="font-display text-2xl text-ink mb-2">How are you feeling today?</h2>
              <p className="font-sans text-warm mb-6">Choose a prompt or type your own message.</p>
            <div className="grid gap-2 sm:grid-cols-2">
              {STARTERS.map((s) => (
                <button
                  key={s}
                  type="button"
                  onClick={() => sendMessage(s)}
                  className="rounded-2xl border border-ink/10 bg-white p-4 text-left text-sm hover:border-sage hover:bg-sage/5 transition-colors duration-300 ease-mb-ease"
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        ) : (
          messages.map((m, i) => <MessageBubble key={i} message={m} />)
        )}
        {isTyping && <TypingIndicator />}
        <div ref={bottomRef} />
      </div>

        {messages.length > 0 && messages[messages.length - 1]?.role === "assistant" && !isTyping && (
          <QuickReplies suggestions={QUICK_REPLIES} onSelect={sendMessage} />
        )}
        <ChatInput onSend={sendMessage} disabled={isTyping} />
      </div>
    </div>
  );
}
