-- ============================================================
-- Kings Club Trades Monitor – Team-Seite
-- ------------------------------------------------------------
-- Einmal im SQL Editor von Supabase ausführen (New query → einfügen → Run).
-- Kann gefahrlos mehrfach ausgeführt werden.
--
-- Prinzip: Jeder Trader veröffentlicht freiwillig eine Kurzfassung (Name, Foto,
-- Ergebnisse, letzte Trades). Nur wer selbst eine Kurzfassung teilt, darf die
-- der anderen lesen. Die vollständigen Daten (Tabelle dashboards) bleiben privat.
-- ============================================================

create table if not exists public.team_cards (
  user_id       uuid primary key references auth.users(id) on delete cascade,
  display_name  text,
  avatar        text,
  card          jsonb not null default '{}'::jsonb,
  updated_at    timestamptz not null default now()
);

alter table public.team_cards enable row level security;

-- Prüft, ob der angemeldete Nutzer selbst teilt (läuft mit Eigentümerrechten, damit die Leseregel sich nicht selbst aufruft)
create or replace function public.is_team_member()
returns boolean
language sql
security definer
stable
set search_path = public
as $$
  select exists (select 1 from public.team_cards where user_id = auth.uid());
$$;

revoke all on function public.is_team_member() from public;
grant execute on function public.is_team_member() to authenticated;

drop policy if exists "team: lesen, wenn man selbst teilt" on public.team_cards;
drop policy if exists "team: eigene Karte anlegen"         on public.team_cards;
drop policy if exists "team: eigene Karte ändern"          on public.team_cards;
drop policy if exists "team: eigene Karte löschen"         on public.team_cards;

create policy "team: lesen, wenn man selbst teilt" on public.team_cards for select to authenticated using (user_id = auth.uid() or public.is_team_member());
create policy "team: eigene Karte anlegen"         on public.team_cards for insert to authenticated with check (user_id = auth.uid());
create policy "team: eigene Karte ändern"          on public.team_cards for update to authenticated using (user_id = auth.uid()) with check (user_id = auth.uid());
create policy "team: eigene Karte löschen"         on public.team_cards for delete to authenticated using (user_id = auth.uid());
