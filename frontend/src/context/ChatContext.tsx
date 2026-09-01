import {
  createContext,
  useContext,
  useState,
  useCallback,
  useEffect,
  type ReactNode,
} from "react";
import { type Doc, type Message, getDocuments } from "../api/client";

interface ChatContextValue {
  docs: Doc[];
  setDocs: React.Dispatch<React.SetStateAction<Doc[]>>;
  checkedIds: string[];
  setCheckedIds: React.Dispatch<React.SetStateAction<string[]>>;
  messages: Message[];
  setMessages: React.Dispatch<React.SetStateAction<Message[]>>;
  input: string;
  setInput: React.Dispatch<React.SetStateAction<string>>;
  thinkingEnabled: boolean;
  setThinkingEnabled: React.Dispatch<React.SetStateAction<boolean>>;
  handleUploaded: (doc: Doc) => void;
  handleDeleted: (id: string) => void;
  handleToggle: (id: string) => void;
}

const ChatContext = createContext<ChatContextValue | null>(null);

export function ChatProvider({ children }: { children: ReactNode }) {
  const [docs, setDocs] = useState<Doc[]>([]);
  const [checkedIds, setCheckedIds] = useState<string[]>([]);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [thinkingEnabled, setThinkingEnabled] = useState(false);

  useEffect(() => {
    getDocuments().then(setDocs).catch(console.error);
  }, []);

  const handleUploaded = useCallback((doc: Doc) => {
    setDocs((prev) => [...prev, doc]);
    setCheckedIds((prev) => [...prev, doc.id]);
  }, []);

  const handleDeleted = useCallback((id: string) => {
    setDocs((prev) => prev.filter((d) => d.id !== id));
    setCheckedIds((prev) => prev.filter((cid) => cid !== id));
  }, []);

  const handleToggle = useCallback((id: string) => {
    setCheckedIds((prev) =>
      prev.includes(id) ? prev.filter((cid) => cid !== id) : [...prev, id],
    );
  }, []);

  const value: ChatContextValue = {
    docs,
    setDocs,
    checkedIds,
    setCheckedIds,
    messages,
    setMessages,
    input,
    setInput,
    thinkingEnabled,
    setThinkingEnabled,
    handleUploaded,
    handleDeleted,
    handleToggle,
  };

  return (
    <ChatContext.Provider value={value}>{children}</ChatContext.Provider>
  );
}

export function useChatContext(): ChatContextValue {
  const ctx = useContext(ChatContext);
  if (!ctx) {
    throw new Error("useChatContext must be used within ChatProvider");
  }
  return ctx;
}
