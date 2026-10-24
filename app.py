"""Campus Find: public read-only search and an authenticated staff inventory."""
from html import escape
import streamlit as st
from sqlalchemy.exc import SQLAlchemyError
from lostfound.config import ROOT, load_settings
from lostfound.database import connect_database, initialize, list_items, get_photo
from lostfound.matching import search
from lostfound.locations import PLACE_OPTIONS, PLACES, UNSPECIFIED
from lostfound.staff_ui import render_staff

st.set_page_config(page_title="Campus Find", page_icon="🌿", layout="centered")
st.html("<style>" + (ROOT / "assets/style.css").read_text(encoding="utf-8") + "</style>")

@st.cache_resource(show_spinner=False)
def get_database(url):
    engine = connect_database(url)
    initialize(engine)
    return engine

def item_card(item, rank=None, evidence=None):
    label = f"Possible match {rank}" if rank else item.type
    quotes = ""
    if evidence:
        quotes = '<div class="evidence"><span>Evidence from this record</span>' + "".join(
            "<blockquote>" + escape(quote) + "</blockquote>" for quote in evidence) + "</div>"
    st.html(
        f'<article class="item-card"><div class="item-meta"><span>{escape(label)}</span>'
        f'<span class="item-id">{escape(item.id)}</span></div>'
        f'<h3>{escape(item.colour.title() + " " + item.type.lower())}</h3>'
        f'<p>{escape(item.description)}</p><p><small>Found at: '
        f'<abbr title="{escape(PLACES.get(item.place, item.place), quote=True)}">{escape(item.place)}</abbr>'
        f'</small></p>{quotes}</article>')
    photo = get_photo(engine, item.id)
    if photo:
        st.image(photo, caption="Item photo · " + item.id, width=320)

st.html('<header class="app-header"><span class="wordmark">Campus Find<span class="brand-dot">.</span></span>'
        '<span class="project-label">AILT9019 · Group 19</span></header>')
try:
    settings = load_settings()
    engine = get_database(settings.database_url)
    catalogue = list_items(engine)
except (SQLAlchemyError, ValueError, OSError):
    st.error("The catalogue is unavailable. Please try again later.")
    st.stop()

st.html('<h1>Find a lost item</h1><p class="intro">Describe the item and, if known, where it was found.</p>')
search_tab, browse_tab, staff_tab = st.tabs(["Search", "Catalogue", "Staff"], key="main_tabs", on_change="rerun")
place_choices = ["All places"] + PLACE_OPTIONS + ([UNSPECIFIED] if any(r.place == UNSPECIFIED for r in catalogue) else [])

with search_tab:
    st.caption("Search available items. Leave out names, contact details and ID numbers.")
    mode_label = st.radio("Search method", ["Keyword search", "AI matching"], horizontal=True)
    mode = "ai" if mode_label == "AI matching" else "keyword"
    if mode == "ai":
        if settings.ai_ready:
            st.caption(f"{settings.provider} · {settings.model}. Your description and catalogue text are sent to this provider.")
        else:
            st.info("AI matching is not configured. Use Keyword search until the team's API key is added.")
    else:
        st.caption("Matches shared words, including place names. Synonyms and conflicting details may be missed.")
    with st.form("search_form", border=False):
        query = st.text_area("Describe the item", max_chars=300, height=96,
                             placeholder="e.g. black insulated bottle with a silver lid")
        left, right = st.columns(2)
        with left:
            category = st.selectbox("Category (optional)", ["All items"] + sorted({r.type for r in catalogue}))
        with right:
            place = st.selectbox("Found at (optional)", place_choices)
        submitted = st.form_submit_button("Search items", type="primary", width="stretch")
    if submitted:
        # Read the database again at submission; collected records cannot enter a new search.
        selected = list_items(engine, category, place)
        with st.spinner("Searching…"):
            result = search(query, selected, mode, settings)
        st.session_state["result"] = result
        st.session_state["result_mode"] = mode
        st.session_state["result_query"] = query
    result = st.session_state.get("result")
    if result and st.session_state.get("result_mode") == mode:
        st.divider()
        st.subheader("Search results")
        st.caption("AI matching · source-checked evidence" if mode == "ai" else "Keyword search · not AI")
        if result.status == "matches":
            by_id = {r.id:r for r in list_items(engine)}
            remaining = [m for m in result.matches if m.id in by_id]
            if remaining:
                st.write("Review the descriptions. Staff will verify ownership before collection.")
                for index, match in enumerate(remaining, 1):
                    item_card(by_id[match.id], index, match.evidence if mode == "ai" else None)
            else:
                st.info("These items are no longer available. Search again for current records.")
        elif result.status in {"error","invalid"}:
            st.error(result.message)
        elif result.status == "refused":
            st.warning(result.message)
        else:
            st.info(result.message)

with browse_tab:
    st.subheader("Available items")
    browse_category = st.selectbox("Browse by category", ["All items"] + sorted({r.type for r in catalogue}))
    browse_place = st.selectbox("Browse by place", place_choices)
    visible = list_items(engine, browse_category, browse_place)
    st.caption(f"{len(visible)} items awaiting collection")
    if visible:
        pages = max(1, (len(visible)+11)//12)
        page = st.number_input("Page", min_value=1, max_value=pages, value=1, step=1)
        for item in visible[(page-1)*12:page*12]:
            item_card(item)
    else:
        st.info("No items at this location or in this category.")
    if st.button("Refresh catalogue"):
        st.rerun()

with staff_tab:
    try:
        render_staff(engine, item_card)
    except SQLAlchemyError:
        st.error("The staff database is unavailable. Please try again later.")

st.html('<footer class="app-footer">Student search · Staff-managed records · In-person collection</footer>')
