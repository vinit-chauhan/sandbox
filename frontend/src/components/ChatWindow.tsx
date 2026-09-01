import { useState, useRef, useEffect } from "react";
import { type Message, streamChat } from "../api/client";
import { useChatContext } from "../context/ChatContext";
import MessageBubble from "./MessageBubble";

export default function ChatWindow() {
  const { messages, setMessages, input, setInput, checkedIds, thinkingEnabled, setThinkingEnabled } =
    useChatContext();
  const [streaming, setStreaming] = useState(false);
  const [isThinking, setIsThinking] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSend = async () => {
    const text = input.trim();
    if (!text || streaming) return;

    const userMsg: Message = { role: "user", content: text };
    const history = [...messages, userMsg];
    setMessages(history);
    setInput("");
    setStreaming(true);

    const assistantMsg: Message = { role: "assistant", content: "" };
    setMessages((prev) => [...prev, assistantMsg]);

    try {
      if (thinkingEnabled) {
        setIsThinking(true);
        assistantMsg.thinking = "";
      }
      const timing = await streamChat(
        {
          message: text,
          document_ids: checkedIds.length > 0 ? checkedIds : undefined,
          history: messages,
          enable_thinking: thinkingEnabled || undefined,
        },
        (token) => {
          setIsThinking(false);
          assistantMsg.content += token;
          setMessages((prev) => [...prev.slice(0, -1), { ...assistantMsg }]);
        },
        thinkingEnabled
          ? (token) => {
              assistantMsg.thinking = (assistantMsg.thinking || "") + token;
              setMessages((prev) => [...prev.slice(0, -1), { ...assistantMsg }]);
            }
          : undefined,
      );
      assistantMsg.timing = timing;
      setMessages((prev) => [...prev.slice(0, -1), { ...assistantMsg }]);
    } catch (err) {
      console.error("Chat error:", err);
      assistantMsg.content += "\n\n[Error communicating with the model]";
      setMessages((prev) => [...prev.slice(0, -1), { ...assistantMsg }]);
    }

    setStreaming(false);
    setIsThinking(false);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <>
      <div className="flex-1 overflow-y-auto p-6">
        {messages.length === 0 && (
          <div className="flex items-center justify-center h-full">
            <div className="text-center text-gray-400">
              <p className="text-lg">Start a conversation</p>
              <p className="text-sm mt-1">
                Upload documents and ask questions, or just chat
              </p>
            </div>
          </div>
        )}
        {messages.map((msg, i) => (
          <MessageBubble key={i} role={msg.role} content={msg.content} thinking={msg.thinking} timing={msg.timing} />
        ))}
        {streaming && messages[messages.length - 1]?.content === "" && (
          <div className="flex justify-start mb-3">
            <div className="bg-white border border-gray-200 rounded-2xl rounded-bl-md px-4 py-2.5 shadow-sm">
              <span className="inline-flex items-center gap-1">
                {isThinking && (
                  <span className="text-xs text-purple-600 font-medium mr-1">Thinking</span>
                )}
                <span className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce [animation-delay:0ms]" />
                <span className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce [animation-delay:150ms]" />
                <span className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce [animation-delay:300ms]" />
              </span>
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <div className="border-t border-gray-200 bg-white p-4">
        {checkedIds.length > 0 && (
          <div className="mb-2">
            <span className="inline-flex items-center rounded-full bg-blue-50 px-2.5 py-0.5 text-xs font-medium text-blue-700">
              {checkedIds.length} doc{checkedIds.length > 1 ? "s" : ""}{" "}
              attached
            </span>
          </div>
        )}
        <div className="flex gap-2">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Type a message... (Ctrl+Enter to send)"
            rows={2}
            className="flex-1 resize-none rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
          <div className="flex flex-col gap-1 self-end">
            <button
              onClick={() => setThinkingEnabled((prev) => !prev)}
              title={thinkingEnabled ? "Disable thinking" : "Enable thinking"}
              className={`rounded-lg px-3 py-1.5 text-xs font-medium transition-colors ${
                thinkingEnabled
                  ? "bg-purple-100 text-purple-700 border border-purple-300"
                  : "bg-gray-100 text-gray-500 border border-gray-200 hover:bg-gray-200"
              }`}
            >
              Think
            </button>
            <button
              onClick={handleSend}
              disabled={streaming || !input.trim()}
              className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              Send
            </button>
          </div>
        </div>
      </div>
    </>
  );
}
