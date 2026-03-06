import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import RedactPage from "../pages/RedactPage";
import * as client from "../api/client";

vi.mock("../api/client");

function renderRedactPage() {
  return render(
    <MemoryRouter>
      <RedactPage />
    </MemoryRouter>,
  );
}

describe("RedactPage", () => {
  beforeEach(() => {
    vi.mocked(client.streamRedact).mockReset();
  });

  it("renders heading Clean Logs", () => {
    renderRedactPage();
    expect(screen.getByRole("heading", { name: "Clean Logs" })).toBeInTheDocument();
  });

  it("renders drop zone and textarea", () => {
    renderRedactPage();
    expect(
      screen.getByPlaceholderText("Drop a file or paste log text..."),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Clean" })).toBeInTheDocument();
  });

  it("disables Clean button when input is empty", () => {
    renderRedactPage();
    const cleanBtn = screen.getByRole("button", { name: "Clean" });
    expect(cleanBtn).toBeDisabled();
  });

  it("shows expandable Redaction summary in preview with PII counts when expanded", async () => {
    vi.mocked(client.streamRedact).mockImplementation((_text, _onProgress, onDone) => {
      onDone({
        redacted_text: "user-1@example.com logged in",
        mapping: {
          "alice@corp.com": "user-1@example.com",
          "bob@corp.com": "user-2@example.com",
        },
        warning: null,
      });
      return Promise.resolve();
    });
    renderRedactPage();
    const textarea = screen.getByPlaceholderText("Drop a file or paste log text...");
    fireEvent.change(textarea, { target: { value: "alice@corp.com logged in" } });
    fireEvent.click(screen.getByRole("button", { name: "Clean" }));

    await waitFor(() => {
      expect(screen.getByText(/Redaction summary \(2 changes\)/)).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: /Redaction summary/ }));
    await waitFor(() => {
      expect(screen.getByText(/email/i)).toBeInTheDocument();
    });
  });
});
