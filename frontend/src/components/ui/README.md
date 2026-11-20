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

| Component                             | Figma             | Props                                                                                                                                |
| ------------------------------------- | ----------------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| `Button`                              | Button            | `variant`: `primary` \| `secondary` \| `ghost` \| `danger`; `size`: `md` \| `sm`. Children: label, optionally a lucide icon first.   |
| `ButtonLink`                          | Button            | Same as Button, plus router link props (`to`, `params`, `disabled`).                                                                 |
| `IconButton`                          | Icon Button       | `label` (required: accessible name and tooltip); `variant`: `ghost` \| `secondary`; `pressed` for toggles. Child: a lucide icon.     |
| `Input`                               | Input             | `label`, `helper`, `error` (replaces helper, marks invalid), `icon`, `variant`: `text` \| `timestamp` (mono font).                   |
| `Select`                              | Select            | `options: {value, label}[]`, `value`, `onValueChange`, `label` or `aria-label`, `placeholder`, `disabled`. No other props.           |
| `Search`                              | Search            | `aria-label` (required), `placeholder`, `shortcut` (⌘K/Ctrl+K focuses it; one per page).                                             |
| `Checkbox`                            | Checkbox          | `label`, `indeterminate` (Figma "Mixed"), plus native checkbox props (`checked`, `onChange`…).                                       |
| `Toggle`                              | Toggle            | `label`, plus native checkbox props; renders as a switch.                                                                            |
| `SegmentedControl`                    | Segmented Control | `options: {value, label}[]`, `value`, `onChange`, `aria-label` (required). No other props.                                           |
| `Tabs`, `TabList`, `Tab`, `TabPanel`  | Tab               | Radix Tabs: `Tabs` takes `value`/`defaultValue`/`onValueChange`; `Tab` and `TabPanel` take a matching `value`.                       |
| `Avatar`                              | Avatar            | `initials`, `name` (accessible name and hover title). No other props.                                                                |
| `Tooltip`                             | Tooltip           | `content`, `side`; child: one focusable element. Needs `TooltipProvider` (in `main.tsx`).                                            |
| `Menu`, `MenuItem`, `MenuSeparator`   | Menu              | `Menu`: `trigger` (a button), `align`. `MenuItem`: `icon`, `danger`, `onSelect`, `disabled`.                                         |
| `Modal`, `ModalClose`                 | Modal             | `title`, `children` (body), `footer`, and `open` + `onOpenChange` or `trigger`. Wrap a footer button in `ModalClose`.                |
| `Toaster`, `showToast(type, message)` | Toast             | `Toaster` is rendered once in `main.tsx`; call `showToast("success" \| "error" \| "info", message)` from anywhere (`toastStore.ts`). |
| `Notice`                              | Alert Banner      | `tone`: `error` \| `warning` \| `info`; `title`; children: the description.                                                          |
| `EmptyState`                          | Empty State       | `message`, `title`, `icon`, `action` (e.g. a primary Button).                                                                        |
| `LoadingState`                        | –                 | `message` (default "Loading…").                                                                                                      |
| `ErrorState`                          | –                 | `error` (any thrown value; shown via `describeError`).                                                                               |
| `Pagination`                          | –                 | `page`, `pageCount`, `onPageChange`, `label`.                                                                                        |
| `ProgressBar`                         | –                 | `label` (accessible name), `value` (0–1; leave out for indeterminate).                                                               |

Run-specific components built on these live next to their feature, e.g.
`components/runs/StatusBadge` (Figma "Status Badge": `status`, `detail`).
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
