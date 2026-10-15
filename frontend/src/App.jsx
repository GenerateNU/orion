import { useState } from "react";

import Husky from "./components/Husky.jsx";
import RunListView from "./views/RunListView.jsx";
import RunMapView from "./views/RunMapView.jsx";

// Two views for now: the run list, and the track for whichever run was picked from it.
export default function App() {
  const [selectedRun, setSelectedRun] = useState(null);

  return (
    <>
      <header className="site-header">
        <div className="site-header__inner">
          <Husky className="site-header__logo" title="Northeastern husky" />
          <div>
            <h1 className="site-header__title">
              Ori<span>on</span>
            </h1>
            <p className="site-header__tagline">Northeastern Electric Racing · Telemetry</p>
          </div>
        </div>
        <div className="checkered" />
      </header>

      <main className="page">
        {selectedRun ? (
          <RunMapView run={selectedRun} onBack={() => setSelectedRun(null)} />
        ) : (
          <RunListView onSelectRun={setSelectedRun} />
        )}
      </main>
    </>
  );
}
