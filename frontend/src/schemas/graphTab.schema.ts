import { z } from "zod";

// Mirrors GraphResponse in services/backend/.../schemas/graph_tab_schema.py: one
// channel plotted over time; `channel` is a Penelope `dataTypeName`.
export const GraphSchema = z.object({
  id: z.string(),
  channel: z.string(),
});

// Mirrors GraphTabResponse: one dashboard graph tab, with its graph columns.
export const GraphTabSchema = z.object({
  id: z.string(),
  name: z.string(),
  layout: z.union([z.literal(1), z.literal(2)]),
  graphs: z.array(GraphSchema),
});

export type Graph = z.infer<typeof GraphSchema>;
export type GraphTab = z.infer<typeof GraphTabSchema>;
export type GraphLayout = GraphTab["layout"];
