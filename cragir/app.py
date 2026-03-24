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

    st.warning("💾 **ՇԱՏ ԿԱՐԵՎՈՐ:** Ցանկացած փոփոխությունից հետո սեղմեք ձախ մենյուի **«Պահպանել բոլորը»** կոճակը՝ տվյալները ամպային բազայում պահելու համար։")

    if st.button("Հասկանալի է, անցնենք գործի! ✅", use_container_width=True, type="primary"):
        st.rerun()


# --- 🔑 ՏՎՅԱԼՆԵՐԻ ԲԱԶԱՅԻ ԵՎ ԼՈԳԻՆԻ ՖՈՒՆԿՑԻԱՆԵՐ ---

# 👑 Միակ Prime Admin-ը (Owner)
DEFAULT_OWNER = {"username": "armshekyan", "password": "arms567", "role": "owner", "school_id": "prime_admin"}
DAYS_AM = ["Երկուշաբթի", "Երեքշաբթի", "Չորեքշաբթի", "Հինգշաբթի", "Ուրբաթ"]


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


def get_dynamic_filename():
    """Ստեղծում է անհատական JSON ֆայլի անուն ըստ school_id-ի"""
    current_school = st.session_state.get('school_id', 'default_school')
    return f"data_{current_school}.json"


def save_to_disk():
    with st.spinner("⏳ Պահպանվում է..."):
        time.sleep(1)
        current_school = st.session_state.get('school_id', 'default_school')
        dynamic_file = get_dynamic_filename()

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

        # 🌐 1. Պահպանում Supabase-ում
        headers = get_supabase_headers()
        if headers:
            try:
                url = f"{st.secrets['supabase_url']}/rest/v1/timetable_data"
                payload = {"school_id": current_school, "data": data}
                headers["Prefer"] = "resolution=merge-duplicates"
                requests.post(url, headers=headers, data=json.dumps(payload))
                st.toast(f"✅ Տվյալները պահպանվեցին Cloud-ում ({current_school})!", icon="🌐")
                return
            except Exception:
                pass

        # 📁 2. Պահպանում Տեղական JSON-ում
        with open(dynamic_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        st.toast(f"💾 Պահպանվեց տեղական ֆայլում ({dynamic_file})!", icon="📁")


def reset_all_data():
    with st.spinner("🚨 Ամբողջական ջնջում..."):
        time.sleep(2)
        current_school = st.session_state.get('school_id', 'default_school')
        dynamic_file = get_dynamic_filename()

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
                payload = {"school_id": current_school, "data": data}
                headers["Prefer"] = "resolution=merge-duplicates"
                requests.post(url, headers=headers, data=json.dumps(payload))
                st.toast(f"💥 Բազան զրոյացվեց Cloud-ում ({current_school})!", icon="💣")
                st.balloons()
                return
            except Exception:
                pass

        with open(dynamic_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        st.toast(f"💥 Բազան զրոյացվեց տեղական ֆայլում ({dynamic_file})!", icon="💣")
        st.balloons()


def manual_refresh():
    with st.spinner("🔄 Տվյալները թարմացվում են..."):
        time.sleep(1.5)
        current_school = st.session_state.get('school_id', 'default_school')
        dynamic_file = get_dynamic_filename()

        headers = get_supabase_headers()
        if headers:
            try:
                url = f"{st.secrets['supabase_url']}/rest/v1/timetable_data?school_id=eq.{current_school}&select=data"
                response = requests.get(url, headers=headers)
                if response.status_code == 200 and response.json():
                    data = response.json()[0]["data"]
                    parse_data(data)
                    st.toast("✅ Տվյալները թարմ են Cloud-ից:", icon="🔄")
                    st.rerun()
                    return
            except Exception:
                pass

        if os.path.exists(dynamic_file):
            try:
                with open(dynamic_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    parse_data(data)
                    st.toast("✅ Տեղական տվյալները թարմ են:", icon="🔄")
            except Exception:
                pass
    st.rerun()


def load_from_disk():
    current_school = st.session_state.get('school_id', 'default_school')
    dynamic_file = get_dynamic_filename()

    headers = get_supabase_headers()
    if headers:
        try:
            url = f"{st.secrets['supabase_url']}/rest/v1/timetable_data?school_id=eq.{current_school}&select=data"
            response = requests.get(url, headers=headers)
            if response.status_code == 200 and response.json():
                data = response.json()[0]["data"]
                parse_data(data)
                return
        except Exception:
            pass

    if os.path.exists(dynamic_file):
        try:
            with open(dynamic_file, "r", encoding="utf-8") as f:
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
        "school_id": "default_school",         
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
                        st.session_state.school_id = user.get('school_id', 'default_school')
                        
                        st.session_state.show_readme = True 
                        
                        if user['role'] in ['owner', 'admin', 'subject_editor', 'teacher_editor']:
                            st.session_state.active_tab = "📊 Վահանակ"
                        else:
                            st.session_state.active_tab = "📂 Վերջին պահպանվածը"

                        load_from_disk()
                        st.toast(f"🎉 Բարի վերադարձ, {username_input}!", icon="🚀")
                        st.snow() 
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("❌ Սխալ օգտանուն կամ գաղտնաբառ:")
                
    st.stop()


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

active_school = st.session_state.get('school_id', 'Ընդհանուր')
st.sidebar.caption(f"🏫 Դպրոց՝ **{active_school}**")

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
            manual_school_id = ""

            if st.session_state.user_role == 'owner':
                roles_list.append("owner")
                manual_school_id = st.text_input("🏫 School ID (Գրել միայն նոր դպրոցների համար)")

            new_r = st.selectbox("Դերը", roles_list)
            
            if st.form_submit_button("Ավելացնել Օգտատեր", width='stretch'):
                if new_u and new_p:
                    if not any(u['username'] == new_u for u in st.session_state.users_list):
                        
                        if st.session_state.user_role == 'owner' and manual_school_id:
                            final_school_id = manual_school_id
                        else:
                            final_school_id = st.session_state.get('school_id', 'default_school')

                        new_user_data = {
                            "username": new_u, 
                            "password": new_p, 
                            "role": new_r,
                            "school_id": final_school_id
                        }
                        
                        st.session_state.users_list.append(new_user_data)
                        
                        headers = get_supabase_headers()
                        if headers:
                            try:
                                url = f"{st.secrets['supabase_url']}/rest/v1/users"
                                requests.post(url, headers=headers, data=json.dumps(new_user_data))
                                st.toast(f"✅ Օգտատեր {new_u}-ն ավելացվեց Cloud-ում ({final_school_id}):", icon="👤")
                            except Exception:
                                pass
                        st.rerun()

    st.divider()
    st.subheader("📋 Գրանցված Օգտատերեր")
    
    for i, u in enumerate(st.session_state.users_list):
        if st.session_state.user_role != 'owner' and u.get('school_id') != st.session_state.school_id:
            continue

        with st.container(border=True):
            c1, c2, c3 = st.columns([3, 3, 1])
            c1.markdown(f"👤 **{u['username']}** | 🏫 Դպրոց՝ `{u.get('school_id', 'default')}`")
            c2.markdown(f"🎭 Դերը՝ <span style='color: #0d6efd;'>{u['role']}</span>", unsafe_allow_html=True)
            
            can_delete = True
            if u['username'] == st.session_state.username or u['role'] == 'owner':
                can_delete = False 
            elif u['role'] == 'admin' and st.session_state.user_role != 'owner':
                can_delete = False
                    
            if can_delete:
                if c3.button("🗑️", key=f"del_user_{i}"):
                    deleted_username = u['username']
                    
                    # 🌐 1. Ջնջում ենք Supabase SQL բազայից
                    headers = get_supabase_headers()
                    if headers:
                        try:
                            url = f"{st.secrets['supabase_url']}/rest/v1/users?username=eq.{deleted_username}"
                            response = requests.delete(url, headers=headers)
                            if response.status_code in [200, 204]:
                                st.toast(f"✅ {deleted_username}-ն ջնջվեց Cloud-ից:", icon="👨‍⚖️")
                            else:
                                st.error("❌ Չհաջողվեց ջնջել Cloud-ից:")
                        except Exception as e:
                            st.error(f"❌ Սխալ Cloud ջնջման ժամանակ: {e}")

                    # 📁 2. Ջնջում ենք Session ցուցակից
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
            all_subjects_option = Subject(id="all", name="🌐 Բոլոր Առարկաները", complexity=0)
            subject_options = [all_subjects_option] + st.session_state.subjects

            selected_subject_view = st.selectbox(
                "🔍 Ֆիլտրել ըստ առարկայի", 
                subject_options, 
                format_func=lambda x: x.name
            )

            if selected_subject_view.id == "all":
                filtered_teachers = [(i, t) for i, t in enumerate(st.session_state.teachers)]
                st.markdown("📌 **Բոլոր գրանցված ուսուցիչները.**")
            else:
                filtered_teachers = [
                    (i, t) for i, t in enumerate(st.session_state.teachers) 
                    if selected_subject_view.id in t.subject_ids
                ]
                st.markdown(f"📌 **{selected_subject_view.name}** դասավանդող ուսուցիչները.")

            if filtered_teachers:
                for i, t in filtered_teachers:
                    with st.container(border=True):
                        c1, c2 = st.columns([5, 1])
                        subj_names = [get_subj_name(sid) for sid in t.subject_ids]
                        
                        c1.markdown(
                            f"👤 **{t.name}** — <span style='color: #6c757d;'>{', '.join(subj_names)}</span>", 
                            unsafe_allow_html=True
                        )
                        
                        if c2.button("🗑️", key=f"t_view_{i}"):
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
                sel_t = st.selectbox(
                    "👩‍🏫 Ընտրեք Ուսուցչին", 
                    st.session_state.teachers, 
                    format_func=lambda x: x.name,
                    key="selected_teacher_box_outside"
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
                                st.error(f"⚠️ «{sel_s.name}» առարկան այս դասարանում արդեն ունի դասեր:")
                            else:
                                st.session_state.assignments.append(Assignment(str(uuid.uuid4()), sel_t.id, sel_s.id, sel_c.id, hrs))
                                st.toast(f"✅ Կապը հաստատվեց:", icon="🔗")
                                st.rerun()

        st.divider()
        st.subheader("📋 Դասավանդման Կապեր")
        for i, a in enumerate(st.session_state.assignments):
            t_name = next((t.name for t in st.session_state.teachers if t.id == a.teacher_id), "Անհայտ")
            s_name = get_subj_name(a.subject_id)
            c_name = next((f"{c.grade}{c.section}" for c in st.session_state.classes if c.id == a.class_id), "Անհայտ")

            with st.container(border=True):
                c1, c2 = st.columns([5, 1])
                c1.markdown(f"🏫 **{c_name}** | 👩‍🏫 {t_name} — 📖 {s_name} | 🕒 {a.lessons_per_week} ժամ")
                if c2.button("🗑️", key=f"a_{a.id}"):
                    st.session_state.assignments.pop(i)
                    st.toast(f"🗑️ Կապը ջնջվեց:", icon="🔗")
                    st.rerun()

    # --- 🚀 ԷԿՐԱՆ 5: ԳԵՆԵՐԱՑՈՒՄ ---
    elif st.session_state.active_tab == "🚀 Գեներացում":
        st.title("🚀 Գեներացնել Խելացի Դասացուցակ")

        if st.button("🏗️ Ստեղծել Խելացի Դասացուցակ", use_container_width=True, type="primary"):
            with st.spinner("⏳ Ալգորիթմը հաշվարկում է..."):
                time.sleep(2)

                schedule = []
                for cls in st.session_state.classes:
                    cls_assignments = [a for a in st.session_state.assignments if a.class_id == cls.id]
                    
                    pool = []
                    for assign in cls_assignments:
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
                st.balloons()

        if st.session_state.get('schedule'):
            st.divider()
            st.subheader("📊 Արդյունք")
            df_sched = pd.DataFrame(st.session_state.schedule)
            st.dataframe(df_sched, width='stretch', hide_index=True)

            pdf_out = generate_pdf(st.session_state.schedule)
            st.download_button(
                label="📥 Ներբեռնել PDF (English Titles)",
                data=pdf_out,
                file_name="smart_timetable.pdf",
                mime="application/pdf",
                use_container_width=True
            )

    # --- 📂 ԷԿՐԱՆ 6: ՎԵՐՋԻՆ ՊԱՀՊԱՆՎԱԾԸ ---
    elif st.session_state.active_tab == "📂 Վերջին պահպանվածը":
        st.title("📂 Դիտել Գեներացված Դասացուցակը")

        if not st.session_state.get('schedule'):
            st.info("ℹ️ Դեռևս ոչ մի դասացուցակ գեներացված կամ պահպանված չէ:")
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

                st.subheader(f"📅 {selected_class} Դասարանի Դասացուցակը")
                st.dataframe(pivot, width='stretch')

    # --- 👤 ԷԿՐԱՆ 7: ՈՒՍՈՒՑՉԻ ԱՆՁՆԱԿԱՆ ---
    elif st.session_state.active_tab == "👤 Ուսուցչի Անձնական":
        st.title("👤 Ուսուցչի Անձնական Գրաֆիկ")

        if not st.session_state.teachers:
            st.info("ℹ️ Բազայում ուսուցիչներ գրանցված չեն:")
        elif not st.session_state.get('schedule'):
            st.info("ℹ️ Դեռևս ոչ մի դասացուցակ գեներացված չէ:")
        else:
            selected_teacher = st.selectbox("👩‍🏫 Ընտրեք Ձեր անունը", st.session_state.teachers, format_func=lambda x: x.name)

            if selected_teacher:
                df = pd.DataFrame(st.session_state.schedule)
                teacher_df = df[df['Առարկա'].str.contains(f"\\({selected_teacher.name}\\)")]

                if teacher_df.empty:
                    st.warning(f"⚠️ {selected_teacher.name}-ի համար դասեր չեն գտնվել:")
                else:
                    teacher_pivot = teacher_df.pivot(index='Ժամ', columns='Օր', values='Դասարան').fillna("-")
                    for day in DAYS_AM:
                        if day not in teacher_pivot.columns:
                            teacher_pivot[day] = "-"
                    teacher_pivot = teacher_pivot[DAYS_AM]

                    st.subheader(f"📅 {selected_teacher.name}-ի Շաբաթվա Գրաֆիկը")
                    st.dataframe(teacher_pivot, width='stretch')

    # --- 🤖 ԷԿՐԱՆ 8: AI ՕԳՆԱԿԱՆ ---
    elif st.session_state.active_tab == "🤖 AI Օգնական":
        st.title("🤖 Խելացի AI Օգնական")

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

            context = f"""
            Համակարգում առկա տվյալներ՝
            Առարկաներ՝ {len(st.session_state.subjects)}
            Ուսուցիչներ՝ {len(st.session_state.teachers)}
            Դասարաններ՝ {len(st.session_state.classes)}
            
            Դու Smart Time Table-ի ներկառուցված օգնականն ես։ Պատասխանիր հայերեն, կիրառական և օգնող ոճով։
            """

            with st.chat_message("assistant"):
                message_placeholder = st.empty()
                try:
                    client = genai.Client(api_key=st.secrets["gemini_key"])
                    full_prompt = f"{context}\n\nՕգտատիրոջ հարցը՝ {prompt}"
                    
                    response = client.models.generate_content(
                        model='gemini-2.5-flash',
                        contents=full_prompt,
                    )
                    
                    answer = response.text
                    message_placeholder.markdown(answer)
                    chat_history.append({"role": "assistant", "content": answer})
                except Exception as e:
                    error_msg = f"❌ Սխալ API հարցման ժամանակ։ {e}"
                    message_placeholder.markdown(error_msg)
                    chat_history.append({"role": "assistant", "content": error_msg})
