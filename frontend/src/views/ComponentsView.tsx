import { useState, type ReactNode } from "react";
import {
  Calendar,
  Copy,
  Download,
  Link,
  Maximize2,
  MoreHorizontal,
  Pencil,
  Plus,
  RefreshCw,
  Route,
  Trash2,
} from "lucide-react";
import ChartTooltip from "@components/charts/ChartTooltip";
import PlotCard from "@components/charts/PlotCard";
import type { Series } from "@components/charts/series";
import SeriesChip from "@components/charts/SeriesChip";
import SignalRow from "@components/charts/SignalRow";
import { TimeSeriesChart } from "@components/charts/TimeSeriesChart";
import Breadcrumb, { BreadcrumbCurrent, BreadcrumbLink } from "@components/layout/Breadcrumb";
import LapRow from "@components/runs/LapRow";
import LapStepper from "@components/runs/LapStepper";
import StatTile from "@components/ui/StatTile";
import PageHeader from "@components/layout/PageHeader";
import TopBar, { TopBarLink, TopBarNav } from "@components/layout/TopBar";
import StatusBadge from "@components/runs/StatusBadge";
import Avatar from "@components/ui/Avatar";
import Button from "@components/ui/Button";
import Checkbox from "@components/ui/Checkbox";
import EmptyState from "@components/ui/EmptyState";
import IconButton from "@components/ui/IconButton";
import Input from "@components/ui/Input";
import Menu, { MenuItem, MenuSeparator } from "@components/ui/Menu";
import Modal, { ModalClose } from "@components/ui/Modal";
import Notice from "@components/ui/Notice";
import Search from "@components/ui/Search";
import SegmentedControl from "@components/ui/SegmentedControl";
import Select from "@components/ui/Select";
import { Tab, TabList, TabPanel, Tabs } from "@components/ui/Tabs";
import { showToast } from "@components/ui/toastStore";
import Toggle from "@components/ui/Toggle";
import Tooltip from "@components/ui/Tooltip";
import styles from "./ComponentsView.module.css";

const VARIANTS = ["primary", "secondary", "ghost", "danger"] as const;
const TRACKS = [
  { value: "palmer", label: "Palmer Motorsports Park" },
  { value: "burlington", label: "Burlington test lot" },
];
const LAPS = [
  { lap: 1, time: "1:12.06", delta: "−0.42", series: 1 },
  { lap: 2, time: "1:12.48", delta: "+0.42", series: 2 },
  { lap: 3, time: "1:13.13", delta: "+1.07", series: 4 },
] as const satisfies readonly { lap: number; time: string; delta: string; series: Series }[];
const SIGNALS = [
  { name: "Pack_Current", unit: "A" },
  { name: "Speed", unit: "mph" },
  { name: "Steering_Angle", unit: "°" },
];
// A fake speed trace, 0–60 s, for the Plot Card demo.
const DEMO_TIME = Array.from({ length: 240 }, (_, i) => i * 250);
const DEMO_SPEED = DEMO_TIME.map((t) => 32 + 12 * Math.sin(t / 4000) + 4 * Math.sin(t / 900));

