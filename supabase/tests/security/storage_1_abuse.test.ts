// RED TEAM / storage #1 — can an outsider abuse the Storage API?  (config.toml: [storage] enabled, s3_protocol enabled)
// Storage sits on the same gateway as the game. An anonymous account must NOT be able to create buckets or
// upload objects (resource exhaustion / unauthorised write / hosting arbitrary content on the project).
// Attack: C (fresh anon) tries to create a bucket, upload an object to a made-up bucket, and upload via the
//         s3-style object path. Every write must be refused.
// EXIT 0 = all storage writes refused. throw / EXIT 1 = any bucket created or object stored.
import { anon } from "../flow.test.ts";

const URL_ = process.env.SB_URL ?? "http://127.0.0.1:54321";
const KEY = process.env.SB_KEY ?? "sb_publishable_ACJWlzQHlZjBrEguHvfOxg_3BJgxAaH";
const C = await anon();
const h = (extra: Record<string, string> = {}) => ({ apikey: KEY, Authorization: `Bearer ${C}`, ...extra });

const leaks: string[] = [];
const bucket = "pwned-" + Math.random().toString(36).slice(2, 8);

// 1) create a bucket
{
  const r = await fetch(`${URL_}/storage/v1/bucket`, { method: "POST", headers: h({ "Content-Type": "application/json" }), body: JSON.stringify({ name: bucket, id: bucket, public: true }) });
  const t = await r.text();
  console.log(`  create bucket -> [${r.status}] ${t.slice(0, 120)}`);
  if (r.status >= 200 && r.status < 300) leaks.push("created bucket " + bucket);
}
// 2) upload an object to a (possibly auto-created) bucket
{
  const r = await fetch(`${URL_}/storage/v1/object/${bucket}/x.txt`, { method: "POST", headers: h({ "Content-Type": "text/plain" }), body: "arbitrary-attacker-content" });
  const t = await r.text();
  console.log(`  upload object -> [${r.status}] ${t.slice(0, 120)}`);
  if (r.status >= 200 && r.status < 300) leaks.push("uploaded object to " + bucket);
}
// 3) upload to the conventional "public" bucket name some stacks ship with
{
  const r = await fetch(`${URL_}/storage/v1/object/public/x.txt`, { method: "POST", headers: h({ "Content-Type": "text/plain" }), body: "x" });
  const t = await r.text();
  console.log(`  upload to 'public' -> [${r.status}] ${t.slice(0, 120)}`);
  if (r.status >= 200 && r.status < 300) leaks.push("uploaded object to 'public'");
}
// 4) confirm no buckets are readable to the attacker as a side effect
{
  const r = await fetch(`${URL_}/storage/v1/bucket`, { headers: h() });
  const t = await r.text();
  console.log(`  list buckets -> [${r.status}] ${t.slice(0, 120)}`);
  let arr: unknown[] = []; try { arr = JSON.parse(t); } catch { /* */ }
  if (Array.isArray(arr) && arr.length > 0) leaks.push("buckets visible: " + t.slice(0, 120));
}

if (leaks.length) throw new Error("EXPLOITED storage abuse:\n" + leaks.join("\n"));
console.log("BLOCKED: anonymous account cannot create buckets or upload objects");
process.exit(0);
