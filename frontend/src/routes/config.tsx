import ChatPage from "../pages/ChatPage";
import RedactPage from "../pages/RedactPage";

export const ROUTE_CONFIG = [
  { path: "/", label: "Chat", element: <ChatPage /> },
  { path: "/redact", label: "Redact Logs", element: <RedactPage /> },
] as const;
