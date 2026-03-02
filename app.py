import re
import pandas as pd
import streamlit as st

# =========================
# CONFIG
# =========================
st.set_page_config(page_title="Recruiting Board", layout="wide")

SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQYiTwd8DBw8G1UpSDMuGt0BRaan84cR5CdDDG06v0ljMgPQCK5oS_s8z9QlXFmQ4apM7jL9PhqSm4e/pub?gid=0&single=true&output=csv"  # <-- IMPORTANTISSIMO

# Colonne minime attese (aggiungine se vuoi)
REQUIRED_COLS = [
    "athlete_id", "first_name", "last_name", "name",
    "status", "public", "is_featured", "featured_rank",
    "sport", "gender", "grad_year", "country", "height_cm", "gpa",
    "photo", "photo_url", "highlight_video_url", "bio_short",
    "placed_school", "placed_division", "placed_year",
    "tennis_utr", "volley_position", "basket_position",
    "swim_primary_events", "swim_best_time_1",
]

SPORTS = ["Tennis", "Volleyball", "Basketball", "Swimming"]
STATUSES = ["available", "placed", "hidden"]


def _to_bool(x):
    if pd.isna(x):
        return False
    if isinstance(x, bool):
        return x
    s = str(x).strip().lower()
    return s in ("true", "1", "yes", "y")


def _to_int(x):
    try:
        if pd.isna(x) or x == "":
            return None
        return int(float(x))
    except Exception:
        return None


def _to_float(x):
    try:
        if pd.isna(x) or x == "":
            return None
        return float(x)
    except Exception:
        return None


def _safe_str(x):
    if pd.isna(x):
        return ""
    return str(x).strip()


@st.cache_data(ttl=300)
def load_data(csv_url: str) -> pd.DataFrame:
    df = pd.read_csv(csv_url)
def normalize_url(u: str) -> str:
    u = _safe_str(u)
    if not u:
        return ""
    if u.startswith("www."):
        return "https://" + u
    return u

df["highlight_video_url"] = df["highlight_video_url"].apply(normalize_url)
df["photo_url"] = df["photo_url"].apply(normalize_url)
df["photo"] = df["photo"].apply(normalize_url)
    # Normalizza nomi colonne (evita spazi)
    df.columns = [c.strip() for c in df.columns]

    # Se mancano colonne, creale vuote (così non crasha)
    for c in REQUIRED_COLS:
        if c not in df.columns:
            df[c] = ""

    # Normalizzazioni tipi
    df["public"] = df["public"].apply(_to_bool)
    df["is_featured"] = df["is_featured"].apply(_to_bool)
    df["featured_rank"] = df["featured_rank"].apply(_to_int)
    df["grad_year"] = df["grad_year"].apply(_to_int)
    df["placed_year"] = df["placed_year"].apply(_to_int)
    df["height_cm"] = df["height_cm"].apply(_to_int)
    df["gpa"] = df["gpa"].apply(_to_float)
    df["tennis_utr"] = df["tennis_utr"].apply(_to_float)

    # Normalizza status/sport (ma non forziamo, così vedi errori)
    df["status"] = df["status"].astype(str).str.strip().str.lower()
    df["sport"] = df["sport"].astype(str).str.strip()

    # Name fallback
    df["name"] = df["name"].apply(_safe_str)
    missing_name = df["name"].eq("")
    df.loc[missing_name, "name"] = (
        df.loc[missing_name, "first_name"].astype(str).str.strip()
        + " "
        + df.loc[missing_name, "last_name"].astype(str).str.strip()
    ).str.strip()

    return df


def card_meta(row) -> str:
    parts = []
    if row.get("grad_year"):
        parts.append(f"Class of {row['grad_year']}")
    if row.get("gpa") is not None:
        parts.append(f"GPA {row['gpa']:.1f}")
    if row.get("country"):
        parts.append(str(row["country"]))
    return " • ".join(parts)


def athlete_image(row) -> str:
    # Preferisci photo_url se lo usi come link diretto
    url = _safe_str(row.get("photo_url"))
    if url:
        return url
    # Se usi "photo" come URL (può essere vuoto)
    url2 = _safe_str(row.get("photo"))
    return url2


