# Kings Club Trades Monitor – Team-Version einrichten

Das Dashboard läuft als Website. Jeder Kollege legt sich selbst ein Konto an
(E-Mail + Passwort) und sieht nur seine eigenen Trades.

Es braucht zwei kostenlose Dienste:

| Dienst | Aufgabe | Kosten |
|---|---|---|
| **Supabase** | Login, Passwörter, Datenbank | kostenlos (Free-Plan reicht für ein Team) |
| **GitHub + GitHub Pages** | Code aufbewahren und Website ins Internet stellen | kostenlos (Repository muss öffentlich sein) |

Gesamtdauer: etwa 20 Minuten.

---

## Teil 1 – Supabase einrichten (Login + Datenbank)

1. Gehe auf **https://supabase.com** und klicke rechts oben auf **Start your project**.
2. Melde dich an. Am einfachsten: **Continue with GitHub** (dann brauchst du kein neues Passwort).
3. Klicke auf **New project**.
   - **Name:** `trade-reflect`
   - **Database Password:** ein langes Passwort erzeugen lassen und im Passwort-Manager speichern. Du brauchst es später normalerweise nicht mehr.
   - **Region:** `Central EU (Frankfurt)`
   - Klicke auf **Create new project**. Warte etwa eine Minute, bis das Projekt fertig ist.
4. **Datenbank anlegen:**
   - Klicke links in der Leiste auf **SQL Editor** (Symbol mit `>_`).
   - Klicke auf **New query**.
   - Öffne die Datei `supabase-setup.sql` aus diesem Ordner, kopiere den **gesamten** Inhalt und füge ihn ins große Textfeld ein.
   - Klicke rechts unten auf **Run**. Unten muss `Success. No rows returned` stehen.
5. **Zugangsdaten für das Dashboard holen:**
   - Klicke links unten auf das **Zahnrad** (Project Settings), dann auf **API**.
   - Kopiere die **Project URL** (sieht aus wie `https://abcdefgh.supabase.co`).
   - Kopiere darunter den Schlüssel **anon public** (lange Zeichenkette, beginnt mit `eyJ`).
   - Öffne die Datei `config.js` aus diesem Ordner in einem Texteditor und trage beide Werte zwischen die Anführungszeichen ein. Speichern.
6. **Website-Adresse bei Supabase hinterlegen** (damit Bestätigungs-Mails auf die richtige Seite führen).
   Diesen Schritt machst du **nach Teil 2**, wenn du die Adresse deiner Website kennst:
   - Links auf **Authentication** → **URL Configuration**.
   - **Site URL:** deine Website-Adresse, z.B. `https://pendlroman-star.github.io/trade-reflect-team/`
   - **Redirect URLs:** **Add URL** → dieselbe Adresse eintragen.
   - **Save**.

### Optional: Einstellungen zur Registrierung

Unter **Authentication → Sign In / Providers → Email**:

- **Confirm email** ist standardmäßig **an**: Neue Nutzer bekommen eine Bestätigungs-Mail und müssen den Link anklicken. Das ist sicherer. Wenn du es einfacher willst, schalte es aus.
- Willst du **nur eingeladene Personen** zulassen? Dann unter **Authentication → Sign In / Providers** den Punkt **Allow new users to sign up** ausschalten und Kollegen unter **Authentication → Users → Invite user** per E-Mail einladen.

---

## Teil 2 – Website mit GitHub Pages veröffentlichen

Der Ordner `trade-reflect-team` ist bereits ein Git-Repository mit einem ersten Commit.

1. Öffne **GitHub Desktop**.
2. Menü **File → Add Local Repository…**, dann **Choose…** und den Ordner
   `/Users/romanpendl/Claude Code/Claude/trade-reflect-team` auswählen. **Add Repository**.
3. Falls du `config.js` bereits ausgefüllt hast, siehst du die Änderung links. Unten links einen Text eingeben (z.B. `Supabase-Zugang eingetragen`) und **Commit to main** klicken.
4. Klicke oben auf **Publish repository**.
   - **Name:** `trade-reflect-team`
   - **Keep this code private:** Haken **entfernen** (GitHub Pages ist nur bei öffentlichen Repositories kostenlos. Im Code stehen keine Geheimnisse; der anon-Key ist dafür gedacht, öffentlich zu sein.)
   - **Publish Repository**.
5. Website einschalten: Gehe im Browser auf **https://github.com/pendlroman-star/trade-reflect-team**.
   - Oben auf **Settings** (Zahnrad-Reiter).
   - Links auf **Pages**.
   - Bei **Source** muss **Deploy from a branch** stehen. Bei **Branch** `main` und `/ (root)` wählen. **Save**.
   - Nach etwa einer Minute erscheint oben die Adresse, z.B. `https://pendlroman-star.github.io/trade-reflect-team/`.
6. Jetzt **Teil 1, Schritt 6** ausführen (Adresse bei Supabase hinterlegen).

Fertig. Diese Adresse schickst du deinen Kollegen. Sie klicken auf **Registrieren**, geben Anzeigename, E-Mail und Passwort ein und legen los.

Wenn du später etwas am Code änderst: In GitHub Desktop **Commit to main** und dann **Push origin**. Die Website aktualisiert sich nach etwa einer Minute.

---

## Teil 3 – Deine eigenen Daten übernehmen

