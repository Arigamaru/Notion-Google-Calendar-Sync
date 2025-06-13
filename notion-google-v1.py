import os
import uuid
import json
import pickle
import time
import datetime
import streamlit as st
from notion_client import Client as NotionClient
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request

SETTINGS_PATH = "sync_settings.json"
st.set_page_config(page_title="Bidirectional Notion-to-Google Calendar Sync")
st.title("🗓️ Bidirectional Notion-to-Google Calendar Sync")
SETTINGS_PATH = "sync_settings.json"

# Load previous settings
if os.path.exists(SETTINGS_PATH):
    with open(SETTINGS_PATH) as f:
        saved_settings = json.load(f)
else:
    saved_settings = {}

if "log_messages" not in st.session_state:
    st.session_state.log_messages = []

CACHE_PATH = "sync_cache.json"
GOOGLE_CALENDAR_ID = "primary"

def extract_shared_id_from_google(ev):
    desc = ev.get("description", "") or ""
    for token in desc.split():
        if token.startswith("SharedID:"):
            return token.split("SharedID:")[1]
    return None

def extract_shared_id_from_notion(page):
    rt = page["properties"].get("Shared ID", {}).get("rich_text", [])
    return rt[0]["text"]["content"] if rt else None

def load_cache():
    if os.path.exists(CACHE_PATH):
        with open(CACHE_PATH) as f:
            return json.load(f)
    return {}

def save_cache(cache):
    with open(CACHE_PATH, "w") as f:
        json.dump(cache, f, indent=2)

def ensure_notion_shared_ids(notion, pages, db_id):
    for p in pages:
        if not extract_shared_id_from_notion(p):
            new_sid = str(uuid.uuid4())
            st.session_state.log_messages.append(f"🔖 Assigned Shared ID to Notion page {p['id']}: {new_sid}")
            notion.pages.update(
                page_id=p["id"],
                properties={"Shared ID": {"rich_text":[{"text":{"content":new_sid}}]}}
            )
    time.sleep(0.1)

def ensure_google_shared_ids(service, events):
    updated = []
    for ev in events:
        sid = extract_shared_id_from_google(ev)
        if not sid:
            new_sid = str(uuid.uuid4())
            st.session_state.log_messages.append(f"🔖 Assigned Shared ID to Google event {ev['id']}: {new_sid}")
            desc = (ev.get("description") or "") + f" SharedID:{new_sid}"
            service.events().patch(
                calendarId=GOOGLE_CALENDAR_ID,
                eventId=ev["id"],
                body={"description": desc.strip()}
            ).execute()
            ev["description"] = desc
        updated.append(ev)
    time.sleep(0.1)
    return updated

def init_google_client(client_info):
    scopes = ['https://www.googleapis.com/auth/calendar']
    creds = None

    if os.path.exists('token.json'):
        with open('token.json', 'rb') as token_file:
            try:
                creds = pickle.load(token_file)
            except:
                creds = None

    if creds and creds.valid:
        pass
    elif creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    else:
        flow = InstalledAppFlow.from_client_config(client_info, scopes)
        creds = flow.run_local_server(port=8080)

    with open('token.json', 'wb') as token_file:
        pickle.dump(creds, token_file)

    return build('calendar', 'v3', credentials=creds)

def get_google_events(service, start_dt, end_dt):
    tmin = start_dt.isoformat()+"Z"
    tmax = end_dt.isoformat()+"Z"
    return service.events().list(
        calendarId=GOOGLE_CALENDAR_ID,
        timeMin=tmin,
        timeMax=tmax,
        singleEvents=True,
        orderBy="startTime"
    ).execute().get("items", [])

def get_notion_events(notion, db_id, start_dt, end_dt):
    d1 = start_dt.date().isoformat()
    d2 = end_dt.date().isoformat()
    return notion.databases.query(
        database_id=db_id,
        filter={"and":[
            {"property":"Due Date","date":{"on_or_after":d1}},
            {"property":"Due Date","date":{"on_or_before":d2}}
        ]}
    ).get("results", [])

def events_match(t1, d1, t2, d2):
    return t1.strip().lower() == t2.strip().lower() and d1 == d2

