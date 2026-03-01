"""ZotMacros MVP — MyFitnessPal for UCI Dining. Uses AnteaterAPI only (no scraping)."""

import streamlit as st
from datetime import date

from anteater_api import get_restaurants, get_restaurant_today, get_dishes_batch
from models import Dish, parse_dish
from recommend import recommend

RESTAURANT_IDS = ["anteatery", "brandywine"]
RESTAURANT_LABELS = {"anteatery": "Anteatery", "brandywine": "Brandywine"}


def _inject_css():
    st.markdown("""
    <style>
    /* Ensure all text is readable (no white on white) */
    .stApp, .block-container, [data-testid="stAppViewContainer"] { color: #1e293b !important; }
    p, span, label, div[data-testid="stMarkdown"] { color: #1e293b !important; }
    .stMarkdown { color: #1e293b !important; }
    .stMarkdown p { color: #1e293b !important; }
    .stCaption { color: #475569 !important; }
    input, select, textarea { color: #1e293b !important; }
    /* Base */
    .stApp { background: linear-gradient(180deg, #f8fafc 0%, #f1f5f9 100%); color: #1e293b !important; }
    .block-container { padding-top: 1.25rem; max-width: 900px; color: #1e293b !important; }
    h1 { font-weight: 700 !important; letter-spacing: -0.02em; color: #0f172a !important; margin-bottom: 0.25rem !important; }
    h2, h3 { font-weight: 600 !important; color: #1e293b !important; margin-top: 1rem !important; }
    /* Metrics row */
    [data-testid="stMetric"] { background: white; padding: 0.75rem 1rem; border-radius: 10px; box-shadow: 0 1px 2px rgba(0,0,0,.05); border: 1px solid #e2e8f0; color: #1e293b !important; }
    [data-testid="stMetric"] label { color: #475569 !important; font-size: 0.85rem !important; }
    [data-testid="stMetric"] [data-testid="stMetricValue"] { color: #0f172a !important; font-weight: 600 !important; }
    [data-testid="stMetric"] [data-testid="stMetricDelta"] { color: #475569 !important; }
    /* Inputs - ensure text is dark */
    .stSelectbox > div, .stNumberInput > div { border-radius: 8px; color: #1e293b !important; }
    .stSelectbox label, .stNumberInput label { color: #1e293b !important; }
    /* Buttons */
    .stButton > button { border-radius: 8px; font-weight: 500; transition: box-shadow .15s ease; color: #1e293b; }
    .stButton > button:hover { box-shadow: 0 2px 8px rgba(0,0,0,.1); }
    /* Dividers */
    hr { margin: 1rem 0 !important; border-color: #e2e8f0 !important; }
    /* Info / warning boxes */
    [data-testid="stAlert"] { color: #1e293b !important; }
    [data-testid="stAlert"] p { color: #1e293b !important; }
    /* Debug expander */
    [data-testid="stExpander"] details summary { color: #475569; font-size: 0.85rem; }
    </style>
    """, unsafe_allow_html=True)


def _today_iso() -> str:
    return date.today().isoformat()


@st.cache_data(ttl=600)
def cached_restaurants(restaurant_id: str | None) -> list[dict]:
    return get_restaurants(restaurant_id)


@st.cache_data(ttl=300)
def cached_restaurant_today(restaurant_id: str, day_iso: str) -> dict:
    return get_restaurant_today(restaurant_id, day_iso)


def _station_name_map(restaurant_id: str) -> dict[str, str]:
    """Map station id -> display name from /restaurants."""
    raw = cached_restaurants(restaurant_id)
    name_map = {}
    items = raw if isinstance(raw, list) else ([raw] if isinstance(raw, dict) else [])
    for r in items:
        if not isinstance(r, dict):
            continue
        for s in r.get("stations") or []:
            if not isinstance(s, dict):
                continue
            sid = s.get("id") or s.get("stationId")
            if sid:
                name_map[str(sid)] = s.get("name") or s.get("stationName") or str(sid)
    return name_map


def _ensure_log():
    if "log" not in st.session_state:
        st.session_state.log = []
    if "recommend_results" not in st.session_state:
        st.session_state.recommend_results = None


