import { useId, useState } from "react";
import EmptyState from "@components/ui/EmptyState";
import LoadingState from "@components/ui/LoadingState";
import Menu from "@components/ui/Menu";
import Notice from "@components/ui/Notice";
import { useSensors } from "@hooks/useSensors";
import { useGraphViews } from "@features/dashboard/state/graphViews";
import { useGraphTabsSync } from "@features/dashboard/state/useGraphTabsSync";
import type { Graph, GraphLayout, GraphTab } from "@schemas/graphTab.schema";
import {
  useDashboardActions,
  useGraphView,
  useVisibleWindow,
} from "@features/dashboard/state/useDashboard";
import { cx } from "@utils/classNames";
import { describeError } from "@utils/describeError";
import styles from "./SensorChartPanel.module.css";
import SensorChart from "./SensorChart";

// The right pane: tabs of graph cards (state/graphViews.ts), each a channel over
// time. The active tab is ?view= when that names a tab, else the saved one.
// Tabs work like a browser's: hover for ×, middle-click closes, double-click renames.
// The tabs are shared by the team, loaded from and saved to the backend.
export default function SensorChartsPanel({ height = 260 }: { height?: number }) {
  const { isLoading, loadError, saveError } = useGraphTabsSync();
  const views = useGraphViews();
  const view = useGraphView();
  const { setGraphView, resetWindow } = useDashboardActions();
  const visibleWindow = useVisibleWindow();
  const { sensors, sensorsError } = useSensors();
  const [renamingId, setRenamingId] = useState<string | null>(null);
  const [adding, setAdding] = useState(false);

  if (isLoading) return <LoadingState message="Loading graph tabs…" />;

  const { tabs } = views;
  const active =
    tabs.find((tab) => tab.id === view) ??
    tabs.find((tab) => tab.id === views.activeTabId) ??
    tabs[0];

  const selectTab = (tabId: string) => {
    views.setActiveTab(tabId);
    setGraphView(tabId);
  };
  // For actions that pick a new active tab themselves: point ?view= at it.
  const thenFollow = (action: () => void) => {
    action();
    setGraphView(useGraphViews.getState().activeTabId);
  };
  const closeTab = (tabId: string) => thenFollow(() => views.deleteTab(tabId));

  const units = new Map(sensors?.map((sensor) => [sensor.name, sensor.unit ?? ""]));
  const channels = [...units.keys()].filter((name) => name.trim() !== "");
  const available = channels.filter((name) => !active.graphs.some((g) => g.channel === name));
  const otherTabs = tabs.filter((tab) => tab.id !== active.id);

  return (
    <section className={styles.panel}>
      <header className={styles.header}>
        <div role="tablist" aria-label="Graph tabs" className={styles.tabs}>
          {tabs.map((tab) => (
            <div key={tab.id} className={cx(styles.tab, tab.id === active.id && styles.active)}>
              {renamingId === tab.id ? (
                <input
                  className={styles.tabInput}
                  aria-label="Tab name"
                  defaultValue={tab.name}
                  autoFocus
                  onFocus={(e) => e.currentTarget.select()}
                  onBlur={(e) => {
                    views.renameTab(tab.id, e.currentTarget.value);
                    setRenamingId(null);
                  }}
                  onKeyDown={(e) => {
                    if (e.key === "Escape") e.currentTarget.value = tab.name;
                    if (e.key === "Enter" || e.key === "Escape") e.currentTarget.blur();
                  }}
                />
              ) : (
                <button
                  type="button"
                  role="tab"
                  aria-selected={tab.id === active.id}
                  className={styles.tabLabel}
                  title="Double-click to rename"
                  onClick={() => selectTab(tab.id)}
                  onDoubleClick={() => setRenamingId(tab.id)}
                  onAuxClick={(e) => {
                    if (e.button === 1) closeTab(tab.id);
                  }}
                >
                  {tab.name}
                </button>
              )}
              <button
                type="button"
                className={styles.closeTab}
                aria-label={`Close ${tab.name}`}
                title="Close tab"
                onClick={() => closeTab(tab.id)}
              >
                ×
              </button>
            </div>
          ))}
          <button
            type="button"
            className={styles.newTab}
            aria-label="New tab"
            title="New tab"
            onClick={() => thenFollow(views.addTab)}
          >
            +
          </button>
        </div>

        <div className={styles.tools}>
          {visibleWindow && (
            <button type="button" className={styles.textButton} onClick={() => resetWindow()}>
              Reset zoom
            </button>
          )}
          <select
            className={styles.select}
            aria-label="Graph layout"
            value={active.layout}
            onChange={(e) => views.setLayout(active.id, Number(e.target.value) as GraphLayout)}
          >
            <option value={1}>1 column</option>
            <option value={2}>2 columns</option>
          </select>
          <Menu
            label="Tab options"
            items={[
              { label: "Rename tab", onSelect: () => setRenamingId(active.id) },
              {
                label: "Duplicate tab",
                onSelect: () => thenFollow(() => views.duplicateTab(active.id)),
              },
              {
                label: "Group by sensor",
                onSelect: () => thenFollow(views.groupBySensor),
                disabled: !tabs.some((tab) => tab.graphs.length > 0),
              },
              {
                label: "Delete tab",
                onSelect: () => closeTab(active.id),
                danger: true,
                separated: true,
              },
            ]}
          />
        </div>
      </header>

      {(loadError || saveError) && (
        <div className={styles.notices}>
          {loadError && (
            <Notice tone="warning">
              Graph tabs couldn't be loaded, so changes here won't be saved.{" "}
              {describeError(loadError)}
            </Notice>
          )}
          {saveError && (
            <Notice tone="error">Graph tabs couldn't be saved. {describeError(saveError)}</Notice>
          )}
        </div>
      )}

      {/* The only part that scrolls: the tab bar above stays put. */}
      <div className={styles.body}>
        <div className={cx(styles.grid, active.layout === 2 && styles.twoColumns)}>
          {active.graphs.map((graph) => (
            <GraphCard
              key={graph.id}
              graph={graph}
              unit={units.get(graph.channel) ?? ""}
              missing={!!sensors && !units.has(graph.channel)}
              options={available}
              otherTabs={otherTabs}
              height={height}
            />
          ))}

          <div className={cx(styles.addCard, active.graphs.length === 0 && styles.emptyTab)}>
            {active.graphs.length === 0 && !adding && (
              <EmptyState message="No graphs in this tab yet." />
            )}
            {adding ? (
              <SensorPicker
                options={available}
                label="Search channels"
                autoFocus
                onPick={(channel) => {
                  views.addGraph(active.id, channel);
                  setAdding(false);
                }}
                onCancel={() => setAdding(false)}
              />
            ) : (
              <button
                type="button"
                className={styles.addButton}
                onClick={() => setAdding(true)}
                disabled={!sensors}
              >
                + Add graph
              </button>
            )}
            {sensorsError && (
              <p className={styles.hint}>Can't load the channel list. Is Penelope reachable?</p>
            )}
          </div>
        </div>
      </div>
    </section>
  );
}

