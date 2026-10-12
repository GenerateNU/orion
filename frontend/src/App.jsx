import { useState } from "react";

import RunListView from "./views/RunListView.jsx";
import RunMapView from "./views/RunMapView.jsx";

// Two views for now: the run list, and the map for whichever run was picked from it.
export default function App() {
  const [selectedRun, setSelectedRun] = useState(null);

  return (
    <main style={{ fontFamily: "system-ui", padding: "2rem", maxWidth: "960px", margin: "0 auto" }}>
      <h1>orion</h1>
      {selectedRun ? (
        <RunMapView run={selectedRun} onBack={() => setSelectedRun(null)} />
      ) : (
        <RunListView onSelectRun={setSelectedRun} />
      )}
    </main>
  );
}
