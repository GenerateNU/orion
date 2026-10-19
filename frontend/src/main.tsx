import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import CurrentRunProvider from "@components/CurrentRunProvider";
import App from "./App";
import "./styles/global.css";

const queryClient = new QueryClient();

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <CurrentRunProvider>
        <App />
      </CurrentRunProvider>
    </QueryClientProvider>
  </StrictMode>,
);
