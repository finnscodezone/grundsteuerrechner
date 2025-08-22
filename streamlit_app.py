# streamlit_app.py
# -*- coding: utf-8 -*-
"""
Grundsteuer – Einsparungsrechner (Frontend) bei Verkehrswertnachweis (§ 220 Abs. 2 BewG)
- Eingaben: Grundsteuerwert, Messzahl (‰), Hebesatz (%), Restjahre, optionaler Verkehrswert (Custom)
- Ausgabe: Jahressteuer Status quo, 40%-Schwelle (GSW/1,4), Steuer & Ersparnis an der Schwelle,
           optional Steuer & Ersparnis für den Custom-Verkehrswert
Hinweis: § 251 BewG wird hier bewusst nicht berücksichtigt (kein Mindestwert-Cap), da im Fall des § 220 Abs. 2 BewG nicht anwendbar.
"""
# --- top of file ---
from pathlib import Path
import streamlit as st

ASSETS = Path(__file__).parent / "assets"
LOGO_PATHS = [
    ASSETS / "bossin_logo.png",            # preferred: repo/app/assets/bossin_logo.png
    Path.cwd() / "assets" / "bossin_logo.png",  # fallback
]
LOGO = next((p for p in LOGO_PATHS if p.exists()), None)

st.set_page_config(page_title="Grundsteuer-Rechner (§ 220 Abs. 2 BewG)",
                   page_icon="📉", layout="centered")

# Optional: Streamlit's newer logo API, guarded for older versions
if hasattr(st, "logo") and LOGO is not None:
    st.logo(str(LOGO))  # also sets header/side logo in recent versions

# --- header row with safe image usage ---
col_logo, col_title = st.columns([1, 5], vertical_alignment="center")

with col_logo:
    if LOGO is not None:
        # either size it explicitly...
        st.image(str(LOGO), width=140)
        # ...or fill the column width:
        # st.image(str(LOGO), use_container_width=True)
    else:
        st.write("")  # no-op if logo not found

with col_title:
    st.title("BossinCheck – Schnellcheck Grundsteuer")
    st.caption("Berechnet die Ersparnis, wenn ein **niedrigerer gemeiner Wert** …")


with st.form("eingaben"):
    col1, col2 = st.columns(2)
    with col1:
        gsw = st.number_input("Grundsteuerwert (festgestellt, €)", min_value=0, value=1_031_600, step=1_000, format="%i")
        years = st.number_input("Restjahre bis nächste Hauptfeststellung", min_value=1, value=4, step=1, format="%i")
    with col2:
        mess_permille = st.number_input("Steuermesszahl (‰)", min_value=0.0, value=0.31, step=0.01, format="%.2f")
        heb_prozent = st.number_input("Hebesatz (%)", min_value=0.0, value=470.0, step=10.0, format="%.0f")

    with st.expander("Optionales Szenario (eigener Verkehrswert)", expanded=False):
        use_custom = st.checkbox("Eigenen Verkehrswert berechnen", value=False)
        custom_v = None
        if use_custom:
            custom_v = st.number_input("Verkehrswert laut (fiktivem) Gutachten (€, optional)", min_value=0, value=600_000, step=10_000, format="%i")

    submitted = st.form_submit_button("Berechnen")

# Höhere Präzision für Zwischenrechnungen
getcontext().prec = 28
EURO = Decimal("0.01")

def d(x):
    return Decimal(str(x))

def quant2(x):
    return d(x).quantize(EURO, rounding=ROUND_HALF_UP)

def eur(x: Decimal) -> str:
    xq = quant2(x)
    s = f"{xq:.2f}"
    whole, frac = s.split(".")
    rev = whole[::-1]
    chunks = [rev[i:i+3] for i in range(0, len(rev), 3)]
    whole_fmt = ".".join(chunks)[::-1]
    return f"{whole_fmt},{frac} €"

if submitted:
    # Rechnen
    mess = d(mess_permille) / Decimal("1000")
    heb = d(heb_prozent) / Decimal("100")

    steuer_now = quant2(d(gsw) * mess * heb)
    vmax = quant2(d(gsw) / Decimal("1.4"))
    steuer_vmax = quant2(vmax * mess * heb)
    ersparnis_vmax_jahr = quant2(steuer_now - steuer_vmax)
    ersparnis_vmax_gesamt = quant2(ersparnis_vmax_jahr * d(years))

    st.subheader("Ergebnisse")

    m1, m2, m3 = st.columns(3)
    m1.metric("Status quo – Jahressteuer", eur(steuer_now))
    m2.metric("40%-Schwelle (GSW / 1,4)", eur(vmax))
    m3.metric("Steuer bei 40%-Schwelle", eur(steuer_vmax))

    st.write("---")
    st.write("**Ersparnis bei 40%-Schwelle**")
    c1, c2 = st.columns(2)
    c1.metric("pro Jahr", eur(ersparnis_vmax_jahr))
    c2.metric(f"über {years} Jahr(e)", eur(ersparnis_vmax_gesamt))

    if use_custom and custom_v is not None and custom_v > 0:
        steuer_custom = quant2(d(custom_v) * mess * heb)
        ersparnis_custom_jahr = quant2(steuer_now - steuer_custom)
        ersparnis_custom_gesamt = quant2(ersparnis_custom_jahr * d(years))

        st.write("---")
        st.write("**Optionales Szenario – eigener Verkehrswert**")
        cc1, cc2, cc3 = st.columns(3)
        cc1.metric("Verkehrswert (Custom)", eur(d(custom_v)))
        cc2.metric("Jahressteuer (Custom)", eur(steuer_custom))
        cc3.metric("Ersparnis p.a. (Custom)", eur(ersparnis_custom_jahr))
        st.metric(f"Ersparnis über {years} Jahr(e) (Custom)", eur(ersparnis_custom_gesamt))

    with st.expander("Rechengrundlagen / Hinweise"):
        st.markdown(
            "- Formel: **Grundsteuer = Wert × Messzahl × Hebesatz**  \n"
            "- 40%-Schwelle: **Wert_max = Grundsteuerwert / 1,4**  \n"
            "- Normhinweise: **§§ 220, 198, 221 BewG; § 15 GrStG**  \n"
            "- Diese Variante berücksichtigt **keine Mindestwertkappung** nach § 251 BewG."
        )
else:
    st.info("Werte eingeben und **Berechnen** klicken.")
