import { useCurrentRun } from "@hooks/useCurrentRun";
import { formatRunLabel } from "@utils/format";
import RunSelectView from "@views/RunSelectView";

export default function App() {
  const { currentRun } = useCurrentRun();

  return (
    <div className="app">
      <header className="app-header">
        <h1>Orion</h1>
        <span className="app-header__run">
          {currentRun
            ? `Loaded: ${formatRunLabel({
                run_id: currentRun.run_id,
                time: currentRun.run_time ?? currentRun.start_time,
              })}`
            : "No run loaded"}
        </span>
      </header>
      <main className="app-main">
        <RunSelectView />
      </main>
    </div>
  );
}
