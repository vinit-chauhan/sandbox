import { describe, it, expect } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import { ChatProvider, useChatContext } from "../context/ChatContext";
import AppLayout from "../layouts/AppLayout";
import RedactPage from "../pages/RedactPage";
import App from "../App";

function TestChatWithAddButton() {
  const { messages, setMessages } = useChatContext();
  return (
    <div>
      <button
        type="button"
        onClick={() =>
          setMessages([...messages, { role: "user" as const, content: "persisted" }])
        }
      >
        Add message
      </button>
      <span data-testid="messages-count">{messages.length}</span>
    </div>
  );
}

function renderAppWithMemoryRouter(initialEntries: string[] = ["/"]) {
  return render(
    <ChatProvider>
      <MemoryRouter initialEntries={initialEntries}>
        <App />
      </MemoryRouter>
    </ChatProvider>,
  );
}

function renderAppWithTestChatPage() {
  return render(
    <ChatProvider>
      <MemoryRouter initialEntries={["/"]}>
        <Routes>
          <Route path="/" element={<AppLayout />}>
            <Route index element={<TestChatWithAddButton />} />
            <Route path="redact" element={<RedactPage />} />
          </Route>
        </Routes>
      </MemoryRouter>
    </ChatProvider>,
  );
}

describe("Navigation", () => {
  it("renders nav with Chat and Redact Logs links", () => {
    renderAppWithMemoryRouter();
    expect(screen.getByRole("link", { name: "Chat" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Redact Logs" })).toBeInTheDocument();
  });

  it("navigates to Redact Logs when link is clicked", () => {
    renderAppWithMemoryRouter();
    fireEvent.click(screen.getByRole("link", { name: "Redact Logs" }));
    expect(screen.getByRole("heading", { name: "Redact Logs" })).toBeInTheDocument();
    expect(screen.getByText("Coming soon.")).toBeInTheDocument();
  });

  it("persists Chat state when navigating away and back", () => {
    renderAppWithTestChatPage();
    expect(screen.getByTestId("messages-count")).toHaveTextContent("0");
    fireEvent.click(screen.getByRole("button", { name: "Add message" }));
    expect(screen.getByTestId("messages-count")).toHaveTextContent("1");
    fireEvent.click(screen.getByRole("link", { name: "Redact Logs" }));
    expect(screen.getByRole("heading", { name: "Redact Logs" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("link", { name: "Chat" }));
    expect(screen.getByTestId("messages-count")).toHaveTextContent("1");
  });
});
