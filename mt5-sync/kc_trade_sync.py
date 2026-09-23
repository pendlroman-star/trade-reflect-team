#!/usr/bin/env python3
"""Kings Club Trades Monitor – MetaTrader-5-Import.

Liest die Datei, die der MT5-Dienst KingsClubExport schreibt
(MQL5/Files/kc_trades_<Konto>.csv), baut daraus Trades im Format des
Trades Monitors und spielt neue Trades in den eigenen Datensatz in Supabase ein.

- Eine MT5-Position = eine Order. Positionen auf gleichem Konto, Symbol und
  in gleicher Richtung, die innerhalb von 30 Minuten nach der letzten Order
  eröffnet wurden, werden zu einem Trade zusammengefasst (Formular: 60 Min).
- USD = Brutto-Ergebnis. Kommission, Swap und Gebühren kommen als
  Tagesgebühr je Konto in die Gebührenliste.
- Bereits eingespielte Positionen merkt sich das Programm in
  ~/.config/kc-trade-sync/state.json. Was man im Trades Monitor löscht,
  kommt deshalb nicht wieder.
- Von Hand eingetragene Trades werden nie verändert.

Anmeldung: E-Mail steht in ~/.config/kc-trade-sync/config.json, das Passwort
im Schlüsselbund (Dienst "kc-trades-monitor").

Aufruf:
  python3 kc_trade_sync.py            # einspielen
  python3 kc_trade_sync.py --dry-run  # nur anzeigen, nichts schreiben
"""
import argparse
import csv
import datetime as dt
import glob
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from zoneinfo import ZoneInfo

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
CONF_DIR = os.path.expanduser("~/.config/kc-trade-sync")
CONF_FILE = os.path.join(CONF_DIR, "config.json")
STATE_FILE = os.path.join(CONF_DIR, "state.json")
LOG_FILE = os.path.join(CONF_DIR, "sync.log")
MT5_FILES = os.path.expanduser(
    "~/Library/Application Support/net.metaquotes.wine.metatrader5/drive_c/"
    "Program Files/MetaTrader 5/MQL5/Files")
KEYCHAIN_SERVICE = "kc-trades-monitor"
VIENNA = ZoneInfo("Europe/Vienna")
GROUP_MS = 30 * 60 * 1000    # neue Order innerhalb von 30 Min nach der letzten = derselbe Trade
STALE_HOURS = 26

DEFAULT_CONF = {
    "email": "",
    "default_style": "Eigene Trades",
    # je MT5-Kontonummer: Name im Trades Monitor und ab wann eingespielt wird
    "accounts": {},
    # Broker-Symbol -> Symbol im Trades Monitor (Endungen wie ".r" fallen automatisch weg)
    "symbols": {"GOLD": "XAUUSD", "SILVER": "XAGUSD", "DJ30": "US30", "USA30": "US30",
                "NAS100": "US100", "USTEC": "US100", "DAX40": "GER40"},
}

# --- gleiche Tabellen wie in index.html ---
POINT_VALUES = {"XAUUSD": 100, "XAGUSD": 5000, "US30": 1, "US100": 1, "NAS100": 1, "US500": 1,
                "SPX500": 1, "GER40": 1, "DE40": 1, "BTCUSDT": 1, "ETHUSDT": 1, "SOLUSDT": 1}
SESSIONS = [("opening", 0, 2), ("asia", 2, 6), ("prelondon", 6, 8), ("london", 8, 12),
            ("preny", 12, 14), ("ny", 14, 18), ("afterny", 18, 24)]
ACCOUNT_COLOR = "#3E6E9B"

# MT5-Konstanten
DEAL_BUY, DEAL_SELL = 0, 1
FEE_DEAL_TYPES = {4, 7, 8, 9, 10, 11}      # Charge und Kommissionsbuchungen
ENTRY_IN, ENTRY_OUT, ENTRY_INOUT, ENTRY_OUT_BY = 0, 1, 2, 3
REASON_SL, REASON_TP = 4, 5


def log(msg):
    line = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S") + "  " + msg
    print(line)
    try:
        os.makedirs(CONF_DIR, exist_ok=True)
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except OSError:
        pass


