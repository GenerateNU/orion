import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import EmptyState from "./EmptyState.jsx";
import ErrorState from "./ErrorState.jsx";
import LoadingState from "./LoadingState.jsx";
import RunListItem from "./RunListItem.jsx";
import { describeError } from "../utils/describeError";

describe("describeError", () => {
  it("explains an unreachable backend", () => {
    expect(describeError(new TypeError("Failed to fetch"))).toMatch(/couldn't reach the server/i);
  });

  it("explains a 404", () => {
    expect(describeError(new Error("API request failed: 404"))).toMatch(/couldn't find/i);
  });

  it("explains a server error", () => {
    expect(describeError(new Error("API request failed: 500"))).toMatch(/server ran into a problem/i);
  });

  it("falls back to a generic message", () => {
    expect(describeError(new Error("API request failed: 400"))).toMatch(/something went wrong/i);
    expect(describeError(undefined)).toMatch(/something went wrong/i);
  });
});

describe("LoadingState", () => {
  it("shows a default message", () => {
    render(<LoadingState />);
    expect(screen.getByRole("status")).toHaveTextContent("Loading...");
  });

  it("shows a custom message", () => {
    render(<LoadingState message="Loading runs..." />);
    expect(screen.getByRole("status")).toHaveTextContent("Loading runs...");
  });
});

describe("ErrorState", () => {
  it("shows the title and a readable explanation", () => {
    render(<ErrorState title="Couldn't load runs" error={new Error("API request failed: 500")} />);
    const alert = screen.getByRole("alert");
    expect(alert).toHaveTextContent("Couldn't load runs");
    expect(alert).toHaveTextContent(/server ran into a problem/i);
  });
});

describe("EmptyState", () => {
  it("shows its message", () => {
    render(<EmptyState message="No runs found." />);
    expect(screen.getByText("No runs found.")).toBeInTheDocument();
  });
});

describe("RunListItem", () => {
  const run = { run_id: "run-7", name: "Test Run", dates: "2026-05-14" };

  it("shows the run name and date", () => {
    render(<RunListItem run={run} onSelect={() => {}} />);
    expect(screen.getByRole("button")).toHaveTextContent("Test Run");
    expect(screen.getByRole("button")).toHaveTextContent("2026-05-14");
  });

  it("hands the run back when clicked", () => {
    const onSelect = vi.fn();
    render(<RunListItem run={run} onSelect={onSelect} />);
    fireEvent.click(screen.getByRole("button"));
    expect(onSelect).toHaveBeenCalledWith(run);
  });
});
