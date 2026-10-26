// RED TEAM / authz #7 — GraphQL introspection & data access at /graphql/v1
// Attack: if pg_graphql is enabled and games is exposed, an outsider could introspect the schema and run
//         gamesCollection queries to read/enumerate rooms, dodging the REST RLS story. Try introspection
//         and a direct collection query (user token AND bare key). Even if GraphQL is enabled, RLS must
//         still hide non-member rows.
// EXIT 0 = introspection unavailable OR no game rows returned. throw = schema/rows leaked.
import { anon } from "../flow.test.ts";

const URL_ = process.env.SB_URL ?? "http://127.0.0.1:54321";
const KEY = process.env.SB_KEY ?? "sb_publishable_ACJWlzQHlZjBrEguHvfOxg_3BJgxAaH";
const tok = await anon();

async function gql(token: string | undefined, query: string) {
  const headers: Record<string, string> = { apikey: KEY, "Content-Type": "application/json" };
  if (token) headers.Authorization = `Bearer ${token}`;
  const r = await fetch(`${URL_}/graphql/v1`, { method: "POST", headers, body: JSON.stringify({ query }) });
  return { status: r.status, text: await r.text() };
}

const leaks: string[] = [];

// Create a real game so a working query would have something to return.
await fetch(`${URL_}/functions/v1/game`, { method: "POST", headers: { apikey: KEY, Authorization: `Bearer ${tok}`, "Content-Type": "application/json" }, body: JSON.stringify({ action: "create", color: "white" }) });

for (const token of [tok, undefined]) {
  const intro = await gql(token, "{ __schema { types { name } } }");
  console.log(`  introspection (${token ? "user" : "anon"}): [${intro.status}] ${intro.text.slice(0, 120)}`);
  // leak only if introspection actually returned a schema (no "not enabled"/error)
  if (intro.status >= 200 && intro.status < 300 && /"__schema"/.test(intro.text) && !/not enabled|errors/i.test(intro.text)) {
    leaks.push(`introspection succeeded (${token ? "user" : "anon"}): ${intro.text.slice(0, 160)}`);
  }

  const data = await gql(token, "{ gamesCollection { edges { node { id code white black status } } } }");
  console.log(`  gamesCollection (${token ? "user" : "anon"}): [${data.status}] ${data.text.slice(0, 120)}`);
  const m = data.text.match(/"node"\s*:/g);
  if (data.status >= 200 && data.status < 300 && m && m.length > 0 && !/not enabled|errors/i.test(data.text)) {
    leaks.push(`gamesCollection returned ${m.length} node(s) (${token ? "user" : "anon"}): ${data.text.slice(0, 160)}`);
  }
}

if (leaks.length) throw new Error("EXPLOITED: GraphQL exposed schema/data:\n" + leaks.join("\n"));
console.log("BLOCKED: GraphQL yields no schema introspection and no game rows");
process.exit(0);
