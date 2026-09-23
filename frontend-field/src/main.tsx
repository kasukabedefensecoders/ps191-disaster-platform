import React from "react";
import ReactDOM from "react-dom/client";
import { registerSW } from "virtual:pwa-register";

import App from "./App";
import "./styles/tokens.css";

// autoUpdate (vite.config.ts): the Workbox SW checks for a new app-shell
// build and swaps it in without asking — right for a field tool nobody
// wants a "reload to update" prompt on mid-survey.
registerSW({ immediate: true });

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
