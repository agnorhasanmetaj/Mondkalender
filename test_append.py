import math
import datetime as dt
import calendar

import streamlit as st
from astral import LocationInfo
from astral.sun import sun
from astral.moon import moonrise, moonset, phase
import pytz
import pandas as pd


# -------------------------------------------------
# Preset-Standorte
# -------------------------------------------------
PRESET_LOCATIONS = {
    "Villach": (46.6167, 13.8500, "Europe/Vienna"),
    "Wien": (48.2082, 16.3738, "Europe/Vienna"),
    "Berlin": (52.5200, 13.4050, "Europe/Berlin"),
    "London": (51.5074, -0.1278, "Europe/London"),
    "New York": (40.7128, -74.0060, "America/New_York"),
}


# -------------------------------------------------
# Helper: Mondphase -> Name & Icon
# -------------------------------------------------
def phase_name_and_icon(phase_value: float):
    synodic = 29.53
    fraction = (phase_value % synodic) / synodic
    if fraction < 0.0625 or fraction >= 0.9375:
        return "New Moon", "🌑"
    elif fraction < 0.1875:
        return "Waxing Crescent", "🌒"
    elif fraction < 0.3125:
        return "First Quarter", "🌓"
    elif fraction < 0.4375:
        return "Waxing Gibbous", "🌔"
    elif fraction < 0.5625:
        return "Full Moon", "🌕"
    elif fraction < 0.6875:
        return "Waning Gibbous", "🌖"
    elif fraction < 0.8125:
        return "Last Quarter", "🌗"
    else:
        return "Waning Crescent", "🌘"


def ideal_day_night_hours(phase_value: float):
    # Idealisiertes Modell (Neumond Tag, Vollmond Nacht)
    full_phase_age = 14.0
    phi = math.pi * (phase_value / full_phase_age)
    night_share = (1 - math.cos(phi)) / 2
    night_share = max(0.0, min(1.0, night_share))
    night_hours = 24 * night_share
    day_hours = 24 - night_hours
    return day_hours, night_hours


def illumination_percent(phase_value: float):
    full_phase_age = 14.0
    phi = math.pi * (phase_value / full_phase_age)
    illum = (1 - math.cos(phi)) / 2
    illum = max(0.0, min(1.0, illum))
    return illum * 100


# -------------------------------------------------
# Auf-/Untergang
# -------------------------------------------------
def get_sun_times(location: LocationInfo, date: dt.date):
    tz = pytz.timezone(location.timezone)
    s = sun(location.observer, date=date, tzinfo=tz)
    return s.get("sunrise"), s.get("sunset")


def get_moon_times(location: LocationInfo, date: dt.date):
    tz = pytz.timezone(location.timezone)
    try:
        mr = moonrise(location.observer, date=date, tzinfo=tz)
    except Exception:
        mr = None
    try:
        ms = moonset(location.observer, date=date, tzinfo=tz)
    except Exception:
        ms = None
    return mr, ms


def fmt_time(t: dt.datetime | None):
    if t is None:
        return "–"
    return t.strftime("%H:%M")


