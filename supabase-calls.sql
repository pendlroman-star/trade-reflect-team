-- ============================================================
-- Kings Club Trades Monitor – Club Calls
-- ------------------------------------------------------------
-- Einmal im SQL Editor von Supabase ausführen (New query → einfügen → Run).
-- Kann gefahrlos mehrfach ausgeführt werden.
--
-- Prinzip: Alle angemeldeten Mitglieder dürfen die Videos sehen.
-- Anlegen, ändern und löschen darf nur, wer in der Tabelle app_admins steht.
--
-- WICHTIG: In der Zeile mit 'BETREIBER@BEISPIEL.AT' die E-Mail-Adresse eintragen,
-- mit der sich der Betreiber im Dashboard anmeldet. Weitere Betreiber einfach
-- als zusätzliche Zeile ergänzen.
-- ============================================================

-- 1) Wer ist Betreiber? (über die Schnittstelle für niemanden lesbar)
create table if not exists public.app_admins (
  email text primary key
);
alter table public.app_admins enable row level security;

insert into public.app_admins (email) values
  ('BETREIBER@BEISPIEL.AT')
on conflict (email) do nothing;

create or replace function public.is_admin()
returns boolean
language sql
security definer
stable
set search_path = public
as $$
  select exists (select 1 from public.app_admins where lower(email) = lower(auth.jwt() ->> 'email'));
$$;

revoke all on function public.is_admin() from public;
grant execute on function public.is_admin() to authenticated;

-- 2) Die Videos
create table if not exists public.community_calls (
  id           uuid primary key default gen_random_uuid(),
  title        text not null,
  url          text not null,
  video_id     text not null,
  call_date    date,
  description  text,
  created_at   timestamptz not null default now(),
  created_by   uuid default auth.uid()
);
alter table public.community_calls enable row level security;

drop policy if exists "calls: alle Mitglieder lesen"  on public.community_calls;
drop policy if exists "calls: Betreiber legt an"      on public.community_calls;
drop policy if exists "calls: Betreiber ändert"       on public.community_calls;
drop policy if exists "calls: Betreiber löscht"       on public.community_calls;

create policy "calls: alle Mitglieder lesen" on public.community_calls for select to authenticated using (true);
create policy "calls: Betreiber legt an"     on public.community_calls for insert to authenticated with check (public.is_admin());
create policy "calls: Betreiber ändert"      on public.community_calls for update to authenticated using (public.is_admin()) with check (public.is_admin());
create policy "calls: Betreiber löscht"      on public.community_calls for delete to authenticated using (public.is_admin());
