import type { ComponentPropsWithoutRef } from "react";
import { Tabs as RadixTabs } from "radix-ui";
import { cx } from "@utils/classNames";
import styles from "./Tabs.module.css";

// Figma "Tab": Active (true | false). Radix Tabs, styled:
//   <Tabs defaultValue="laps">
//     <TabList aria-label="Panels"><Tab value="laps">Laps</Tab>…</TabList>
//     <TabPanel value="laps">…</TabPanel>
//   </Tabs>
export const Tabs = RadixTabs.Root;

export function TabList({ className, ...props }: ComponentPropsWithoutRef<typeof RadixTabs.List>) {
  return <RadixTabs.List className={cx(styles.list, className)} {...props} />;
}

export function Tab({ className, ...props }: ComponentPropsWithoutRef<typeof RadixTabs.Trigger>) {
  return <RadixTabs.Trigger className={cx(styles.tab, className)} {...props} />;
}

export const TabPanel = RadixTabs.Content;
