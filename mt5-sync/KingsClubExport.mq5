//+------------------------------------------------------------------+
//| KingsClubExport.mq5                                              |
//| Kings Club Trades Monitor - Trade-Export                         |
//|                                                                  |
//| Liest die Deal-Historie des eingeloggten Kontos und schreibt sie |
//| alle paar Minuten nach MQL5/Files/kc_trades_<Konto>.csv.         |
//| Das Programm LIEST NUR. Es setzt, aendert oder schliesst keine   |
//| Orders und Positionen.                                           |
//+------------------------------------------------------------------+
#property service
#property copyright   "Kings Club"
#property version     "1.00"
#property description "Schreibt die abgeschlossenen Deals in eine CSV-Datei (nur lesend)."

input int IntervalSeconds = 300;   // Abstand zwischen zwei Exporten in Sekunden

string Clean(string s)
  {
   StringReplace(s, ";", ",");
   StringReplace(s, "\r", " ");
   StringReplace(s, "\n", " ");
   return s;
  }

string Num(double v, int digits) { return DoubleToString(v, digits); }

bool ExportDeals()
  {
   long login = AccountInfoInteger(ACCOUNT_LOGIN);
   if(login <= 0)
      return false;                          // noch kein Konto eingeloggt

   if(!HistorySelect(0, TimeCurrent() + 86400))
      return false;

   int total = HistoryDealsTotal();
   // Abstand Serverzeit - UTC in Sekunden, auf Viertelstunden gerundet
   long offset = (long)(TimeTradeServer() - TimeGMT());
   offset = (long)MathRound(offset / 900.0) * 900;

   string tmpName = "kc_trades_" + IntegerToString(login) + ".tmp";
   string csvName = "kc_trades_" + IntegerToString(login) + ".csv";
   int h = FileOpen(tmpName, FILE_WRITE | FILE_TXT | FILE_ANSI);
   if(h == INVALID_HANDLE)
      return false;

   FileWriteString(h, "# login=" + IntegerToString(login)
                   + ";server=" + Clean(AccountInfoString(ACCOUNT_SERVER))
                   + ";company=" + Clean(AccountInfoString(ACCOUNT_COMPANY))
                   + ";currency=" + AccountInfoString(ACCOUNT_CURRENCY)
                   + ";server_utc_offset=" + IntegerToString(offset)
                   + ";connected=" + IntegerToString(TerminalInfoInteger(TERMINAL_CONNECTED))
                   + ";balance=" + Num(AccountInfoDouble(ACCOUNT_BALANCE), 2)
                   + ";written_utc=" + TimeToString(TimeGMT(), TIME_DATE | TIME_SECONDS)
                   + ";deals=" + IntegerToString(total) + "\n");
   FileWriteString(h, "ticket;order;position;time_server;time_msc;type;entry;symbol;volume;price;sl;tp;profit;commission;swap;fee;magic;reason;comment\n");

   for(int i = 0; i < total; i++)
     {
      ulong t = HistoryDealGetTicket(i);
      if(t == 0)
         continue;
      string line =
         IntegerToString((long)t) + ";" +
         IntegerToString(HistoryDealGetInteger(t, DEAL_ORDER)) + ";" +
         IntegerToString(HistoryDealGetInteger(t, DEAL_POSITION_ID)) + ";" +
         TimeToString((datetime)HistoryDealGetInteger(t, DEAL_TIME), TIME_DATE | TIME_SECONDS) + ";" +
         IntegerToString(HistoryDealGetInteger(t, DEAL_TIME_MSC)) + ";" +
         IntegerToString(HistoryDealGetInteger(t, DEAL_TYPE)) + ";" +
         IntegerToString(HistoryDealGetInteger(t, DEAL_ENTRY)) + ";" +
         Clean(HistoryDealGetString(t, DEAL_SYMBOL)) + ";" +
         Num(HistoryDealGetDouble(t, DEAL_VOLUME), 2) + ";" +
         Num(HistoryDealGetDouble(t, DEAL_PRICE), 5) + ";" +
         Num(HistoryDealGetDouble(t, DEAL_SL), 5) + ";" +
         Num(HistoryDealGetDouble(t, DEAL_TP), 5) + ";" +
         Num(HistoryDealGetDouble(t, DEAL_PROFIT), 2) + ";" +
         Num(HistoryDealGetDouble(t, DEAL_COMMISSION), 2) + ";" +
         Num(HistoryDealGetDouble(t, DEAL_SWAP), 2) + ";" +
         Num(HistoryDealGetDouble(t, DEAL_FEE), 2) + ";" +
         IntegerToString(HistoryDealGetInteger(t, DEAL_MAGIC)) + ";" +
         IntegerToString(HistoryDealGetInteger(t, DEAL_REASON)) + ";" +
         Clean(HistoryDealGetString(t, DEAL_COMMENT)) + "\n";
      FileWriteString(h, line);
     }
   FileClose(h);
   return FileMove(tmpName, 0, csvName, FILE_REWRITE);
  }

void OnStart()
  {
   Print("KingsClubExport gestartet (nur lesend), Intervall ", IntervalSeconds, " s");
   while(!IsStopped())
     {
      if(!ExportDeals())
         Print("KingsClubExport: Export uebersprungen (kein Konto oder Datei nicht schreibbar), Fehler ", GetLastError());
      for(int i = 0; i < IntervalSeconds && !IsStopped(); i++)
         Sleep(1000);
     }
   Print("KingsClubExport beendet");
  }
//+------------------------------------------------------------------+
