import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { ChatProvider, useChatContext } from "../context/ChatContext";

function TestConsumer() {
  const { docs, checkedIds, messages, input } = useChatContext();
  return (
    <div>
      <span data-testid="docs-count">{docs.length}</span>
      <span data-testid="checked-count">{checkedIds.length}</span>
      <span data-testid="messages-count">{messages.length}</span>
      <span data-testid="input-value">{input}</span>
    </div>
  );
}

describe("ChatContext", () => {
  it("ChatProvider renders and useChatContext provides initial state", () => {
    render(
      <ChatProvider>
        <TestConsumer />
      </ChatProvider>,
    );
    expect(screen.getByTestId("docs-count")).toHaveTextContent("0");
    expect(screen.getByTestId("checked-count")).toHaveTextContent("0");
    expect(screen.getByTestId("messages-count")).toHaveTextContent("0");
    expect(screen.getByTestId("input-value")).toHaveTextContent("");
  });

  it("useChatContext throws when used outside provider", () => {
    expect(() => render(<TestConsumer />)).toThrow(
      "useChatContext must be used within ChatProvider",
    );
  });
});