def sport_specific_line(row) -> str:
    sport = _safe_str(row.get("sport"))
    if sport == "Tennis":
        utr = row.get("tennis_utr")
        if utr is not None:
            return f"UTR: {utr:.1f}"
    if sport == "Volleyball":
        pos = _safe_str(row.get("volley_position"))
        if pos:
            return f"Position: {pos}"
    if sport == "Basketball":
        pos = _safe_str(row.get("basket_position"))
        if pos:
            return f"Position: {pos}"
    if sport == "Swimming":
        ev = _safe_str(row.get("swim_primary_events"))
        t1 = _safe_str(row.get("swim_best_time_1"))
        if ev and t1:
            return f"{ev} | {t1}"
        if ev:
            return ev
    return ""


def filter_df(df: pd.DataFrame, status: str):
    d = df.copy()
    d = d[d["public"] == True]
    d = d[d["status"] == status]
    return d


# =========================
# APP
# =========================
st.title("Recruiting Board")

if "selected_id" not in st.session_state:
    st.session_state.selected_id = None

# Load
try:
    df = load_data(SHEET_CSV_URL)
except Exception as e:
    st.error("Non riesco a leggere il Google Sheet come CSV pubblico.")
    st.write("Controlla che l’URL CSV sia pubblico e apra direttamente un CSV anche in incognito.")
    st.code(str(e))
    st.stop()

# Sidebar filters (per Available/Placed)
with st.sidebar:
    st.header("Filters")
    view = st.radio("Section", ["Home", "Available Prospects", "Placed Athletes"], index=0)
    
    if st.session_state.get("selected_id"):
    if st.button("← Back to results", key="back_sidebar"):
        st.session_state.selected_id = None
        st.rerun()
    
    sport_filter = st.multiselect("Sport", SPORTS, default=[])
    # Calcola range reale dai dati
    gy_min_data = int(df["grad_year"].dropna().min()) if df["grad_year"].notna().any() else 2024
    gy_max_data = int(df["grad_year"].dropna().max()) if df["grad_year"].notna().any() else 2032

    grad_year_min, grad_year_max = st.slider(
        "Grad Year range",
        min_value=gy_min_data,
        max_value=gy_max_data,
        value=(gy_min_data, gy_max_data),
    )
    gpa_min = st.slider("Min GPA", min_value=0.0, max_value=4.0, value=0.0, step=0.1)
    search = st.text_input("Search name", "")

def apply_common_filters(d: pd.DataFrame) -> pd.DataFrame:
    out = d.copy()
    if sport_filter:
        out = out[out["sport"].isin(sport_filter)]
    # Grad year
    out = out[(out["grad_year"].fillna(0) >= grad_year_min) & (out["grad_year"].fillna(9999) <= grad_year_max)]
    # GPA
    out = out[out["gpa"].fillna(0) >= gpa_min]
    # Search
    if search.strip():
        s = search.strip().lower()
        out = out[out["name"].str.lower().str.contains(re.escape(s), na=False)]
    return out


def render_grid(d: pd.DataFrame, cols: int = 4):
    if d.empty:
        st.info("No results.")
        return

    rows = list(d.to_dict(orient="records"))
    for i in range(0, len(rows), cols):
        chunk = rows[i:i+cols]
        columns = st.columns(cols)
        for j, row in enumerate(chunk):
            with columns[j]:
                img = athlete_image(row)
                if img:
                    st.image(img, use_container_width=True)
                st.subheader(_safe_str(row.get("name")))
                st.caption(_safe_str(row.get("sport")))
                ss = sport_specific_line(row)
                if ss:
                    st.write(ss)
                meta = card_meta(row)
                if meta:
                    st.caption(meta)

                if st.button("View profile", key=f"view_{row['athlete_id']}"):
                    st.session_state.selected_id = row["athlete_id"]
                    st.rerun()


