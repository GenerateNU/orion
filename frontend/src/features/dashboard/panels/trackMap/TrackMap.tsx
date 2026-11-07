import { useMemo, useRef } from "react";
import EmptyState from "@components/ui/EmptyState";
import ErrorState from "@components/ui/ErrorState";
import LoadingState from "@components/ui/LoadingState";
import { useRunPositions } from "@features/dashboard/data/useDashboardData";
import {
  useDashboardActions,
  useDashboardRun,
  useHoverTimeSubscription,
  useVisibleSelection,
} from "@features/dashboard/state/useDashboard";
import { buildTrackGeometry } from "@features/dashboard/utils/trackGeometry";
import { resolveSelection } from "@features/dashboard/utils/trackSelection";
import { fitTransform } from "@features/dashboard/utils/trackView";
import { TrackMapView, type TrackMapViewHandle } from "./TrackMapView";
import { useElementSize } from "./useElementSize";
import { useTrackInteraction } from "./useTrackInteraction";

// CSS pixels kept clear around the track, so notches and the point marker at its
// edge aren't clipped.
const PADDING_PX = 24;

// The track map panel: wires the run's positions and the dashboard's selection to
// the interaction hook (input → selection) and the view (drawing). Neither of
// those knows about the dashboard; this is the only place they meet it.
export function TrackMap() {
  const { timeline } = useDashboardRun();
  const durationMs = timeline?.durationMs ?? 0;
  const { positions, positionsIsLoading, positionsError } = useRunPositions("overview");

  const geometry = useMemo(
    () =>
      positions ? buildTrackGeometry(positions.time, positions.positions, positions.startMs) : null,
    [positions],
  );

  const [stageRef, size] = useElementSize<HTMLDivElement>();
  const transform = useMemo(
    () => (geometry && size ? fitTransform(geometry.bounds, size, PADDING_PX) : null),
    [geometry, size],
  );

  const { point, window } = useVisibleSelection();
  const selection = useMemo(
    () => resolveSelection(point, window, durationMs),
    [point, window, durationMs],
  );

  const { previewSelection, commitSelection, discardPreview, setHoverTime } = useDashboardActions();
  const { handlers, activeHandle, hoveredHandle } = useTrackInteraction({
    geometry,
    transform,
    durationMs,
    selection,
    onPreview: previewSelection,
    onCommit: commitSelection,
    onDiscard: discardPreview,
    onHover: setHoverTime,
  });

  const viewRef = useRef<TrackMapViewHandle>(null);
  useHoverTimeSubscription((time) => viewRef.current?.showHover(time));

  if (positionsIsLoading) return <LoadingState message="Loading track…" />;
  if (positionsError) return <ErrorState error={positionsError} />;
  if (!geometry) return <EmptyState message="No position data for this run." />;

  return (
    <TrackMapView
      stageRef={stageRef}
      handleRef={viewRef}
      geometry={geometry}
      size={size}
      transform={transform}
      durationMs={durationMs}
      selection={selection}
      activeHandle={activeHandle}
      hoveredHandle={hoveredHandle}
      events={handlers}
    />
  );
}
