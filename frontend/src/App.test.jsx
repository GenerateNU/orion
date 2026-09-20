import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import App from "./App.jsx";

describe("App", () => {
  beforeEach(() => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() => Promise.resolve({ json: () => Promise.resolve({ status: "ok" }) }))
    );
  });

  it("renders the backend health status", async () => {
    render(<App />);

    expect(await screen.findByText("backend: ok")).toBeInTheDocument();
    expect(fetch).toHaveBeenCalledWith("/api/health");
  });
});