-- Online play (room codes). Security model:
--  * clients sign in anonymously and may only READ the games they sit in (RLS); they can never write a table
--  * every write goes through the `game` Edge Function (service role), which checks the player, the turn and the
--    legality of the move against the stored position before saving it
--  * the private schema (rate limits, the position itself) is not exposed through the API at all

create schema if not exists private;
revoke all on schema private from public, anon, authenticated;

create table public.games (
  id            uuid primary key default gen_random_uuid(),
  code          text not null unique check (code ~ '^[A-HJ-NP-Z2-9]{6}$'),
  white         uuid references auth.users (id) on delete set null,
  black         uuid references auth.users (id) on delete set null,
  moves         text[] not null default '{}' check (cardinality(moves) <= 1200),
  status        text not null default 'waiting'
                check (status in ('waiting', 'playing', 'white_won', 'black_won', 'draw', 'abandoned')),
  result_reason text check (result_reason is null or result_reason ~ '^[a-z_]{1,32}$'),
  version       integer not null default 0 check (version >= 0),
  created_at    timestamptz not null default now(),
  updated_at    timestamptz not null default now(),
  check (white is distinct from black)
);
create index games_white_idx on public.games (white);
create index games_black_idx on public.games (black);
create index games_waiting_idx on public.games (created_at) where status = 'waiting';

-- the authoritative position lives apart from what players can read
create table private.positions (
  game_id  uuid primary key references public.games (id) on delete cascade,
  state    jsonb not null
);

alter table public.games enable row level security;
alter table public.games force row level security;
revoke all on public.games from public, anon, authenticated;
grant select (id, code, white, black, moves, status, result_reason, version, created_at, updated_at)
  on public.games to authenticated;

-- a player sees only the games they sit in; nobody else (not even with the room code) can read a game
create policy games_players_read on public.games
  for select to authenticated
  using ((select auth.uid()) = white or (select auth.uid()) = black);
-- no insert / update / delete policies: with RLS forced, clients cannot write at all

-- ---------------------------------------------------------------- rate limiting (fixed window, per user + action)
create table private.rate_limits (
  user_id      uuid not null,
  action       text not null,
  window_start timestamptz not null,
  hits         integer not null,
  primary key (user_id, action)
);

create or replace function public.rate_hit(p_user uuid, p_action text, p_max integer, p_window_seconds integer)
returns boolean
language plpgsql
security definer
set search_path = ''
as $$
declare
  n integer;
begin
  insert into private.rate_limits as r (user_id, action, window_start, hits)
  values (p_user, p_action, now(), 1)
  on conflict (user_id, action) do update
    set hits = case when r.window_start < now() - make_interval(secs => p_window_seconds) then 1 else r.hits + 1 end,
        window_start = case when r.window_start < now() - make_interval(secs => p_window_seconds) then now() else r.window_start end
  returning hits into n;
  return n <= p_max;
end;
$$;
revoke all on function public.rate_hit(uuid, text, integer, integer) from public, anon, authenticated;
grant execute on function public.rate_hit(uuid, text, integer, integer) to service_role;

-- ---------------------------------------------------------------- server-side helpers (service role only)
-- read the position for the function (private schema is not reachable through the REST API)
create or replace function public.game_state(p_game uuid)
returns jsonb
language sql
security definer
set search_path = ''
as $$ select state from private.positions where game_id = p_game $$;
revoke all on function public.game_state(uuid) from public, anon, authenticated;
grant execute on function public.game_state(uuid) to service_role;

-- create a room: the code is drawn by the database (crypto-strong), the host takes the colour they asked for
create or replace function public.game_create(p_user uuid, p_color text, p_state jsonb)
returns public.games
language plpgsql
security definer
set search_path = ''
as $$
declare
  alphabet constant text := 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789';   -- no 0/O/1/I
  c text; g public.games; open_rooms integer; tries integer := 0;
begin
  if p_color not in ('white', 'black') then raise exception 'bad_color'; end if;
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

-- join by code: one atomic statement, so two joiners can never both take the empty seat
create or replace function public.game_join(p_user uuid, p_code text)
returns public.games
language plpgsql
security definer
set search_path = ''
as $$
declare g public.games;
begin
  update public.games
     set white = coalesce(white, p_user), black = coalesce(black, p_user),
         status = 'playing', version = version + 1, updated_at = now()
   where code = p_code and status = 'waiting'
     and created_at > now() - interval '30 minutes'
     and (white is null or black is null)
     and p_user is distinct from white and p_user is distinct from black
  returning * into g;
  return g;   -- null row when there is no such open room
end;
$$;
revoke all on function public.game_join(uuid, text) from public, anon, authenticated;
grant execute on function public.game_join(uuid, text) to service_role;

-- save a checked move: compare-and-set on version, so a stale or duplicated request changes nothing
create or replace function public.game_commit(p_game uuid, p_version integer, p_move text, p_state jsonb,
                                              p_status text, p_reason text)
returns public.games
language plpgsql
security definer
set search_path = ''
as $$
declare g public.games;
begin
  update public.games
     set moves = case when p_move is null then moves else array_append(moves, p_move) end,
         status = p_status, result_reason = p_reason, version = version + 1, updated_at = now()
   where id = p_game and version = p_version and status = 'playing'
  returning * into g;
  if g.id is not null then
    update private.positions set state = p_state where game_id = p_game;
  end if;
  return g;
end;
$$;
revoke all on function public.game_commit(uuid, integer, text, jsonb, text, text) from public, anon, authenticated;
grant execute on function public.game_commit(uuid, integer, text, jsonb, text, text) to service_role;

-- stale rooms nobody joined, and rate-limit rows, are cleaned up by the function on each create (cheap, bounded)
create or replace function public.game_housekeeping()
returns void
language sql
security definer
set search_path = ''
as $$
  update public.games set status = 'abandoned', updated_at = now()
   where status = 'waiting' and created_at < now() - interval '30 minutes';
  delete from private.rate_limits where window_start < now() - interval '1 day';
$$;
revoke all on function public.game_housekeeping() from public, anon, authenticated;
grant execute on function public.game_housekeeping() to service_role;
