import { useState, type ReactNode } from "react";
import {
  Calendar,
  Copy,
  Download,
  Link,
  MoreHorizontal,
  Pencil,
  Plus,
  RefreshCw,
  Route,
  Trash2,
} from "lucide-react";
import Breadcrumb, { BreadcrumbCurrent, BreadcrumbLink } from "@components/layout/Breadcrumb";
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

// Dev-only gallery of components/ui, to compare against the Figma library.
export default function ComponentsView() {
  const [axis, setAxis] = useState<"track" | "distance" | "time">("track");
  const [track, setTrack] = useState("palmer");
  const [on, setOn] = useState(true);

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
