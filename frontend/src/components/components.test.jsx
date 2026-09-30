import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import EmptyState from "./EmptyState.jsx";
import ErrorState from "./ErrorState.jsx";
import LoadingState from "./LoadingState.jsx";
import RaceListItem from "./RaceListItem.jsx";
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
    render(<LoadingState message="Loading races..." />);
    expect(screen.getByRole("status")).toHaveTextContent("Loading races...");
  });
});

describe("ErrorState", () => {
  it("shows the title and a readable explanation", () => {
    render(<ErrorState title="Couldn't load races" error={new Error("API request failed: 500")} />);
    const alert = screen.getByRole("alert");
    expect(alert).toHaveTextContent("Couldn't load races");
    expect(alert).toHaveTextContent(/server ran into a problem/i);
  });
});

describe("EmptyState", () => {
  it("shows its message", () => {
    render(<EmptyState message="No races found." />);
    expect(screen.getByText("No races found.")).toBeInTheDocument();
  });
});

describe("RaceListItem", () => {
  const race = { race_id: 7, name: "Test Race", dates: "2026-05-14" };

  it("shows the race name and date", () => {
    render(<RaceListItem race={race} onSelect={() => {}} />);
    expect(screen.getByRole("button")).toHaveTextContent("Test Race");
    expect(screen.getByRole("button")).toHaveTextContent("2026-05-14");
  });

  it("hands the race back when clicked", () => {
    const onSelect = vi.fn();
    render(<RaceListItem race={race} onSelect={onSelect} />);
    fireEvent.click(screen.getByRole("button"));
    expect(onSelect).toHaveBeenCalledWith(race);
  });
});