def load_json(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def load_conf():
    conf = load_json(CONF_FILE, None)
    if conf is None:
        conf = json.loads(json.dumps(DEFAULT_CONF))
        save_json(CONF_FILE, conf)
    for k, v in DEFAULT_CONF.items():
        conf.setdefault(k, v)
    return conf


# ---------------------------------------------------------------- Supabase
def supabase_cfg():
    with open(os.path.join(REPO, "config.js"), encoding="utf-8") as f:
        src = f.read()
    url = re.search(r'SUPABASE_URL\s*=\s*"([^"]+)"', src).group(1).rstrip("/")
    key = re.search(r'SUPABASE_ANON_KEY\s*=\s*"([^"]+)"', src).group(1)
    return url, key


def keychain_password(email):
    r = subprocess.run(["/usr/bin/security", "find-generic-password", "-s", KEYCHAIN_SERVICE,
                        "-a", email, "-w"], capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit("Kein Passwort im Schlüsselbund (Dienst %s, Konto %s)." % (KEYCHAIN_SERVICE, email))
    return r.stdout.rstrip("\n")


def http(method, url, key, token=None, body=None, extra=None):
    headers = {"apikey": key, "Content-Type": "application/json"}
    if token:
        headers["Authorization"] = "Bearer " + token
    headers.update(extra or {})
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            raw = r.read()
            return json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        raise SystemExit("Supabase %s %s -> %s %s" % (method, url.split("?")[0], e.code, e.read()[:300]))


def sb_login(url, key, email, pw):
    res = http("POST", url + "/auth/v1/token?grant_type=password", key,
               body={"email": email, "password": pw})
    return res["access_token"], res["user"]["id"]


def sb_get(url, key, token, uid):
    rows = http("GET", url + "/rest/v1/dashboards?select=data,updated_at&user_id=eq." + uid, key, token)
    return (rows[0]["data"] or {}, rows[0]["updated_at"]) if rows else ({}, None)


def sb_put(url, key, token, uid, data, old_updated):
    now = dt.datetime.now(dt.timezone.utc).isoformat()
    if old_updated is None:
        http("POST", url + "/rest/v1/dashboards?on_conflict=user_id", key, token,
             body={"user_id": uid, "data": data, "updated_at": now},
             extra={"Prefer": "resolution=merge-duplicates,return=minimal"})
        return True
    q = "user_id=eq.%s&updated_at=eq.%s" % (uid, urllib.parse.quote(old_updated))
    rows = http("PATCH", url + "/rest/v1/dashboards?" + q, key, token,
                body={"data": data, "updated_at": now}, extra={"Prefer": "return=representation"})
    return bool(rows)   # leer = jemand hat inzwischen gespeichert -> neu versuchen


# ---------------------------------------------------------------- MT5-Datei
def read_export(path):
    with open(path, encoding="latin-1") as f:
        lines = f.read().splitlines()
    meta = {}
    if lines and lines[0].startswith("#"):
        for part in lines[0][1:].strip().split(";"):
            if "=" in part:
                k, v = part.split("=", 1)
                meta[k.strip()] = v.strip()
        lines = lines[1:]
    deals = list(csv.DictReader(lines, delimiter=";"))
    return meta, deals


def f2(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return 0.0


def norm_symbol(sym, conf):
    s = (sym or "").strip().upper()
    s = re.sub(r"[.#_\-+!].*$", "", s)
    return conf["symbols"].get(s, s)


def is_crypto(sym):
    return bool(re.search(r"(USDT|USDC|BTC|ETH|SOL|XRP|DOGE|BNB|ADA)", sym)) and not re.match(r"^XA[UG]", sym)


def session_for(sym, local):
    if is_crypto(sym):
        return "krypto"
    for sid, a, b in SESSIONS:
        if a <= local.hour < b:
            return sid
    return "afterny"


def calc_risk(sym, entry, sl, lot):
    if entry is None or sl is None or lot is None or entry == sl or lot <= 0:
        return None
    return round(abs(entry - sl) * POINT_VALUES.get(sym, 1) * lot, 2)


def utc_ms(deal, offset_s):
    return int(deal["time_msc"]) - offset_s * 1000


def local_of(ms):
    return dt.datetime.fromtimestamp(ms / 1000, tz=dt.timezone.utc).astimezone(VIENNA)


def build_positions(deals, offset_s, conf):
    """Abgeschlossene Positionen + Kosten je Tag (Wiener Datum)."""
    by_pos, day_costs = {}, {}
    for d in deals:
        typ, entry = int(d["type"]), int(d["entry"])
        ms = utc_ms(d, offset_s)
        day = local_of(ms).date().isoformat()
        if typ in FEE_DEAL_TYPES:
            day_costs[day] = day_costs.get(day, 0.0) + f2(d["profit"])
            continue
        if typ not in (DEAL_BUY, DEAL_SELL):
            continue                                   # Einzahlungen usw.
        day_costs[day] = day_costs.get(day, 0.0) + f2(d["commission"]) + f2(d["swap"]) + f2(d["fee"])
        p = by_pos.setdefault(d["position"], {"ins": [], "outs": []})
        (p["ins"] if entry == ENTRY_IN else p["outs"]).append((ms, d))

    positions = []
    for pid, p in by_pos.items():
        if not p["ins"] or not p["outs"]:
            continue
        ins = sorted(p["ins"], key=lambda x: x[0])
        outs = sorted(p["outs"], key=lambda x: x[0])
        vin = sum(f2(d["volume"]) for _, d in ins)
        vout = sum(f2(d["volume"]) for _, d in outs)
        if vout + 1e-9 < vin:
            continue                                   # noch (teilweise) offen
        first = ins[0][1]
        sym = norm_symbol(first["symbol"], conf)
        entry = sum(f2(d["price"]) * f2(d["volume"]) for _, d in ins) / vin if vin else None
        sl = next((f2(d["sl"]) for _, d in ins + outs if f2(d["sl"]) > 0), None)
        positions.append({
            "pos": int(pid), "symbol": sym,
            "dir": "Long" if int(first["type"]) == DEAL_BUY else "Short",
            "open_ms": ins[0][0], "close_ms": outs[-1][0],
            "lot": round(vin, 3), "entry": round(entry, 2) if entry else None, "sl": sl,
            "pnl": round(sum(f2(d["profit"]) for _, d in ins + outs), 2),
            "slHit": any(int(d["reason"]) == REASON_SL for _, d in outs),
            "tpHit": any(int(d["reason"]) == REASON_TP for _, d in outs),
        })
    positions.sort(key=lambda x: x["open_ms"])
    return positions, day_costs


# ---------------------------------------------------------------- Zusammenführen
def aggregate(orders):
    pnl = round(sum(o["pnl"] or 0 for o in orders), 2)
    lots = [o for o in orders if o.get("lot") is not None]
    lot = round(sum(o["lot"] for o in lots), 3) if lots else None
    we = [o for o in orders if o.get("entry") is not None]
    entry = None
    if we:
        wl = sum(o.get("lot") or 0 for o in we)
        entry = (sum(o["entry"] * (o.get("lot") or 0) for o in we) / wl) if wl > 0 else sum(o["entry"] for o in we) / len(we)
        entry = round(entry, 2)
    return pnl, lot, entry


def trade_orders(t):
    if isinstance(t.get("orders"), list) and t["orders"]:
        return t["orders"]
    return [{"lot": t.get("lot"), "entry": t.get("entry"), "pnl": t.get("pnl")}]


def auto_note(start_ms, end_ms):
    return "MT5 · %s–%s" % (local_of(start_ms).strftime("%H:%M"), local_of(end_ms).strftime("%H:%M"))


def ensure_account(data, login, meta, conf):
    acc_conf = conf["accounts"].setdefault(str(login), {})
    name = acc_conf.get("name") or "Tauro %s" % login
    accounts = data.setdefault("accounts", [])
    acc_id = acc_conf.get("id") or "mt5_%s" % login
    for a in accounts:
        if a.get("id") == acc_id:
            return a["id"], False
    for a in accounts:
        if (a.get("name") or "").strip().lower() == name.lower():
            acc_conf["id"] = a["id"]          # merken, damit ein Umbenennen im Trades Monitor nichts kaputt macht
            return a["id"], False
    bal = f2(meta.get("balance"))
    accounts.append({"id": acc_id, "name": name, "sub": "MetaTrader 5 · automatisch",
                     "capital": round(bal) if bal > 0 else 100000, "target": 0, "loss": 0,
                     "color": ACCOUNT_COLOR, "demo": False, "challenge": False, "profitPct": 0,
                     "phase": 1, "lost": False, "firmRules": "", "startPnl": 0, "logo": "", "lostDate": ""})
    return acc_id, True


def find_style(data, conf):
    styles = data.get("styles") or []
    want = (conf.get("default_style") or "").strip().lower()
    for s in styles:
        if (s.get("name") or "").strip().lower() == want or s.get("id") == want:
            return s["id"]
    return styles[0]["id"] if styles else "eigen"


def merge(data, login, meta, positions, day_costs, conf, st):
    """Neue Positionen und Tagesgebühren in den Datensatz einarbeiten. Gibt eine Liste von Meldungen zurück."""
    msgs = []
    trades = data.setdefault("trades", [])
    fees = data.setdefault("fees", [])
    acc_id, new_acc = ensure_account(data, login, meta, conf)
    if new_acc:
        msgs.append("Konto „%s“ angelegt" % next(a["name"] for a in data["accounts"] if a["id"] == acc_id))
    style = find_style(data, conf)
    # "since": Datum "2026-09-22" oder Zeitpunkt in UTC "2026-09-22T07:33:11Z"
    since = conf["accounts"][str(login)].get("since") or ""
    since_ms = 0
    if len(since) > 10:
        since_ms = int(dt.datetime.strptime(since.rstrip("Z"), "%Y-%m-%dT%H:%M:%S")
                       .replace(tzinfo=dt.timezone.utc).timestamp() * 1000)
        since = local_of(since_ms).date().isoformat()

    seen = set(st.setdefault("pos", []))
    for t in trades:
        m = t.get("mt5")
        if isinstance(m, dict) and str(m.get("login")) == str(login):
            seen.update(m.get("pos") or [])
    ids = {t.get("id") for t in trades}

    added = appended = 0
    for p in positions:
        if p["pos"] in seen:
            continue
        date = local_of(p["open_ms"]).date().isoformat()
        if (since and date < since) or p["open_ms"] < since_ms:
            continue
        order ={"lot": p["lot"], "entry": p["entry"], "pnl": p["pnl"]}
        run = None
        for t in reversed(trades):
            m = t.get("mt5")
            if (isinstance(m, dict) and str(m.get("login")) == str(login) and t.get("account") == acc_id
                    and t.get("symbol") == p["symbol"] and t.get("dir") == p["dir"] and t.get("date") == date
                    and 0 <= p["open_ms"] - (t.get("lastOrderAt") or 0) < GROUP_MS):
                run = t
                break
        if run:
            orders = trade_orders(run) + [order]
            run["orders"] = orders
            run["pnl"], run["lot"], run["entry"] = aggregate(orders)
            if run.get("sl") is None and p["sl"]:
                run["sl"] = p["sl"]
            run["risk"] = calc_risk(run["symbol"], run["entry"], run.get("sl"), run["lot"])
            run["slHit"] = bool(run.get("slHit")) or p["slHit"]
            run["tpHit"] = bool(run.get("tpHit")) or p["tpHit"]
            m = run["mt5"]
            m["pos"] = (m.get("pos") or []) + [p["pos"]]
            m["end"] = max(m.get("end") or 0, p["close_ms"])
            if run.get("note") == m.get("note"):
                run["note"] = m["note"] = auto_note(m["start"], m["end"])
            run["lastOrderAt"] = p["open_ms"]
            appended += 1
        else:
            tid = p["open_ms"]
            while tid in ids:
                tid += 1
            ids.add(tid)
            note = auto_note(p["open_ms"], p["close_ms"])
            trades.append({
                "id": tid, "date": date, "account": acc_id, "style": style,
                "symbol": p["symbol"], "dir": p["dir"], "lot": p["lot"], "entry": p["entry"],
                "sl": p["sl"], "risk": calc_risk(p["symbol"], p["entry"], p["sl"], p["lot"]),
                "pnl": p["pnl"], "slHit": p["slHit"], "tpHit": p["tpHit"],
                "session": session_for(p["symbol"], local_of(p["open_ms"])), "sv": 2,
                "reason": None, "note": note, "lastOrderAt": p["open_ms"],
                "mt5": {"login": str(login), "pos": [p["pos"]], "start": p["open_ms"],
                        "end": p["close_ms"], "note": note},
            })
            added += 1
        seen.add(p["pos"])
        st["pos"].append(p["pos"])

    # Tagesgebühren (Kommission, Swap, Gebühren) als Gebühreneintrag je Tag
    fee_state = st.setdefault("fees", {})
    fee_changes = 0
    for day, cost in sorted(day_costs.items()):
        if since and day < since:
            continue
        amount = round(-cost, 2)
        key = "%s:%s" % (login, day)
        fee = next((f for f in fees if f.get("mt5") == key), None)
        if fee is None:
            if day in fee_state or amount <= 0:
                continue          # schon einmal eingespielt und im Trades Monitor gelöscht, oder keine Kosten
            fees.append({"id": int("7%s%s" % (login, day.replace("-", ""))), "date": day,
                         "account": acc_id, "amount": amount, "mt5": key})
            fee_changes += 1
        elif abs((fee.get("amount") or 0) - amount) > 0.004 and amount > 0:
            fee["amount"] = amount
            fee_changes += 1
        fee_state[day] = amount

    if added or appended:
        msgs.append("%d neue Trades, %d Orders an bestehende Trades angehängt" % (added, appended))
    if fee_changes:
        msgs.append("%d Tagesgebühren eingetragen/aktualisiert" % fee_changes)
    return msgs


# ---------------------------------------------------------------- Ablauf
def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--dry-run", action="store_true", help="nur anzeigen, nichts schreiben")
    args = ap.parse_args()

    conf = load_conf()
    exports = sorted(glob.glob(os.path.join(MT5_FILES, "kc_trades_*.csv")))
    if not exports:
        log("Keine Exportdatei gefunden – läuft der Dienst KingsClubExport in MetaTrader?")
        return 1

    parsed = []
    for path in exports:
        meta, deals = read_export(path)
        login = meta.get("login") or re.search(r"kc_trades_(\d+)", path).group(1)
        written = meta.get("written_utc", "")
        try:
            age_h = (dt.datetime.utcnow() - dt.datetime.strptime(written, "%Y.%m.%d %H:%M:%S")).total_seconds() / 3600
        except ValueError:
            age_h = None
        if age_h is not None and age_h > STALE_HOURS:
            log("Achtung: Export für Konto %s ist %.0f Stunden alt – läuft MetaTrader?" % (login, age_h))
        positions, day_costs = build_positions(deals, int(meta.get("server_utc_offset") or 0), conf)
        parsed.append((login, meta, positions, day_costs))

    if args.dry_run and not conf.get("email"):
        data, st_all = {"trades": [], "fees": [], "accounts": [], "styles": []}, {}
    else:
        if not conf.get("email"):
            raise SystemExit("Bitte E-Mail in %s eintragen." % CONF_FILE)
        url, key = supabase_cfg()
        token, uid = sb_login(url, key, conf["email"], keychain_password(conf["email"]))

    for attempt in range(3):
        st_all = load_json(STATE_FILE, {})
        if not (args.dry_run and not conf.get("email")):
            data, updated = sb_get(url, key, token, uid)
        msgs = []
        for login, meta, positions, day_costs in parsed:
            st = st_all.setdefault(str(login), {})
            for m in merge(data, login, meta, positions, day_costs, conf, st):
                msgs.append("Konto %s: %s" % (login, m))
        if not msgs:
            log("Nichts Neues (%s)." % ", ".join("%s: %d Positionen" % (l, len(p)) for l, _, p, _ in parsed))
            save_json(CONF_FILE, conf)
            return 0
        if args.dry_run:
            for m in msgs:
                log("[Probelauf] " + m)
            new = [t for t in data.get("trades", []) if isinstance(t.get("mt5"), dict)]
            for t in new[-15:]:
                print("   %s %-8s %-5s Lot %-5s Entry %-9s USD %9.2f  %s%s" % (
                    t["date"], t["symbol"], t["dir"], t["lot"], t["entry"], t["pnl"],
                    t["note"], "  (%d Orders)" % len(t["orders"]) if t.get("orders") else ""))
            return 0
        if sb_put(url, key, token, uid, data, updated):
            save_json(STATE_FILE, st_all)
            save_json(CONF_FILE, conf)
            for m in msgs:
                log(m)
            return 0
        log("Datensatz wurde gerade im Trades Monitor gespeichert – neuer Versuch.")
    log("Abgebrochen: Datensatz änderte sich dreimal hintereinander.")
    return 2


if __name__ == "__main__":
    sys.exit(main())
