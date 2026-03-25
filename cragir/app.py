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
from google import genai  # ✨ Google-ի պաշտոնական AI գրադարանը

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
        * **Ինչպե՞ս է աշխատում.** Մեկ էջում տեսնում եք, թե քանի՞ առարկա, ուսուցիչ, դասարան և ժամ կա համակարգում։
        """)

    with st.expander("📚 2. Առարկաներ"):
        st.markdown("""
        * **Ֆունկցիան.** Դպրոցում անցնող բոլոր դասերի շտեմարանն է։
        * **Ինչպե՞ս է աշխատում.** Մուտքագրում եք առարկան և նշում դրա **բարդությունը (1-ից 5 բալ)**։ Ծանր առարկաները ալգորիթմը ավտոմատ կդնի օրվա առաջին կեսին։
        """)

    with st.expander("👩‍🏫 3. Ուսուցիչներ"):
        st.markdown("""
        * **Ֆունկցիան.** Դասավանդող անձնակազմի պաշտոնական ցուցակն է։
        * **Ինչպե՞ս է աշխատում.** Գրանցում եք ուսուցչի անունը և բազմակի ընտրությամբ կապում նրան այն առարկաների հետ, որոնք նա դասավանդում է։
        """)

    with st.expander("🏫 4. Դասարաններ և Ժամեր"):
        st.markdown("""
        * **Ֆունկցիան.** Դասացուցակի պլանավորման բաժինն է։
        * **Ինչպե՞ս է աշխատում.** Ստեղծում եք դասարանը (օր.՝ 10-Ա), ընտրում եք ուսուցչին, առարկան և շաբաթական ժամաքանակը (օր.՝ 4 ժամ)։
        """)

    with st.expander("🚀 5. Գեներացում"):
        st.markdown("""
        * **Ֆունկցիան.** Դասացուցակի ավտոմատ հաշվարկման համակարգն է։
        * **Ինչպե՞ս է աշխատում.** Սեղմում եք «Ստեղծել Խելացի Դասացուցակ»։ Ալգորիթմը վերցնում է բոլոր ժամերը և սարքում է անթերի դասացուցակ։ Արդյունքը կարելի է ներբեռնել **PDF** ֆորմատով։
        """)

    with st.expander("📂 6. Վերջին պահպանվածը"):
        st.markdown("""
        * **Ֆունկցիան.** Գեներացված դասացուցակների արխիվային դիտումն է։
        * **Ինչպե՞ս է աշխատում.** Ցանկացած պահի աշակերտները կամ ծնողները կարող են մտնել այս էջ, ընտրել իրենց դասարանը և տեսնել իրենց գրաֆիկը։
        """)

    with st.expander("👤 7. Ուսուցչի Անձնական"):
        st.markdown("""
        * **Ֆունկցիան.** Անհատականացված էջ ուսուցիչների համար։
        * **Ինչպե՞ս է աշխատում.** Ուսուցիչն ընտրում է իր անունը և տեսնում է միայն իր անձնական շաբաթվա գրաֆիկը։
        """)

    with st.expander("🤖 8. AI Օգնական"):
        st.markdown("""
        * **Ֆունկցիան.** Ներկառուցված արհեստական բանականություն։
        * **Ինչպե՞ս է աշխատում.** Կարող եք հարցեր տալ չաթում դասացուցակի վերլուծության համար։ Չաթը անձնական է, այլ օգտատերեր չեն տեսնի Ձեր հարցերը։
        """)

    # 💾 Շատ կարևոր հիշեցում բոլոր քայլերի համար
    st.warning("💾 **ՇԱՏ ԿԱՐԵՎՈՐ:** Ցանկացած փոփոխությունից հետո սեղմեք ձախ մենյուի **«Պահպանել բոլորը»** կոճակը՝ տվյալները ամպային բազայում պահելու համար։")

    if st.button("Հասկանալի է, անցնենք գործի! ✅", use_container_width=True, type="primary"):
        st.rerun()

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


# ✅ ՆՈՐ ԿՈԴԸ (Պատճենիր և դիր հին save_to_disk-ի տեղը)
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

st.markdown("""
<style>
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
    [data-testid="stDataFrameDataframe"] div table {
        border-radius: 10px;
        overflow: hidden;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
    }
    [data-testid="stDataFrameDataframe"] div table thead tr th {
        background-color: #343a40 !important;
        color: white !important;
    }
    [data-testid="stMetricValue"] {
        color: #0d6efd;
        font-weight: bold;
    }
    .streamlit-expanderHeader {
        background-color: #e9ecef;
        border-radius: 8px;
        font-weight: bold;
    }
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
        "active_tab": "📊 Վահանակ",
        "chat_histories": {},  # ✨ Անհատական AI չաթի պատմություններ
        "show_readme": False   # ✨ Թռնող պատուհանի ստուգում
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
                        
                        st.session_state.show_readme = True  # ✨ Ակտիվացնում ենք ինստրուկցիայի պատուհանը
                        
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


