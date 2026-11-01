// Runs before every test file (vite.config.ts → test.setupFiles).
import { afterEach } from "vitest";
import { cleanup } from "@testing-library/react";
import "@testing-library/jest-dom/vitest";

// Remove whatever the previous test rendered.
afterEach(cleanup);
