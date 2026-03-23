import streamlit as st
import uuid
import random
import pandas as pd
import json
import os
import requests
import time # ⏳ Ավելացրինք անիմացիաների համար
from dataclasses import dataclass, asdict
from typing import List
# --- 📄 PDF-Ի import ---
from fpdf import FPDF
import io

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
    # 🔥 ԱՆԻՄԱՑԻԱ ՊԱՀՊԱՆԵԼԻՍ
    with st.spinner("⏳ Պահպանվում է..."):
        time.sleep(1) # Փոքրիկ դադար անիմացիան ցույց տալու համար
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
    # 🔥 ԱՆԻՄԱՑԻԱ ԶՐՈՅԱՑՆԵԼԻՍ
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
                st.balloons() # 🥳 Գեղեցիկ փուչիկներ
                return
            except Exception:
                pass

        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        st.toast("💥 Բազան զրոյացվեց տեղական ֆայլում:", icon="💣")
        st.balloons()


def manual_refresh():
    # 🔥 ԱՆԻՄԱՑԻԱ ԹԱՐՄԱՑՆԵԼԻՍ
    with st.spinner("🔄 Տվյալները թարմացվում են Cloud-ից..."):
        time.sleep(1.5)
        # Կրկնում ենք load_from_disk-ի տրամաբանությունը
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
st.set_page_config(page_title="Smart Time Table", layout="wide", page_icon="📅")

