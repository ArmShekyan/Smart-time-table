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


DB_FILE = "smart_timetable_final.json"
DAYS_AM = ["Երկուշաբթի", "Երեքշաբթի", "Չորեքշաբթի", "Հինգշաբթի", "Ուրբաթ"]

DEFAULT_OWNER = {"username": "armshekyan", "password": "arms567", "role": "owner"}
DEFAULT_ADMIN = {"username": "arsoo", "password": "123", "role": "admin"}
DEFAULT_SUB_EDIT = {"username": "sub", "password": "123", "role": "subject_editor"}
DEFAULT_TEACH_EDIT = {"username": "teach", "password": "123", "role": "teacher_editor"}
DEFAULT_USER = {"username": "user", "password": "123", "role": "user"}


# --- 🔑 ՏՎՅԱԼՆԵՐԻ ԲԱԶԱՅԻ ԵՎ ԼՈԳԻՆԻ ՖՈՒՆԿՑԻԱՆԵՐ ---

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


def check_user(username, password):
    for u in st.session_state.users_list:
        if u["username"] == username and u["password"] == password:
            return u

    headers = get_supabase_headers()
    if headers:
        url = f"{st.secrets['supabase_url']}/rest/v1/users?username=eq.{username}&password=eq.{password}"
        try:
            response = requests.get(url, headers=headers)
            if response.status_code == 200 and response.json():
                return response.json()[0]
        except Exception:
            pass

    return None


def save_to_disk():
    with st.spinner("⏳ Պահպանվում է..."):
        time.sleep(1)
        data = {
            "subjects": [asdict(s) for s in st.session_state.subjects],
            "teachers": [asdict(t) for t in st.session_state.teachers],
            "classes": [asdict(c) for c in st.session_state.classes],
            "assignments": [asdict(a) for a in st.session_state.assignments],
            "schedule": st.session_state.schedule,
            "subj_pool": st.session_state.subj_pool,
            "teacher_pool": st.session_state.teacher_pool,
            "users_list": st.session_state.users_list 
        }

        headers = get_supabase_headers()
        if headers:
            try:
                url = f"{st.secrets['supabase_url']}/rest/v1/timetable_data"
                payload = {"id": 1, "data": data}
                headers["Prefer"] = "resolution=merge-duplicates"
                requests.post(url, headers=headers, data=json.dumps(payload))
                st.toast("✅ Տվյալները պահպանվեցին Cloud-ում!", icon="🌐")
                return
            except Exception:
                pass

        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        st.toast("⚠️ Պահպանվեց տեղական ֆայլում:", icon="💾")


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
    
    st.session_state.users_list = [DEFAULT_OWNER, DEFAULT_ADMIN, DEFAULT_SUB_EDIT, DEFAULT_TEACH_EDIT, DEFAULT_USER]


def parse_data(data):
    st.session_state.subjects = [Subject(**s) for s in data.get("subjects", [])]
    st.session_state.teachers = [Teacher(**t) for t in data.get("teachers", [])]
    st.session_state.classes = [ClassGroup(**c) for c in data.get("classes", [])]
    st.session_state.assignments = [Assignment(**a) for a in data.get("assignments", [])]
    st.session_state.schedule = data.get("schedule", None)
    st.session_state.subj_pool = data.get("subj_pool", [])
    st.session_state.teacher_pool = data.get("teacher_pool", [])
    st.session_state.users_list = data.get("users_list", [DEFAULT_OWNER, DEFAULT_ADMIN, DEFAULT_SUB_EDIT, DEFAULT_TEACH_EDIT, DEFAULT_USER])


# --- INITIALIZATION ---

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


# --- 🚪 ԼՈԳԻՆԻ ԷՋ ---

