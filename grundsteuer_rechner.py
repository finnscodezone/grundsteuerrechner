#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Grundsteuer – Einsparungsrechner bei Verkehrswertnachweis (§ 220 Abs. 2 BewG)

Funktionen:
- Berechnet die aktuelle Grundsteuer aus Grundsteuerwert, Messzahl (‰) und Hebesatz (%).
- Ermittelt die 40%-Schwelle (Grundsteuerwert / 1,4) und die Steuer/Ersparnis an der Schwelle.
- Optional: Rechnet ein frei wählbares Gutachten-Szenario (custom Verkehrswert).
- CLI-Ausgabe als gut lesbare Tabelle oder als JSON.
"""

from __future__ import annotations
from dataclasses import dataclass, asdict
from decimal import Decimal, ROUND_HALF_UP, getcontext
import argparse
import json
import sys

# Höhere Präzision für Zwischenrechnungen
getcontext().prec = 28

EURO = Decimal("0.01")

def d(x) -> Decimal:
    """Decimal-Konverter mit sicherer String-Konvertierung."""
    if isinstance(x, Decimal):
        return x
    return Decimal(str(x))

def quant2(x: Decimal) -> Decimal:
    """Auf 2 Nachkommastellen runden (kaufmännisch)."""
    return d(x).quantize(EURO, rounding=ROUND_HALF_UP)

def eur(x: Decimal) -> str:
    """Deutsche Euro-Formatierung: Tausenderpunkt, Dezimalkomma."""
    xq = quant2(x)
    s = f"{xq:.2f}"
    # Punkt als Tausender, Komma als Dezimaltrenner
    whole, frac = s.split(".")
    # Tausenderpunkt einfügen
    rev = whole[::-1]
    chunks = [rev[i:i+3] for i in range(0, len(rev), 3)]
    whole_fmt = ".".join(chunks)[::-1]
    return f"{whole_fmt},{frac} €"

@dataclass
class Inputs:
    grundsteuerwert: Decimal          # €
    messzahl_permille: Decimal        # ‰, z. B. 0,31
    hebesatz_prozent: Decimal         # %, z. B. 470
    years: int = 4                    # Restjahre bis nächste Hauptfeststellung
    custom_verkehrswert: Decimal | None = None

@dataclass
class Results:
    steuer_status_quo: Decimal
    schwelle_40_prozent: Decimal
    steuer_beim_schwellenwert: Decimal
    ersparnis_pro_jahr_schwelle: Decimal
    ersparnis_gesamt_schwelle: Decimal
    # Optional
    steuer_beim_custom: Decimal | None = None
    ersparnis_pro_jahr_custom: Decimal | None = None
    ersparnis_gesamt_custom: Decimal | None = None

def berechne(inputs: Inputs) -> Results:
    gsw = d(inputs.grundsteuerwert)
    mess = d(inputs.messzahl_permille) / Decimal("1000")  # ‰ -> dezimal
    heb = d(inputs.hebesatz_prozent) / Decimal("100")    # % -> faktor
    years = int(inputs.years)

    # Aktuelle Steuer
    steuer_now = quant2(gsw * mess * heb)

    # 40%-Schwelle
    vmax = quant2(gsw / Decimal("1.4"))
    steuer_vmax = quant2(vmax * mess * heb)
    ersparnis_vmax_jahr = quant2(steuer_now - steuer_vmax)
    ersparnis_vmax_gesamt = quant2(ersparnis_vmax_jahr * d(years))

    res = Results(
        steuer_status_quo=steuer_now,
        schwelle_40_prozent=vmax,
        steuer_beim_schwellenwert=steuer_vmax,
        ersparnis_pro_jahr_schwelle=ersparnis_vmax_jahr,
        ersparnis_gesamt_schwelle=ersparnis_vmax_gesamt
    )

    # Optional: Custom-Szenario
    if inputs.custom_verkehrswert is not None:
        cv = d(inputs.custom_verkehrswert)
        steuer_custom = quant2(cv * mess * heb)
        ersparnis_custom_jahr = quant2(steuer_now - steuer_custom)
        ersparnis_custom_gesamt = quant2(ersparnis_custom_jahr * d(years))
        res.steuer_beim_custom = steuer_custom
        res.ersparnis_pro_jahr_custom = ersparnis_custom_jahr
        res.ersparnis_gesamt_custom = ersparnis_custom_gesamt

    return res

def print_table(inputs: Inputs, results: Results) -> None:
    print("Grundsteuer – Einsparungsrechner (§ 220 Abs. 2 BewG)")
    print()
    print("Eingaben:")
    print(f"  Grundsteuerwert:        {eur(inputs.grundsteuerwert)}")
    print(f"  Messzahl:               {inputs.messzahl_permille} ‰")
    print(f"  Hebesatz:               {inputs.hebesatz_prozent} %")
    print(f"  Restjahre:              {inputs.years}")
    if inputs.custom_verkehrswert is not None:
        print(f"  Custom-Verkehrswert:    {eur(inputs.custom_verkehrswert)}")
    print()
    print("Ergebnisse:")
    print(f"  Status quo – Jahressteuer:              {eur(results.steuer_status_quo)}")
    print(f"  40%-Schwelle (Wert = GSW / 1,4):        {eur(results.schwelle_40_prozent)}")
    print(f"  Steuer bei 40%-Schwelle:                {eur(results.steuer_beim_schwellenwert)}")
    print(f"  Ersparnis pro Jahr (Schwelle):          {eur(results.ersparnis_pro_jahr_schwelle)}")
    print(f"  Ersparnis über {inputs.years} Jahr(e):             {eur(results.ersparnis_gesamt_schwelle)}")
    if results.steuer_beim_custom is not None:
        print()
        print(f"  Szenario – Verkehrswert {eur(inputs.custom_verkehrswert)}:")
        print(f"    Jahressteuer:                          {eur(results.steuer_beim_custom)}")
        print(f"    Ersparnis pro Jahr:                    {eur(results.ersparnis_pro_jahr_custom)}")
        print(f"    Ersparnis über {inputs.years} Jahr(e):           {eur(results.ersparnis_gesamt_custom)}")

def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        description="Grundsteuer-Einsparungsrechner bei Verkehrswertnachweis (§ 220 Abs. 2 BewG)"
    )
    p.add_argument("--gsw", type=str, required=True, help="Grundsteuerwert (Euro), z. B. 1031600")
    p.add_argument("--mess", type=str, default="0.31", help="Steuermesszahl in ‰, z. B. 0.31 (Default)")
    p.add_argument("--heb", type=str, default="470", help="Hebesatz in %, z. B. 470 (Default)")
    p.add_argument("--years", type=int, default=4, help="Restjahre bis zur nächsten Hauptfeststellung (Default: 4)")
    p.add_argument("--custom", type=str, default=None, help="Optional: Verkehrswert (Euro) für Szenario-Berechnung")
    p.add_argument("--json", action="store_true", help="Ergebnis als JSON ausgeben")

    args = p.parse_args(argv)

    inputs = Inputs(
        grundsteuerwert=d(args.gsw),
        messzahl_permille=d(args.mess),
        hebesatz_prozent=d(args.heb),
        years=args.years,
        custom_verkehrswert=d(args.custom) if args.custom is not None else None
    )

    results = berechne(inputs)

    if args.json:
        out = asdict(results)
        # Dezimals für JSON seriell machen
        def enc(o):
            if isinstance(o, Decimal):
                return float(o)  # oder str(o) je nach Bedarf
            return o
        print(json.dumps(out, default=enc, ensure_ascii=False, indent=2))
    else:
        print_table(inputs, results)

    return 0

if __name__ == "__main__":
    sys.exit(main())
