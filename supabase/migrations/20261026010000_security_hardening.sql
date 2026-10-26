-- Security hardening (blue-team response to red-team round 1).
--
-- Finding [medium] session_3: every throttle is keyed on the uid, and anonymous sign-in is free and
-- unbound to IP/device, so an outsider mints unlimited anonymous accounts and multiplies every per-user
-- limit (room creation, moves, joins). Demonstrated: 12 freshly minted accounts opened 36 rooms with 0
-- throttles, and each room also writes a private.positions row that game_housekeeping never deleted
-- (it only flipped waiting->abandoned), so storage grew without bound.
--
-- This migration adds the two fixes that belong in the database layer and are enforceable against an
-- outsider on this stack:
--   (1) rate_hit_ip(): a rate limiter keyed on the CLIENT IP (not the uid), so minting new accounts no
--       longer resets the bucket. The edge function uses it as an anti-burst limit on room creation.
--   (2) game_housekeeping() now DELETEs stale rooms (cascading to private.positions) instead of leaving
--       rows forever, so abandoned/old games can no longer grow storage without bound.
--
-- The remaining layer of this finding (the account-minting itself) is an auth-server / deployment control:
-- a captcha on anonymous sign-in and a low per-IP anonymous_users limit. Those cannot be enabled on this
-- local stack without breaking the unauthenticated test harness (anon()), so they are documented as the
-- production configuration in supabase/config.toml and in the blue-team report rather than toggled here.

-- ---------------------------------------------------------------- per-IP rate limiting (fixed window)
-- Separate table/key space from private.rate_limits so the two limiters never collide.
create table if not exists private.ip_rate_limits (
  ip           text not null,
  action       text not null,
  window_start timestamptz not null,
  hits         integer not null,
  primary key (ip, action)
);
revoke all on table private.ip_rate_limits from public, anon, authenticated;

-- Same fixed-window algorithm as rate_hit(), but keyed on the caller's IP address. Returns true while the
-- IP is under the limit for this action/window, false once it is exceeded. SECURITY DEFINER + empty
-- search_path + service_role-only execute: unreachable through the Data API, callable only by the function.
create or replace function public.rate_hit_ip(p_ip text, p_action text, p_max integer, p_window_seconds integer)
returns boolean
language plpgsql
security definer
set search_path = ''
as $$
declare
  n integer;
begin
  if p_ip is null or p_ip = '' then p_ip := 'unknown'; end if;
  insert into private.ip_rate_limits as r (ip, action, window_start, hits)
  values (p_ip, p_action, now(), 1)
  on conflict (ip, action) do update
    set hits = case when r.window_start < now() - make_interval(secs => p_window_seconds) then 1 else r.hits + 1 end,
        window_start = case when r.window_start < now() - make_interval(secs => p_window_seconds) then now() else r.window_start end
  returning hits into n;
  return n <= p_max;
end;
$$;
revoke all on function public.rate_hit_ip(text, text, integer, integer) from public, anon, authenticated;
grant execute on function public.rate_hit_ip(text, text, integer, integer) to service_role;

-- ---------------------------------------------------------------- bounded storage (housekeeping deletes)
-- Replaces the old version that only flipped waiting->abandoned and deleted nothing. Now it DELETEs, so a
-- flood of rooms (even one that slips past the rate limits) cannot grow storage without bound. Deleting a
-- game cascades to private.positions (on delete cascade) and to private.ip_rate_limits we prune by age.
--   * waiting rooms past the 30-minute expiry   -> deleted (they were already unreachable/abandoned)
--   * rooms already marked 'abandoned'           -> deleted
--   * finished games (won/lost/draw) older than 1 day -> deleted (history retained a day for the clients)
-- Cheap and bounded: runs on each create, touches only old rows (indexes on status/created_at).
create or replace function public.game_housekeeping()
returns void
language sql
security definer
set search_path = ''
as $$
  delete from public.games
   where (status = 'waiting'  and created_at < now() - interval '30 minutes')
      or (status = 'abandoned')
      or (status in ('white_won', 'black_won', 'draw') and updated_at < now() - interval '1 day');
  delete from private.rate_limits    where window_start < now() - interval '1 day';
  delete from private.ip_rate_limits where window_start < now() - interval '1 day';
$$;
revoke all on function public.game_housekeeping() from public, anon, authenticated;
grant execute on function public.game_housekeeping() to service_role;