def apply_edits_strict(notion, gcal, old_cache, db_id):
    notion_pages = notion.databases.query(database_id=db_id).get("results", [])
    notion_map = {}
    for p in notion_pages:
        sid = extract_shared_id_from_notion(p)
        if not sid:
            continue
        title = p["properties"]["Task"]["title"][0]["plain_text"]
        due_date = p.get("properties", {}).get("Due Date", {}).get("date")
        date = due_date["start"][:10] if due_date and due_date.get("start") else None
        notion_map[sid] = (p["id"], title, date)

    now = datetime.datetime.utcnow()
    events = gcal.events().list(
        calendarId=GOOGLE_CALENDAR_ID,
        timeMin=(now - datetime.timedelta(days=30)).isoformat() + "Z",
        timeMax=(now + datetime.timedelta(days=30)).isoformat() + "Z",
        singleEvents=True
    ).execute().get("items", [])

    gcal_map = {
        extract_shared_id_from_google(ev): ev
        for ev in events if extract_shared_id_from_google(ev)
    }

    for sid, old in old_cache.items():
        # Notion → Google
        if sid in notion_map and old.get("event_id"):
            page_id, n_title, n_date = notion_map[sid]
            if n_title != old["title"] or n_date != old["date"]:
                st.session_state.log_messages.append(
                    f"✏️ Notion edit SID={sid}: {old['title']}@{old['date']} → {n_title}@{n_date}"
                )
                ev = gcal_map.get(sid)
                if ev:
                    raw = ev["start"].get("dateTime")
                    if raw:
                        orig = datetime.datetime.fromisoformat(raw)
                        new_dt = orig.replace(year=int(n_date[:4]), month=int(n_date[5:7]), day=int(n_date[8:10]))
                        body = {
                            "summary": n_title,
                            "start": {"dateTime": new_dt.isoformat(), "timeZone": ev["start"].get("timeZone", "UTC")},
                            "end":   {"dateTime": (new_dt + datetime.timedelta(hours=1)).isoformat(), "timeZone": ev["end"].get("timeZone", "UTC")},
                            "description": f"SharedID:{sid}"
                        }
                    else:
                        body = {
                            "summary": n_title,
                            "start": {"date": n_date},
                            "end":   {"date": (datetime.date.fromisoformat(n_date) + datetime.timedelta(days=1)).isoformat()},
                            "description": f"SharedID:{sid}"
                        }
                    gcal.events().patch(calendarId=GOOGLE_CALENDAR_ID, eventId=ev["id"], body=body).execute()

        # Google → Notion
        if sid in gcal_map and old.get("page_id"):
            ev = gcal_map[sid]
            g_title = ev.get("summary", "")
            raw = ev["start"].get("dateTime") or ev["start"].get("date")
            g_date = raw[:10]
            if g_title != old["title"] or g_date != old["date"]:
                st.session_state.log_messages.append(
                    f"✏️ Google edit SID={sid}: {old['title']}@{old['date']} → {g_title}@{g_date}"
                )
                notion.pages.update(
                    page_id=old["page_id"],
                    properties={
                        "Task": {"title": [{"text": {"content": g_title}}]},
                        "Due Date": {"date": {"start": g_date}}
                    }
                )

    for sid, ev in gcal_map.items():
        if sid in old_cache and ev["id"] != old_cache[sid].get("event_id"):
            old_cache[sid]["event_id"] = ev["id"]

    for sid, (page_id, title, date) in notion_map.items():
        if sid in old_cache and page_id != old_cache[sid].get("page_id"):
            old_cache[sid]["page_id"] = page_id

def sync_google_to_notion(events, pages, notion, db_id):
    n_map = {extract_shared_id_from_notion(p): p for p in pages}
    for ev in events:
        sid   = extract_shared_id_from_google(ev)
        title = ev.get("summary", "").strip()
        date  = ev["start"].get("date") or ev["start"].get("dateTime", "")[:10]
        if not title or not date or sid in n_map:
            continue
        if any(events_match(title, date,
                p["properties"]["Task"]["title"][0]["text"]["content"],
                p["properties"]["Due Date"]["date"]["start"][:10]) for p in pages):
            continue
        st.session_state.log_messages.append(f"➕ Created Notion task: {title}@{date} (SID={sid})")
        notion.pages.create(parent={"database_id": db_id}, properties={
            "Task": {"title":[{"text":{"content":title}}]},
            "Due Date": {"date":{"start":date}},
            "Shared ID": {"rich_text":[{"text":{"content":sid}}]}
        })