def render_profile(df_all: pd.DataFrame, athlete_id: str):
    if st.button("← Back", key="back_top"):
    st.session_state.selected_id = None
    st.rerun()
    row = df_all[df_all["athlete_id"] == athlete_id]
    if row.empty:
        st.error("Athlete not found.")
        return
    r = row.iloc[0].to_dict()

    st.markdown("---")
    st.header(_safe_str(r.get("name")))

    c1, c2 = st.columns([1, 2])
    with c1:
        img = athlete_image(r)
        if img:
            st.image(img, use_container_width=True)
        st.write(f"**Sport:** {_safe_str(r.get('sport'))}")
        if r.get("grad_year"):
            st.write(f"**Grad year:** {int(r['grad_year'])}")
        if _safe_str(r.get("country")):
            st.write(f"**Country:** {_safe_str(r.get('country'))}")
        if r.get("height_cm"):
            st.write(f"**Height:** {int(r['height_cm'])} cm")
        if r.get("gpa") is not None:
            st.write(f"**GPA:** {float(r['gpa']):.1f}")

    with c2:
        bio = _safe_str(r.get("bio_short"))
        if bio:
            st.write(bio)

        ss = sport_specific_line(r)
        if ss:
            st.info(ss)

        video = _safe_str(r.get("highlight_video_url"))
        if video:
            st.subheader("Highlight video")
            st.video(video)

        st.subheader("Request full profile")
        st.write("Opzione senza credenziali: usa un Google Form o una mail precompilata.")
        # Mailto semplice (sostituisci la tua email)
        to_email = "YOUR_EMAIL@example.com"
        subject = f"Recruiting Request - {r.get('name')}"
        body = f"Hi,\n\nI would like the full profile for {r.get('name')} ({r.get('sport')}).\n\nCollege:\nNeeds:\n\nThanks,\n"
        mailto = f"mailto:{to_email}?subject={pd.io.common.urlencode(subject)}"
        st.markdown(f"- Email: {to_email}")
        # Bottone link (Streamlit non ha un vero button mailto, usiamo link)
        st.link_button("Request via email", f"mailto:{to_email}?subject={subject}&body={body}")

    if st.button("Back"):
        st.session_state.selected_id = None
        st.rerun()


# =========================
# VIEW LOGIC
# =========================
# Se è selezionato un profilo, mostralo sopra a qualsiasi vista
if st.session_state.selected_id:
    render_profile(df, st.session_state.selected_id)
    st.stop()

if view == "Home":
    # Featured
    st.subheader("Featured Prospects")
    featured = filter_df(df, "available")
    featured = featured[featured["is_featured"] == True].copy()
    featured["featured_rank"] = featured["featured_rank"].fillna(999999)
    featured = featured.sort_values(["featured_rank", "grad_year", "name"], ascending=[True, True, True])
    render_grid(featured, cols=4)

    st.markdown("---")
    st.subheader("Recently Placed Athletes")
    placed = filter_df(df, "placed").copy()
    placed = placed.sort_values(["placed_year", "name"], ascending=[False, True]).head(12)

    # placed as compact list
    for _, r in placed.iterrows():
        left, right = st.columns([1, 4])
        with left:
            img = athlete_image(r.to_dict())
            if img:
                st.image(img, use_container_width=True)
        with right:
            st.write(f"**{r['name']}** — {r['sport']}")
            school = _safe_str(r.get("placed_school"))
            div = _safe_str(r.get("placed_division"))
            yr = r.get("placed_year")
            line = " | ".join([x for x in [school, div, str(int(yr)) if pd.notna(yr) else ""] if x])
            if line:
                st.caption(line)

elif view == "Available Prospects":
    st.subheader("Available Prospects")
    av = filter_df(df, "available")
    av = apply_common_filters(av)
    # ordina featured prima, poi grad_year
    av["featured_rank"] = av["featured_rank"].fillna(999999)
    av = av.sort_values(["featured_rank", "grad_year", "name"], ascending=[True, True, True])
    render_grid(av, cols=4)

else:
    st.subheader("Placed Athletes")
    pl = filter_df(df, "placed")
    pl = apply_common_filters(pl)
    pl = pl.sort_values(["placed_year", "name"], ascending=[False, True])
    render_grid(pl, cols=4)
