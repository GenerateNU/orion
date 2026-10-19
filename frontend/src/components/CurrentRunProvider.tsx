import { useMemo, useState, type ReactNode } from "react";
import type { RunResponse } from "@schemas/run.schema";
import { CurrentRunContext } from "@hooks/useCurrentRun";

export default function CurrentRunProvider({ children }: { children: ReactNode }) {
  const [currentRun, setCurrentRun] = useState<RunResponse | null>(null);
  const value = useMemo(() => ({ currentRun, setCurrentRun }), [currentRun]);

  return <CurrentRunContext.Provider value={value}>{children}</CurrentRunContext.Provider>;
}
