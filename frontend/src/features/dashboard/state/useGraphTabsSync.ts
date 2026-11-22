import { useEffect } from "react";
import { GraphTabSchema, type GraphTab } from "@schemas/graphTab.schema";
import { useGraphTabMutations, useGraphTabs } from "@hooks/useGraphTabs";
import { useGraphViews } from "@features/dashboard/state/graphViews";
import { z } from "zod";

// Quick edits, like typing a tab name, go out as one save.
const SAVE_DEBOUNCE_MS = 500;

// Where this browser kept its tabs before the backend stored them, in zustand's
// persist format.
const LEGACY_STORAGE_KEY = "orion-graph-views";
const LegacyStorageSchema = z.object({
  state: z.object({ tabs: z.array(GraphTabSchema).min(1) }),
});

function readLegacyTabs(): GraphTab[] | undefined {
  try {
    const stored = JSON.parse(localStorage.getItem(LEGACY_STORAGE_KEY) ?? "null");
    const result = LegacyStorageSchema.safeParse(stored);
    return result.success ? result.data.state.tabs : undefined;
  } catch {
    // Storage blocked or malformed JSON: nothing to upload.
    return undefined;
  }
}

// Connects the graph tab store (graphViews.ts) to the backend. The saved tabs are
// loaded once per page load; after that the store is the source of truth and every
// tab change is saved, debounced. Nothing is saved if loading failed, so the
// default tab can't overwrite the team's tabs.
export function useGraphTabsSync() {
  const { graphTabs, graphTabsError } = useGraphTabs();
  const { saveGraphTabs, saveGraphTabsError } = useGraphTabMutations();
  const loaded = useGraphViews((state) => state.loaded);

  useEffect(() => {
    const { loaded: alreadyLoaded, load } = useGraphViews.getState();
    if (!graphTabs || alreadyLoaded) return;
    // The backend has no tabs yet: upload this browser's old ones so they aren't lost.
    const legacyTabs = graphTabs.length === 0 ? readLegacyTabs() : undefined;
    load(legacyTabs ?? graphTabs);
    if (legacyTabs) {
      saveGraphTabs(legacyTabs, { onSuccess: () => localStorage.removeItem(LEGACY_STORAGE_KEY) });
    }
  }, [graphTabs, saveGraphTabs]);

  useEffect(() => {
    let timer: ReturnType<typeof setTimeout> | undefined;
    const save = () => {
      timer = undefined;
      saveGraphTabs(useGraphViews.getState().tabs);
    };
    // Skips the load itself (prev not loaded) and changes that leave the tabs as
    // they were, like switching the active tab.
    const unsubscribe = useGraphViews.subscribe((state, prev) => {
      if (!prev.loaded || state.tabs === prev.tabs) return;
      clearTimeout(timer);
      timer = setTimeout(save, SAVE_DEBOUNCE_MS);
    });
    return () => {
      unsubscribe();
      // Leaving the dashboard sends a save still waiting on the timer right away.
      if (timer) {
        clearTimeout(timer);
        save();
      }
    };
  }, [saveGraphTabs]);

  return {
    isLoading: !loaded && !graphTabsError,
    loadError: graphTabsError,
    saveError: saveGraphTabsError,
  };
}
