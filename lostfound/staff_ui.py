"""Staff-only Streamlit controls; every mutation also checks the database session."""
import os
import uuid
from datetime import datetime, timezone
import streamlit as st
from sqlalchemy.exc import SQLAlchemyError
from pydantic import ValidationError
from .auth import (authenticate, authenticate_microsoft, logout, staff_account,
                   microsoft_configured)
from .database import (add_item, collect_item, list_items, list_audit, inventory_writes_allowed)
from .locations import PLACE_OPTIONS, PLACES

CATEGORIES = ["Bottle", "Umbrella", "Wallet", "Keys", "Bag", "Clothing",
              "Electronics", "Notebook", "Phone case", "Stationery", "Other"]

def render_staff(engine, item_card):
    st.subheader("Staff workspace")
    token = st.session_state.get("staff_token")
    account = staff_account(engine, token)
    if not account:
        st.caption("Authorised lost-and-found centre staff only. Students can use Search and Catalogue.")
        if microsoft_configured():
            if st.user.is_logged_in:
                if st.button("Continue with Microsoft identity"):
                    verified = authenticate_microsoft(engine, st.user.to_dict(), os.environ["MS_TENANT_ID"])
                    if verified:
                        st.session_state["staff_token"] = verified
                        st.session_state["staff_oidc"] = True
                        st.rerun()
                    st.error("This Microsoft account is not registered as staff, or its sign-in has expired.")
                if st.button("Sign out of Microsoft"):
                    st.logout()
            elif st.button("Sign in with Microsoft"):
                st.login("microsoft")
        else:
            st.caption("HKU/Microsoft sign-in awaits university application registration.")
        with st.form("staff_login", clear_on_submit=True):
            email = st.text_input("Staff email", max_chars=254)
            password = st.text_input("App password", type="password", max_chars=128,
                                     help="Use the separate Campus Find password, never your HKU Portal password.")
            clicked = st.form_submit_button("Sign in")
        if clicked:
            verified = authenticate(engine, email, password)
            if verified and staff_account(engine, verified):
                st.session_state["staff_token"] = verified
                st.session_state["staff_oidc"] = False
                st.rerun()
            if verified:
                logout(engine, verified)
            st.error("Sign-in unsuccessful. Check your staff credentials or try again after 15 minutes.")
        return
    st.caption("Signed in as " + account["email"])
    if st.button("Sign out", key="staff_logout"):
        logout(engine, token)
        st.session_state.pop("staff_token", None)
        if st.session_state.pop("staff_oidc", False):
            st.logout()
        st.rerun()
    if not inventory_writes_allowed(engine):
        st.warning("Staff recording is disabled until persistent PostgreSQL is connected.")
        return
    if notice := st.session_state.pop("staff_notice", None):
        st.success(notice)
    add_tab, collect_tab, history_tab = st.tabs(["Record an item", "Confirm collection", "Activity"], key="staff_tabs", on_change="rerun")
    with add_tab:
        st.caption("Describe the item only. Do not include names, ID numbers or contact details. Crop these out of photos.")
        form_id = st.session_state.setdefault("record_form_id", uuid.uuid4().hex)
        with st.form("record_" + form_id):
            kind = st.selectbox("Item category", CATEGORIES)
            colour = st.text_input("Colour", max_chars=60)
            place = st.selectbox("Found at", PLACE_OPTIONS, index=None, placeholder="Select a place")
            description = st.text_area("Item description", max_chars=600,
                                       placeholder="Colour, material, distinctive marks and specific found location.")
            image = st.file_uploader("Photo (optional)", type=["jpg","jpeg","png","webp"],
                                     help="Up to 5 MB. Photos are compressed and location metadata is removed.")
            submitted = st.form_submit_button("Save item", type="primary")
        if submitted:
            try:
                new_item = add_item(engine, token, item_type=kind, colour=colour,
                    description=description, place=place,
                    photo=image.getvalue() if image else None, item_id="LF-" + form_id[:12])
                st.session_state["record_form_id"] = uuid.uuid4().hex
                st.session_state["staff_notice"] = f"Saved {new_item.id}. It is now available in student search."
                st.rerun()
            except (ValueError, ValidationError):
                st.error("Check the category, colour, place, description (10–600 characters) and photo (JPEG/PNG/WebP, up to 5 MB).")
            except PermissionError as exc:
                st.error(str(exc))
            except SQLAlchemyError:
                st.error("The item could not be saved. Refresh the catalogue before retrying.")
    with collect_tab:
        active = list_items(engine)
        by_id = {r.id:r for r in active}
        item_id = st.selectbox("Item to collect", list(by_id), index=None,
            format_func=lambda key: f"{key} · {by_id[key].colour} {by_id[key].type} · {by_id[key].place}",
            placeholder="Select the item handed over")
        if item_id:
            item_card(by_id[item_id])
            with st.form("collect_" + item_id):
                confirmed = st.checkbox("I have verified the collection in person and handed over this item.")
                remove = st.form_submit_button("Confirm collection and remove item", type="primary")
            if remove:
                if not confirmed:
                    st.error("Confirm the handover before removing this item.")
                else:
                    try:
                        collect_item(engine, token, item_id)
                        st.session_state.pop("result", None)
                        st.session_state["staff_notice"] = f"{item_id} collected. The record and photo were removed."
                        st.rerun()
                    except (ValueError, PermissionError) as exc:
                        st.error(str(exc))
                    except SQLAlchemyError:
                        st.error("Collection could not be saved. Refresh and check the item before retrying.")
        elif not active:
            st.info("No items are awaiting collection.")
    with history_tab:
        st.caption("Latest 100 actions. Collected descriptions and photos are deleted; item IDs and action times remain.")
        rows = list_audit(engine, token)
        st.dataframe([{"Item":r["item_id"],"Action":r["action"],
            "Time (UTC)":datetime.fromtimestamp(r["timestamp"], timezone.utc).strftime("%Y-%m-%d %H:%M")}
            for r in rows], hide_index=True, width="stretch")