# --- 🔔 Թռնող Ինստրուկցիան Լոգինից հետո ---
if st.session_state.get("show_readme", False):
    st.session_state.show_readme = False
    show_instruction_modal()


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
        with st.container(border=True):
            c1, c2, c3 = st.columns([3, 3, 1])
            c1.markdown(f"👤 **{u['username']}**")
            
            # ✅ Գունավոր դերեր `unsafe_allow_html=True`-ով
            c2.markdown(f"🎭 Դերը՝ <span style='color: #0d6efd;'>{u['role']}</span>", unsafe_allow_html=True)
            
            can_delete = True
            if u['username'] == st.session_state.username or u['role'] == 'owner':
                can_delete = False 
            elif u['role'] == 'admin' and st.session_state.user_role != 'owner':
                can_delete = False
                    
            # ✅ Ջնջելու կոճակը ցույց է տրվում ճիշտ (երբ can_delete-ը True է), բայց մնացած տվյալները չեն թաքնվում
            if can_delete:
                if c3.button("🗑️", key=f"del_user_{i}"):
                    st.session_state.users_list.pop(i)
                    st.toast(f"🗑️ Օգտատերը ջնջվեց:", icon="👨‍⚖️")
                    st.rerun()

elif st.session_state.active_page == "normal":

    if st.session_state.active_tab == "📊 Վահանակ":
        st.title("📊 Ընդհանուր Վիճակագրություն")
        
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
        st.subheader("📋 Դիտել Ուսուցիչներն ըստ Առարկաների")

        if st.session_state.subjects and st.session_state.teachers:
            # 1. Առարկաների ցուցակ Selectbox-ի համար (ավելացնում ենք «Բոլորը» տարբերակը)
            all_subjects_option = Subject(id="all", name="🌐 Բոլոր Առարկաները", complexity=0)
            subject_options = [all_subjects_option] + st.session_state.subjects

            selected_subject_view = st.selectbox(
                "🔍 Ֆիլտրել ըստ առարկայի", 
                subject_options, 
                format_func=lambda x: x.name
            )

            # 2. Ֆիլտրում ենք ուսուցիչներին
            if selected_subject_view.id == "all":
                filtered_teachers = [(i, t) for i, t in enumerate(st.session_state.teachers)]
                st.markdown("📌 **Բոլոր գրանցված ուսուցիչները.**")
            else:
                filtered_teachers = [
                    (i, t) for i, t in enumerate(st.session_state.teachers) 
                    if selected_subject_view.id in t.subject_ids
                ]
                st.markdown(f"📌 **{selected_subject_view.name}** դասավանդող ուսուցիչները.")

            # 3. Արտածում ենք ֆիլտրված ուսուցիչներին
            if filtered_teachers:
                for i, t in filtered_teachers:
                    with st.container(border=True):
                        c1, c2 = st.columns([5, 1])
                        
                        # Հավաքում ենք ուսուցչի բոլոր առարկաների անունները
                        subj_names = [get_subj_name(sid) for sid in t.subject_ids]
                        
                        c1.markdown(
                            f"👤 **{t.name}** — <span style='color: #6c757d;'>{', '.join(subj_names)}</span>", 
                            unsafe_allow_html=True
                        )
                        
                        if c2.button("🗑️", key=f"t_view_{i}"):
                            # Ջնջում ենք ուսուցչին նաև կապերից (assignments)
                            st.session_state.assignments = [a for a in st.session_state.assignments if a.teacher_id != t.id]
                            st.session_state.teachers.pop(i)
                            st.toast(f"🗑️ Ուսուցիչը ջնջվեց:", icon="👩‍🏫")
                            st.rerun()
            else:
                st.info(f"ℹ️ {selected_subject_view.name} առարկայի համար դեռ ոչ մի ուսուցիչ չկա գրանցված։")
        else:
            st.info("ℹ️ Դեռևս չկան գրանցված առարկաներ կամ ուսուցիչներ։")
            

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
                
                def on_teacher_change():
                    pass 

                sel_t = st.selectbox(
                    "👩‍🏫 Ընտրեք Ուսուցչին", 
                    st.session_state.teachers, 
                    format_func=lambda x: x.name,
                    key="selected_teacher_box_outside",
                    on_change=on_teacher_change
                )

                t_subjs = [sub for sub in st.session_state.subjects if sub.id in sel_t.subject_ids]

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
        st.subheader("📋 Դիտել Կապերն ըստ Դասարանների")

        if st.session_state.classes and st.session_state.assignments:
            # 1. Սարքում ենք դասարանների ցուցակ Selectbox-ի համար
            class_options = st.session_state.classes
            selected_class_view = st.selectbox(
                "🔍 Ընտրեք դասարանը՝ կապերը տեսնելու համար", 
                class_options, 
                format_func=lambda x: f"{x.grade}{x.section}"
            )

            # 2. Ֆիլտրում ենք կապերը միայն ընտրված դասարանի համար
            filtered_assignments = [
                (i, a) for i, a in enumerate(st.session_state.assignments) 
                if a.class_id == selected_class_view.id
            ]

            if filtered_assignments:
                st.markdown(f"📌 **{selected_class_view.grade}{selected_class_view.section}** դասարանի կապերը.")
                
                # 3. Տպում ենք միայն այս դասարանի կապերը
                for i, a in filtered_assignments:
                    cls_obj = next((c for c in st.session_state.classes if c.id == a.class_id), None)
                    t_obj = next((t for t in st.session_state.teachers if t.id == a.teacher_id), None)
                    
                    if cls_obj and t_obj:
                        with st.container(border=True):
                            c1, c2 = st.columns([5,1])
                            c1.markdown(
                                f"📖 **{get_subj_name(a.subject_id)}** | 👤 {t_obj.name} | "
                                f"<span style='color: #0d6efd;'>{a.lessons_per_week} ժամ</span>", 
                                unsafe_allow_html=True
                            )
                            if c2.button("🗑️", key=f"as_{i}"):
                                st.session_state.assignments.pop(i)
                                st.toast("🗑️ Կապը ջնջվեց:", icon="🔗")
                                st.rerun()
            else:
                st.info(f"ℹ️ {selected_class_view.grade}{selected_class_view.section} դասարանի համար դեռ ոչ մի կապ չկա ստեղծված։")
        else:
            st.info("ℹ️ Դեռևս չկան ստեղծված դասարաններ կամ կապեր։")
            

    elif st.session_state.active_tab == "🚀 Գեներացում":
        st.title("🚀 Պրոֆեսիոնալ Գեներացում")
        
        if st.button("🔥 Ստեղծել Խելացի Դասացուցակ", use_container_width=True, type="primary"):
            if not st.session_state.classes or not st.session_state.assignments:
                st.error("❌ Բացակայում են դասարանները կամ ժամերը գեներացման համար:")
            else:
                with st.spinner("🧠 Ալգորիթմը մտածում է... Խնդրում ենք սպասել..."):
                    time.sleep(2.5) 
                    
                    final_schedule = []
                    # 👩‍🏫 Ուսուցիչների և դասարանների զբաղվածության ստուգման քարտեզ
                    teacher_occupancy = {d: {h: set() for h in range(1, 8)} for d in DAYS_AM}
                    class_occupancy = {d: {h: set() for h in range(1, 8)} for d in DAYS_AM}

                    shuffled_classes = list(st.session_state.classes)
                    random.shuffle(shuffled_classes)

                    success = True

                    for cls in shuffled_classes:
                        class_fund = []
                        assignments_for_cls = [a for a in st.session_state.assignments if a.class_id == cls.id]
                        for ass in assignments_for_cls:
                            class_fund.extend([ass] * ass.lessons_per_week)
                        
                        # ✅ Սորտավորում ենք ըստ բարդության (Քո գրած խելացի մասը)
                        class_fund.sort(key=lambda x: get_subj_complexity(x.subject_id), reverse=True)
                        class_day_counts = {d: 0 for d in DAYS_AM}
                        
                        timeout = 0
                        # 🔄 Գեներացման ցիկլ
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
                                # 🛑 ՍՏՈՒԳՈՒՄ՝ Արդյոք ուսուցիչը կամ դասարանն ազատ են այս ժամին
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
                            
                            # 🔒 Գրանցում ենք զբաղվածությունը
                            teacher_occupancy[best_day][next_hour].add(target.teacher_id)
                            class_occupancy[best_day][next_hour].add(f"{cls.grade}{cls.section}")
                            class_day_counts[best_day] += 1

                        if timeout >= 3000:
                            success = False
                            break

                if success:
                    st.session_state.schedule = final_schedule
                    st.success("🎉 Դասացուցակը հաջողությամբ գեներացվեց:")
                    st.balloons() 
                else:
                    st.error("⚠️ Ալգորիթմը խճճվեց բախումների մեջ։ Փորձեք նորից սեղմել կոճակը կամ թեթևացրեք ժամաքանակը։")

        # 📊 ԱՐԴՅՈՒՆՔՆԵՐԻ ՑՈՒՑԱԴՐՈՒՄ
        if st.session_state.get('schedule'):
            df = pd.DataFrame(st.session_state.schedule)
            st.subheader("📋 Արդյունքներն ըստ Դասարանների")
            
            for c in df['Դասարան'].unique():
                with st.expander(f"🏫 Դասարան՝ {c}", expanded=True):
                    cls_df = df[df['Դասարան'] == c].copy()
                    cls_df['Առարկա'] = cls_df['Առարկա'].apply(lambda x: x.split(" (")[0])
                    pivot = cls_df.pivot(index='Ժամ', columns='Օր', values='Առարկա').fillna("-")
                    
                    existing_days = [day for day in DAYS_AM if day in pivot.columns]
                    if existing_days:
                        # 📆 Դասավորում ենք օրերը ճիշտ հերթականությամբ՝ Երկուշաբթիից Ուրբաթ
                        ordered_days = [d for d in DAYS_AM if d in existing_days]
                        pivot = pivot[ordered_days]

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
                
                pivot = t_data_clean.pivot(index='Ժամ', columns='Օր', values='Ցուցադրում').fillna("-")
                
                existing_days = [day for day in DAYS_AM if day in pivot.columns]
                if existing_days:
                    pivot = pivot[existing_days]

                st.dataframe(pivot, width='stretch')
            else: st.warning("Այս ուսուցչի համար դեռևս դասեր չկան բաշխված։")
        else: st.info("Դեռևս չկա գեներացված դասացուցակ կամ գրանցված ուսուցիչ։")

    elif st.session_state.active_tab == "🤖 AI Օգնական":
        st.title("🤖 AI Օգնական (Gemini)")
        st.caption(f"Բարև, **{st.session_state.username}**! Ես քո անձնական AI օգնականն եմ։")

        # ✨ Յուրաքանչյուր օգտատիրոջ համար ստեղծում ենք իր սեփական պատմությունը
        current_user = st.session_state.username
        if current_user not in st.session_state.chat_histories:
            st.session_state.chat_histories[current_user] = []

        # 1. Արտածում ենք ՄԻԱՅՆ այս օգտատիրոջ նախորդ հաղորդագրությունները
        for message in st.session_state.chat_histories[current_user]:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        # 2. Չաթի մուտքագրման դաշտը
        if prompt := st.chat_input("Ինչպե՞ս կարող եմ օգնել քեզ այսօր։"):
            
            st.session_state.chat_histories[current_user].append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)

            with st.chat_message("assistant"):
                with st.spinner("🧠 Մտածում եմ..."):
                    try:
                        if "GEMINI_API_KEY" not in st.secrets:
                            response_text = "⚠️ API բանալին բացակայում է Streamlit Cloud-ի Secrets-ից:"
                        else:
                            context = f"Դու 'Smart Time Table' պրոյեկտի AI օգնականն ես։ Պատասխանիր հստակ, հայերենով և սեղմ։\n"
                            context += f"Դու խոսում ես {current_user}-ի հետ։\n"
                            if st.session_state.schedule:
                                context += f"Ներկայիս գեներացված դասացուցակը՝ {json.dumps(st.session_state.schedule, ensure_ascii=False)}\n"
                            else:
                                context += "Դեռևս գեներացված դասացուցակ չկա։\n"
                            
                            context += f"Օգտատիրոջ հարցը՝ {prompt}"

                            client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
                            response = client.models.generate_content(
                                model='gemini-2.5-flash',
                                contents=context,
                            )
                            response_text = response.text

                    except Exception as e:
                        response_text = f"❌ Սխալ տեղի ունեցավ API կանչի ժամանակ: {str(e)}"

                    st.markdown(response_text)
                    st.session_state.chat_histories[current_user].append({"role": "assistant", "content": response_text})