def sync_notion_to_google(notion, pages, events, service, db_id):
    g_map = {extract_shared_id_from_google(ev): ev for ev in events}
    for p in pages:
        sid   = extract_shared_id_from_notion(p)
        title = p["properties"]["Task"]["title"][0]["plain_text"]
        date  = p["properties"]["Due Date"]["date"]["start"][:10]
        if sid in g_map:
            continue
        if any(events_match(title, date,
                ev.get("summary", ""),
                ev["start"].get("date") or ev["start"].get("dateTime", "")[:10]) for ev in events):
            continue
        st.session_state.log_messages.append(f"➕ Created Google event: {title}@{date} (SID={sid})")
        service.events().insert(calendarId=GOOGLE_CALENDAR_ID, body={
            "summary": title,
            "start": {"date": date},
            "end": {"date": (datetime.date.fromisoformat(date)+datetime.timedelta(days=1)).isoformat()},
            "description": f"SharedID:{sid}"
        }).execute()
        if sid:
            notion.pages.update(p["id"], properties={
                "Shared ID": {"rich_text": [{"text": {"content": sid}}]}
            })
        else:
            st.session_state.log_messages.append(f"⚠️ Skipped updating Shared ID for page {p['id']} because SID was None")



# === UI: Gather Input ===
client_info_file = st.sidebar.file_uploader("Upload Google `client_info.json`", type="json")
notion_token = st.sidebar.text_input(
    "🔑 Notion API Key", 
    type="password", 
    value=saved_settings.get("NOTION_API_KEY", "")
)
notion_db_id = st.sidebar.text_input(
    "🗂️ Notion Database ID", 
    value=saved_settings.get("NOTION_DATABASE_ID", "")
)
days = st.sidebar.slider("Days to Sync", 1, 30, 7)
start_dt = datetime.datetime.utcnow()
end_dt = start_dt + datetime.timedelta(days=days)
save_settings = st.sidebar.checkbox("💾 Remember credentials for next time")
client_info = None
if client_info_file:
    try:
        content = client_info_file.read()
        client_info = json.loads(content)
        client_info_file.seek(0)
    except Exception as e:
        st.error("❌ Failed to read client_info.json. Make sure it is a valid JSON file.")
        st.stop()
elif saved_settings.get("client_info"):
    client_info = saved_settings["client_info"]


if notion_token and notion_db_id and st.sidebar.button("Run Sync"):
    st.session_state.log_messages = []
    with st.spinner("Syncing..."):

        if client_info_file:
            try:
                content = client_info_file.read()
                client_info = json.loads(content)
                client_info_file.seek(0)
            except Exception as e:
                st.error("❌ Failed to read client_info.json. Make sure it is a valid JSON file.")
                st.stop()
        elif "client_info" in saved_settings:
            client_info = saved_settings["client_info"]
        else:
            client_info = None
        if save_settings:
            with open(SETTINGS_PATH, "w") as f:
                json.dump({
                    "client_info": client_info,
                    "NOTION_API_KEY": notion_token,
                    "NOTION_DATABASE_ID": notion_db_id
                }, f, indent=2)
        gcal = init_google_client(client_info)
        try:
            notion = NotionClient(auth=notion_token)
            notion_pages = get_notion_events(notion, notion_db_id, start_dt, end_dt)
        except Exception as e:
            st.error(f"❌ Notion error: {e}")
            st.stop()

        old_cache = load_cache()

        notion_pages = get_notion_events(notion, notion_db_id, start_dt, end_dt)
        google_events = get_google_events(gcal, start_dt, end_dt)

        ensure_notion_shared_ids(notion, notion_pages, notion_db_id)
        google_events = ensure_google_shared_ids(gcal, google_events)
        apply_edits_strict(notion, gcal, old_cache, notion_db_id)

        sync_google_to_notion(google_events, notion_pages, notion, notion_db_id)
        sync_notion_to_google(notion, notion_pages, google_events, gcal, notion_db_id)

        # Save snapshot
        snapshot = {}
        for p in notion_pages:
            sid = extract_shared_id_from_notion(p)
            title = p["properties"]["Task"]["title"][0]["plain_text"]
            date = p["properties"]["Due Date"]["date"]["start"][:10]
            snapshot[sid] = {"title": title, "date": date, "page_id": p["id"], "event_id": None}
        for ev in google_events:
            sid = extract_shared_id_from_google(ev)
            title = ev.get("summary", "")
            date = ev["start"].get("date") or ev["start"].get("dateTime", "")[:10]
            entry = snapshot.get(sid, {"page_id": None})
            entry.update({"title": title, "date": date, "event_id": ev["id"]})
            snapshot[sid] = entry
        save_cache(snapshot)

    st.success("✅ Sync complete!")
    if st.session_state.log_messages:
        st.subheader("Sync Log")
        for msg in st.session_state.log_messages:
            st.text(msg)
