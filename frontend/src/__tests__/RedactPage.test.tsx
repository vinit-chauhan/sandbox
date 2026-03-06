import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
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
});
