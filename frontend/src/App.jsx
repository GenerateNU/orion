import { useState } from "react";

import RaceListView from "./views/RaceListView.jsx";
import RaceMapView from "./views/RaceMapView.jsx";

// Two views for now: the race list, and the map for whichever race was picked from it.
export default function App() {
  const [selectedRace, setSelectedRace] = useState(null);

  return (
    <main style={{ fontFamily: "system-ui", padding: "2rem", maxWidth: "960px", margin: "0 auto" }}>
      <h1>orion</h1>
      {selectedRace ? (
        <RaceMapView race={selectedRace} onBack={() => setSelectedRace(null)} />
      ) : (
        <RaceListView onSelectRace={setSelectedRace} />
      )}
    </main>
  );
}