type GraphCardProps = {
  graph: Graph;
  unit: string;
  // The channel isn't in the channel list (renamed or removed upstream).
  missing: boolean;
  options: readonly string[];
  otherTabs: readonly GraphTab[];
  height: number;
};

// One channel over time. Click the title to change the channel; ⋯ for the rest.
function GraphCard({ graph, unit, missing, options, otherTabs, height }: GraphCardProps) {
  const [editing, setEditing] = useState(false);
  const actions = useGraphViews.getState();

  return (
    <article className={styles.card}>
      <header className={styles.cardHeader}>
        {editing ? (
          <SensorPicker
            value={graph.channel}
            options={options}
            label="Search channels"
            autoFocus
            onPick={(channel) => {
              actions.setGraphChannel(graph.id, channel);
              setEditing(false);
            }}
            onCancel={() => setEditing(false)}
          />
        ) : (
          <button
            type="button"
            className={styles.cardTitle}
            title="Change channel"
            onClick={() => setEditing(true)}
          >
            {graph.channel}
            {unit && <span className={styles.unit}>{unit}</span>}
          </button>
        )}
        <Menu
          label={`Options for ${graph.channel}`}
          items={[
            { label: "Change channel", onSelect: () => setEditing(true) },
            { label: "Duplicate graph", onSelect: () => actions.duplicateGraph(graph.id) },
            ...otherTabs.map((tab, index) => ({
              label: `Move to ${tab.name}`,
              onSelect: () => actions.moveGraph(graph.id, tab.id),
              separated: index === 0,
            })),
            {
              label: "Remove graph",
              onSelect: () => actions.removeGraph(graph.id),
              danger: true,
              separated: true,
            },
          ]}
        />
      </header>
      {missing ? (
        <EmptyState message={`Channel "${graph.channel}" isn't available. Pick another.`} />
      ) : (
        <SensorChart name={graph.channel} unit={unit} height={height} />
      )}
    </article>
  );
}

type SensorPickerProps = {
  value?: string;
  options: readonly string[];
  label: string;
  autoFocus?: boolean;
  onPick: (name: string) => void;
  onCancel?: () => void;
};

function SensorPicker({
  value = "",
  options,
  label,
  autoFocus,
  onPick,
  onCancel,
}: SensorPickerProps) {
  const listId = useId();
  const [text, setText] = useState(value);

  return (
    <>
      <input
        className={styles.picker}
        list={listId}
        value={text}
        placeholder={value || label}
        aria-label={label}
        autoFocus={autoFocus}
        onFocus={() => setText("")}
        onChange={(e) => {
          if (options.includes(e.target.value)) onPick(e.target.value);
          else setText(e.target.value);
        }}
        onBlur={() => {
          setText(value);
          onCancel?.();
        }}
        onKeyDown={(e) => {
          if (e.key === "Escape") e.currentTarget.blur();
        }}
      />
      <datalist id={listId}>
        {options.map((name) => (
          <option key={name} value={name} />
        ))}
      </datalist>
    </>
  );
}
