/* ============================================================
   Trade Reflect – Verbindung zur Supabase-Datenbank
   ------------------------------------------------------------
   Beide Werte findest du in deinem Supabase-Projekt unter:
   Project Settings (Zahnrad links unten) → API

   1. "Project URL"           → SUPABASE_URL
   2. "anon public" API key   → SUPABASE_ANON_KEY

   Der anon-Key darf öffentlich sichtbar sein. Er erlaubt nur,
   was die Sicherheitsregeln in supabase-setup.sql zulassen:
   Jeder angemeldete Nutzer darf ausschließlich seine eigenen Daten lesen und schreiben.
   ============================================================ */

window.SUPABASE_URL      = "https://HIER-DEINE-PROJEKT-ID.supabase.co";
window.SUPABASE_ANON_KEY = "HIER-DEN-ANON-PUBLIC-KEY-EINFUEGEN";