if not st.session_state.logged_in:
    left_col, center_col, right_col = st.columns([1, 1.5, 1])

    with center_col:
        st.markdown("<br><br>", unsafe_allow_html=True)
        
        with st.container(border=True):
            st.markdown(
                "<h2 style='text-align: center; color: #0d6efd; font-weight: 800; margin-bottom: 5px;'>Smart Time Table</h2>"
                "<p style='text-align: center; color: #6c757d; font-size: 14px;'>Մուտք գործեք համակարգ՝ աշխատանքը շարունակելու համար</p>", 
                unsafe_allow_html=True
            )
            
            with st.form("login_panel", clear_on_submit=False):
                username_input = st.text_input("👤 Օգտատիրոջ անուն", placeholder="Մուտքագրեք username-ը")
                password_input = st.text_input("🔒 Գաղտնաբառ", type="password", placeholder="••••••••")
                
                st.markdown("<br>", unsafe_allow_html=True)
                
                submit_login = st.form_submit_button("Մուտք գործել", use_container_width=True, type="primary")

            if submit_login:
                if not username_input or not password_input:
                    st.error("⚠️ Խնդրում ենք լրացնել բոլոր դաշտերը:")
                else:
                    user = check_user(username_input, password_input)
                    if user:
                        st.session_state.logged_in = True
                        st.session_state.username = user['username']
                        st.session_state.user_role = user['role']
                        
                        if user['role'] in ['owner', 'admin', 'subject_editor', 'teacher_editor']:
                            st.session_state.active_tab = "📊 Վահանակ"
                        else:
                            st.session_state.active_tab = "📂 Վերջին պահպանվածը"

                        st.toast(f"🎉 Բարի վերադարձ, {username_input}!", icon="🚀")
                        st.snow() 
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("❌ Սխալ օգտանուն կամ գաղտնաբառ:")
                
    st.stop()


# --- 🛠️ ՀԻՄՆԱԿԱՆ ԾՐԱԳԻՐ ---

def get_subj_name(sid):
    return next((s.name for s in st.session_state.subjects if s.id == sid), "Անհայտ")


st.sidebar.title(f"👤 {st.session_state.username}")
st.sidebar.caption(f"Պաշտոն՝ **{st.session_state.user_role}**")

if st.sidebar.button("🚪 Ելք համակարգից", width='stretch'):
    st.session_state.logged_in = False
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
elif st.session_state.user_role == 'subject_editor':
    available_pages = ["📊 Վահանակ", "📚 Առարկաներ", "📂 Վերջին պահպանվածը", "🤖 AI Օգնական"]
elif st.session_state.user_role == 'teacher_editor':
    available_pages = ["📊 Վահանակ", "👩‍🏫 Ուսուցիչներ", "📂 Վերջին պահպանվածը", "🤖 AI Օգնական"]
else:
    available_pages = ["📂 Վերջին պահպանվածը", "👤 Ուսուցչի Անձնական", "🤖 AI Օգնական"]

default_index = 0
if st.session_state.active_tab in available_pages:
    default_index = available_pages.index(st.session_state.active_tab)

page = st.sidebar.radio("Նավիգացիա", available_pages, index=default_index, key="nav_radio", on_change=on_page_change)

st.sidebar.divider()

if st.sidebar.button("💾 Պահպանել Բոլորը", width='stretch', type="primary"):
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
    if st.sidebar.button("👥 Օգտատերերի Կառավարում", width='stretch'):
        st.session_state.active_page = "👥 Օգտատերեր"
        st.rerun()


# --- ԷՋԵՐԻ ՄԱՐՄԻՆԸ ---

