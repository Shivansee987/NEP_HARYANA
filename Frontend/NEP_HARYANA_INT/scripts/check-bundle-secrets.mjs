// Fails when a production build contains development/demo credentials or dev-only shortcuts (FIN-02).
// Usage: node scripts/check-bundle-secrets.mjs [distDir]   (default: ./dist)
import fs from "node:fs";
import path from "node:path";

const dist = path.resolve(process.argv[2] || "dist");
const FORBIDDEN = [
  { name: "demo account domain", re: /@demo\.local/ },
  { name: "dev account domain", re: /@dev\.local/ },
  { name: "demo institution password", re: /Demo@1234/ },
  { name: "dev applicant password", re: /Dev(Principal|Nodal|Admin)@\d+/ },
  { name: "split dev admin password", re: /"Dev"\s*,\s*"Admin"/ },
  { name: "quick dev login section", re: /Quick Applicant Dev Login/ },
];

if (!fs.existsSync(dist)) {
  console.error(`check-bundle-secrets: ${dist} does not exist; run the production build first.`);
  process.exit(2);
}

const files = [];
(function walk(dir) {
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) walk(full);
    else if (/\.(js|mjs|html|css|map|json|txt)$/i.test(entry.name)) files.push(full);
  }
})(dist);

const hits = [];
for (const file of files) {
  const text = fs.readFileSync(file, "utf8");
  for (const { name, re } of FORBIDDEN) {
    if (re.test(text)) hits.push(`${path.relative(dist, file)}: ${name}`);
  }
}

if (hits.length) {
  console.error("check-bundle-secrets: FAILED. Development credentials found in the production bundle:");
  for (const h of hits) console.error("  - " + h);
  process.exit(1);
}
console.log(`check-bundle-secrets: OK (${files.length} files scanned, no development credentials).`);