# -------------------------------------------------
# Mond-Aktivitäten (Mondkalender-Style)
# -------------------------------------------------
def moon_activity_tips(phase_name: str):
    phase_name_lower = phase_name.lower()
    if "new moon" in phase_name_lower:
        good = ["Neustart von Projekten planen",
                "Ziele setzen & reflektieren",
                "Altes mental loslassen, Detox, Ruhe"]
        avoid = ["Überstürzte große Entscheidungen",
                 "Zu viel Aktionismus ohne Plan"]
    elif "waxing" in phase_name_lower and "crescent" in phase_name_lower:
        good = ["Neue Gewohnheiten beginnen",
                "Langfristige Trainingspläne starten",
                "Ideen sammeln, Brainstorming"]
        avoid = ["Aufgeben nur wegen kleiner Rückschläge"]
    elif "first quarter" in phase_name_lower:
        good = ["Konkrete Schritte setzen & dranbleiben",
                "Verhandlungen vorbereiten",
                "Teamarbeit & Abstimmung"]
        avoid = ["Konflikte ignorieren, die nach Klarheit verlangen"]
    elif "waxing gibbous" in phase_name_lower:
        good = ["Projekte fertig vorbereiten",
                "Präsentationen, Pitches ausfeilen",
                "Feinschliff an Konzepten"]
        avoid = ["Alles auf den letzten Drücker komplett ändern"]
    elif "full moon" in phase_name_lower:
        good = ["Kreative Aktivitäten, Kunst, Musik",
                "Soziale Treffen & Feiern",
                "Reflexion: Was hat der letzte Zyklus gebracht?"]
        avoid = ["Übertreibungen (Stress, Alkohol, Drama)",
                 "Unnötige Streitgespräche"]
    elif "waning gibbous" in phase_name_lower:
        good = ["Aufräumen, Ausmisten (physisch & mental)",
                "Wissen teilen, Feedback geben",
                "Abschließen von offenen Punkten"]
        avoid = ["Ständig neue Baustellen aufmachen"]
    elif "last quarter" in phase_name_lower:
        good = ["Bilanz ziehen, Analysen machen",
                "Entscheiden, was du loslassen willst",
                "Routinen optimieren"]
        avoid = ["Starres Festhalten an Dingen, die nicht mehr passen"]
    elif "waning crescent" in phase_name_lower:
        good = ["Regeneration, Schlaf, langsamer machen",
                "Meditation, Journaling",
                "Vorbereitung auf neuen Zyklus"]
        avoid = ["Dich für Ruhe/Erholung schuldig fühlen"]
    else:
        good = ["Balance halten, beobachten, wie sich Dinge entwickeln"]
        avoid = ["Zu hart zu dir selbst sein"]
    return good, avoid


# -------------------------------------------------
# Live-Hintergrund basierend auf Phase
# -------------------------------------------------
def background_gradient_for_phase(phase_name: str) -> str:
    n = phase_name.lower()
    if "new moon" in n:
        return "radial-gradient(circle at top, #020617, #020617, #000000)"
    if "full moon" in n:
        return "radial-gradient(circle at top, #facc15, #1f2937 45%, #020617 80%)"
    if "waxing" in n:
        return "linear-gradient(135deg,#020617,#0f172a,#1d4ed8)"
    if "waning" in n:
        return "linear-gradient(135deg,#020617,#0f172a,#7e22ce)"
    if "quarter" in n:
        return "linear-gradient(135deg,#020617,#0f172a,#22c55e)"
    return "linear-gradient(135deg,#020617,#111827,#020617)"


# -------------------------------------------------
# Echte Sichtbarkeitsdauer (API)
# -------------------------------------------------
def clamp_interval(start: dt.datetime, end: dt.datetime,
                   day_start: dt.datetime, day_end: dt.datetime):
    s = max(start, day_start)
    e = min(end, day_end)
    if s >= e:
        return None
    return s, e


def interval_hours(start: dt.datetime, end: dt.datetime) -> float:
    return (end - start).total_seconds() / 3600.0


def compute_real_visibility(date: dt.date,
                            sunrise: dt.datetime | None,
                            sunset: dt.datetime | None,
                            moonrise_time: dt.datetime | None,
                            moonset_time: dt.datetime | None,
                            tz: pytz.timezone):
    day_start = tz.localize(dt.datetime(date.year, date.month, date.day, 0, 0))
    day_end = day_start + dt.timedelta(days=1)

    # Mond-Intervalle über dem Horizont
    moon_intervals = []
    if moonrise_time and moonset_time:
        if moonrise_time < moonset_time:
            ci = clamp_interval(moonrise_time, moonset_time, day_start, day_end)
            if ci:
                moon_intervals.append(ci)
        else:
            # über Mitternacht
            ci1 = clamp_interval(moonrise_time, day_end, day_start, day_end)
            ci2 = clamp_interval(day_start, moonset_time, day_start, day_end)
            for ci in (ci1, ci2):
                if ci:
                    moon_intervals.append(ci)
    elif moonrise_time and not moonset_time:
        ci = clamp_interval(moonrise_time, day_end, day_start, day_end)
        if ci:
            moon_intervals.append(ci)
    elif moonset_time and not moonrise_time:
        ci = clamp_interval(day_start, moonset_time, day_start, day_end)
        if ci:
            moon_intervals.append(ci)

    if not moon_intervals:
        return None

    total_visible = sum(interval_hours(s, e) for s, e in moon_intervals)

    if sunrise and sunset:
        sun_interval = clamp_interval(sunrise, sunset, day_start, day_end)
    else:
        sun_interval = None

    day_visible = 0.0
    if sun_interval:
        sun_s, sun_e = sun_interval
        for ms, me in moon_intervals:
            si = clamp_interval(ms, me, sun_s, sun_e)
            if si:
                day_visible += interval_hours(*si)

    night_visible = max(0.0, total_visible - day_visible)

    return {
        "total": total_visible,
        "day": day_visible,
        "night": night_visible,
    }


