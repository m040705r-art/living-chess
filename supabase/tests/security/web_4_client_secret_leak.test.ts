// WEB-4  No real secret may ship to the client.  The build serves OnlineConfig.json and OnlineClient.cs
// to the browser (GitHub Pages).  Only the project URL + the PUBLISHABLE key may appear there; a
// service-role key (sb_secret_... / role":"service_role" JWT) or the JWT signing secret must never.
// BLOCKED => exit 0.  Any real secret found in client-shipped files => throw (exploited).
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";

const here = dirname(fileURLToPath(import.meta.url));
const root = resolve(here, "../../.."); // repo root (chess/)
const files = [
  "Assets/Chess/Resources/OnlineConfig.json",
  "Assets/Chess/Code/Runtime/OnlineClient.cs",
];

// patterns that indicate a REAL secret (not the public publishable key, not a mere identifier name)
const SECRET_PATTERNS: [string, RegExp][] = [
  ["service-role secret key", /sb_secret_[A-Za-z0-9_-]{10,}/],
  ["service_role JWT", /eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}/], // any JWT literal shipped
  ["service_role role claim", /"role"\s*:\s*"service_role"/],
  ["jwt signing secret", /(JWT_SECRET|super-secret-jwt|GOTRUE_JWT_SECRET)\s*[:=]/i],
  ["db password", /postgres(ql)?:\/\/[^@\s]+:[^@\s]+@/],
];

const hits: string[] = [];
for (const rel of files) {
  const text = readFileSync(resolve(root, rel), "utf8");
  for (const [label, re] of SECRET_PATTERNS) {
    const m = text.match(re);
    if (m) hits.push(`${rel}: ${label} -> ${m[0].slice(0, 24)}...`);
  }
  // sanity: publishable key is expected and fine
  if (/sb_publishable_/.test(text)) console.log(`${rel}: publishable key present (expected, public by design)`);
}
if (hits.length) throw new Error("EXPLOITED: secret shipped to client:\n" + hits.join("\n"));
console.log("BLOCKED: client files contain only URL + publishable key; no service-role/JWT/db secret.");
process.exit(0);