if st.session_state.active_page == "👥 Օգտատերեր" and st.session_state.user_role in ['owner', 'admin']:
    st.title("👥 Օգտատերերի և Իրավունքների Կառավարում")
    
    col1, col2 = st.columns(2)
    with col1:
        with st.form("add_user_form", clear_on_submit=True):
            st.subheader("🆕 Ավելացնել Նոր Օգտատեր")
            new_u = st.text_input("Username")
            new_p = st.text_input("Password", type="password")
            roles_list = ["user", "subject_editor", "teacher_editor", "admin"]
            new_r = st.selectbox("Դերը", roles_list)
            
            if st.form_submit_button("Ավելացնել Օգտատեր", width='stretch'):
                if new_u and new_p:
                    if not any(u['username'] == new_u for u in st.session_state.users_list):
                        new_user_data = {"username": new_u, "password": new_p, "role": new_r}
                        st.session_state.users_list.append(new_user_data)
                        st.rerun()

    st.divider()
    st.subheader("📋 Գրանցված Օգտատերեր")
    
    for i, u in enumerate(st.session_state.users_list):
        with st.container(border=True):
            c1, c2, c3 = st.columns([3, 3, 1])
            c1.markdown(f"👤 **{u['username']}**")
            c2.markdown(f"🎭 Դերը՝ <span style='color: #0d6efd;'>{u['role']}</span>", unsafe_allow_html=True)
            
            can_delete = True
            if u['username'] == st.session_state.username or u['role'] == 'owner':
                can_delete = False 
                    
            if can_delete:
                if c3.button("🗑️", key=f"del_user_{i}"):
                    st.session_state.users_list.pop(i)
                    st.rerun()

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
                st.markdown("### 🆕 Ավելացնել ցուցակում")
                new_name = st.text_input("Առարկայի անուն")
                if st.form_submit_button("Ավելացնել ցանկում", width='stretch'):
                    if new_name and new_name not in st.session_state.subj_pool:
                        st.session_state.subj_pool.append(new_name)
                        st.rerun()

        with col_r:
            if st.session_state.subj_pool:
                with st.form("register_subj", clear_on_submit=True):
                    st.markdown("### 📋 Գրանցել Առարկան")
                    selected = st.selectbox("Ընտրեք ցանկից", st.session_state.subj_pool)
                    comp = st.select_slider("Բարդություն (1-5)", options=[1,2,3,4,5], value=3)
                    if st.form_submit_button("Գրանցել", width='stretch'):
                        if not any(s.name == selected for s in st.session_state.subjects):
                            st.session_state.subjects.append(Subject(str(uuid.uuid4()), selected, comp))
                            st.rerun()

        st.divider()
        st.subheader("✅ Գրանցված Առարկաներ")
        for i, s in enumerate(st.session_state.subjects):
            with st.container(border=True):
                c1, c2 = st.columns([5,1])
                c1.markdown(f"📖 **{s.name}** | Բարդություն՝ <span style='color: #0d6efd;'>{s.complexity}</span>", unsafe_allow_html=True)
                if c2.button("🗑️", key=f"s_{s.id}"):
                    st.session_state.subjects.pop(i)
                    st.rerun()

    elif st.session_state.active_tab == "👩‍🏫 Ուսուցիչներ":
        st.title("👩‍🏫 Ուսուցիչների Շտեմարան")
        
        col_l, col_r = st.columns([1, 1])
        with col_l:
            with st.form("add_t_pool", clear_on_submit=True):
                st.markdown("### 🆕 Ավելացնել ցուցակում")
                t_name = st.text_input("Ուսուցչի անուն")
                if st.form_submit_button("Ավելացնել ցանկում", width='stretch'):
                    if t_name and t_name not in st.session_state.teacher_pool:
                        st.session_state.teacher_pool.append(t_name)
                        st.rerun()

        with col_r:
            if st.session_state.teacher_pool and st.session_state.subjects:
                with st.form("register_teacher", clear_on_submit=True):
                    st.markdown("### 📋 Գրանցել Ուսուցչին")
                    sel_t = st.selectbox("Ընտրեք ուսուցչին", st.session_state.teacher_pool)
                    sel_subjs = st.multiselect("Ընտրեք առարկաները", st.session_state.subjects, format_func=lambda x: x.name)
                    if st.form_submit_button("Գրանցել", width='stretch'):
                        if not any(t.name == sel_t for t in st.session_state.teachers):
                            st.session_state.teachers.append(Teacher(str(uuid.uuid4()), sel_t, [s.id for s in sel_subjs]))
                            st.rerun()

        st.divider()
        st.subheader("✅ Գրանցված Ուսուցիչներ")
        for i, t in enumerate(st.session_state.teachers):
            with st.container(border=True):
                c1, c2 = st.columns([5, 1])
                subj_names = [get_subj_name(sid) for sid in t.subject_ids]
                c1.markdown(f"👤 **{t.name}** — <span style='color: #6c757d;'>{', '.join(subj_names)}</span>", unsafe_allow_html=True)
                if c2.button("🗑️", key=f"t_{t.id}"):
                    st.session_state.teachers.pop(i)
                    st.rerun()

    elif st.session_state.active_tab == "🏫 Դասարաններ":
        st.title("🏫 Դասարաններ և Ժամեր")
        
        col1, col2 = st.columns(2)
        with col1:
            with st.form("cl_form", clear_on_submit=True):
                st.markdown("### 🆕 Նոր Դասարան")
                g = st.text_input("Հոսք (օր. ԱԲ)")
                s = st.text_input("Թիվ/Տառ (օր. 1 կամ Ա)")
                if st.form_submit_button("Ավելացնել", width='stretch'):
                    if g and s:
                        st.session_state.classes.append(ClassGroup(str(uuid.uuid4()), g, s))
                        st.rerun()

        with col2:
            if st.session_state.teachers and st.session_state.classes:
                sel_t = st.selectbox("👩‍🏫 Ուսուցիչ", st.session_state.teachers, format_func=lambda x: x.name)
                t_subjs = [sub for sub in st.session_state.subjects if sub.id in sel_t.subject_ids]

                with st.form("as_form", clear_on_submit=True):
                    st.markdown("### 🔗 Կապել Դասարանին")
                    sel_c = st.selectbox("Դասարան", st.session_state.classes, format_func=lambda x: f"{x.grade}{x.section}")
                    
                    if t_subjs:
                        sel_s = st.selectbox("Առարկա", t_subjs, format_func=lambda x: x.name)
                    else:
                        st.warning("⚠️ Այս ուսուցչի համար առարկա չկա:")
                        sel_s = None

                    hrs = st.number_input("Շաբաթական ժամեր", 1, 10, 2)
                    
                    if st.form_submit_button("Կապել", width='stretch'):
                        if sel_s:
                            st.session_state.assignments.append(Assignment(str(uuid.uuid4()), sel_t.id, sel_s.id, sel_c.id, hrs))
                            st.rerun()

        st.divider()
        st.subheader("📋 Դասավանդման Կապեր")
        
        if st.session_state.classes:
            all_classes_option = ClassGroup(id="all", grade="🌐 Բոլոր", section="Դասարանները")
            class_options = [all_classes_option] + st.session_state.classes

            selected_class_view = st.selectbox("🔍 Ֆիլտրել ըստ դասարանի", class_options, format_func=lambda x: f"{x.grade}{x.section}" if x.id != "all" else x.grade)

            if selected_class_view.id == "all":
                filtered_assignments = [(i, a) for i, a in enumerate(st.session_state.assignments)]
            else:
                filtered_assignments = [(i, a) for i, a in enumerate(st.session_state.assignments) if a.class_id == selected_class_view.id]

            if filtered_assignments:
                for i, a in filtered_assignments:
                    t_name = next((t.name for t in st.session_state.teachers if t.id == a.teacher_id), "Անհայտ")
                    s_name = get_subj_name(a.subject_id)
                    c_name = next((f"{c.grade}{c.section}" for c in st.session_state.classes if c.id == a.class_id), "Անհայտ")

                    with st.container(border=True):
                        c1, c2 = st.columns([5, 1])
                        c1.markdown(f"🏫 **{c_name}** | 👩‍🏫 {t_name} — 📖 {s_name} | 🕒 {a.lessons_per_week} ժամ")
                        if c2.button("🗑️", key=f"del_a_{a.id}_{i}"):
                            st.session_state.assignments.pop(i)
                            st.rerun()
            else:
                st.info("ℹ️ Այս դասարանի համար կապեր չկան:")

    elif st.session_state.active_tab == "🚀 Գեներացում":
        st.title("🚀 Գեներացնել")

        if st.button("🏗️ Ստեղծել Խելացի Դասացուցակ", use_container_width=True, type="primary"):
            with st.spinner("⏳ Հաշվարկում է..."):
                time.sleep(1.5)

                schedule = []
                for cls in st.session_state.classes:
                    cls_assign = [a for a in st.session_state.assignments if a.class_id == cls.id]
                    pool = []
                    for assign in cls_assign:
                        for _ in range(assign.lessons_per_week):
                            pool.append(assign)

                    random.shuffle(pool)

                    hour_map = {day: 1 for day in DAYS_AM}
                    day_idx = 0

                    for p_item in pool:
                        day = DAYS_AM[day_idx % 5]
                        hour = hour_map[day]

                        t_name = next((t.name for t in st.session_state.teachers if t.id == p_item.teacher_id), "Անհայտ")
                        s_name = get_subj_name(p_item.subject_id)

                        schedule.append({
                            "Դասարան": f"{cls.grade}{cls.section}",
                            "Օր": day,
                            "Ժամ": hour,
                            "Առարկա": f"{s_name} ({t_name})"
                        })

                        hour_map[day] += 1
                        day_idx += 1

                st.session_state.schedule = schedule
                st.success("🎉 Դասացուցակը հաջողությամբ գեներացվեց:")

        if st.session_state.get('schedule'):
            st.divider()
            df_sched = pd.DataFrame(st.session_state.schedule)
            st.dataframe(df_sched, width='stretch', hide_index=True)

    elif st.session_state.active_tab == "📂 Վերջին պահպանվածը":
        st.title("📂 Դիտել Գեներացված Դասացուցակը")

        if not st.session_state.get('schedule'):
            st.info("ℹ️ Դեռևս ոչ մի դասացուցակ չկա:")
        else:
            df = pd.DataFrame(st.session_state.schedule)
            classes_list = df['Դասարան'].unique()
            selected_class = st.selectbox("🎯 Ընտրեք Դասարանը", classes_list)

            if selected_class:
                class_df = df[df['Դասարան'] == selected_class]
                pivot = class_df.pivot(index='Ժամ', columns='Օր', values='Առարկա').fillna("-")
                for day in DAYS_AM:
                    if day not in pivot.columns:
                        pivot[day] = "-"
                pivot = pivot[DAYS_AM]
                st.dataframe(pivot, width='stretch')

    elif st.session_state.active_tab == "👤 Ուսուցչի Անձնական":
        st.title("👤 Ուսուցչի Անձնական Գրաֆիկ")

        if not st.session_state.teachers or not st.session_state.get('schedule'):
            st.info("ℹ️ Տվյալները կամ դասացուցակը բացակայում են:")
        else:
            selected_teacher = st.selectbox("👩‍🏫 Ուսուցիչ", st.session_state.teachers, format_func=lambda x: x.name)

            if selected_teacher:
                df = pd.DataFrame(st.session_state.schedule)
                teacher_df = df[df['Առարկա'].str.contains(f"\\({selected_teacher.name}\\)")]

                if teacher_df.empty:
                    st.warning("⚠️ Դասեր չկան:")
                else:
                    teacher_pivot = teacher_df.pivot(index='Ժամ', columns='Օր', values='Դասարան').fillna("-")
                    for day in DAYS_AM:
                        if day not in teacher_pivot.columns:
                            teacher_pivot[day] = "-"
                    teacher_pivot = teacher_pivot[DAYS_AM]
                    st.dataframe(teacher_pivot, width='stretch')

    elif st.session_state.active_tab == "🤖 AI Օգնական":
        st.title("🤖 AI Օգնական")

        if st.session_state.username not in st.session_state.chat_histories:
            st.session_state.chat_histories[st.session_state.username] = []

        chat_history = st.session_state.chat_histories[st.session_state.username]

        for msg in chat_history:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        if prompt := st.chat_input("Հարցրեք Ձեր դասացուցակի մասին..."):
            with st.chat_message("user"):
                st.markdown(prompt)
            chat_history.append({"role": "user", "content": prompt})

            context = f"Առարկաներ՝ {len(st.session_state.subjects)}, Ուսուցիչներ՝ {len(st.session_state.teachers)}"

            with st.chat_message("assistant"):
                message_placeholder = st.empty()
                try:
                    client = genai.Client(api_key=st.secrets["gemini_key"])
                    response = client.models.generate_content(
                        model='gemini-2.5-flash',
                        contents=f"{context}\n\nՀարց՝ {prompt}",
                    )
                    answer = response.text
                    message_placeholder.markdown(answer)
                    chat_history.append({"role": "assistant", "content": answer})
                except Exception as e:
                    message_placeholder.markdown(f"❌ Սխալ։ {e}")
