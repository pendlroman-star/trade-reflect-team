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