# 🔥🎨 ԱՎԵԼԱՑՐԻՆՔ ԱՆՀԱՏԱԿԱՆ CSS ՈՃԵՐ ԵՎ ԱՆԻՄԱՑԻԱՆԵՐ
st.markdown("""
<style>
    /* 1. Sidebar-ի սիրունացում */
    [data-testid="stSidebar"] {
        background-color: #1a1c24;
        border-right: 1px solid #343a40;
    }
    [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h3 {
        color: #f8f9fa;
    }
    [data-testid="stSidebar"] .stButton>button {
        border-radius: 20px;
        transition: all 0.3s ease-in-out;
    }
    [data-testid="stSidebar"] .stButton>button:hover {
        transform: scale(1.05);
        box-shadow: 0 4px 15px rgba(255, 255, 255, 0.1);
    }

    /* 2. Հիմնական Աղյուսակների (Dataframe) սիրունացում */
    [data-testid="stDataFrameDataframe"] div table {
        border-radius: 10px;
        overflow: hidden;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
    }
    [data-testid="stDataFrameDataframe"] div table thead tr th {
        background-color: #343a40 !important;
        color: white !important;
    }
    [data-testid="stDataFrameDataframe"] div table tbody tr:hover {
        background-color: #f1f3f5 !important;
    }

    /* 3. Metrics (Վիճակագրություն) սիրունացում */
    [data-testid="stMetricValue"] {
        color: #0d6efd;
        font-weight: bold;
    }
    [data-testid="stMetricLabel"] {
        color: #6c757d;
    }

    /* 4. Expander-ի (Դասարանների) սիրունացում */
    .streamlit-expanderHeader {
        background-color: #e9ecef;
        border-radius: 8px;
        font-weight: bold;
    }

    /* 5. Fade-in Անիմացիա էջը բացելիս */
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(10px); }
        to { opacity: 1; transform: translateY(0); }
    }
    .stApp {
        animation: fadeIn 0.8s ease-in-out;
    }
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
        "active_tab": "📊 Վահանակ" 
    })
    load_from_disk()


# --- 🚪 ԼՈԳԻՆԻ ԷՋ ---
if not st.session_state.logged_in:
    left_col, center_col, right_col = st.columns([1, 2, 1])

    with center_col:
        st.markdown("<h1 style='text-align: center; color: #0d6efd;'>🔐 Մուտք Smart Time Table</h1>", unsafe_allow_html=True)
        
        with st.form("login_form", clear_on_submit=False):
            username_input = st.text_input("Օգտատիրոջ անուն (Username)")
            password_input = st.text_input("Գաղտնաբառ (Password)", type="password")
            
            submit_login = st.form_submit_button("Մուտք գործել", width='stretch', type="primary")
            
        if submit_login:
            user = check_user(username_input, password_input)
            if user:
                st.session_state.logged_in = True
                st.session_state.username = user['username']
                st.session_state.user_role = user['role']
                
                if user['role'] in ['owner', 'admin', 'subject_editor', 'teacher_editor']:
                    st.session_state.active_tab = "📊 Վահանակ"
                else:
                    st.session_state.active_tab = "📂 Վերջին պահպանվածը"

                st.success(f"✅ Բարի գալուստ, {username_input}!")
                st.snow() # ❄️ Գեղեցիկ անիմացիա լոգինից հետո
                time.sleep(1)
                st.rerun()
            else:
                st.error("❌ Սխալ օգտանուն կամ գաղտնաբառ")
                
    st.stop()


# --- 🛠️ ՀԻՄՆԱԿԱՆ ԾՐԱԳԻՐ ---

def get_subj_name(sid):
    return next((s.name for s in st.session_state.subjects if s.id == sid), "Անհայտ")

def get_subj_complexity(sid):
    return next((s.complexity for s in st.session_state.subjects if s.id == sid), 3)


def generate_pdf(schedule_data):
    pdf = FPDF()
    pdf.add_page()
    
    pdf.set_font("Helvetica", style='B', size=14)
    pdf.cell(200, 10, txt="Smart Time Table - School Schedule", ln=True, align='C')
    pdf.ln(10)

    df = pd.DataFrame(schedule_data)
    days_eng = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    
    day_mapping = {
        "Երկուշաբթի": "Monday",
        "Երեքշաբթի": "Tuesday",
        "Չորեքշաբթի": "Wednesday",
        "Հինգշաբթի": "Thursday",
        "Ուրբաթ": "Friday"
    }

    for cls in df['Դասարան'].unique():
        pdf.set_font("Helvetica", style='B', size=12)
        pdf.cell(0, 10, txt=f"Class: {cls}", ln=True)
        pdf.set_font("Helvetica", size=10)
        
        cls_df = df[df['Դասարան'] == cls].copy()
        cls_df['Օր'] = cls_df['Օր'].map(day_mapping)
        cls_df['Առարկա'] = cls_df['Առարկա'].apply(lambda x: x.split(" (")[0])
        
        pivot = cls_df.pivot(index='Ժամ', columns='Օր', values='Առարկա').fillna("-")
        
        pdf.set_font("Helvetica", style='B', size=10)
        pdf.cell(15, 8, "Day", border=1, align='C')
        for day in days_eng:
            pdf.cell(35, 8, day, border=1, align='C')
        pdf.ln()

        pdf.set_font("Helvetica", size=10)
        for hour in pivot.index:
            pdf.cell(15, 8, str(hour), border=1, align='C')
            for day in days_eng:
                val = pivot.loc[hour, day] if day in pivot.columns else "-"
                cell_text = str(val)
                if any(ord(c) > 127 for c in cell_text):
                    cell_text = "Lesson" 
                pdf.cell(35, 8, cell_text[:15], border=1, align='C')
            pdf.ln()
        pdf.ln(10)

    return pdf.output()


st.sidebar.title(f"👤 {st.session_state.username}")
st.sidebar.caption(f"Պաշտոն՝ **{st.session_state.user_role}**")

if st.sidebar.button("🚪 Ելք համակարգից", width='stretch'):
    st.session_state.logged_in = False
    st.rerun()

# 🔥 ԱՆԻՄԱՑԻՈՆ ԿՈՃԱԿ
if st.sidebar.button("🔄 Թարմացնել Cloud-ից", use_container_width=True):
    manual_refresh()

st.sidebar.divider()


def on_page_change():
    st.session_state.active_page = "normal"
    st.session_state.active_tab = st.session_state.nav_radio

available_pages = []

if st.session_state.user_role in ['owner', 'admin']:
    available_pages = ["📊 Վահանակ", "📚 Առարկաներ", "👩‍🏫 Ուսուցիչներ", "🏫 Դասարաններ", "🚀 Գեներացում", "📂 Վերջին պահպանվածը", "👤 Ուսուցչի Անձնական"]
elif st.session_state.user_role == 'subject_editor':
    available_pages = ["📊 Վահանակ", "📚 Առարկաներ", "📂 Վերջին պահպանվածը"]
elif st.session_state.user_role == 'teacher_editor':
    available_pages = ["📊 Վահանակ", "👩‍🏫 Ուսուցիչներ", "📂 Վերջին պահպանվածը"]
else:
    available_pages = ["📂 Վերջին պահպանվածը", "👤 Ուսուցչի Անձնական"]

default_index = 0
if st.session_state.active_tab in available_pages:
    default_index = available_pages.index(st.session_state.active_tab)

page = st.sidebar.radio("Նավիգացիա", available_pages, index=default_index, key="nav_radio", on_change=on_page_change)


st.sidebar.divider()

# 🔥 ԱՆԻՄԱՑԻՈՆ ԿՈՃԱԿ
if st.sidebar.button("💾 Պահպանել Բոլորը", width='stretch', type="primary"):
    save_to_disk()


if st.session_state.user_role == 'owner':
    st.sidebar.divider()
    st.sidebar.markdown("<h3 style='color: #dc3545;'>⚠️ Վտանգավոր Գոտի</h3>", unsafe_allow_html=True)
    confirm_reset = st.sidebar.checkbox("Հաստատում եմ ամբողջական ջնջումը")
    # 🔥 ԱՆԻՄԱՑԻՈՆ ԿԱՐՄԻՐ ԿՈՃԱԿ
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
            new_p = st.text_input("Password")
            
            roles_list = ["user", "subject_editor", "teacher_editor", "admin"]
            new_r = st.selectbox("Դերը", roles_list)
            
            if st.form_submit_button("Ավելացնել Օգտատեր", width='stretch'):
                if new_u and new_p:
                    if not any(u['username'] == new_u for u in st.session_state.users_list):
                        new_user_data = {"username": new_u, "password": new_p, "role": new_r}
                        st.session_state.users_list.append(new_user_data)
                        
                        headers = get_supabase_headers()
                        if headers:
                            try:
                                url = f"{st.secrets['supabase_url']}/rest/v1/users"
                                response = requests.post(url, headers=headers, data=json.dumps(new_user_data))
                                st.toast(f"✅ Օգտատեր {new_u}-ն ավելացվեց Cloud-ում:", icon="👤")
                            except Exception:
                                pass
                        st.rerun()

    st.divider()
    st.subheader("📋 Գրանցված Օգտատերեր")
    
    for i, u in enumerate(st.session_state.users_list):
        # Օգտագործում ենք st.container() գեղեցիկ շրջանակի համար
        with st.container(border=True):
            c1, c2, c3 = st.columns([3, 3, 1])
            c1.markdown(f"👤 **{u['username']}**")
            c2.markdown(f"🎭 Դերը՝ `<span style='color: #0d6efd;'>{u['role']}</span>`", unsafe_allow_html=True)
            
            can_delete = True
            if u['username'] == st.session_state.username or u['role'] == 'owner':
                can_delete = False 
            elif u['role'] == 'admin' and st.session_state.user_role != 'owner':
                can_delete = False
                    
            if can_delete:
                if c3.button("🗑️", key=f"del_user_{i}"):
                    st.session_state.users_list.pop(i)
                    st.toast(f"🗑️ Օգտատերը ջնջվեց:", icon="👨‍⚖️")
                    st.rerun()

elif st.session_state.active_page == "normal":

    if st.session_state.active_tab == "📊 Վահանակ":
        st.title("📊 Ընդհանուր Վիճակագրություն")
        
        # Օգտագործում ենք Columns + Metrics CSS ոճերով
        m1, m2, m3, m4 = st.columns(4)
        m1.metric(label="📚 Առարկաներ", value=len(st.session_state.subjects))
        m2.metric(label="👩‍🏫 Ուսուցիչներ", value=len(st.session_state.teachers))
        m3.metric(label="🏫 Դասարաններ", value=len(st.session_state.classes))
        m4.metric(label="📋 Կապեր/Ժամեր", value=len(st.session_state.assignments))

        st.divider()

        c1, c2 = st.columns(2)
        with c1:
            st.subheader("🏫 Դասարաններ")
            if st.session_state.classes:
                df_cl = pd.DataFrame([{"Դասարան": f"{c.grade}{c.section}"} for c in st.session_state.classes])
                st.dataframe(df_cl, width='stretch', hide_index=True)
            else: st.caption("Դասարաններ գրանցված չեն:")
            
        with c2:
            st.subheader("👩‍🏫 Ուսուցիչներ")
            if st.session_state.teachers:
                df_t = pd.DataFrame([{"Անուն": t.name, "Առարկաներ": len(t.subject_ids)} for t in st.session_state.teachers])
                st.dataframe(df_t, width='stretch', hide_index=True)
            else: st.caption("Ուսուցիչներ գրանցված չեն:")

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
                        st.toast(f"📚 {new_name}-ն ավելացվեց ցանկում:", icon="📝")
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
                            st.toast(f"✅ Առարկան գրանցվեց:", icon="📚")
                            st.rerun()

        st.divider()
        st.subheader("✅ Գրանցված Առարկաներ")
        for i, s in enumerate(st.session_state.subjects):
            with st.container(border=True):
                c1, c2 = st.columns([5,1])
                c1.markdown(f"📖 **{s.name}** | Բարդություն՝ <span style='color: #0d6efd; font-weight: bold;'>{s.complexity}</span>", unsafe_allow_html=True)
                if c2.button("🗑️", key=f"s_{s.id}"):
                    st.session_state.assignments = [a for a in st.session_state.assignments if a.subject_id != s.id]
                    st.session_state.subjects.pop(i)
                    st.toast(f"🗑️ Առարկան ջնջվեց:", icon="📚")
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
                        st.toast(f"👤 {t_name}-ն ավելացվեց ցանկում:", icon="📝")
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
                            st.toast(f"✅ Ուսուցիչը գրանցվեց:", icon="👩‍🏫")
                            st.rerun()

        st.divider()
        st.subheader("✅ Գրանցված Ուսուցիչներ")
        for i, t in enumerate(st.session_state.teachers):
            with st.container(border=True):
                c1, c2 = st.columns([5,1])
                c1.markdown(f"👤 **{t.name}** — <span style='color: #6c757d;'>{', '.join([get_subj_name(sid) for sid in t.subject_ids])}</span>", unsafe_allow_html=True)
                if c2.button("🗑️", key=f"t_{t.id}"):
                    st.session_state.assignments = [a for a in st.session_state.assignments if a.teacher_id != t.id]
                    st.session_state.teachers.pop(i)
                    st.toast(f"🗑️ Ուսուցիչը ջնջվեց:", icon="👩‍🏫")
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
                        st.toast(f"✅ Դասարանը ավելացվեց:", icon="🏫")
                        st.rerun()

        with col2:
            if st.session_state.teachers and st.session_state.classes:
                
                # --- Ուսուցչի ընտրությունը FORM-ից դուրս (Անխաթար տրամաբանություն) ---
                def on_teacher_change():
                    pass # Ստիպում է Rerun լինել Ուսուցչին փոխելիս

                sel_t = st.selectbox(
                    "👩‍🏫 Ընտրեք Ուսուցչին", 
                    st.session_state.teachers, 
                    format_func=lambda x: x.name,
                    key="selected_teacher_box_outside",
                    on_change=on_teacher_change
                )

                # Ֆիլտրում ենք առարկաները
                t_subjs = [sub for sub in st.session_state.subjects if sub.id in sel_t.subject_ids]

                # --- Մնացած ձևաթուղթը ---
                with st.form("as_form_fixed", clear_on_submit=True):
                    st.markdown("### 🔗 Կապել Դասարանին")
                    
                    sel_c = st.selectbox("Դասարան", st.session_state.classes, format_func=lambda x: f"{x.grade}{x.section}")
                    
                    if t_subjs:
                        sel_s = st.selectbox("Առարկա", t_subjs, format_func=lambda x: x.name)
                    else:
                        st.warning(f"⚠️ {sel_t.name}-ն դեռ ոչ մի առարկայի հետ կապված չէ:")
                        sel_s = None

                    hrs = st.number_input("Շաբաթական ժամեր", 1, 10, 2)
                    
                    if st.form_submit_button("Կապել", width='stretch'):
                        if not sel_s:
                            st.error("❌ Առարկա ընտրված չէ:")
                        else:
                            current_hrs = sum(a.lessons_per_week for a in st.session_state.assignments if a.class_id == sel_c.id)
                            
                            subject_already_assigned = any(
                                a.class_id == sel_c.id and a.subject_id == sel_s.id 
                                for a in st.session_state.assignments
                            )

                            if current_hrs + hrs > 35:
                                st.error("❌ Դասարանը չի կարող 35 ժամից ավել ունենալ։")
                            elif subject_already_assigned:
                                st.error(f"⚠️ «{sel_s.name}» առարկան այս դասարանում արդեն ունի դասավանդող ուսուցիչ։")
                            else:
                                st.session_state.assignments.append(Assignment(str(uuid.uuid4()), sel_t.id, sel_s.id, sel_c.id, hrs))
                                st.toast("✅ Կապը ստեղծվեց:", icon="🔗")
                                st.rerun()

        st.divider()
        st.subheader("✅ Շաբաթական Ժամերի Բաշխում")
        for i, a in enumerate(st.session_state.assignments):
            cls_obj = next((c for c in st.session_state.classes if c.id == a.class_id), None)
            t_obj = next((t for t in st.session_state.teachers if t.id == a.teacher_id), None)
            if cls_obj and t_obj:
                with st.container(border=True):
                    c1, c2 = st.columns([5,1])
                    c1.markdown(f"📍 **{cls_obj.grade}{cls_obj.section}** | {get_subj_name(a.subject_id)} | {t_obj.name} | <span style='color: #0d6efd;'>{a.lessons_per_week} ժամ</span>", unsafe_allow_html=True)
                    if c2.button("🗑️", key=f"as_{i}"):
                        st.session_state.assignments.pop(i)
                        st.toast("🗑️ Կապը ջնջվեց:", icon="🔗")
                        st.rerun()

    elif st.session_state.active_tab == "🚀 Գեներացում":
        st.title("🚀 Պրոֆեսիոնալ Գեներացում")
        
        # 🔥 ԱՆԻՄԱՑԻՈՆ ԳԵՆԵՐԱՑՄԱՆ ԿՈՃԱԿ
        if st.button("🔥 Ստեղծել Խելացի Դասացուցակ", width='stretch', type="primary"):
            with st.spinner("🧠 Ալգորիթմը մտածում է... Խնդրում ենք սպասել..."):
                time.sleep(2.5) # Ավելի երկար դադար AI-ի տպավորություն թողնելու համար
                
                final_schedule = []
                teacher_occupancy = {d: {h: set() for h in range(1, 8)} for d in DAYS_AM}
                class_occupancy = {d: {h: set() for h in range(1, 8)} for d in DAYS_AM}

                shuffled_classes = list(st.session_state.classes)
                random.shuffle(shuffled_classes)

                for cls in shuffled_classes:
                    class_fund = []
                    assignments_for_cls = [a for a in st.session_state.assignments if a.class_id == cls.id]
                    for ass in assignments_for_cls:
                        class_fund.extend([ass] * ass.lessons_per_week)
                    
                    class_fund.sort(key=lambda x: get_subj_complexity(x.subject_id), reverse=True)
                    class_day_counts = {d: 0 for d in DAYS_AM}
                    
                    timeout = 0
                    while class_fund and timeout < 3000:
                        timeout += 1
                        min_count = min(class_day_counts.values())
                        lightest_days = [d for d in DAYS_AM if class_day_counts[d] == min_count]
                        best_day = random.choice(lightest_days)
                        
                        if class_day_counts[best_day] >= 7:
                            continue 
                        
                        next_hour = class_day_counts[best_day] + 1
                        chosen_candidate_idx = -1
                        
                        for idx, candidate in enumerate(class_fund):
                            if (candidate.teacher_id not in teacher_occupancy[best_day][next_hour] and 
                                f"{cls.grade}{cls.section}" not in class_occupancy[best_day][next_hour]):
                                chosen_candidate_idx = idx
                                break 

                        if chosen_candidate_idx == -1:
                            continue

                        target = class_fund.pop(chosen_candidate_idx)
                        t_name = next((t.name for t in st.session_state.teachers if t.id == target.teacher_id), "Անհայտ")
                        subj_name = get_subj_name(target.subject_id)
                        
                        final_schedule.append({
                            "Դասարան": f"{cls.grade}{cls.section}",
                            "Օր": best_day, 
                            "Ժամ": next_hour, 
                            "Առարկա": f"{subj_name} ({t_name})" 
                        })
                        
                        teacher_occupancy[best_day][next_hour].add(target.teacher_id)
                        class_occupancy[best_day][next_hour].add(f"{cls.grade}{cls.section}")
                        class_day_counts[best_day] += 1

                st.session_state.schedule = final_schedule
                st.toast("✅ Դասացուցակը պատրաստ է:", icon="🚀")
                st.balloons() # 🥳🥳🥳

        if st.session_state.schedule:
            df = pd.DataFrame(st.session_state.schedule)
            st.subheader("📋 Արդյունքներն ըստ Դասարանների")
            # Օգտագործում ենք st.expander()՝ CSS ոճերով
            for c in df['Դասարան'].unique():
                with st.expander(f"🏫 Դասարան՝ {c}", expanded=True):
                    cls_df = df[df['Դասարան'] == c].copy()
                    cls_df['Առարկա'] = cls_df['Առարկա'].apply(lambda x: x.split(" (")[0])
                    pivot = cls_df.pivot(index='Ժամ', columns='Օր', values='Առարկա').fillna("-")
                    
                    # Ուղղում ենք օրերի հերթականությունը (Pandas-ի թերությունը)
                    existing_days = [day for day in DAYS_AM if day in pivot.columns]
                    if existing_days:
                        pivot = pivot[existing_days]

                    st.dataframe(pivot, width='stretch')

            st.divider()
            pdf_bytes = generate_pdf(st.session_state.schedule)
            st.download_button(
                label="📥 Ներբեռնել PDF (English Only)",
                data=bytes(pdf_bytes),
                file_name="School_Timetable.pdf",
                mime="application/pdf",
                use_container_width=True,
                type="primary"
            )

    elif st.session_state.active_tab == "📂 Վերջին պահպանվածը":
        st.title("📂 Պահպանված Դասացուցակ")
        if st.session_state.schedule:
            df = pd.DataFrame(st.session_state.schedule)
            all_grades = sorted(list(set([c.grade for c in st.session_state.classes])))
            if all_grades:
                sel_grade = st.selectbox("Ընտրեք հոսքը", all_grades)
                for cls in [f"{c.grade}{c.section}" for c in st.session_state.classes if c.grade == sel_grade]:
                    cls_data = df[df['Դասարան'] == cls]
                    if not cls_data.empty:
                        with st.expander(f"🏫 Դասարան՝ {cls}", expanded=True):
                            cls_df_clean = cls_data.copy()
                            cls_df_clean['Առարկա'] = cls_df_clean['Առարկա'].apply(lambda x: x.split(" (")[0])
                            pivot = cls_df_clean.pivot(index='Ժամ', columns='Օր', values='Առարկա').fillna("-")
                            
                            existing_days = [day for day in DAYS_AM if day in pivot.columns]
                            if existing_days:
                                pivot = pivot[existing_days]

                            st.dataframe(pivot, width='stretch')
            else: st.info("Դեռ դասարաններ չկան")
        else: st.info("Պահպանված տվյալներ չկան")

    elif st.session_state.active_tab == "👤 Ուսուցչի Անձնական":
        st.title("👤 Ուսուցչի Շաբաթվա Գրաֆիկ")
        if st.session_state.schedule and st.session_state.teachers:
            df = pd.DataFrame(st.session_state.schedule)
            sel_t = st.selectbox("Ընտրեք ուսուցչին", st.session_state.teachers, format_func=lambda x: x.name)
            t_data = df[df['Առարկա'].str.contains(sel_t.name)]
            if not t_data.empty:
                t_data_clean = t_data.copy()
                t_data_clean['Ցուցադրում'] = t_data_clean['Դասարան'] + " - " + t_data_clean['Առարկա'].apply(lambda x: x.split(" (")[0])
                
                # Pivot
                pivot = t_data_clean.pivot(index='Ժամ', columns='Օր', values='Ցուցադրում').fillna("-")
                
                # Օրերի ճիշտ հերթականություն
                existing_days = [day for day in DAYS_AM if day in pivot.columns]
                if existing_days:
                    pivot = pivot[existing_days]

                st.dataframe(pivot, width='stretch')
            else: st.warning("Այս ուսուցչի համար դեռևս դասեր չկան բաշխված։")
        else: st.info("Դեռևս չկա գեներացված դասացուցակ կամ գրանցված ուսուցիչ։")