1. Öffne dein **altes** Dashboard (die bisherige `index.html`), klicke auf **Daten → Backup (JSON)**. Eine Datei wird heruntergeladen.
2. Öffne das **neue** Dashboard im Browser, registriere dich und melde dich an.
3. Im neuen Dashboard **Verwalten → Import (CSV / JSON)** → die Backup-Datei wählen → **Ersetzen** bestätigen.
4. Deine Trades, Konten, Regeln und Notizen sind jetzt in deiner Cloud-Datenbank. Der Status oben rechts zeigt „Gespeichert".

---

## So arbeiten Kollegen mit dem Dashboard

1. Adresse öffnen, auf **Registrieren** klicken, Anzeigename, E-Mail und Passwort eingeben.
2. Link in der Bestätigungs-Mail anklicken, dann anmelden.
3. **Verwalten → Konten**: eigene Trading-Konten anlegen (Name, Startkapital, optional Tagesziel und Verlustlimit). Der Knopf „Konten verwalten“ in der Ansicht „Heute“ führt ebenfalls dorthin.
4. **Verwalten → Kategorien**: sagen, woher ein Trade kommt. Vorgegeben sind „Eigene Trades", „Signal XYZ", „Signal Coinminds" und „Signal Claude". Jeder kann Kategorien umbenennen, löschen oder neue anlegen.
5. **＋ Trade eintragen** (oben rechts, öffnet ein Fenster): Konto und Kategorie wählen, Ergebnis eintragen. Alles wird automatisch in der eigenen Cloud-Datenbank gespeichert.
6. **Personen-Symbol oben rechts** öffnet „Mein Konto“: Anzeigename oder Passwort ändern, abmelden oder das eigene Konto samt allen Daten endgültig löschen. Das **Regler-Symbol** daneben ist das Menü „Verwalten“, das **Kurven-Symbol** öffnet die Kings Club Goldanalyse in einem neuen Fenster.

Das Dashboard hat vier Ansichten, umschaltbar über die Reiter in der Kopfzeile: **Heute** (Tagesstand, Konten, Woche, Regeln), **Analyse** (Kategorie-Ranking, Auswertung, Verlust-Analyse, Kurve), **Kalender** und **Historie**.

---

## Team-Seite (freiwillig)

Das **Personen-Gruppen-Symbol** oben rechts öffnet die Team-Seite. Sie zeigt je Trader eine Karte mit Foto, Tagesergebnis, Woche, Monat, Gesamt, Verlaufskurve und den letzten Trades. Ein Klick auf eine Karte öffnet die Details.

- **Aktivieren:** Personen-Symbol → „Mein Konto“ → Haken bei **„Auf der Team-Seite sichtbar sein“** → Speichern. Dort lässt sich auch ein **Profilfoto** hochladen und wählen, ob Beträge in USD oder nur in Prozent gezeigt werden.
- **Geteilt wird nur eine Kurzfassung:** Name, Foto, Ergebnisse, Trefferquote, Kategorien, die letzten 30 Trades. Notizen, Regeln und Kontonamen bleiben privat.
- **Gegenseitigkeit:** Nur wer selbst teilt, sieht die anderen. Haken entfernen und speichern löscht die eigene Karte sofort.
- **Einmalige Einrichtung durch den Betreiber:** Datei `supabase-team.sql` im SQL Editor von Supabase ausführen.

---

## Club Calls

Im Menü **Verwalten** (Regler-Symbol) gibt es den Punkt **Club Calls**. Dort stehen die Aufzeichnungen als YouTube-Videos: der neueste Call groß oben, frühere als Karten darunter. Ein Klick spielt das Video direkt auf der Seite ab. YouTube wird erst beim Klick geladen.

- **Sehen** dürfen die Videos alle angemeldeten Mitglieder.
- **Hinzufügen, bearbeiten, löschen** darf nur der Betreiber. Bei ihm erscheint der Knopf **„＋ Video hinzufügen“**: YouTube-Link einfügen, Titel wird automatisch geholt, Datum und Beschreibung ergänzen, speichern. Auch nicht gelistete Videos funktionieren.
- **Einmalige Einrichtung:** Datei `supabase-calls.sql` im SQL Editor von Supabase ausführen und dabei in der Zeile mit `BETREIBER@BEISPIEL.AT` die eigene Anmelde-Adresse eintragen. Weitere Betreiber lassen sich dort als zusätzliche Zeile ergänzen.

---

## Später: Team-Ranking

Die Datenbank ist dafür schon vorbereitet (Sicht `trades_flat` mit Anzeigenamen).
Sobald das Team es will, braucht es nur eine zusätzliche Leseregel in Supabase und eine neue Seite im Dashboard.

## Häufige Fragen

- **Bestätigungs-Mail kommt nicht an?** Spam-Ordner prüfen. Im Supabase Free-Plan werden nur wenige Mails pro Stunde verschickt; für ein größeres Team später einen eigenen Mail-Versand unter Authentication → SMTP Settings eintragen.
- **Login-Seite meldet „config.js ist noch nicht ausgefüllt"?** Teil 1, Schritt 5 wiederholen und die Änderung mit GitHub Desktop hochladen.
- **Demo ohne Anmeldung zeigen?** An die Adresse `?demo` anhängen, z.B. `https://…/trade-reflect-team/?demo`.
