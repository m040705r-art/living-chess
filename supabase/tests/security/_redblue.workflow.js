export const meta = {
  name: 'living-chess-red-blue',
  description: 'Red team attacks the local chess backend (authorised), blue team fixes, red team re-attacks until clean',
  phases: [
    { title: 'Attack', detail: 'red-team agents probe each attack surface with real HTTP tests' },
    { title: 'Defend', detail: 'blue team fixes every exploitable finding' },
    { title: 'Re-attack', detail: 'bypass attempts on the fixes + completeness critic' },
  ],
}

const CONTEXT = [
  'Project "Living Chess", repo C:/Users/m0407/chess (Windows; use the Bash tool with forward slashes; node 24 runs .ts files directly).',
  'This is the OWNER\'S OWN local Supabase dev stack, running now. Security testing it is authorised by the owner. Scope is strictly this local stack.',
  'Endpoints: http://127.0.0.1:54321 with /auth/v1, /rest/v1, /graphql/v1, /functions/v1/game .',
  'Publishable key (public by design): sb_publishable_ACJWlzQHlZjBrEguHvfOxg_3BJgxAaH',
  'Source to read (white-box): supabase/functions/game/index.ts, supabase/functions/_shared/chess.ts,',
  '  supabase/migrations/20261026000000_online_games.sql, Assets/Chess/Code/Runtime/OnlineClient.cs,',
  '  the online section of Assets/Chess/Code/Runtime/ChessGame.cs, supabase/config.toml.',
  'Helpers: supabase/tests/flow.test.ts exports anon() (returns a fresh anonymous access token) and call(token, body) (POSTs to the game function).',
  '',
  'Intended security model: anonymous sign-in; a player may only READ the games they sit in (RLS); clients never write tables directly;',
  'every change goes through the edge function, which verifies the JWT via the auth server, rate-limits, validates input strictly,',
  'checks move legality against the server\'s own stored position, and uses compare-and-set on a version number. Room codes are 6 chars',
  'from a 32-char alphabet and expire after 30 minutes. The private schema (positions, rate_limits) must never be reachable through the API.',
  '',
  'RULES for every agent:',
  '- Act as an OUTSIDER: you may use only the publishable key, anonymous accounts you create, and HTTP. NEVER attack with the service-role key,',
  '  the JWT secret, or the DB password (those are owner-only secrets; using them proves nothing about an outside attacker).',
  '- Read any source you like. Do NOT stop/restart docker, do NOT git commit/push, do NOT touch Unity scenes, art, animations, or BlenderSource.',
  '- Keep load modest: <= 40 concurrent requests; every test file must finish within 90s.',
  '- Write each attack as an executable regression test at supabase/tests/security/<name>.test.ts that EXITS 0 when the attack is BLOCKED',
  '  and EXITS 1 (throw) when the attack SUCCEEDS. Import { anon, call } from "../flow.test.ts". Run it: cd C:/Users/m0407/chess && node supabase/tests/security/<name>.test.ts',
  '- Only mark "exploitable" with concrete evidence from a real run you performed. Use "theoretical" for things you reasoned about but could not run.',
].join('\n')

const FINDINGS = {
  type: 'object',
  properties: {
    findings: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          id: { type: 'string' },
          title: { type: 'string' },
          severity: { type: 'string', enum: ['critical', 'high', 'medium', 'low', 'info'] },
          status: { type: 'string', enum: ['exploitable', 'blocked', 'theoretical'] },
          attack: { type: 'string' },
          evidence: { type: 'string' },
          fix: { type: 'string' },
          test_file: { type: 'string' },
        },
        required: ['id', 'title', 'severity', 'status', 'attack', 'evidence', 'fix'],
      },
    },
    summary: { type: 'string' },
  },
  required: ['findings', 'summary'],
}

const SURFACES = [
  ['authz', 'AUTHORISATION & DATA EXPOSURE. Try to read or change games you do not sit in, or to write any table at all. Probe: REST select/insert/update/delete/patch on games, positions, rate_limits (with your user token AND with the bare publishable key); PostgREST operators (or=, not., ilike, in) on code/ids to enumerate rooms or read others; embedding/joins to pull the hidden position "state"; RPC calls to rate_hit/game_create/game_join/game_commit/game_state/game_housekeeping directly over /rest/v1/rpc; the private schema via Accept-Profile / Content-Profile headers; GraphQL introspection and queries at /graphql/v1; and whether the function leaks whether a game exists to a non-member.'],
  ['logic', 'GAME LOGIC & INPUT VALIDATION. As a legitimate member of a game, try to cheat or crash it: move out of turn; move the opponent\'s pieces; make illegal/teleport/own-king-capture moves; replay or reorder a move (stale version); send two moves concurrently (race the version check); oversized/malformed/deeply-nested JSON bodies; unicode/emoji/null bytes in fields; wrong types; extra fields; promotion edge cases; resign twice; act on a finished game. Also port a few perft-style positions to confirm the SERVER rejects every illegal move your client could send.'],
  ['session', 'AUTH, SESSION & RATE LIMITING. Attack the identity and throttling layer: forged/edited/expired/none/alg=none JWTs; using the publishable key as a bearer token to call the function; another project\'s anon JWT; reusing/refresh-token abuse; whether rate limits actually trigger (hammer create/join/move and confirm 429), whether they are per-user and bypassable by making many anonymous accounts, and whether the limits are low enough to matter; room-code brute force (how many guesses per minute, and is 6 chars from 32 symbols enough given the rate limit and 30-min expiry); resource exhaustion via many open rooms per user.'],
  ['web', 'WEB / DEPLOYMENT EXPOSURE. The build is served from GitHub Pages at https://m040705r-art.github.io. Check: CORS (does the function reflect arbitrary Origins? can evil.example call it from a browser? are the Access-Control headers correct and locked to the allow-list?); whether any real secret is shipped to the client (scan Assets/Chess/Resources/OnlineConfig.json and OnlineClient.cs — only URL + publishable key should be there, never service-role/JWT secret); security headers on function responses; the repo for committed secrets or .env files that should be gitignored (git ls-files | grep -i env, scan tracked files for service_role/sb_secret/JWT); and supabase/config.toml for prod-unsafe values that must not ship.'],
]

