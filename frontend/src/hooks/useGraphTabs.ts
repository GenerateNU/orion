import { useMutation, useQuery } from "@tanstack/react-query";
import { GraphTabSchema, type GraphTab } from "@schemas/graphTab.schema";
import axios from "@api/client";
import { graphTabKeys } from "@api/queryKeys";
import { apiUrls } from "@utils/urls";
import { z } from "zod";

const GraphTabListSchema = z.array(GraphTabSchema);

// Hook for the dashboard's graph tabs (OrionDB `graph_tabs`), in tab-bar order.
// `[]` if none have been saved yet. Read once: after that the dashboard's store
// (state/graphViews.ts) is the source of truth, so it is never refetched.
export const useGraphTabs = () => {
  const query = useQuery({
    queryKey: graphTabKeys.all,
    queryFn: async (): Promise<GraphTab[]> => {
      const { data } = await axios.get(apiUrls.graphTabs());

      const result = GraphTabListSchema.safeParse(data);
      if (!result.success) {
        throw new Error(`Data validation failed: ${result.error.message}`);
      }
      return result.data;
    },
    staleTime: Infinity,
    refetchOnWindowFocus: false,
  });

  return {
    graphTabs: query.data,
    graphTabsIsLoading: query.isLoading,
    graphTabsError: query.error,
  };
};

// Hook for graph tab mutations. A save replaces every tab; it rejects with a 422
// ApiError on invalid tabs or duplicate tab/graph ids.
export const useGraphTabMutations = () => {
  const saveMutation = useMutation({
    mutationFn: async (tabs: GraphTab[]) => {
      await axios.put(apiUrls.graphTabs(), tabs);
    },
    // One save at a time, in order, so an older save can't land after a newer one.
    scope: { id: "graph-tabs" },
  });

  return {
    saveGraphTabs: saveMutation.mutate,
    saveGraphTabsError: saveMutation.error,
  };
};