# -------------------------------------------------
# 24h Timeline-Balken
# -------------------------------------------------
def build_timeline_segments(intervals, day_start: dt.datetime, day_end: dt.datetime):
    segments = []
    current = 0.0
    full_seconds = (day_end - day_start).total_seconds()
    for s, e in sorted(intervals, key=lambda x: x[0]):
        start_frac = (s - day_start).total_seconds() / full_seconds
        end_frac = (e - day_start).total_seconds() / full_seconds
        start_frac = max(0.0, min(1.0, start_frac))
        end_frac = max(0.0, min(1.0, end_frac))
        if end_frac <= start_frac:
            continue
        if start_frac > current:
            segments.append(("off", start_frac - current))
        segments.append(("on", end_frac - start_frac))
        current = end_frac
    if current < 1.0:
        segments.append(("off", 1.0 - current))
    return segments


def render_timeline_bar(label: str, intervals, day_start: dt.datetime,
                        day_end: dt.datetime, color_on: str, color_off: str):
    segments = build_timeline_segments(intervals, day_start, day_end)
    html_segments = ""
    for state, width in segments:
        w = width * 100.0
        bg = color_on if state == "on" else color_off
        html_segments += f'<div style="height:100%;width:{w:.1f}%;float:left;background:{bg};"></div>'
    return f"""
    <div style="margin-bottom:0.5rem;">
        <div style="font-size:0.85rem;margin-bottom:0.2rem;">{label}</div>
        <div style="height:14px;border-radius:999px;overflow:hidden;background:{color_off};">
            {html_segments}
        </div>
    </div>
    """


