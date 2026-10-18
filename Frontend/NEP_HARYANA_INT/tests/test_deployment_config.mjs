// Deployment contract (G6, docs/deployment/VM_SERVER_REQUIREMENTS.md): production builds must not fall back to the
// development API on http://<host>:8000, which fails over HTTPS. Source-level checks.
import { describe, it } from "node:test";
import assert from "node:assert";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const rootDir = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const read = (...p) => fs.readFileSync(path.join(rootDir, "src", ...p), "utf8");

describe("Deployment: API base URL", () => {
  it("auth.js defaults to same-origin /api outside development", () => {
    const src = read("api", "auth.js");
    assert.ok(src.includes("import.meta.env.VITE_API_BASE_URL ||"), "VITE_API_BASE_URL still takes precedence");
    assert.ok(
      src.includes('(import.meta.env.DEV ? `http://${window.location.hostname}:8000/api` : "/api")'),
      "the :8000 runserver fallback is gated by import.meta.env.DEV"
    );
  });

  it("no other API client defines its own base URL", () => {
    const apiDir = path.join(rootDir, "src", "api");
    for (const file of fs.readdirSync(apiDir).filter((f) => f !== "auth.js")) {
      const src = fs.readFileSync(path.join(apiDir, file), "utf8");
      assert.ok(!src.includes(":8000"), `${file} must not hard-code the development API port`);
      assert.ok(!src.includes("VITE_API_BASE_URL"), `${file} must import API_BASE_URL from auth.js`);
    }
    assert.match(read("api", "checker.js"), /import \{[^}]*API_BASE_URL[^}]*\} from "\.\/auth\.js"/);
    assert.match(read("api", "reports.js"), /import \{[^}]*API_BASE_URL[^}]*\} from "\.\/auth"/);
  });
});