def main():
    st.set_page_config(page_title="ZotMacros MVP", layout="wide")
    _inject_css()
    _ensure_log()

    st.title("ZotMacros MVP")
    st.caption("Track calories & protein for UCI Dining — Anteatery & Brandywine")

    # Restaurant & date
    restaurant_id = st.selectbox(
        "Restaurant",
        options=RESTAURANT_IDS,
        format_func=lambda x: RESTAURANT_LABELS.get(x, x),
    )
    day = st.date_input("Date", value=date.today())
    day_iso = day.isoformat()

    # Goals
    col_goal1, col_goal2 = st.columns(2)
    with col_goal1:
        cal_goal = st.number_input("Calories goal", min_value=0, value=2000, step=50)
    with col_goal2:
        protein_goal = st.number_input("Protein goal (g)", min_value=0, value=150, step=5)

    # Logged totals and remaining
    log: list[Dish] = st.session_state.log
    logged_cal = sum(d.calories for d in log)
    logged_protein = sum(d.protein_g for d in log)
    cal_remaining = max(0, cal_goal - logged_cal)
    protein_remaining = max(0, protein_goal - logged_protein)

    st.divider()
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Logged calories", f"{logged_cal:.0f}", f"goal {cal_goal}")
    m2.metric("Logged protein (g)", f"{logged_protein:.0f}", f"goal {protein_goal}")
    m3.metric("Remaining calories", f"{cal_remaining:.0f}", "")
    m4.metric("Remaining protein (g)", f"{protein_remaining:.0f}", "")

    # Fetch menu data
    try:
        today_data = cached_restaurant_today(restaurant_id, day_iso)
    except Exception as e:
        st.error(f"Could not load menu: {e}")
        st.stop()

    # Debug: inspect API structure if needed
    with st.expander("Debug: API response", expanded=False):
        st.write(today_data)

    periods = today_data.get("periods") or {}

    if not periods:
        st.warning("No meal periods available for this date.")
        _render_planner(log)
        _render_recommend(
            [], cal_remaining, protein_remaining, station_name_map={}
        )
        return

    st.subheader("Browse menu")
    # Convert dict into list of (key, value)
    period_items = [(k, v) for k, v in periods.items() if isinstance(v, dict)]

    period_key = st.selectbox(
        "Meal Period",
        options=[k for k, _ in period_items],
        format_func=lambda k: (periods.get(k) or {}).get("name", k),
    )

    period_obj = periods.get(period_key) or {}
    station_to_dishes = period_obj.get("stationToDishes") or {}
    station_name_map = _station_name_map(restaurant_id)

    if not station_to_dishes:
        st.info("No stations available for this period.")
        _render_planner(log)
        _render_recommend(
            [], cal_remaining, protein_remaining, station_name_map=station_name_map
        )
        return

    station_ids = list(station_to_dishes.keys())

    station_choice = st.selectbox(
        "Station",
        options=station_ids,
        format_func=lambda sid: station_name_map.get(sid, sid),
    )

    dish_ids = station_to_dishes.get(station_choice, [])
    dish_ids = [str(x) for x in dish_ids]  # ensure strings

    raw_dishes = get_dishes_batch(dish_ids)
    dishes = [parse_dish(d) for d in raw_dishes]
    station_name = station_name_map.get(station_choice, station_choice)

    st.subheader("Dishes")
    st.caption(f"Select items to add to your log from **{station_name}**.")
    for d in dishes:
        with st.container():
            img_col, text_col, btn_col = st.columns([1, 3, 1])
            with img_col:
                if d.image_url:
                    st.image(d.image_url, width=80, use_container_width=True)
                else:
                    st.caption("No image")
            with text_col:
                st.markdown(f"**{d.name}**")
                st.caption(f"{d.calories:.0f} cal  ·  {d.protein_g:.0f} g protein")
            with btn_col:
                if st.button("Add", key=f"add_{d.id}_{station_choice}", type="primary"):
                    add_dish = Dish(
                        id=d.id,
                        station_id=d.station_id,
                        name=d.name,
                        calories=d.calories,
                        protein_g=d.protein_g,
                        station_name=station_name,
                        image_url=d.image_url,
                    )
                    st.session_state.log.append(add_dish)
                    st.rerun()

    _render_planner(log)
    all_period_dish_ids = []
    for ids in station_to_dishes.values():
        all_period_dish_ids.extend(ids or [])
    all_period_dish_ids = [str(x) for x in list(dict.fromkeys(all_period_dish_ids))]
    _render_recommend(
        all_period_dish_ids,
        cal_remaining,
        protein_remaining,
        station_name_map=station_name_map,
    )


def _render_planner(log: list[Dish]):
    st.divider()
    st.subheader("Your log")
    if not log:
        st.info("No items logged yet. Pick a meal period and station above, then click **Add** on any dish.")
        return
    for i, d in enumerate(log):
        with st.container():
            img_col, r1, r2 = st.columns([1, 3, 1])
            with img_col:
                if d.image_url:
                    st.image(d.image_url, width=64, use_container_width=True)
                else:
                    st.caption("—")
            with r1:
                st.markdown(f"**{d.name}**" + (f" — *{d.station_name}*" if d.station_name else ""))
                st.caption(f"{d.calories:.0f} cal  ·  {d.protein_g:.0f} g protein")
            with r2:
                if st.button("Remove", key=f"rm_{i}"):
                    log.pop(i)
                    st.rerun()
    if st.button("Clear log"):
        st.session_state.log = []
        st.rerun()


def _render_recommend(
    all_dish_ids: list[str],
    cal_remaining: float,
    protein_remaining: float,
    station_name_map: dict[str, str],
):
    st.divider()
    st.subheader("Recommend combos")
    if not all_dish_ids or cal_remaining <= 0:
        st.caption("Set your goals and pick a meal period with dishes, then click **Recommend** to see combos that fit your remaining calories and maximize protein.")
        return
    if st.button("Recommend", type="primary"):
        raw = get_dishes_batch(all_dish_ids)
        dishes = [parse_dish(d) for d in raw]
        combos = recommend(
            dishes,
            cal_left=cal_remaining,
            protein_left=protein_remaining,
            max_items=3,
            top_k=5,
            cal_wiggle=50,
        )
        st.session_state.recommend_results = combos if combos else []
        st.rerun()
    results = st.session_state.recommend_results
    if results:
        st.caption("Top combos that fit your remaining calories and prioritize protein:")
        for combo_list, total_cal, total_protein in results:
            names = ", ".join(d.name for d in combo_list)
            st.markdown(f"**{total_cal:.0f} cal**, **{total_protein:.0f} g protein** — {names}")


if __name__ == "__main__":
    main()