# -------------------------------------------------
# Streamlit Grund-Setup
# -------------------------------------------------
st.set_page_config(
    page_title="Moon Phase Dashboard",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    .big-card {
        padding: 1.5rem;
        border-radius: 1.5rem;
        background: linear-gradient(135deg,#050814,#151a30);
        border: 1px solid rgba(255,255,255,0.10);
    }
    .small-card {
        padding: 0.7rem;
        border-radius: 1rem;
        background: rgba(255,255,255,0.04);
        border: 1px solid rgba(255,255,255,0.06);
        text-align:center;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("🌙 Moon Phase Dashboard")


# -------------------------------------------------
# Sidebar: Standort & Datum
# -------------------------------------------------
loc_choice = st.sidebar.selectbox(
    "Standort auswählen",
    list(PRESET_LOCATIONS.keys()) + ["Manuell"],
)

if loc_choice == "Manuell":
    default_lat, default_lon, default_tz = PRESET_LOCATIONS["Villach"]
    lat = st.sidebar.number_input("Breitengrad (Lat)", value=float(default_lat))
    lon = st.sidebar.number_input("Längengrad (Lon)", value=float(default_lon))
    tz_name = st.sidebar.text_input("Zeitzone (IANA)", value=default_tz)
    city_name = st.sidebar.text_input("Stadtname", value="Custom")
    region_name = st.sidebar.text_input("Region", value="Earth")
    CITY = LocationInfo(
        name=city_name,
        region=region_name,
        timezone=tz_name,
        latitude=lat,
        longitude=lon,
    )
else:
    lat, lon, tz_name = PRESET_LOCATIONS[loc_choice]
    CITY = LocationInfo(
        name=loc_choice,
        region="",
        timezone=tz_name,
        latitude=lat,
        longitude=lon,
    )

today = dt.date.today()
date = st.sidebar.date_input("Datum auswählen", today)
st.sidebar.write(f"📍 Standort: **{CITY.name}**")
st.sidebar.write(f"🕒 Zeitzone: **{CITY.timezone}**")

# -------------------------------------------------
# Berechnungen für aktuellen Tag
# -------------------------------------------------
phase_today = phase(date)
phase_name, phase_icon = phase_name_and_icon(phase_today)
day_hours_ideal, night_hours_ideal = ideal_day_night_hours(phase_today)
illum = illumination_percent(phase_today)

tz = pytz.timezone(CITY.timezone)
sunrise, sunset = get_sun_times(CITY, date)
moonrise_time, moonset_time = get_moon_times(CITY, date)

# Live Background
bg_gradient = background_gradient_for_phase(phase_name)
st.markdown(
    f"""
    <style>
    [data-testid="stAppViewContainer"] {{
        background: {bg_gradient};
    }}
    </style>
    """,
    unsafe_allow_html=True,
)

# Tabs
tab_overview, tab_timeline, tab_calendar, tab_location = st.tabs(
    ["Übersicht", "24h Timeline", "Monatskalender", "Standort-Tools"]
)

# -------------------------------------------------
# TAB: Übersicht
# -------------------------------------------------
with tab_overview:
    col_main, col_side = st.columns([2.2, 1])

    with col_main:
        st.subheader(f"Heute – {date.isoformat()}")
        st.markdown(
            f"""
            <div class="big-card">
                <div style="display:flex;flex-direction:row;gap:1.5rem;align-items:center;justify-content:space-between;flex-wrap:wrap;">
                    <div style="flex:1;min-width:220px;text-align:center;">
                        <div style="font-size:4.2rem;">{phase_icon}</div>
                        <h2 style="margin-bottom:0.4rem;">{phase_name}</h2>
                        <p style="margin:0.2rem 0;color:#ddd;">
                            Phase value: {phase_today:.2f} / 29.53<br/>
                            Illumination: {illum:.1f} %
                        </p>
                    </div>
                    <div style="flex:1;min-width:260px;">
                        <h4 style="margin-bottom:0.5rem;">Day vs. Night (idealised visibility)</h4>
                        <p style="margin:0.2rem 0;">
                            Sichtbar am <b>Tag</b>: {day_hours_ideal:4.1f} h<br/>
                            Sichtbar in der <b>Nacht</b>: {night_hours_ideal:4.1f} h
                        </p>
                        <div style="margin-top:0.8rem;height:18px;border-radius:999px;
                                    background:rgba(255,255,255,0.06);overflow:hidden;">
                            <div style="height:100%;width:{day_hours_ideal/24*100:.1f}%;
                                        float:left;background:linear-gradient(90deg,#f6d365,#fda085);"></div>
                            <div style="height:100%;width:{night_hours_ideal/24*100:.1f}%;
                                        float:left;background:linear-gradient(90deg,#4b6cb7,#182848);"></div>
                        </div>
                        <p style="font-size:0.8rem;color:#aaa;margin-top:0.4rem;">
                            Modell: Neumond eher tags sichtbar, Vollmond überwiegend nachts, Halbmonde etwa halb/halb.
                        </p>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        real_vis = compute_real_visibility(
            date, sunrise, sunset, moonrise_time, moonset_time, tz
        )
        if real_vis:
            st.markdown(
                f"""
                <div style="margin-top:1rem;padding:0.9rem;border-radius:1rem;
                            background:rgba(15,23,42,0.85);border:1px solid rgba(148,163,184,0.4);">
                    <h4>Reale Sichtbarkeit (aus Auf- & Untergang berechnet)</h4>
                    <p style="margin:0.2rem 0;">
                        Gesamt sichtbar: <b>{real_vis['total']:.1f} h</b><br/>
                        Davon am <b>Tag</b>: {real_vis['day']:.1f} h<br/>
                        Davon in der <b>Nacht</b>: {real_vis['night']:.1f} h
                    </p>
                    <p style="font-size:0.8rem;color:#9ca3af;margin-top:0.4rem;">
                        Hinweis: Diese Werte basieren auf den tatsächlichen Mondauf- und -untergangszeiten
                        sowie Sonnenauf- und -untergang.
                    </p>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.info(
                "Für diesen Tag konnten keine sinnvollen realen Sichtbarkeitszeiten berechnet werden "
                "(z.B. Mond bleibt unter dem Horizont)."
            )

    with col_side:
        st.subheader("Auf- & Untergang")
        st.markdown(
            f"""
            <div class="small-card" style="margin-bottom:0.7rem;">
                <div style="font-size:1.3rem;margin-bottom:0.3rem;">☀️ Sonne</div>
                <div>Aufgang: <b>{fmt_time(sunrise)}</b></div>
                <div>Untergang: <b>{fmt_time(sunset)}</b></div>
            </div>
            <div class="small-card">
                <div style="font-size:1.3rem;margin-bottom:0.3rem;">🌙 Mond</div>
                <div>Aufgang: <b>{fmt_time(moonrise_time)}</b></div>
                <div>Untergang: <b>{fmt_time(moonset_time)}</b></div>
                <div style="font-size:0.75rem;color:#aaa;margin-top:0.3rem;">
                    Hinweis: An manchen Tagen kann der Mond in einem Kalenderdatum
                    nicht „klassisch“ auf- oder untergehen (dann steht hier „–“).
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("---")

    # Wochen-Strips
    def week_strip(title, center_date, direction="past"):
        st.subheader(title)
        cols = st.columns(7)
        for i in range(7):
            if direction == "past":
                d = center_date - dt.timedelta(days=7 - i)
            else:
                d = center_date + dt.timedelta(days=i + 1)
            p = phase(d)
            name, icon = phase_name_and_icon(p)
            with cols[i]:
                st.markdown(
                    f"""
                    <div class="small-card" style="margin-bottom:0.3rem;">
                        <div style="font-size:1.6rem;">{icon}</div>
                        <div style="font-size:0.75rem;">{d.strftime('%a %d')}</div>
                        <div style="font-size:0.7rem;color:#aaa;">{name}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

    week_strip("Letzte 7 Tage", date, direction="past")
    week_strip("Nächste 7 Tage", date, direction="future")

    st.markdown("---")
    st.subheader("Typische Aktivitäten für diese Mondphase")
    good, avoid = moon_activity_tips(phase_name)
    col_good, col_avoid = st.columns(2)
    with col_good:
        st.markdown("**Günstig / Unterstützend**")
        for g in good:
            st.markdown(f"- ✅ {g}")
    with col_avoid:
        st.markdown("**Eher vermeiden / Vorsicht**")
        for a in avoid:
            st.markdown(f"- ⚠️ {a}")
    st.markdown(
        """
        <p style="font-size:0.8rem;color:#888;margin-top:0.6rem;">
        Hinweis: Diese Hinweise sind inspiriert von traditionellen Mondkalendern.
        Sie ersetzen keine wissenschaftliche Empfehlung, sondern dienen als Inspiration.
        </p>
        """,
        unsafe_allow_html=True,
    )

# -------------------------------------------------
# TAB: 24h Timeline
# -------------------------------------------------
with tab_timeline:
    st.subheader("🌗 Sonne & Mond – 24h Timeline")

    day_start = tz.localize(dt.datetime(date.year, date.month, date.day, 0, 0))
    day_end = day_start + dt.timedelta(days=1)

    # Sonnen-Intervalle
    sun_intervals = []
    if sunrise and sunset:
        ci = clamp_interval(sunrise, sunset, day_start, day_end)
        if ci:
            sun_intervals.append(ci)

    # Mond-Intervalle (wie oben)
    moon_intervals = []
    if moonrise_time and moonset_time:
        if moonrise_time < moonset_time:
            ci = clamp_interval(moonrise_time, moonset_time, day_start, day_end)
            if ci:
                moon_intervals.append(ci)
        else:
            ci1 = clamp_interval(moonrise_time, day_end, day_start, day_end)
            ci2 = clamp_interval(day_start, moonset_time, day_start, day_end)
            for ci in (ci1, ci2):
                if ci:
                    moon_intervals.append(ci)
    elif moonrise_time and not moonset_time:
        ci = clamp_interval(moonrise_time, day_end, day_start, day_end)
        if ci:
            moon_intervals.append(ci)
    elif moonset_time and not moonrise_time:
        ci = clamp_interval(day_start, moonset_time, day_start, day_end)
        if ci:
            moon_intervals.append(ci)

    sun_bar = render_timeline_bar(
        "Sonne über Horizont",
        sun_intervals,
        day_start,
        day_end,
        color_on="linear-gradient(90deg,#facc15,#f97316)",
        color_off="rgba(15,23,42,0.7)",
    )
    moon_bar = render_timeline_bar(
        "Mond über Horizont",
        moon_intervals,
        day_start,
        day_end,
        color_on="linear-gradient(90deg,#4f46e5,#7c3aed)",
        color_off="rgba(15,23,42,0.7)",
    )

    st.markdown(
        f"""
        <div style="padding:1.2rem;border-radius:1.2rem;
                    background:rgba(15,23,42,0.9);border:1px solid rgba(148,163,184,0.5);">
            {sun_bar}
            {moon_bar}
            <div style="display:flex;justify-content:space-between;font-size:0.75rem;color:#9ca3af;margin-top:0.4rem;">
                <span>00:00</span>
                <span>06:00</span>
                <span>12:00</span>
                <span>18:00</span>
                <span>24:00</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if real_vis := compute_real_visibility(
        date, sunrise, sunset, moonrise_time, moonset_time, tz
    ):
        st.markdown(
            f"""
            **Reale Sichtbarkeit heute ({date}):**  
            • Gesamt: **{real_vis['total']:.1f} h**  
            • Davon am Tag: **{real_vis['day']:.1f} h**  
            • Davon in der Nacht: **{real_vis['night']:.1f} h**
            """
        )
    else:
        st.info(
            "Für diesen Tag konnten keine realen Sichtbarkeitszeiten berechnet werden."
        )

# -------------------------------------------------
# TAB: Monatskalender
# -------------------------------------------------
with tab_calendar:
    st.subheader("📆 Mondphasen im Monat")
    year = date.year
    month = date.month
    first_weekday, num_days = calendar.monthrange(year, month)

    st.markdown(f"**{calendar.month_name[month]} {year} – Standort: {CITY.name}**")
    week_days = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]
    cols = st.columns(7)
    for i, wd in enumerate(week_days):
        with cols[i]:
            st.markdown(f"**{wd}**")

    day_counter = 1
    row = 0
    while day_counter <= num_days:
        cols = st.columns(7)
        for col_idx in range(7):
            with cols[col_idx]:
                if row == 0 and col_idx < (first_weekday - 0) % 7:
                    st.markdown(" ")
                elif day_counter <= num_days:
                    d = dt.date(year, month, day_counter)
                    p = phase(d)
                    name, icon = phase_name_and_icon(p)
                    st.markdown(
                        f"""
                        <div class="small-card" style="padding:0.4rem 0.3rem;">
                            <div style="font-size:0.8rem;font-weight:600;">{day_counter}</div>
                            <div style="font-size:1.1rem;">{icon}</div>
                            <div style="font-size:0.6rem;color:#aaa;">{name}</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                    day_counter += 1
        row += 1

# -------------------------------------------------
# TAB: Standort-Tools
# -------------------------------------------------
with tab_location:
    st.subheader("📍 Standort & Karte")
    st.write(
        f"Aktueller Standort: **{CITY.name}**  "
        f"(Lat: {CITY.latitude:.4f}, Lon: {CITY.longitude:.4f}, TZ: {CITY.timezone})"
    )
    df = pd.DataFrame(
        {"lat": [CITY.latitude], "lon": [CITY.longitude]}
    )
    st.map(df, zoom=8)
    st.markdown(
        """
        Du kannst im Sidebar oben einen anderen Ort auswählen oder auf
        **Manuell** gehen und eigene Koordinaten & Zeitzone eintragen.
        Alle Berechnungen (Sonnenauf/untergang, Mondauf/untergang, Sichtbarkeit)
        passen sich dann automatisch an.
        """
    )
