import { createContext, useContext } from "react";
import type { RunResponse } from "@schemas/run.schema";

export type CurrentRunContextValue = {
  // The run the user loaded on the Run Select page; later views read it.
  currentRun: RunResponse | null;
  setCurrentRun: (run: RunResponse | null) => void;
};

export const CurrentRunContext = createContext<CurrentRunContextValue | null>(null);

// Hook for the currently loaded run. Must be used under <CurrentRunProvider>.
export const useCurrentRun = (): CurrentRunContextValue => {
  const value = useContext(CurrentRunContext);
  if (!value) {
    throw new Error("useCurrentRun must be used inside <CurrentRunProvider>");
  }
  return value;
};
