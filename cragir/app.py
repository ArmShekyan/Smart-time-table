import streamlit as st
import uuid
import random
import pandas as pd
import json
import os
import requests
import time
from dataclasses import dataclass, asdict
from typing import List
from fpdf import FPDF
import streamlit_authenticator as stauth  # 🔥 Պաշտոնական Auth
from google import genai

# --- ՄՈԴԵԼՆԵՐ ---
@dataclass
class Subject:
    id: str
    name: str
    complexity: int

@dataclass
class Teacher:
    id: str
    name: str
    subject_ids: List[str]

@dataclass
class ClassGroup:
    id: str
    grade: str
    section: str

@dataclass
class Assignment:
    id: str
    teacher_id: str
    subject_id: str
    class_id: str
    lessons_per_week: int


# --- 📌 Ինստրուկցիայի Թռնող Պատուհան (Modal) ---
@st.dialog("📖 Ֆունկցիաների Մանրամասն Ուղեցույց")
def show_instruction_modal():
    st.markdown("""
    Բարի գալուստ Smart Time Table։ Հետևեք այս կանոններին՝ անթերի դասացուցակ ստանալու համար։
    """)

    with st.expander("📊 1. Վահանակ", expanded=True):
        st.markdown("""
        * **Ֆունկցիան.** Ցույց է տալիս բազայում գրանցված տվյալների ամփոփ պատկերը։
        """)

    with st.expander("📚 2. Առարկաներ"):
        st.markdown("""
        * **Ֆունկցիան.** Դպրոցում անցնող բոլոր դասերի շտեմարանն է։
        """)

    with st.expander("👩‍🏫 3. Ուսուցիչներ"):
        st.markdown("""
        * **Ֆունկցիան.** Դասավանդող անձնակազմի պաշտոնական ցուցակն է։
        """)

    if st.button("Հասկանալի է, անցնենք գործի! ✅", use_container_width=True, type="primary"):
        st.rerun()


DB_FILE = "smart_timetable_final.json"
DAYS_AM = ["Երկուշաբթի", "Երեքշաբթի", "Չորեքշաբթի", "Հինգշաբթի", "Ուրբաթ"]

DEFAULT_OWNER = {"username": "armshekyan", "password": "arms567", "role": "owner"}


# --- 🔑 ՏՎՅԱԼՆԵՐԻ ԲԱԶԱՅԻ ՖՈՒՆԿՑԻԱՆԵՐ ---

def get_supabase_headers():
    try:
        if "supabase_key" in st.secrets and "supabase_url" in st.secrets:
            return {
                "apikey": st.secrets["supabase_key"],
                "Authorization": f"Bearer {st.secrets['supabase_key']}",
                "Content-Type": "application/json"
            }
    except Exception:
        pass
    return None


