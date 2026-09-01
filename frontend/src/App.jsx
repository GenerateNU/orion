import { useEffect, useState } from "react";

export default function App() {
  const [status, setStatus] = useState("...");

  useEffect(() => {
    fetch("/api/health")
      .then((r) => r.json())
      .then((d) => setStatus(d.status))
      .catch(() => setStatus("unreachable"));
  }, []);

  return (
    <main style={{ fontFamily: "system-ui", padding: "2rem" }}>
      <h1>orion</h1>
      <p>backend: {status}</p>
    </main>
  );
}
