-- Security hardening round 2 (blue-team response to red-team round 2).
--
-- Round 1 fixed the per-uid throttle bypass with a per-IP anti-burst limit and delete-based housekeeping.
-- Round 2 showed that layer is still not a hard guarantee for an outsider:
--   * RED2-S6-XFF  [medium] the per-IP limiter keyed on the client-supplied X-Forwarded-For first hop,
--                  which an outsider forges per request so every request gets its own empty bucket.
--   * RED2-S6c     [low]    even with the limiter working, a sustained flood keeps a 30-minute backlog of
--                  rooms (+ private.positions rows) alive, so storage is still unbounded under flooding.
--   * logic_11_abandon [low] a 'playing' game whose loser simply stops acting is never cleaned up.
--
-- The robust root fix every round-2 agent pointed to is a cap that does NOT depend on IP or uid, so neither
-- forged headers nor minted accounts can exceed it. This migration adds:
--   (1) a GLOBAL cap on concurrent live rooms inside game_create (service-role only), checked atomically
--       before the insert. No amount of X-Forwarded-For spoofing or account minting can push the number of
--       live rooms past it, so storage and the per-create work are hard-bounded regardless of the attacker.
--   (2) housekeeping now also deletes long-idle 'playing' games (no clock exists by design, so a truly dead
--       game is reclaimed after a generous idle window) — bounding storage for the abandon case too.
--
-- The edge-layer per-IP limiter (now keyed on the un-spoofable socket peer, see index.ts) stays as cheap
-- defense-in-depth in front of this cap. The remaining account-minting amplification of move/join and the
-- worker-exhaustion DoS are auth-server / deployment controls (captcha on ALL sign-up paths + low per-IP
-- anonymous_users/sign_in_sign_ups), documented in supabase/config.toml; they cannot be toggled on the local
-- test stack without breaking the unauthenticated harness (anon()).

-- ---------------------------------------------------------------- global live-room cap in game_create
-- Live rooms = rooms still reachable: 'waiting' (not yet expired) or 'playing'. Finished/abandoned rows are
-- short-lived (housekeeping deletes them) and excluded. The cap is high enough that a real player never meets
-- it, but it hard-bounds total storage and work no matter how the attacker multiplies identities or IPs.
-- Tradeoff: a determined flood can occupy creation slots (not a privilege/data break, only new-room
-- availability); the real anti-abuse for that is the production captcha on sign-up (see config.toml).
create or replace function public.game_create(p_user uuid, p_color text, p_state jsonb)
returns public.games
language plpgsql
security definer
set search_path = ''
as $$
declare
  alphabet constant text := 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789';   -- no 0/O/1/I
  global_max constant integer := 5000;   -- hard ceiling on concurrent live rooms (IP/uid-independent)
  c text; g public.games; open_rooms integer; live_rooms integer; tries integer := 0;
begin
  if p_color not in ('white', 'black') then raise exception 'bad_color'; end if;

  -- IP/uid-independent hard cap: forged headers and minted accounts cannot exceed it
  select count(*) into live_rooms from public.games
    where status = 'playing'
       or (status = 'waiting' and created_at > now() - interval '30 minutes');
  if live_rooms >= global_max then raise exception 'server_busy'; end if;

  -- per-user cap on open rooms (unchanged): a single account cannot hoard waiting rooms
  select count(*) into open_rooms from public.games
    where status = 'waiting' and (white = p_user or black = p_user) and created_at > now() - interval '30 minutes';
  if open_rooms >= 3 then raise exception 'too_many_rooms'; end if;

  loop
    tries := tries + 1;
    select string_agg(substr(alphabet, (get_byte(extensions.gen_random_bytes(1), 0) % 32) + 1, 1), '')
      into c from generate_series(1, 6);
    begin
      insert into public.games (code, white, black)
      values (c, case when p_color = 'white' then p_user end, case when p_color = 'black' then p_user end)
      returning * into g;
      exit;
    exception when unique_violation then
      if tries > 8 then raise; end if;
    end;
  end loop;
  insert into private.positions (game_id, state) values (g.id, p_state);
  return g;
end;
$$;
revoke all on function public.game_create(uuid, text, jsonb) from public, anon, authenticated;
grant execute on function public.game_create(uuid, text, jsonb) to service_role;

-- ---------------------------------------------------------------- housekeeping also reclaims dead 'playing' games
-- No clock exists (by design — the owner wants no time control), so a game whose loser stops acting would
-- otherwise sit in 'playing' forever. After a generous idle window a real correspondence game would not hit,
-- the row and its private.positions are deleted so abandonment cannot grow storage without bound. This does
-- not award anyone a result; it only reclaims a game that has gone silent for a very long time.
create or replace function public.game_housekeeping()
returns void
language sql
security definer
set search_path = ''
as $$
  delete from public.games
   where (status = 'waiting'  and created_at < now() - interval '30 minutes')
      or (status = 'abandoned')
      or (status = 'playing'  and updated_at < now() - interval '7 days')
      or (status in ('white_won', 'black_won', 'draw') and updated_at < now() - interval '1 day');
  delete from private.rate_limits    where window_start < now() - interval '1 day';
  delete from private.ip_rate_limits where window_start < now() - interval '1 day';
$$;
revoke all on function public.game_housekeeping() from public, anon, authenticated;
grant execute on function public.game_housekeeping() to service_role;