def save_to_disk():
    with st.spinner("⏳ Պահպանվում է..."):
        time.sleep(1)
        
        local_data = {
            "subjects": {s.id: asdict(s) for s in st.session_state.subjects},
            "teachers": {t.id: asdict(t) for t in st.session_state.teachers},
            "classes": {c.id: asdict(c) for c in st.session_state.classes},
            "assignments": {a.id: asdict(a) for a in st.session_state.assignments},
            "schedule": st.session_state.schedule,
            "subj_pool": list(set(st.session_state.subj_pool)),
            "teacher_pool": list(set(st.session_state.teacher_pool)),
            "users_list": st.session_state.users_list
        }

        headers = get_supabase_headers()
        cloud_data = {}
        if headers:
            try:
                url = f"{st.secrets['supabase_url']}/rest/v1/timetable_data?id=eq.1&select=data"
                response = requests.get(url, headers=headers)
                if response.status_code == 200 and response.json():
                    cloud_data = response.json()[0]["data"]
            except Exception:
                pass

        merged_subjects = {**{s["id"]: s for s in cloud_data.get("subjects", [])}, **local_data["subjects"]}
        merged_teachers = {**{t["id"]: t for t in cloud_data.get("teachers", [])}, **local_data["teachers"]}
        merged_classes = {**{c["id"]: c for c in cloud_data.get("classes", [])}, **local_data["classes"]}
        merged_assignments = {**{a["id"]: a for a in cloud_data.get("assignments", [])}, **local_data["assignments"]}
        
        merged_subj_pool = list(set(cloud_data.get("subj_pool", []) + local_data["subj_pool"]))
        merged_teacher_pool = list(set(cloud_data.get("teacher_pool", []) + local_data["teacher_pool"]))

        final_data = {
            "subjects": list(merged_subjects.values()),
            "teachers": list(merged_teachers.values()),
            "classes": list(merged_classes.values()),
            "assignments": list(merged_assignments.values()),
            "schedule": local_data["schedule"],
            "subj_pool": merged_subj_pool,
            "teacher_pool": merged_teacher_pool,
            "users_list": local_data["users_list"]
        }

        if headers:
            try:
                url = f"{st.secrets['supabase_url']}/rest/v1/timetable_data"
                payload = {"id": 1, "data": final_data}
                headers["Prefer"] = "resolution=merge-duplicates"
                requests.post(url, headers=headers, data=json.dumps(payload))
                st.toast("✅ Տվյալները միացվեցին և պահպանվեցին Cloud-ում!", icon="🌐")
                parse_data(final_data)
                return
            except Exception:
                pass

        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(final_data, f, ensure_ascii=False, indent=4)
        st.toast("⚠️ Պահպանվեց տեղական ֆայլում (Local):", icon="💾")
        parse_data(final_data)


def reset_all_data():
    with st.spinner("🚨 Ամբողջական ջնջում..."):
        time.sleep(2)
        st.session_state.subjects = []
        st.session_state.teachers = []
        st.session_state.classes = []
        st.session_state.assignments = []
        st.session_state.schedule = None
        st.session_state.subj_pool = []
        st.session_state.teacher_pool = []
        
        data = {
            "subjects": [],
            "teachers": [],
            "classes": [],
            "assignments": [],
            "schedule": None,
            "subj_pool": [],
            "teacher_pool": [],
            "users_list": st.session_state.users_list 
        }

        headers = get_supabase_headers()
        if headers:
            try:
                url = f"{st.secrets['supabase_url']}/rest/v1/timetable_data"
                payload = {"id": 1, "data": data}
                headers["Prefer"] = "resolution=merge-duplicates"
                requests.post(url, headers=headers, data=json.dumps(payload))
                st.toast("💥 Բազան զրոյացվեց Cloud-ում:", icon="💣")
                st.balloons()
                return
            except Exception:
                pass

        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        st.toast("💥 Բազան զրոյացվեց տեղական ֆայլում:", icon="💣")
        st.balloons()


