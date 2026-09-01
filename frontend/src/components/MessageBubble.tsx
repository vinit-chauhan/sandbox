import type { ChatTiming } from "../api/client";

function formatMs(ms: number): string {
  return ms >= 1000 ? `${(ms / 1000).toFixed(2)}s` : `${Math.round(ms)}ms`;
}

interface Props {
  role: "user" | "assistant";
  content: string;
  thinking?: string;
  timing?: ChatTiming;
}

export default function MessageBubble({ role, content, thinking, timing }: Props) {
  const isUser = role === "user";

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"} mb-3`}>
      <div className="max-w-[75%]">
        {thinking && !isUser && (
          <details className="mb-1">
            <summary className="cursor-pointer text-xs text-purple-600 font-medium px-2 py-1 bg-purple-50 rounded-lg border border-purple-200 inline-block">
              Thinking
            </summary>
            <div className="mt-1 px-3 py-2 text-xs text-gray-600 bg-purple-50/50 border border-purple-100 rounded-lg whitespace-pre-wrap leading-relaxed max-h-64 overflow-y-auto">
              {thinking}
            </div>
          </details>
        )}
        <div
          className={`rounded-2xl px-4 py-2.5 text-sm leading-relaxed whitespace-pre-wrap ${
            isUser
              ? "bg-blue-600 text-white rounded-br-md"
              : "bg-white text-gray-800 border border-gray-200 rounded-bl-md shadow-sm"
          }`}
        >
          {content}
        </div>
        {timing && !isUser && (
          <div className="flex gap-3 mt-1 px-1 text-[11px] text-gray-400">
            <span>TTFT: {formatMs(timing.ttft)}</span>
            <span>Total: {formatMs(timing.total)}</span>
          </div>
        )}
      </div>
    </div>
  );
}
