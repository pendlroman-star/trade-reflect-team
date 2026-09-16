-- ============================================================
-- Kings Club Trades Monitor – Datenbank-Einrichtung für Supabase
-- ------------------------------------------------------------
-- Einmal komplett in den SQL Editor von Supabase kopieren
-- (linke Leiste → "SQL Editor" → "New query") und auf "Run" klicken.
-- Das Skript kann gefahrlos mehrfach ausgeführt werden.
-- ============================================================

-- 1) Profil je Nutzer (Anzeigename – wird später fürs Team-Ranking gebraucht)
create table if not exists public.profiles (
  id            uuid primary key references auth.users(id) on delete cascade,
  display_name  text,
  created_at    timestamptz not null default now()
);

alter table public.profiles enable row level security;

drop policy if exists "profiles: eigenes Profil lesen"     on public.profiles;
drop policy if exists "profiles: eigenes Profil anlegen"   on public.profiles;
drop policy if exists "profiles: eigenes Profil ändern"    on public.profiles;

create policy "profiles: eigenes Profil lesen"   on public.profiles for select using (auth.uid() = id);
create policy "profiles: eigenes Profil anlegen" on public.profiles for insert with check (auth.uid() = id);
create policy "profiles: eigenes Profil ändern"  on public.profiles for update using (auth.uid() = id) with check (auth.uid() = id);


-- 2) Dashboard-Daten je Nutzer (Trades, Konten, Regeln, Tagesnotizen, Gebühren als ein JSON-Paket)
create table if not exists public.dashboards (
  user_id     uuid primary key references auth.users(id) on delete cascade,
  data        jsonb not null default '{}'::jsonb,
  updated_at  timestamptz not null default now()
);

alter table public.dashboards enable row level security;

drop policy if exists "dashboards: eigene Daten lesen"    on public.dashboards;
drop policy if exists "dashboards: eigene Daten anlegen"  on public.dashboards;
drop policy if exists "dashboards: eigene Daten ändern"   on public.dashboards;
drop policy if exists "dashboards: eigene Daten löschen"  on public.dashboards;

create policy "dashboards: eigene Daten lesen"   on public.dashboards for select using (auth.uid() = user_id);
create policy "dashboards: eigene Daten anlegen" on public.dashboards for insert with check (auth.uid() = user_id);
create policy "dashboards: eigene Daten ändern"  on public.dashboards for update using (auth.uid() = user_id) with check (auth.uid() = user_id);
create policy "dashboards: eigene Daten löschen" on public.dashboards for delete using (auth.uid() = user_id);


-- 3) Bei jeder Registrierung automatisch ein Profil anlegen
create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  insert into public.profiles (id, display_name)
  values (new.id, coalesce(new.raw_user_meta_data->>'display_name', split_part(new.email, '@', 1)))
  on conflict (id) do nothing;
  return new;
end;
$$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
  after insert on auth.users
  for each row execute procedure public.handle_new_user();


-- 4) Aufgeklappte Sicht auf alle Trades (Vorbereitung fürs spätere Team-Ranking).
--    Sie erbt die Sicherheitsregeln der Tabelle dashboards: Jeder sieht darin
--    derzeit NUR seine eigenen Trades. Für ein Ranking später einfach eine
--    zusätzliche select-Policy auf dashboards für alle angemeldeten Nutzer ergänzen.
create or replace view public.trades_flat
with (security_invoker = true) as
select
  d.user_id,
  p.display_name,
  (t->>'id')::bigint            as trade_id,
  (t->>'date')::date            as trade_date,
  t->>'account'                 as account,
  t->>'style'                   as style,
  t->>'symbol'                  as symbol,
  t->>'dir'                     as direction,
  (t->>'pnl')::numeric          as pnl,
  nullif(t->>'risk','')::numeric as risk,
  (t->>'slHit')::boolean        as sl_hit,
  (t->>'tpHit')::boolean        as tp_hit,
  t->>'session'                 as session,
  t->>'reason'                  as reason
from public.dashboards d
left join public.profiles p on p.id = d.user_id,
jsonb_array_elements(coalesce(d.data->'trades', '[]'::jsonb)) as t;


-- 5) Nutzer dürfen ihr eigenes Konto samt allen Daten löschen (Aufruf aus dem Dashboard: "Konto löschen")
create or replace function public.delete_own_account()
returns void
language plpgsql
security definer
set search_path = public
as $$
begin
  if auth.uid() is null then
    raise exception 'Nicht angemeldet';
  end if;
  delete from auth.users where id = auth.uid();   -- profiles und dashboards werden per Cascade mitgelöscht
end;
$$;

revoke all on function public.delete_own_account() from public;
grant execute on function public.delete_own_account() to authenticated;

-- Fertig. Kontrolle: Links unter "Table Editor" sollten jetzt "profiles" und "dashboards" erscheinen.