// Dev-only gallery of components/ui, to compare against the Figma library.
export default function ComponentsView() {
  const [axis, setAxis] = useState<"track" | "distance" | "time">("track");
  const [track, setTrack] = useState("palmer");
  const [on, setOn] = useState(true);
  const [lapIndex, setLapIndex] = useState(1);
  const [compared, setCompared] = useState<readonly number[]>([1]);
  const [signals, setSignals] = useState<readonly string[]>(["Speed"]);
  const toggle = <T,>(list: readonly T[], item: T, add: boolean) =>
    add ? [...list, item] : list.filter((x) => x !== item);

  return (
    <>
      <PageHeader title="Components" description="components/ui next to the Orion Figma library." />

      <Section title="Top Bar">
        <div className={styles.stack}>
          <TopBar
            actions={
              <>
                <Search
                  aria-label="Search signals"
                  placeholder="Search 340 signals…"
                  shortcut
                  className={styles.topBarSearch}
                />
                <Avatar initials="CW" name="Casey Wu" />
              </>
            }
          >
            <TopBarNav>
              <TopBarLink to="/runs">Runs</TopBarLink>
              <TopBarLink to="/components">Components</TopBarLink>
            </TopBarNav>
          </TopBar>
          <TopBar
            actions={
              <>
                <Button variant="secondary" size="sm">
                  <Link /> Share
                </Button>
                <Avatar initials="CW" name="Casey Wu" />
              </>
            }
          >
            <Breadcrumb>
              <BreadcrumbLink to="/runs">Runs</BreadcrumbLink>
              <BreadcrumbCurrent>Shakedown - Endurance sim</BreadcrumbCurrent>
            </Breadcrumb>
          </TopBar>
        </div>
      </Section>

      <Section title="Button">
        {(["md", "sm"] as const).map((size) =>
          VARIANTS.map((variant) => (
            <div key={variant + size} className={styles.row}>
              <Button variant={variant} size={size}>
                Button
              </Button>
              <Button variant={variant} size={size}>
                <Plus /> New run
              </Button>
              <Button variant={variant} size={size} disabled>
                Button
              </Button>
            </div>
          )),
        )}
      </Section>

      <Section title="Icon Button">
        <div className={styles.row}>
          <IconButton label="More">
            <MoreHorizontal />
          </IconButton>
          <IconButton label="More" pressed>
            <MoreHorizontal />
          </IconButton>
          <IconButton label="More" variant="secondary">
            <MoreHorizontal />
          </IconButton>
          <IconButton label="More" variant="secondary" pressed>
            <MoreHorizontal />
          </IconButton>
        </div>
      </Section>

      <Section title="Input">
        <div className={styles.grid}>
          <Input
            label="Start time"
            icon={<Calendar />}
            defaultValue="Laps 1–4"
            helper="Local time, EDT"
          />
          <Input
            label="Start time"
            icon={<Calendar />}
            variant="timestamp"
            defaultValue="2026-10-12  14:32:08.250"
            helper="Local time, EDT"
          />
          <Input
            label="Start time"
            icon={<Calendar />}
            variant="timestamp"
            defaultValue="2026-10-12  14:32:08.250"
            error="Local time, EDT"
          />
          <Input
            label="Start time"
            icon={<Calendar />}
            variant="timestamp"
            defaultValue="2026-10-12  14:32:08.250"
            helper="Local time, EDT"
            disabled
          />
        </div>
      </Section>

      <Section title="Select">
        <div className={styles.grid}>
          <Select label="Track" options={TRACKS} value={track} onValueChange={setTrack} />
          <Select label="Track" options={TRACKS} value={track} disabled />
        </div>
      </Section>

      <Section title="Search, Checkbox, Toggle">
        <div className={styles.row}>
          <Search aria-label="Search signals" placeholder="Search 340 signals…" />
          <Checkbox aria-label="Off" />
          <Checkbox aria-label="On" defaultChecked />
          <Checkbox aria-label="Mixed" indeterminate />
          <Checkbox label="Pack_Current" />
          <Toggle aria-label="Off" />
          <Toggle label="Show laps" checked={on} onChange={(e) => setOn(e.target.checked)} />
        </div>
      </Section>

      <Section title="Segmented Control, Tab">
        <div className={styles.row}>
          <SegmentedControl
            aria-label="X axis"
            value={axis}
            onChange={setAxis}
            options={[
              { value: "track", label: "Track %" },
              { value: "distance", label: "Distance" },
              { value: "time", label: "Time" },
            ]}
          />
          <Tabs defaultValue="laps">
            <TabList aria-label="Panels">
              <Tab value="laps">Laps</Tab>
              <Tab value="signals">Signals</Tab>
            </TabList>
            <TabPanel value="laps" />
            <TabPanel value="signals" />
          </Tabs>
        </div>
      </Section>

      <Section title="Status Badge, Avatar, Tooltip">
        <div className={styles.row}>
          {(["loaded", "processing", "queued", "failed", "not-processed"] as const).map((s) => (
            <StatusBadge key={s} status={s} />
          ))}
          <Avatar initials="CW" name="Casey Wu" />
          <Tooltip content="Full screen">
            <Button variant="secondary" size="sm">
              Hover me
            </Button>
          </Tooltip>
        </div>
      </Section>

      <Section title="Menu, Toast, Modal">
        <div className={styles.row}>
          <Menu
            trigger={
              <IconButton label="Run actions" variant="secondary">
                <MoreHorizontal />
              </IconButton>
            }
          >
            <MenuItem icon={<Pencil />}>Rename</MenuItem>
            <MenuItem icon={<Copy />}>Duplicate run</MenuItem>
            <MenuItem icon={<RefreshCw />}>Re-run pipeline</MenuItem>
            <MenuItem icon={<Download />}>Export CSV</MenuItem>
            <MenuSeparator />
            <MenuItem icon={<Trash2 />} danger>
              Delete run
            </MenuItem>
          </Menu>
          <Button
            variant="secondary"
            onClick={() =>
              showToast("success", "Link copied; anyone with access sees this exact view")
            }
          >
            Success toast
          </Button>
          <Button
            variant="secondary"
            onClick={() => showToast("error", "Couldn’t reach OrionDB. Retrying…")}
          >
            Error toast
          </Button>
          <Button
            variant="secondary"
            onClick={() => showToast("info", "Pipeline re-run queued for State Estimation")}
          >
            Info toast
          </Button>
          <Modal
            title="Modal title"
            trigger={<Button variant="secondary">Open modal</Button>}
            footer={
              <>
                <ModalClose>
                  <Button variant="ghost">Cancel</Button>
                </ModalClose>
                <ModalClose>
                  <Button>Confirm</Button>
                </ModalClose>
              </>
            }
          >
            Content slot
          </Modal>
        </div>
      </Section>

      <Section title="Alert Banner (Notice)">
        <div className={styles.stack}>
          <Notice tone="error" title="Multiple tracks detected">
            Your range spans Palmer Motorsports Park and the Burlington test lot. Narrow the
            start/end so it covers one track.
          </Notice>
          <Notice tone="warning" title="GPS gap in lap 6">
            3.8 s without GPS around 62%; position is estimated by the Kalman filter from IMU only.
          </Notice>
          <Notice tone="info" title="GPS is shifted −3 s">
            Penelope GPS timestamps lag by a constant 3 s; Orion corrects this automatically.
          </Notice>
        </div>
      </Section>

      <Section title="Plot Card, Chart Tooltip">
        <div className={styles.row}>
          <div className={styles.plot}>
            <PlotCard
              title="Speed"
              unit="mph"
              readout="33.6"
              actions={
                <>
                  <IconButton label="Full screen">
                    <Maximize2 />
                  </IconButton>
                  <IconButton label="Chart actions">
                    <MoreHorizontal />
                  </IconButton>
                </>
              }
            >
              <TimeSeriesChart
                height={180}
                series={[
                  { id: "speed", label: "Speed", unit: "mph", time: DEMO_TIME, values: DEMO_SPEED },
                ]}
              />
            </PlotCard>
          </div>
          <ChartTooltip
            title="50.0%, t +00:36.240"
            rows={[
              { series: 1, label: "Lap 4", value: "33.6 mph" },
              { series: 2, label: "Lap 7", value: "32.9 mph" },
              { series: 3, label: "Lap 9", value: "34.1 mph" },
            ]}
          />
        </div>
      </Section>

      <Section title="Stat Tile, Lap Stepper, Series Chip">
        <div className={styles.row}>
          <StatTile
            label="Lap time"
            value="1:12.48"
            delta={{ text: "−0.42s vs best", better: true }}
          />
          <StatTile
            label="Lap time"
            value="1:12.48"
            delta={{ text: "+1.07s vs best", better: false }}
          />
          <StatTile label="Lap time" value="1:12.48" note="Session best" />
        </div>
        <div className={styles.row}>
          <LapStepper
            label={`Lap ${LAPS[lapIndex].lap} of ${LAPS.length}`}
            onPrevious={lapIndex > 0 ? () => setLapIndex(lapIndex - 1) : undefined}
            onNext={lapIndex < LAPS.length - 1 ? () => setLapIndex(lapIndex + 1) : undefined}
          />
          <LapStepper label="3 laps, 4, 7, 9" onPrevious={() => {}} onNext={() => {}} />
        </div>
        <div className={styles.row}>
          {([1, 2, 3, 4, 5, 6, 7, 8] as const).map((series) => (
            <SeriesChip
              key={series}
              series={series}
              label={`Lap ${series + 2}`}
              onRemove={() => showToast("info", `Removed lap ${series + 2}`)}
            />
          ))}
        </div>
      </Section>

      <Section title="Lap Row, Signal Row">
        <div className={styles.grid}>
          <div className={styles.stack}>
            {LAPS.map((lap, index) => (
              <LapRow
                key={lap.lap}
                {...lap}
                selected={index === lapIndex}
                compared={compared.includes(lap.lap)}
                onSelect={() => setLapIndex(index)}
                onCompareChange={(add) => setCompared(toggle(compared, lap.lap, add))}
              />
            ))}
          </div>
          <div className={styles.stack}>
            {SIGNALS.map((signal) => (
              <SignalRow
                key={signal.name}
                {...signal}
                checked={signals.includes(signal.name)}
                onChange={(event) => setSignals(toggle(signals, signal.name, event.target.checked))}
              />
            ))}
          </div>
        </div>
      </Section>

      <Section title="Empty State">
        <div className={styles.narrow}>
          <EmptyState
            icon={<Route />}
            title="No runs yet"
            message="Pick two timestamps from Penelope and Orion will clean the data, estimate the car’s position and split it into laps."
            action={
              <Button>
                <Plus /> New run
              </Button>
            }
          />
        </div>
      </Section>
    </>
  );
}

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className={styles.section}>
      <h2 className={styles.heading}>{title}</h2>
      {children}
    </section>
  );
}
