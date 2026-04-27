import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/restaurants": "http://127.0.0.1:8000",
      "/state": "http://127.0.0.1:8000",
      "/order": "http://127.0.0.1:8000",
      "/payment": "http://127.0.0.1:8000",
      "/reset": "http://127.0.0.1:8000"
    }
  }
});
