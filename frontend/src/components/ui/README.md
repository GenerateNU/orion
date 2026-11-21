# components/ui

Shared components built from the Figma
[Orion Style Guide – Component Library](https://www.figma.com/design/4DzK4qZdEbcNHk69953HiL)
("Hi-fi Components" page). Use these instead of styling raw `<button>`, `<input>`… in a page.

- **Tokens:** every color, size, radius, shadow and text style comes from `styles/global.css`.
  Never hard-code a color; if Figma has one that's missing, add it there as a token.
- **Icons:** [lucide-react](https://lucide.dev/icons), the set the Figma icons are drawn from.
  Inside a component an icon is sized by that component; standalone, pass `size={20}`.
- **Overlays** (Menu, Modal, Select, Tooltip, Toast) are [Radix UI](https://www.radix-ui.com/primitives),
  so focus, keyboard and screen reader handling come built in.
- **Preview:** run `npm run dev` and open `/components` (dev builds only) to see every variant.

Every component also accepts the props of the element it renders (`onClick`, `disabled`,
`aria-*`…) unless noted.

| Component                             | Figma        | Props                                                                                                                                |
| ------------------------------------- | ------------ | ------------------------------------------------------------------------------------------------------------------------------------ |
| `Button`                              | Button       | `variant`: `primary` \| `secondary` \| `ghost` \| `danger`; `size`: `md` \| `sm`. Children: label, optionally a lucide icon first.   |
| `ButtonLink`                          | Button       | Same as Button, plus router link props (`to`, `params`, `disabled`).                                                                 |
| `IconButton`                          | Icon Button  | `label` (required: accessible name and tooltip); `variant`: `ghost` \| `secondary`; `pressed` for toggles. Child: a lucide icon.     |
| `Input`                               | Input        | `label`, `helper`, `error` (replaces helper, marks invalid), `icon`, `variant`: `text` \| `timestamp` (mono font).                   |
| `Select`                              | Select       | `options: {value, label}[]`, `value`, `onValueChange`, `label` or `aria-label`, `placeholder`, `disabled`. No other props.           |
| `Search`                              | Search       | `aria-label` (required), plus native input props (`placeholder`, `value`, `onChange`…).                                              |
| `Checkbox`                            | Checkbox     | `label`, `indeterminate` (Figma "Mixed"), plus native checkbox props (`checked`, `onChange`…).                                       |
| `Toggle`                              | Toggle       | `label`, plus native checkbox props; renders as a switch. Use it for every on/off switch.                                            |
| `Tabs`, `TabList`, `Tab`, `TabPanel`  | Tab          | Radix Tabs: `Tabs` takes `value`/`defaultValue`/`onValueChange`; `Tab` and `TabPanel` take a matching `value`.                       |
| `Avatar`                              | Avatar       | `initials`, `name` (accessible name and hover title). No other props.                                                                |
| `Tooltip`                             | Tooltip      | `content`, `side`; child: one focusable element. Needs `TooltipProvider` (in `main.tsx`).                                            |
| `Menu`, `MenuItem`, `MenuSeparator`   | Menu         | `Menu`: `trigger` (a button), `align`. `MenuItem`: `icon`, `danger`, `onSelect`, `disabled`.                                         |
| `Modal`, `ModalClose`                 | Modal        | `title`, `children` (body), `footer`, and `open` + `onOpenChange` or `trigger`. Wrap a footer button in `ModalClose`.                |
| `Toaster`, `showToast(type, message)` | Toast        | `Toaster` is rendered once in `main.tsx`; call `showToast("success" \| "error" \| "info", message)` from anywhere (`toastStore.ts`). |
| `Notice`                              | Alert Banner | `tone`: `error` \| `warning` \| `info`; `title`; children: the description.                                                          |
| `EmptyState`                          | Empty State  | `message`, `title`, `icon`, `action`. With a `title` it's the Figma card (empty page); without, one line (inside a panel).           |
| `LoadingState`                        | –            | `message` (default "Loading…").                                                                                                      |
| `ErrorState`                          | –            | `error` (any thrown value; shown via `describeError`).                                                                               |
| `Pagination`                          | –            | `page`, `pageCount`, `onPageChange`, `label`.                                                                                        |
| `ProgressBar`                         | –            | `label` (accessible name), `value` (0–1; leave out for indeterminate).                                                               |
| `StatTile`                            | Stat Tile    | `label`, `value`, `delta` (`{ text, better }`: green or red) or `note` (gold, e.g. "Session best").                                  |

Run-specific components built on these live next to their feature, e.g.
`components/runs/StatusBadge` (Figma "Status Badge": `status`, `detail`). The rest of the
Figma "Runs, Laps & Signals" and "Data Viz" pieces:

- `components/runs/LapRow` (Lap Row): `lap`, `time`, `delta`, `series`, `selected`, `compared`,
  `onSelect`, `onCompareChange`. Click the row to select; the checkbox compares.
- `components/runs/LapStepper` (Lap Stepper): `label`, `onPrevious`, `onNext` (leave one out to
  disable that arrow).
- `components/charts/SeriesChip` (Series Chip): `series` (1–8, the `--data-series-N` color),
  `label`, `onRemove` (shows ×).
- `components/charts/SignalRow` (Signal Row): `name`, `unit`, plus Checkbox props.
- `components/charts/ChartTooltip` (Chart Tooltip): `title`, `rows: {series, label, value}[]`.
- `components/charts/PlotCard` (Plot Card): `title`, `unit`, `readout` (a string for Mode=Single, or
  `{series, label, value}[]` for Mode=Compare), `actions`; child: the chart.
- `components/charts/TimeSeriesChart` (Plot Line): `series` (each with `time`, `values` and a
  `series` color slot), `height`, `xAxis="track"` for the lap's 0–100% axis, `onHoverTime` (the x
  under the cursor). Charts with the same `xAxis` share one cursor. The dashboard still plots time
  until it has per-sample track %. Memoize `series`: a new array rebuilds the chart.

Not built as components: Run Row (`components/runs/RunsTable` is the runs list), Session
Timeline and the Track Map pieces (chart/map work).
Page chrome lives in `components/layout`, e.g. `TopBar` (Figma "Top Bar"): children are a
`TopBarNav` of `TopBarLink`s (Context=Library) or a `Breadcrumb` (Context=Run); `actions` go on
the right (Search, Avatar, a Share Button…). The app shell still uses `Sidebar`.

## Which button?

| Use                          | When                                                                                    |
| ---------------------------- | --------------------------------------------------------------------------------------- |
| `Button variant="primary"`   | The one main action of the view ("New run", a modal's "Confirm"). At most one per view. |
| `Button variant="secondary"` | Other actions next to it ("Share", "Export CSV", "Re-run").                             |
| `Button variant="ghost"`     | Low-emphasis actions: "Cancel" in a modal, actions in dense toolbars.                   |
| `Button variant="danger"`    | Destructive actions ("Delete run"); confirm in a Modal when it can't be undone.         |
| `size="sm"`                  | Inside dense UI: the top bar, table rows, cards. Otherwise the default `md`.            |
| `ButtonLink`                 | It opens another page (a link, not an action).                                          |
| `IconButton`                 | Space is tight and the icon is obvious (⋯, ×). Always give a `label`.                   |
| `MenuItem` in a `Menu`       | More than two or three secondary actions on one thing: put them behind ⋯.               |