def manual_refresh():
    with st.spinner("🔄 Տվյալները թարմացվում են Cloud-ից..."):
        time.sleep(1.5)
        headers = get_supabase_headers()
        if headers:
            try:
                url = f"{st.secrets['supabase_url']}/rest/v1/timetable_data?id=eq.1&select=data"
                response = requests.get(url, headers=headers)
                if response.status_code == 200 and response.json():
                    data = response.json()[0]["data"]
                    parse_data(data)
                    st.toast("✅ Տվյալները թարմ են:", icon="🔄")
                    st.rerun()
                    return
            except Exception:
                pass

        if os.path.exists(DB_FILE):
            try:
                with open(DB_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    parse_data(data)
                    st.toast("✅ Տեղական տվյալները թարմ են:", icon="🔄")
            except Exception:
                pass
    st.rerun()


def refresh_users_only():
    with st.spinner("🔄 Բեռնվում են օգտատերերը SQL բազայից..."):
        time.sleep(1)
        headers = get_supabase_headers()
        if headers:
            try:
                url = f"{st.secrets['supabase_url']}/rest/v1/users?select=*"
                response = requests.get(url, headers=headers)
                if response.status_code == 200:
                    st.session_state.users_list = response.json()
                    st.toast("👥 Օգտատերերի ցուցակը թարմացվեց SQL-ից!", icon="👤")
                    st.rerun()
                    return
            except Exception:
                pass
        st.error("❌ Չհաջողվեց կապ հաստատել SQL բազայի հետ:")


def load_from_disk():
    headers = get_supabase_headers()
    if headers:
        try:
            url = f"{st.secrets['supabase_url']}/rest/v1/timetable_data?id=eq.1&select=data"
            response = requests.get(url, headers=headers)
            if response.status_code == 200 and response.json():
                data = response.json()[0]["data"]
                parse_data(data)
                return
        except Exception:
            pass

    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                parse_data(data)
                return
        except Exception:
            pass
    
    st.session_state.users_list = [DEFAULT_OWNER]


def parse_data(data):
    st.session_state.subjects = [Subject(**s) for s in data.get("subjects", [])]
    st.session_state.teachers = [Teacher(**t) for t in data.get("teachers", [])]
    st.session_state.classes = [ClassGroup(**c) for c in data.get("classes", [])]
    st.session_state.assignments = [Assignment(**a) for a in data.get("assignments", [])]
    st.session_state.schedule = data.get("schedule", None)
    st.session_state.subj_pool = data.get("subj_pool", [])
    st.session_state.teacher_pool = data.get("teacher_pool", [])
    st.session_state.users_list = data.get("users_list", [DEFAULT_OWNER])


# --- INITIALIZATION ---
st.set_page_config(page_title="Smart Time Table", layout="wide", page_icon="📅")

st.markdown("""
<style>
    [data-testid="stSidebar"] { background-color: #1a1c24; border-right: 1px solid #343a40; }
    [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h3 { color: #f8f9fa; }
    [data-testid="stSidebar"] .stButton>button { border-radius: 20px; transition: all 0.3s ease-in-out; }
    [data-testid="stDataFrameDataframe"] div table { border-radius: 10px; overflow: hidden; }
</style>
""", unsafe_allow_html=True)


if "subjects" not in st.session_state:
    st.session_state.update({
        "subjects": [], 
        "teachers": [], 
        "classes": [], 
        "assignments": [], 
        "schedule": None, 
        "subj_pool": [], 
        "teacher_pool": [], 
        "users_list": [DEFAULT_OWNER],
        "logged_in": False,       
        "username": "",           
        "user_role": "",         
        "active_page": "normal",
        "active_tab": "📊 Վահանակ",
        "chat_histories": {},
        "show_readme": False
    })
    load_from_disk()


# 🔥 --- ՊԱՇՏՈՆԱԿԱՆ ՄՈՒՏՔԻ ՀԱՄԱԿԱՐԳ --- 🔥

credentials = {"usernames": {}}
for u in st.session_state.users_list:
    credentials["usernames"][u["username"]] = {
        "name": u["username"],
        "password": u["password"],
        "role": u.get("role", "user")
    }

authenticator = stauth.Authenticate(
    credentials,
    "smart_timetable_cookie",
    "smart_timetable_key",
    cookie_expiry_days=30
)

# Authenticator-ի մուտքի պատուհան
name, authentication_status, username = authenticator.login("👤 Մուտք համակարգ", "main")


if authentication_status == False:
    st.error("❌ Օգտանունը կամ գաղտնաբառը սխալ է")
elif authentication_status == None:
    st.warning("⚠️ Խնդրում ենք մուտքագրել Ձեր տվյալները")
elif authentication_status:
    if not st.session_state.logged_in:
        st.session_state.logged_in = True
        st.session_state.username = username
        
        user_role = "user"
        for u in st.session_state.users_list:
            if u["username"] == username:
                user_role = u.get("role", "user")
                break
        st.session_state.user_role = user_role
        st.session_state.show_readme = True
        
        if user_role in ['owner', 'admin', 'subject_editor', 'teacher_editor']:
            st.session_state.active_tab = "📊 Վահանակ"
        else:
            st.session_state.active_tab = "📂 Վերջին պահպանվածը"
        
        st.rerun()


if not st.session_state.logged_in:
    st.stop()


if st.session_state.get("show_readme", False):
    st.session_state.show_readme = False
    show_instruction_modal()


def get_subj_name(sid):
    return next((s.name for s in st.session_state.subjects if s.id == sid), "Անհայտ")

def get_subj_complexity(sid):
    return next((s.complexity for s in st.session_state.subjects if s.id == sid), 3)


def generate_pdf(schedule_data):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", style='B', size=14)
    pdf.cell(200, 10, txt="Smart Time Table - School Schedule", ln=True, align='C')
    return pdf.output()


st.sidebar.title(f"👤 {st.session_state.username}")
st.sidebar.caption(f"Պաշտոն՝ **{st.session_state.user_role}**")


# 🔥 Authenticator-ի Ելքի կոճակ
authenticator.logout("🚪 Ելք համակարգից", "sidebar")


if not authentication_status:
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.session_state.user_role = ""
    st.rerun()


if st.sidebar.button("🔄 Թարմացնել Cloud-ից", use_container_width=True):
    manual_refresh()

st.sidebar.divider()


def on_page_change():
    st.session_state.active_page = "normal"
    st.session_state.active_tab = st.session_state.nav_radio

available_pages = []

if st.session_state.user_role in ['owner', 'admin']:
    available_pages = ["📊 Վահանակ", "📚 Առարկաներ", "👩‍🏫 Ուսուցիչներ", "🏫 Դասարաններ", "🚀 Գեներացում", "📂 Վերջին պահպանվածը", "👤 Ուսուցչի Անձնական", "🤖 AI Օգնական"]
else:
    available_pages = ["📂 Վերջին պահպանվածը", "👤 Ուսուցչի Անձնական", "🤖 AI Օգնական"]

default_index = 0
if st.session_state.active_tab in available_pages:
    default_index = available_pages.index(st.session_state.active_tab)

page = st.sidebar.radio("Նավիգացիա", available_pages, index=default_index, key="nav_radio", on_change=on_page_change)


st.sidebar.divider()


if st.sidebar.button("💾 Պահպանել Բոլորը", use_container_width=True, type="primary"):
    save_to_disk()


if st.session_state.user_role == 'owner':
    st.sidebar.divider()
    st.sidebar.markdown("<h3 style='color: #dc3545;'>⚠️ Վտանգավոր Գոտի</h3>", unsafe_allow_html=True)
    confirm_reset = st.sidebar.checkbox("Հաստատում եմ ամբողջական ջնջումը")
    
    if st.sidebar.button("🚨 Զրոյացնել Ամբողջ Բազան", type="primary", use_container_width=True, disabled=not confirm_reset):
        reset_all_data()
        st.rerun()

st.sidebar.divider()


if st.session_state.user_role in ['owner', 'admin']:
    if st.sidebar.button("👥 Օգտատերերի Կառավարում", use_container_width=True):
        st.session_state.active_page = "👥 Օգտատերեր"
        st.rerun()


@st.dialog("🗑️ Հաստատեք ջնջումը")
def confirm_delete_user_modal(idx):
    target_user = st.session_state.users_list[idx]
    st.warning(f"⚠️ Դուք համոզվա՞ծ եք, որ ուզում եք ջնջել **{target_user['username']}** օգտատիրոջը։")
    
    col_l, col_r = st.columns(2)
    
    if col_l.button("Այո, Ջնջել ✅", use_container_width=True, type="primary"):
        headers = get_supabase_headers()
        if headers:
            try:
                base_url = st.secrets['supabase_url'].strip("/")
                delete_url = f"{base_url}/rest/v1/users?username=eq.{target_user['username']}"
                requests.delete(delete_url, headers=headers)
            except Exception:
                pass

        st.session_state.users_list.pop(idx)
        st.rerun()

    if col_r.button("Ոչ, Չեղարկել ❌", use_container_width=True):
        st.rerun()


# --- ԷՋԵՐԻ ՄԱՐՄԻՆԸ ---

if st.session_state.active_page == "👥 Օգտատերեր" and st.session_state.user_role in ['owner', 'admin']:
    st.title("👥 Օգտատերերի և Իրավունքների Կառավարում")
    
    col1, col2 = st.columns(2)
    with col1:
        with st.form("add_user_form", clear_on_submit=True):
            st.subheader("🆕 Ավելացնել Նոր Օգտատեր")
            new_u = st.text_input("Username")
            new_p = st.text_input("Password")
            new_r = st.selectbox("Դերը", ["user", "subject_editor", "teacher_editor", "admin"])
            
            if st.form_submit_button("Ավելացնել Օգտատեր", use_container_width=True):
                if new_u and new_p:
                    if not any(u['username'] == new_u for u in st.session_state.users_list):
                        new_user_data = {"username": new_u, "password": new_p, "role": new_r}
                        st.session_state.users_list.append(new_user_data)
                        st.rerun()

    st.divider()
    if st.button("🔄 Թարմացնել Ցուցակը (Կարդալ SQL բազայից)", use_container_width=True):
        refresh_users_only()

    st.subheader("📋 Գրանցված Օգտատերեր")
    for i, u in enumerate(st.session_state.users_list):
        with st.container(border=True):
            c1, c2, c3 = st.columns([3, 3, 1])
            c1.markdown(f"👤 **{u['username']}**")
            c2.markdown(f"🎭 Դերը՝ <span style='color: #0d6efd;'>{u['role']}</span>", unsafe_allow_html=True)
            if u['username'] != st.session_state.username and u['role'] != 'owner':
                if c3.button("🗑️", key=f"del_user_{i}"):
                    confirm_delete_user_modal(i)

elif st.session_state.active_page == "normal":

    if st.session_state.active_tab == "📊 Վահանակ":
        st.title("📊 Ընդհանուր Վիճակագրություն")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric(label="📚 Առարկաներ", value=len(st.session_state.subjects))
        m2.metric(label="👩‍🏫 Ուսուցիչներ", value=len(st.session_state.teachers))
        m3.metric(label="🏫 Դասարաններ", value=len(st.session_state.classes))
        m4.metric(label="📋 Կապեր/Ժամեր", value=len(st.session_state.assignments))

    elif st.session_state.active_tab == "📚 Առարկաներ":
        st.title("📚 Առարկաների Շտեմարան")
        col_l, col_r = st.columns([1, 1])
        with col_l:
            with st.form("add_to_pool", clear_on_submit=True):
                new_name = st.text_input("Առարկայի անուն")
                if st.form_submit_button("Ավելացնել ցանկում", use_container_width=True):
                    if new_name and new_name not in st.session_state.subj_pool:
                        st.session_state.subj_pool.append(new_name)
                        st.rerun()

        with col_r:
            if st.session_state.subj_pool:
                with st.form("register_subj", clear_on_submit=True):
                    selected = st.selectbox("Ընտրեք ցանկից", st.session_state.subj_pool)
                    comp = st.select_slider("Բարդություն (1-5)", options=[1,2,3,4,5], value=3)
                    if st.form_submit_button("Գրանցել", use_container_width=True):
                        if not any(s.name == selected for s in st.session_state.subjects):
                            st.session_state.subjects.append(Subject(str(uuid.uuid4()), selected, comp))
                            st.rerun()

    elif st.session_state.active_tab == "👩‍🏫 Ուսուցիչներ":
        st.title("👩‍🏫 Ուսուցիչների Շտեմարան")
        col_l, col_r = st.columns([1, 1])
        with col_l:
            with st.form("add_t_pool", clear_on_submit=True):
                t_name = st.text_input("Ուսուցչի անուն")
                if st.form_submit_button("Ավելացնել ցանկում", use_container_width=True):
                    if t_name and t_name not in st.session_state.teacher_pool:
                        st.session_state.teacher_pool.append(t_name)
                        st.rerun()

        with col_r:
            if st.session_state.teacher_pool and st.session_state.subjects:
                with st.form("register_teacher", clear_on_submit=True):
                    sel_t = st.selectbox("Ընտրեք ուսուցչին", st.session_state.teacher_pool)
                    sel_subjs = st.multiselect("Ընտրեք առարկաները", st.session_state.subjects, format_func=lambda x: x.name)
                    if st.form_submit_button("Գրանցել", use_container_width=True):
                        if not any(t.name == sel_t for t in st.session_state.teachers):
                            st.session_state.teachers.append(Teacher(str(uuid.uuid4()), sel_t, [s.id for s in sel_subjs]))
                            st.rerun()

    elif st.session_state.active_tab == "🏫 Դասարաններ":
        st.title("🏫 Դասարաններ և Ժամեր")
        col1, col2 = st.columns(2)
        with col1:
            with st.form("cl_form", clear_on_submit=True):
                g = st.text_input("Հոսք (օր. ԱԲ)")
                s = st.text_input("Թիվ/Տառ (օր. 1 կամ Ա)")
                if st.form_submit_button("Ավելացնել", use_container_width=True):
                    if g and s:
                        st.session_state.classes.append(ClassGroup(str(uuid.uuid4()), g, s))
                        st.rerun()

        with col2:
            if st.session_state.teachers and st.session_state.classes:
                sel_t = st.selectbox("👩‍🏫 Ընտրեք Ուսուցչին", st.session_state.teachers, format_func=lambda x: x.name)
                t_subjs = [sub for sub in st.session_state.subjects if sub.id in sel_t.subject_ids]

                with st.form("as_form_fixed", clear_on_submit=True):
                    sel_c = st.selectbox("Դասարան", st.session_state.classes, format_func=lambda x: f"{x.grade}{x.section}")
                    if t_subjs:
                        sel_s = st.selectbox("Առարկա", t_subjs, format_func=lambda x: x.name)
                    hrs = st.number_input("Շաբաթական ժամեր", 1, 10, 2)
                    
                    if st.form_submit_button("Կապել", use_container_width=True):
                        st.session_state.assignments.append(Assignment(str(uuid.uuid4()), sel_t.id, sel_s.id, sel_c.id, hrs))
                        st.rerun()

    elif st.session_state.active_tab == "🚀 Գեներացում":
        st.title("🚀 Պրոֆեսիոնալ Գեներացում")
        if st.button("🔥 Ստեղծել Խելացի Դասացուցակ", use_container_width=True, type="primary"):
            st.session_state.schedule = [] # Simple skeleton
            st.success("🎉 Գեներացվեց")

    elif st.session_state.active_tab == "📂 Վերջին պահպանվածը":
        st.title("📂 Պահպանված Դասացուցակ")
        if st.session_state.schedule:
            st.write("Այստեղ է")
        else:
            st.info("Պահպանված տվյալներ չկան")

    elif st.session_state.active_tab == "👤 Ուսուցչի Անձնական":
        st.title("👤 Ուսուցչի Շաբաթվա Գրաֆիկ")

    elif st.session_state.active_tab == "🤖 AI Օգնական":
        st.title("🤖 AI Օգնական (Gemini)")
        
        current_user = st.session_state.username
        if current_user not in st.session_state.chat_histories:
            st.session_state.chat_histories[current_user] = []

        for message in st.session_state.chat_histories[current_user]:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        if prompt := st.chat_input("Ինչպե՞ս կարող եմ օգնել քեզ այսօր։"):
            st.session_state.chat_histories[current_user].append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)

            with st.chat_message("assistant"):
                try:
                    client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
                    response = client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
                    response_text = response.text
                except Exception as e:
                    response_text = f"Սխալ: {str(e)}"

                st.markdown(response_text)
                st.session_state.chat_histories[current_user].append({"role": "assistant", "content": response_text})
