"use client";

import { Bot, User } from "lucide-react";
import { cn } from "@/lib/utils";
import type { ChatMessage } from "@/types/chat.types";

interface Props {
  message: ChatMessage;
}

export function MessageBubble({ message }: Props) {
  const isUser = message.role === "user";

  return (
    <div className={cn("flex gap-3", isUser ? "flex-row-reverse" : "flex-row")}>
      <div
        className={cn(
          "flex h-8 w-8 shrink-0 items-center justify-center rounded-full",
          isUser ? "bg-brand-600 text-white" : "bg-brand-100 text-brand-700"
        )}
      >
        {isUser ? <User className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
      </div>
      <div className={cn("max-w-[75%] space-y-1", isUser ? "items-end" : "items-start")}>
        <div
          className={cn(
            "rounded-2xl px-4 py-2.5 text-sm leading-relaxed",
            isUser
              ? "bg-brand-600 text-white rounded-br-md"
              : "bg-white border border-slate-200 shadow-sm rounded-bl-md text-slate-800"
          )}
        >
          <p className="whitespace-pre-wrap">{message.content}</p>
        </div>
        {!isUser && message.relevance_score != null && (
          <span className="text-xs text-slate-400">
            relevance {(message.relevance_score * 100).toFixed(0)}%
          </span>
        )}
      </div>
    </div>
  );
}
