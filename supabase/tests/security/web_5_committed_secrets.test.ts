// WEB-5  No secret or real .env may be committed to the repo (public GitHub repo backs GitHub Pages).
// Check: no tracked .env file, and no tracked file carries a service-role key, JWT signing secret,
// sb_secret token, or a Postgres URL with a password.
// BLOCKED => exit 0.  A tracked secret / tracked .env => throw (exploited).
import { execSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";

const here = dirname(fileURLToPath(import.meta.url));
const root = resolve(here, "../../.."); // repo root (chess/)
const sh = (cmd: string) => execSync(cmd, { cwd: root, encoding: "utf8" }).trim();

const problems: string[] = [];

// 1) tracked .env files
const tracked = sh("git ls-files").split(/\r?\n/).filter(Boolean);
const envFiles = tracked.filter((f) => /(^|\/)\.env(\.|$)/.test(f) && !/\.env\.example$/.test(f));
if (envFiles.length) problems.push("tracked .env file(s): " + envFiles.join(", "));

// 2) secret values inside tracked files (git grep only searches tracked content)
const grep = (re: string) => {
  try { return sh(`git grep -nI -E ${JSON.stringify(re)}`); } catch { return ""; } // git grep exits 1 when no match
};
const SECRET_VALUE_PATTERNS: [string, string][] = [
  ["service-role secret token", "sb_secret_[A-Za-z0-9_-]{10,}"],
  ["role:service_role JWT claim", "\"role\"[[:space:]]*:[[:space:]]*\"service_role\""],
  ["JWT literal", "eyJ[A-Za-z0-9_-]{10,}\\.[A-Za-z0-9_-]{10,}\\.[A-Za-z0-9_-]{10,}"],
  ["postgres URL with password", "postgres(ql)?://[^@[:space:]]+:[^@[:space:]]+@"],
  ["jwt signing secret assignment", "(JWT_SECRET|GOTRUE_JWT_SECRET)[[:space:]]*="],
];
for (const [label, re] of SECRET_VALUE_PATTERNS) {
  const out = grep(re);
  if (out) problems.push(`${label}:\n${out}`);
}

if (problems.length) throw new Error("EXPLOITED: secret/.env committed to repo:\n" + problems.join("\n\n"));
console.log("BLOCKED: no tracked .env and no service-role/JWT/db secret in tracked files (" + tracked.length + " files scanned).");
process.exit(0);