phase('Attack')
log('Red team: ' + SURFACES.length + ' agents probing the live local backend (authorised, scoped to 127.0.0.1)')

const attackResults = await parallel(SURFACES.map(([key, brief]) => () =>
  agent(
    CONTEXT + '\n\nYou are RED TEAM, surface: ' + key + '.\n' + brief +
    '\n\nActually run your attacks against the live local stack (write the test files and execute them with node). ' +
    'Create a fresh anonymous account per simulated player. Save every attack as supabase/tests/security/' + key + '_<n>.test.ts ' +
    '(exit 0 = blocked, throw = exploited). Return structured findings; for each, set status from what actually happened when you ran it.',
    { phase: 'Attack', label: 'red:' + key, schema: FINDINGS }
  ).then(r => ({ key, ...r }))
))

const allFindings = attackResults.filter(Boolean).flatMap(r => (r.findings || []).map(f => ({ ...f, surface: r.key })))
const exploitable = allFindings.filter(f => f.status === 'exploitable')
log('Attack phase: ' + allFindings.length + ' findings, ' + exploitable.length + ' exploitable')

let defendReport = 'No exploitable findings; nothing to fix.'
if (exploitable.length > 0) {
  phase('Defend')
  log('Blue team fixing ' + exploitable.length + ' exploitable finding(s)')
  const bundle = exploitable.map(f =>
    '- [' + f.severity + '] ' + f.title + ' (surface ' + f.surface + ')\n  attack: ' + f.attack +
    '\n  evidence: ' + f.evidence + '\n  suggested fix: ' + f.fix + (f.test_file ? '\n  test: ' + f.test_file : '')
  ).join('\n')
  defendReport = await agent(
    CONTEXT + '\n\nYou are BLUE TEAM. The red team proved these are exploitable against the live local stack:\n\n' + bundle +
    '\n\nFix EVERY one at the right layer — prefer database RLS/grants/RPC hardening (supabase/migrations: add a NEW migration file ' +
    'named 20261026010000_security_hardening.sql, do not edit the existing migration) and edge-function hardening ' +
    '(supabase/functions/game/index.ts, supabase/functions/_shared/chess.ts), and OnlineClient.cs / config only if the flaw is there. ' +
    'After writing a new migration, apply it with: cd C:/Users/m0407/chess && npx supabase migration up --local (or `npx supabase db reset` ' +
    'if needed — the stack is disposable). The function server hot-reloads on file save. Then RE-RUN every security test in ' +
    'supabase/tests/security/ and the original supabase/tests/flow.test.ts to confirm the holes are closed AND normal play still works. ' +
    'Do not weaken real functionality. Report what you changed, the migration/file names, and the final test results (paste the pass/fail lines).',
    { phase: 'Defend', label: 'blue:fix' }
  )
}

phase('Re-attack')
log('Red team round 2: bypass the fixes + completeness critic')
const prior = allFindings.map(f => f.status + ': ' + f.title).join('\n')
const reResults = await parallel([
  () => agent(
    CONTEXT + '\n\nYou are RED TEAM round 2. The blue team just hardened the backend in response to round 1:\n' + prior +
    '\n\nBlue team report:\n' + defendReport +
    '\n\nTry to BYPASS the fixes — variations, encodings, and alternate paths the patch may have missed. Re-run the existing ' +
    'supabase/tests/security/*.test.ts against the current stack and add new bypass tests. Report any finding that is STILL exploitable.',
    { phase: 'Re-attack', label: 'red:bypass', schema: FINDINGS }
  ),
  () => agent(
    CONTEXT + '\n\nYou are the COMPLETENESS CRITIC. Round 1 covered: authz, game-logic, session/rate-limit, web/deploy.\n' +
    'Findings so far:\n' + prior + '\n\nName attack surfaces or specific cases NOT yet tested (e.g. SQL/NoSQL injection through PostgREST ' +
    'filters, auth provider quirks, storage/functions other than game, IDOR on any id, timing/enumeration oracles, denial of service, ' +
    'business-logic abuse like abandoning to deny a win, draw-claim edge cases). For each gap, actually write and run one test under ' +
    'supabase/tests/security/ to confirm whether it is a real hole. Report what you found.',
    { phase: 'Re-attack', label: 'red:critic', schema: FINDINGS }
  ),
])

const round2 = reResults.filter(Boolean).flatMap(r => r.findings || [])
const stillOpen = round2.filter(f => f.status === 'exploitable')
log('Re-attack: ' + round2.length + ' findings, ' + stillOpen.length + ' still exploitable')

return {
  round1: { total: allFindings.length, exploitable: exploitable.length, findings: allFindings },
  defend: defendReport,
  round2: { total: round2.length, stillExploitable: stillOpen.length, findings: round2 },
  verdict: stillOpen.length === 0 ? 'All exploitable findings closed; round 2 found no surviving holes.' : stillOpen.length + ' finding(s) still exploitable — needs another pass.',
}
