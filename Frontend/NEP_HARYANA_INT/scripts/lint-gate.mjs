// Release lint gate: fails on rules that indicate runtime breakage (undefined identifiers, broken hook usage).
// The full `npm run lint` still reports style debt (unused variables etc.) without blocking deployment.
import { ESLint } from "eslint";

const BLOCKING_RULES = new Set(["no-undef", "react-hooks/rules-of-hooks", "no-dupe-keys", "no-unreachable"]);

const eslint = new ESLint();
const results = await eslint.lintFiles(["src/**/*.{js,jsx}"]);

const blocking = [];
let other = 0;
for (const file of results) {
  for (const msg of file.messages) {
    if (msg.fatal || (msg.severity === 2 && BLOCKING_RULES.has(msg.ruleId))) {
      blocking.push(`${file.filePath}:${msg.line}:${msg.column} ${msg.ruleId || "parse-error"} ${msg.message}`);
    } else if (msg.severity === 2) {
      other += 1;
    }
  }
}

if (blocking.length) {
  console.error(`lint-gate: FAILED with ${blocking.length} blocking problem(s):`);
  for (const line of blocking) console.error("  " + line);
  process.exit(1);
}
console.log(`lint-gate: OK (no blocking problems; ${other} non-blocking lint error(s) remain, see npm run lint).`);
