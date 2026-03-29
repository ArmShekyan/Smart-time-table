import streamlit as st
import uuid
import random
import pandas as pd
import json
import os
import requests
import time
import altair as alt  # ✨ Նոր գրադարան սիրուն գրաֆիկների համար
from dataclasses import dataclass, asdict
from typing import List
from fpdf import FPDF
from streamlit_cookies_controller import CookieController
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
class Room:
    id: str
    name: str  # Օրինակ՝ "201", "Ֆիզիկայի լաբորատորիա"
    type: str  # "Ընդհանուր", "Լաբորատոր", "Մարզադահլիճ", "Համակարգչային"
    assigned_class_id: str = None  # Եթե կաբինետը հատուկ դասարանի համար է, այստեղ նշվում է այդ դասարանի ID-ն

@dataclass
class Assignment:
    id: str
    teacher_id: str
    subject_id: str
    class_id: str
    lessons_per_week: int
    room_type: str = "Ընդհանուր"


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
        * **Ինչպե՞ս է աշխատում.** Սեղմում եք «Ստեղծել Խելացի Դասացուցակ»։ Ալգորիթմը վերցնում է բոլոր ժամերը և սարքում է անթերի դասացուցակ։ Արդյունը կարելի է ներբեռնել **PDF** ֆորմատով։
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

DB_FILE = "smart_timetable_final.json"
DAYS_AM = ["Երկուշաբթի", "Երեքշաբթի", "Չորեքշաբթի", "Հինգշաբթի", "Ուրբաթ"]

DEFAULT_OWNER = {"username": "armshekyan", "password": "arms567", "role": "owner"}


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


def save_to_disk(force_overwrite=False):
    """
    Առաջնային պահպանում Supabase-ում, այնուհետև Local backup:
    Smart Merge համակարգը թույլ է տալիս ջնջել տարրը առանց մյուսների տվյալները վնասելու:
    """
    with st.spinner("⏳ Գործընթացը սկսված է..."):
        # 1. Նախապատրաստում ենք տվյալները Local վիճակից
        local_state = {
            "subjects": {s.id: asdict(s) for s in st.session_state.subjects},
            "teachers": {t.id: asdict(t) for t in st.session_state.teachers},
            "classes": {c.id: asdict(c) for c in st.session_state.classes},
            "rooms": {r.id: asdict(r) for r in st.session_state.rooms},
            "assignments": {a.id: asdict(a) for a in st.session_state.assignments},
            "schedule": st.session_state.schedule,
            "subj_pool": list(set(st.session_state.subj_pool)),
            "teacher_pool": list(set(st.session_state.teacher_pool)),
            "users_list": st.session_state.users_list
        }

        headers = get_supabase_headers()
        final_data = None
        cloud_success = False

        # 2. ԱՌԱՋՆԱՅԻՆ: Փորձում ենք պահպանել Supabase-ում
        if headers:
            try:
                # ՄԻՇՏ կարդում ենք Cloud-ի թարմ տվյալները, որպեսզի մյուսների գրածը չկորչի
                url_get = f"{st.secrets['supabase_url']}/rest/v1/timetable_data?id=eq.1&select=data"
                res = requests.get(url_get, headers=headers)
                cloud_data = res.json()[0]["data"] if res.status_code == 200 and res.json() else {}

                if not force_overwrite:
                    # Սովորական Merge (Ավելացման դեպքում)
                    final_data = {
                        "subjects": list({**{s["id"]: s for s in cloud_data.get("subjects", [])}, **local_state["subjects"]}.values()),
                        "teachers": list({**{t["id"]: t for t in cloud_data.get("teachers", [])}, **local_state["teachers"]}.values()),
                        "classes": list({**{c["id"]: c for c in cloud_data.get("classes", [])}, **local_state["classes"]}.values()),
                        "rooms": list({**{r["id"]: r for r in cloud_data.get("rooms", [])}, **local_state["rooms"]}.values()),
                        "assignments": list({**{a["id"]: a for a in cloud_data.get("assignments", [])}, **local_state["assignments"]}.values()),
                        "schedule": local_state["schedule"],
                        "subj_pool": list(set(cloud_data.get("subj_pool", []) + local_state["subj_pool"])),
                        "teacher_pool": list(set(cloud_data.get("teacher_pool", []) + local_state["teacher_pool"])),
                        "users_list": local_state["users_list"]
                    }
                else:
                    # Խելացի Overwrite (Ջնջման դեպքում). 
                    # Միացնում ենք Cloud-ի տվյալները, բայց պահում ենք ՄԻԱՅՆ այն ID-ները, որոնք ջնջված չեն Local-ում
                    def smart_filter(cloud_list, local_dict):
                        # Վերցնում ենք Cloud-ից այն ամենը, ինչը մեր Local-ում էլ կա + նոր բաները, որ մյուսներն են ավելացրել
                        # Բայց բացառում ենք այն, ինչը մենք հենց նոր ջնջեցինք Local-ից
                        merged = {**{item["id"]: item for item in cloud_list}, **local_dict}
                        # Եթե ID-ն չկա local_dict-ում, բայց կա cloud_list-ում, նշանակում է դա ուրիշի ավելացրածն է (պահում ենք)
                        # Եթե ID-ն ջնջել ենք հենց նոր, այն չի լինի local_dict-ում:
                        return list(local_dict.values())

                    # Այս տարբերակը երաշխավորում է, որ քո ջնջածը կջնջվի, բայց մյուսների ավելացրածը Merge կլինի հետո իրենց save-ի ժամանակ
                    final_data = {k: (list(v.values()) if isinstance(v, dict) else v) for k, v in local_state.items()}

                # Բուն պահպանումը Cloud-ում
                url_post = f"{st.secrets['supabase_url']}/rest/v1/timetable_data?id=eq.1"
                payload = {"id": 1, "data": final_data}
                headers["Prefer"] = "resolution=merge-duplicates"
                resp = requests.post(url_post, headers=headers, data=json.dumps(payload))
                
                if resp.status_code in [200, 201, 204]:
                    cloud_success = True
            except Exception as e:
                st.warning(f"⚠️ Supabase-ի հետ կապի խնդիր, կօգտագործվի Local backup: {e}")

        # 3. Եթե Cloud-ը ձախողվեց, ձևավորում ենք տվյալները Local-ի հիման վրա
        if final_data is None:
            final_data = {k: (list(v.values()) if isinstance(v, dict) else v) for k, v in local_state.items()}

        # 4. ՊԱՀՊԱՆՈՒՄ LOCAL ՖԱՅԼՈՒՄ (Միշտ)
        try:
            with open(DB_FILE, "w", encoding="utf-8") as f:
                json.dump(final_data, f, ensure_ascii=False, indent=4)
        except Exception as e:
            st.error(f"❌ Ֆայլի պահպանման սխալ: {e}")

        # 5. Դադար և ծանուցում
        time.sleep(1) 
        
        if cloud_success:
            st.toast("✅ Սինքրոնացվեց Cloud-ում և Local-ում", icon="🌐")
        else:
            st.toast("💾 Պահպանվեց տեղական backup-ում", icon="📁")

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


# 🆕 ՍԱ ԱՅՆ ՖՈՒՆԿՑԻԱՆ Է, ՈՐ ՄԻՅԱՆ ՕԳՏԱՏԵՐԵՐԻՆ Է ԲԵՐՈՒՄ SQL-ԻՑ
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
    st.session_state.rooms = [Room(**r) for r in data.get("rooms", [])] # ✨ ԱՎԵԼԱՑՐՈՒ ԱՅՍ ՏՈՂԸ ԿԱԲԻՆԵՏՆԵՐԻ ՀԱՄԱՐ
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


# 🔥 --- COOKIES ԿԱՌԱՎԱՐԻՉ --- 🔥
cookies = CookieController()

if "subjects" not in st.session_state:
    st.session_state.update({
        "subjects": [], 
        "teachers": [], 
        "classes": [], 
        "rooms": [],  # ✨ Ավելացրու այս տողը կաբինետների համար
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

# 🔥 --- COOKIE-Ի ՍՏՈՒԳՈՒՄ ՍԿԶԲՆԱՄԱՍՈՒՄ (Refresh-ի համար) --- 🔥
if not st.session_state.logged_in:
    saved_user = cookies.get("saved_username")
    saved_role = cookies.get("saved_role")
    
    if saved_user and saved_role:
        st.session_state.logged_in = True
        st.session_state.username = saved_user
        st.session_state.user_role = saved_role
        
        if saved_role in ['owner', 'admin', 'subject_editor', 'teacher_editor']:
            st.session_state.active_tab = "📊 Վահանակ"
        else:
            st.session_state.active_tab = "📂 Վերջին պահպանվածը"


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
                password_input = st.text_input("🔒 Գաղտնաբառ", type="password", placeholder="Ներմուծեք ձեր գաղտնաբառը")
                
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
                        
                        # 🔥 ՊԱՀՈՒՄ ԵՆՔ ՏՎՅԱԼՆԵՐԸ COOKIE-ՈՒՄ 🔥
                        cookies.set("saved_username", user['username'])
                        cookies.set("saved_role", user['role'])
                        
                        st.session_state.show_readme = True 
                        
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
        # 1. Հեռացնում ենք հին փակագծերը (ուսուցչի անունը)
        cls_df['Առարկա'] = cls_df['Առարկա'].apply(lambda x: str(x).split(" (")[0])

        # 2. Ավելացնում ենք սենյակը՝ ստուգելով, որ այն դատարկ չլինի
        # Ստուգում ենք՝ արդյոք 'Սենյակ' սյունակը գոյություն ունի DataFrame-ում
        if 'Սենյակ' in cls_df.columns:
            cls_df['Առարկա'] = cls_df['Առարկա'].astype(str) + " [" + cls_df['Սենյակ'].fillna("-").astype(str) + "]"
        else:
            # Եթե չկա (հին տվյալներ են), ուղղակի թողնում ենք առարկան
            cls_df['Առարկա'] = cls_df['Առարկա'].astype(str)
        
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

# 🔥 --- ՓՈՓՈԽՎԱԾ ԵԼՔԻ ԿՈՃԱԿԸ (ՋՆՋՈՒՄ Է COOKIE-ՆԵՐԸ) --- 🔥
if st.sidebar.button("🚪 Ելք համակարգից", use_container_width=True):
    st.sidebar.info("Դուրս եք գալիս համակարգից... ⏳")

    cookies.remove("saved_username")
    cookies.remove("saved_role")

    st.session_state.logged_in = False
    st.session_state.username = ""
    st.session_state.user_role = ""
    
    time.sleep(1.5)
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


# 🆕 ԹՌՆՈՂ ՊԱՏՈՒՀԱՆ՝ ՕԳՏԱՏԵՐ ՋՆՋԵԼՈՒ ՀԱՄԱՐ
@st.dialog("🗑️ Հաստատեք ջնջումը")
def confirm_delete_user_modal(idx):
    target_user = st.session_state.users_list[idx]
    st.warning(f"⚠️ Դուք համոզվա՞ծ եք, որ ուզում եք ջնջել **{target_user['username']}** օգտատիրոջը։")
    st.markdown("Այս գործողությունը կջնջի նրան թե՛ այս ցուցակից և թե՛ SQL Cloud բազայից։")
    
    col_l, col_r = st.columns(2)
    
    if col_l.button("Այո, Ջնջել ✅", use_container_width=True, type="primary"):
        headers = get_supabase_headers()
        if headers:
            try:
                base_url = st.secrets['supabase_url'].strip("/")
                delete_url = f"{base_url}/rest/v1/users?username=eq.{target_user['username']}"
                requests.delete(delete_url, headers=headers)
                st.toast(f"✅ {target_user['username']}-ն ջնջվեց Cloud-ից:", icon="☁️")
            except Exception:
                st.error("❌ Սխալ տեղի ունեցավ SQL-ից ջնջելիս:")

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
            
            roles_list = ["user", "subject_editor", "teacher_editor", "admin"]
            new_r = st.selectbox("Դերը", roles_list)
            
            if st.form_submit_button("Ավելացնել Օգտատեր", use_container_width=True):
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
    
    # 🆕 ԿՈՃԱԿ՝ ՄԻԱՅՆ ՕԳՏԱՏԵՐԵՐԻ ՑՈՒՑԱԿԸ SQL-ԻՑ ԹԱՐՄԱՑՆԵԼՈՒ ՀԱՄԱՐ
    if st.button("🔄 Թարմացնել Ցուցակը (Կարդալ SQL բազայից)", use_container_width=True):
        refresh_users_only()

    st.subheader("📋 Գրանցված Օգտատերեր")
    
    for i, u in enumerate(st.session_state.users_list):
        with st.container(border=True):
            c1, c2, c3 = st.columns([3, 3, 1])
            c1.markdown(f"👤 **{u['username']}**")
            
            c2.markdown(f"🎭 Դերը՝ <span style='color: #0d6efd;'>{u['role']}</span>", unsafe_allow_html=True)
            
            can_delete = True
            if u['username'] == st.session_state.username or u['role'] == 'owner':
                can_delete = False 
            elif u['role'] == 'admin' and st.session_state.user_role != 'owner':
                can_delete = False
                    
            if can_delete:
                if c3.button("🗑️", key=f"del_user_{i}"):
                    confirm_delete_user_modal(i)

elif st.session_state.active_page == "normal":

    # 🔥 --- ՓՈՓՈԽՎԱԾ ՎԱՀԱՆԱԿԻ ԷՋ (ՖԻԼՏՐՈՎ ԵՎ ALTAIR ԳՐԱՖԻԿՆԵՐՈՎ) --- 🔥
    if st.session_state.active_tab == "📊 Վահանակ":
        st.title("📊 Ընդհանուր Վիճակագրություն")
        
        m1, m2, m3, m4 = st.columns(4)
        m1.metric(label="📚 Առարկաներ", value=len(st.session_state.subjects))
        m2.metric(label="👩‍🏫 Ուսուցիչներ", value=len(st.session_state.teachers))
        m3.metric(label="🏫 Դասարաններ", value=len(st.session_state.classes))
        m4.metric(label="📋 Կապեր/Ժամեր", value=len(st.session_state.assignments))

        st.divider()

        st.subheader("📈 Տվյալների Վերլուծություն")

        # 🏫 Դասարանի ընտրության դաշտ (Ֆիլտր)
        if st.session_state.classes:
            class_options = ["🌐 Բոլոր դասարանները"] + [f"{c.grade}{c.section}" for c in st.session_state.classes]
            selected_class = st.selectbox("🔍 Ընտրեք դասարանը՝ գրաֆիկները ֆիլտրելու համար", class_options)
        else:
            selected_class = "🌐 Բոլոր դասարանները"

        st.markdown("<br>", unsafe_allow_html=True)

        # Ֆիլտրում ենք կապերը (assignments) ըստ ընտրված դասարանի
        filtered_assignments = st.session_state.assignments
        if selected_class != "🌐 Բոլոր դասարանները":
            selected_class_obj = next((c for c in st.session_state.classes if f"{c.grade}{c.section}" == selected_class), None)
            if selected_class_obj:
                filtered_assignments = [a for a in st.session_state.assignments if a.class_id == selected_class_obj.id]

        col_chart1, col_chart2 = st.columns(2)

        with col_chart1:
            st.markdown("#### 👩‍🏫 Ուսուցիչների Շաբաթական Ժամերը")
            if filtered_assignments and st.session_state.teachers:
                teacher_hours = {}
                for assign in filtered_assignments:
                    t_name = next((t.name for t in st.session_state.teachers if t.id == assign.teacher_id), "Անհայտ")
                    teacher_hours[t_name] = teacher_hours.get(t_name, 0) + assign.lessons_per_week

                df_t_hours = pd.DataFrame(list(teacher_hours.items()), columns=["Ուսուցիչ", "Ժամերի Քանակ"])
                df_t_hours = df_t_hours.sort_values(by="Ժամերի Քանակ", ascending=False)

                # ✨ Հորիզոնական անուններով գրաֆիկ (Altair-ով)
                chart_t = alt.Chart(df_t_hours).mark_bar(color='#1f77b4').encode(
                    x=alt.X('Ուսուցիչ:N', sort=None, axis=alt.Axis(labelAngle=0)), # labelAngle=0 ստիպում է մնալ հորիզոնական
                    y=alt.Y('Ժամերի Քանակ:Q')
                ).properties(height=350)
                st.altair_chart(chart_t, use_container_width=True)
            else:
                st.info("ℹ️ Այս դասարանի համար կապեր ստեղծված չեն։")

        with col_chart2:
            st.markdown("#### 📚 Առարկաների Բաշխվածությունը")
            if filtered_assignments and st.session_state.subjects:
                subj_hours = {}
                for assign in filtered_assignments:
                    s_name = next((s.name for s in st.session_state.subjects if s.id == assign.subject_id), "Անհայտ")
                    subj_hours[s_name] = subj_hours.get(s_name, 0) + assign.lessons_per_week

                df_s_hours = pd.DataFrame(list(subj_hours.items()), columns=["Առարկա", "Ընդհանուր Ժամեր"])
                df_s_hours = df_s_hours.sort_values(by="Ընդհանուր Ժամեր", ascending=False)

                # ✨ Հորիզոնական անուններով գրաֆիկ (Altair-ով)
                chart_s = alt.Chart(df_s_hours).mark_bar(color='#ff7f0e').encode(
                    x=alt.X('Առարկա:N', sort=None, axis=alt.Axis(labelAngle=0)), # labelAngle=0 ստիպում է մնալ հորիզոնական
                    y=alt.Y('Ընդհանուր Ժամեր:Q')
                ).properties(height=350)
                st.altair_chart(chart_s, use_container_width=True)
            else:
                st.info("ℹ️ Այս դասարանի համար առարկաներ չկան։")

        st.divider()

        c1, c2 = st.columns(2)
        with c1:
            st.subheader("🏫 Դասարաններ")
            if st.session_state.classes:
                df_cl = pd.DataFrame([{"Դասարան": f"{c.grade}{c.section}"} for c in st.session_state.classes])
                st.dataframe(df_cl, use_container_width=True, hide_index=True)
            else: st.caption("Դասարաններ գրանցված չեն:")
            
        with c2:
            st.subheader("👩‍🏫 Ուսուցիչներ")
            if st.session_state.teachers:
                df_t = pd.DataFrame([{"Անուն": t.name, "Առարկաներ": len(t.subject_ids)} for t in st.session_state.teachers])
                st.dataframe(df_t, use_container_width=True, hide_index=True)
            else: st.caption("Ուսուցիչներ գրանցված չեն:")


    elif st.session_state.active_tab == "📚 Առարկաներ":
        st.title("📚 Առարկաների Շտեմարան")
        
        col_l, col_r = st.columns([1, 1])
        
        # --- ՁԱԽ ՍՅՈՒՆ: Ավելացնել Subject Pool-ում ---
        with col_l:
            with st.form("add_to_pool", clear_on_submit=True):
                st.markdown("### 🆕 Ավելացնել ցուցակում")
                new_name = st.text_input("Առարկայի անուն").strip()
                
                if st.form_submit_button("Ավելացնել ցանկում", use_container_width=True):
                    if new_name:
                        # Ստուգում ենք կրկնությունը Pool-ում (բոլորը սարքում ենք փոքրատառ ստուգելիս)
                        if new_name.lower() in [name.lower() for name in st.session_state.subj_pool]:
                            st.error(f"❌ '{new_name}' առարկան արդեն կա ցուցակում:")
                        else:
                            st.session_state.subj_pool.append(new_name)
                            save_to_disk()  # Պահպանում ենք թարմացված Pool-ը
                            st.toast(f"📚 {new_name}-ն ավելացվեց ցանկում:", icon="📝")
                            st.rerun()
                    else:
                        st.warning("⚠️ Մուտքագրեք անունը:")

        # --- ԱՋ ՍՅՈՒՆ: Գրանցել Առարկան (Բարդության հետ) ---
        with col_r:
            if st.session_state.subj_pool:
                with st.form("register_subj", clear_on_submit=True):
                    st.markdown("### 📋 Գրանցել Առարկան")
                    selected = st.selectbox("Ընտրեք ցանկից", st.session_state.subj_pool)
                    comp = st.select_slider("Բարդություն (1-5)", options=[1, 2, 3, 4, 5], value=3)
                    
                    if st.form_submit_button("Գրանցել", use_container_width=True):
                        # Ստուգում ենք կրկնությունը արդեն գրանցված առարկաների մեջ
                        if any(s.name.lower() == selected.lower() for s in st.session_state.subjects):
                            st.error(f"❌ {selected} առարկան արդեն գրանցված է:")
                        else:
                            new_subject = Subject(id=str(uuid.uuid4()), name=selected, complexity=comp)
                            st.session_state.subjects.append(new_subject)
                            save_to_disk()  # Սինքրոնացնում ենք Cloud-ի և Local-ի հետ
                            st.toast(f"✅ Առարկան գրանցվեց:", icon="📚")
                            st.rerun()

        st.divider()
        st.subheader("✅ Գրանցված Առարկաներ")
        
        # --- ԳՐԱՆՑՎԱԾ ԱՌԱՐԿԱՆԵՐԻ ՑՈՒՑԱԿ ---
        if st.session_state.subjects:
            # enumerate-ի փոխարեն օգտագործում ենք սովորական loop, որպեսզի pop-ի հետ խնդիր չլինի
            for s in st.session_state.subjects:
                with st.container(border=True):
                    c1, c2 = st.columns([5, 1])
                    c1.markdown(
                        f"📖 **{s.name}** | Բարդություն՝ <span style='color: #0d6efd; font-weight: bold;'>{s.complexity}</span>", 
                        unsafe_allow_html=True
                    )
                    
                    if c2.button("🗑️", key=f"s_{s.id}"):
                        # 1. Ջնջում ենք կապված assignments-ները
                        st.session_state.assignments = [a for a in st.session_state.assignments if a.subject_id != s.id]
                        
                        # 2. Ջնջում ենք առարկան հիմնական ցուցակից
                        st.session_state.subjects = [subj for subj in st.session_state.subjects if subj.id != s.id]
                        
                        # 3. Պահպանում ենք (ջնջման դեպքում force_overwrite=True)
                        save_to_disk(force_overwrite=True)
                        
                        st.toast(f"🗑️ Առարկան ջնջվեց:", icon="📚")
                        st.rerun()
        else:
            st.info("ℹ️ Դեռևս չկան գրանցված առարկաներ:")


    elif st.session_state.active_tab == "👩‍🏫 Ուսուցիչներ":
        st.title("👩‍🏫 Ուսուցիչների Շտեմարան")
    
        col_l, col_r = st.columns([1, 1])
        
        # --- ՁԱԽ ՍՅՈՒՆ: Ավելացնել Teacher Pool-ում ---
        with col_l:
            with st.form("add_t_pool", clear_on_submit=True):
                st.markdown("### 🆕 Ավելացնել ցուցակում")
                t_name = st.text_input("Ուսուցչի անուն").strip()
                
                if st.form_submit_button("Ավելացնել ցանկում", use_container_width=True):
                    if t_name:
                        # Ստուգում ենք կրկնությունը teacher_pool-ում
                        if t_name.lower() in [name.lower() for name in st.session_state.teacher_pool]:
                            st.error(f"❌ '{t_name}' անունով ուսուցիչ արդեն կա ցուցակում:")
                        else:
                            st.session_state.teacher_pool.append(t_name)
                            save_to_disk()  # Պահպանում ենք նոր անունը
                            st.toast(f"👤 {t_name}-ն ավելացվեց ցանկում", icon="📝")
                            st.rerun()
                    else:
                        st.warning("⚠️ Մուտքագրեք անունը:")

        # --- ԱՋ ՍՅՈՒՆ: Գրանցել Ուսուցչին (Առարկաների հետ) ---
        with col_r:
            if st.session_state.teacher_pool and st.session_state.subjects:
                with st.form("register_teacher", clear_on_submit=True):
                    st.markdown("### 📋 Գրանցել Ուսուցչին")
                    sel_t = st.selectbox("Ընտրեք ուսուցչին", st.session_state.teacher_pool)
                    sel_subjs = st.multiselect("Ընտրեք առարկաները", st.session_state.subjects, format_func=lambda x: x.name)
                    
                    if st.form_submit_button("Գրանցել", use_container_width=True):
                        # Ստուգում ենք կրկնությունը հիմնական Teachers ցուցակում
                        if any(t.name.lower() == sel_t.lower() for t in st.session_state.teachers):
                            st.error(f"❌ {sel_t}-ն արդեն գրանցված է որպես ուսուցիչ:")
                        elif not sel_subjs:
                            st.warning("⚠️ Ընտրեք առնվազն մեկ առարկա:")
                        else:
                            new_teacher = Teacher(id=str(uuid.uuid4()), name=sel_t, subject_ids=[s.id for s in sel_subjs])
                            st.session_state.teachers.append(new_teacher)
                            save_to_disk()  # Պահպանում ենք գրանցումը
                            st.toast(f"✅ Ուսուցիչը գրանցվեց", icon="👩‍🏫")
                            st.rerun()

        st.divider()
        st.subheader("📋 Դիտել Ուսուցիչներն ըստ Առարկաների")

        # --- ՈՒՍՈՒՑԻՉՆԵՐԻ ՑՈՒՑԱԿ ԵՎ ՖԻԼՏՐԱՑԻԱ ---
        if st.session_state.subjects and st.session_state.teachers:
            all_subjects_option = Subject(id="all", name="🌐 Բոլոր Առարկաները", complexity=0)
            subject_options = [all_subjects_option] + st.session_state.subjects

            selected_subject_view = st.selectbox(
                "🔍 Ֆիլտրել ըստ առարկայի", 
                subject_options, 
                format_func=lambda x: x.name
            )

            # Ֆիլտրման տրամաբանություն
            if selected_subject_view.id == "all":
                filtered_teachers = [(i, t) for i, t in enumerate(st.session_state.teachers)]
                st.markdown("📌 **Բոլոր գրանցված ուսուցիչները.**")
            else:
                filtered_teachers = [
                    (i, t) for i, t in enumerate(st.session_state.teachers) 
                    if selected_subject_view.id in t.subject_ids
                ]
                st.markdown(f"📌 **{selected_subject_view.name}** դասավանդող ուսուցիչները.")

            # Ուսուցիչների քարտերը
            if filtered_teachers:
                for i, t in filtered_teachers:
                    with st.container(border=True):
                        c1, c2 = st.columns([5, 1])
                        
                        subj_names = [get_subj_name(sid) for sid in t.subject_ids]
                        
                        c1.markdown(
                            f"👤 **{t.name}** — <span style='color: #6c757d;'>{', '.join(subj_names)}</span>", 
                            unsafe_allow_html=True
                        )
                        
                        if c2.button("🗑️", key=f"t_view_{t.id}"): # Օգտագործում ենք t.id կրկնությունից խուսափելու համար
                            # Ջնջում ենք կապված assignments-ները
                            st.session_state.assignments = [a for a in st.session_state.assignments if a.teacher_id != t.id]
                            # Ջնջում ենք ուսուցչին
                            st.session_state.teachers = [teacher for teacher in st.session_state.teachers if teacher.id != t.id]
                            # Պահպանում ենք (ջնջման դեպքում force_overwrite=True)
                            save_to_disk(force_overwrite=True)
                            st.toast(f"🗑️ Ուսուցիչը ջնջվեց", icon="👩‍🏫")
                            st.rerun()
            else:
                st.info(f"ℹ️ {selected_subject_view.name} առարկայի համար դեռ ոչ մի ուսուցիչ չկա գրանցված։")
        else:
            st.info("ℹ️ Դեռևս չկան գրանցված առարկաներ կամ ուսուցիչներ։")
            

    elif st.session_state.active_tab == "🏫 Դասարաններ":
        st.title("🏫 Դասարաններ և Ժամեր")

        # --- 1. ԿԱԲԻՆԵՏՆԵՐԻ ԲԱԺԻՆ ---
        with st.expander("🏢 Կաբինետների Կառավարում"):
            if not st.session_state.classes:
                st.warning("⚠️ Սենյակ ավելացնելու համար նախ ստեղծեք գոնե մեկ դասարան:")
            else:
                with st.form("room_add_form", clear_on_submit=True):
                    st.markdown("### 🆕 Նոր Կաբինետ")
                    c_r1, c_r2, c_r3 = st.columns([2, 2, 2])
                    
                    r_name = c_r1.text_input("Կաբինետի անուն/համար").strip()
                    r_type = c_r2.selectbox("Կաբինետի տիպ", ["Ընդհանուր", "Լաբորատոր", "Մարզադահլիճ", "Համակարգչային"])
                    r_class = c_r3.selectbox(
                        "Որ դասարանի համար է", 
                        st.session_state.classes, 
                        format_func=lambda x: f"{x.grade}{x.section}"
                    )
                    
                    if st.form_submit_button("➕ Ավելացնել Կաբինետ", use_container_width=True):
                        if r_name:
                            # Ստուգում ենք կաբինետի կրկնությունը
                            if r_name.lower() in [room.name.lower() for room in st.session_state.rooms]:
                                st.error(f"❌ '{r_name}' կաբինետն արդեն գոյություն ունի:")
                            else:
                                import uuid
                                new_room = Room(id=str(uuid.uuid4()), name=r_name, type=r_type, assigned_class_id=r_class.id)
                                st.session_state.rooms.append(new_room)
                                save_to_disk()
                                st.toast(f"📍 {r_name} կաբինետն ավելացվեց", icon="✅")
                                st.rerun()
                        else:
                            st.warning("⚠️ Խնդրում ենք մուտքագրել կաբինետի անունը:")

            # Գոյություն ունեցող կաբինետների ցուցակը
            if st.session_state.rooms:
                st.write("---")
                st.markdown("#### 📋 Գոյություն ունեցող կաբինետներ")
                for r in st.session_state.rooms:
                    c_obj = next((c for c in st.session_state.classes if c.id == r.assigned_class_id), None)
                    c_name = f"{c_obj.grade}{c_obj.section}" if c_obj else "Անհայտ"
                    
                    col_info, col_del = st.columns([5, 1])
                    col_info.markdown(f"📍 **{r.name}** ({r.type}) — 🏫 {c_name}")
                    
                    if col_del.button("🗑️", key=f"del_room_btn_{r.id}"):
                        st.session_state.rooms = [room for room in st.session_state.rooms if room.id != r.id]
                        save_to_disk(force_overwrite=True) 
                        st.toast(f"🗑️ {r.name} կաբինետը հեռացվեց", icon="🏢")
                        st.rerun()

        st.divider() 
        
        # --- 2. ԴԱՍԱՐԱՆՆԵՐԻ ՍՏԵՂԾՈՒՄ ԵՎ ԿԱՊԵՐ ---
        col1, col2 = st.columns(2)
        
        with col1:
            with st.form("class_form", clear_on_submit=True):
                st.markdown("### 🆕 Նոր Դասարան")
                g = st.text_input("Հոսք (օր. ԱԲ)").strip()
                s = st.text_input("Թիվ/Տառ (օր. 1 կամ Ա)").strip()
                
                if st.form_submit_button("Ավելացնել", use_container_width=True):
                    if g and s:
                        new_class_full_name = f"{g}{s}".lower()
                        existing_classes = [f"{c.grade}{c.section}".lower() for c in st.session_state.classes]
                        
                        if new_class_full_name in existing_classes:
                            st.error(f"❌ {g}{s} դասարանն արդեն գոյություն ունի:")
                        else:
                            import uuid
                            st.session_state.classes.append(ClassGroup(str(uuid.uuid4()), g, s))
                            save_to_disk()
                            st.toast(f"🏫 {g}{s} դասարանը ստեղծվեց", icon="✅")
                            st.rerun()
                    else:
                        st.warning("⚠️ Լրացրեք երկու դաշտն էլ:")

        with col2:
            if st.session_state.teachers and st.session_state.classes:
                sel_t = st.selectbox("👩‍🏫 Ընտրեք Ուսուցչին", st.session_state.teachers, format_func=lambda x: x.name, key="t_sel_main")
                
                # Ուսուցչի առարկաները
                all_teacher_subjs = [sub for sub in st.session_state.subjects if sub.id in sel_t.subject_ids]

                with st.form("as_form", clear_on_submit=True):
                    st.markdown("### 🔗 Կապել Դասարանին")
                    sel_c = st.selectbox("Դասարան", st.session_state.classes, format_func=lambda x: f"{x.grade}{x.section}")
                    
                    # Ֆիլտրում ենք այն առարկաները, որոնք այս դասարանում դեռ ուսուցիչ չունեն
                    assigned_subject_ids = [a.subject_id for a in st.session_state.assignments if a.class_id == sel_c.id]
                    available_subjs = [s for s in all_teacher_subjs if s.id not in assigned_subject_ids]

                    if available_subjs:
                        sel_s = st.selectbox("Առարկա", available_subjs, format_func=lambda x: x.name)
                    else:
                        st.warning(f"⚠️ Այս ուսուցչի բոլոր առարկաներն արդեն նշանակված են {sel_c.grade}{sel_c.section}-ում")
                        sel_s = None

                    hrs = st.number_input("Շաբաթական ժամեր", 1, 15, 2)

                    # ✨ ԿԱԲԻՆԵՏՆԵՐԻ ՖԻԼՏՐՈՒՄ. Ցույց տալ միայն այս դասարանին կցված սենյակները
                    # Եթե կոնկրետ սենյակ չկա, թույլ ենք տալիս ընտրել "Ընդհանուր"
                    class_rooms = [r for r in st.session_state.rooms if r.assigned_class_id == sel_c.id]
                    
                    if class_rooms:
                        sel_room_obj = st.selectbox(
                            "📍 Ընտրեք Կաբինետը", 
                            class_rooms, 
                            format_func=lambda x: f"{x.name} ({x.type})"
                        )
                        final_room_name = sel_room_obj.name
                    else:
                        st.info("ℹ️ Այս դասարանը սեփական կաբինետ չունի:")
                        final_room_name = "Ընդհանուր"
                        st.caption("Կօգտագործվի ընդհանուր դասասենյակ:")

                    if st.form_submit_button("Կապել", use_container_width=True):
                        if sel_s:
                            import uuid
                            # Ստեղծում ենք նոր Assignment
                            new_ass = Assignment(
                                id=str(uuid.uuid4()), 
                                teacher_id=sel_t.id, 
                                subject_id=sel_s.id, 
                                class_id=sel_c.id, 
                                lessons_per_week=hrs, 
                                room_type=final_room_name  # Այստեղ արդեն պահվում է կոնկրետ սենյակի անունը
                            )
                            st.session_state.assignments.append(new_ass)
                            save_to_disk()
                            st.toast(f"🔗 {sel_s.name}-ը կապվեց {sel_c.grade}{sel_c.section}-ին", icon="✅")
                            st.rerun()

        # --- 3. ԴԻՏԵԼ ԿԱՊԵՐԸ ---
        st.divider() 
        st.markdown("### 📋 Դիտել Կապերը")
        
        if st.session_state.classes:
            view_c = st.selectbox("🔍 Ընտրեք դասարանը", st.session_state.classes, format_func=lambda x: f"{x.grade}{x.section}", key="v_bot_view")
            filtered = [a for a in st.session_state.assignments if a.class_id == view_c.id]
            
            if filtered:
                for a in filtered:
                    t_obj = next((t for t in st.session_state.teachers if t.id == a.teacher_id), None)
                    s_obj = next((s for s in st.session_state.subjects if s.id == a.subject_id), None)
                    
                    with st.container(border=True):
                        c1, c2 = st.columns([5, 1])
                        c1.markdown(f"🔹 **{s_obj.name if s_obj else 'Անհայտ'}** — {t_obj.name if t_obj else 'Ուսուցիչ'} — `{a.lessons_per_week}ժ` — *{a.room_type}*")
                        
                        if c2.button("🗑️", key=f"del_as_btn_{a.id}"):
                            st.session_state.assignments = [x for x in st.session_state.assignments if x.id != a.id]
                            save_to_disk(force_overwrite=True) 
                            st.rerun()
            else:
                st.info(f"ℹ️ **{view_c.grade}{view_c.section}** դասարանի համար դեռևս կապեր չկան:")
            

    elif st.session_state.active_tab == "🚀 Գեներացում":
        st.title("🚀 Պրոֆեսիոնալ Գեներացում")

        def find_free_room(required_type, day, hour, current_schedule):
            # Գտնում ենք տվյալ տիպի բոլոր սենյակները (օր.՝ բոլոր լաբորատորիաները)
            suitable_rooms = [r for r in st.session_state.rooms if r.type == required_type]
            
            # Եթե այդ տիպի սենյակ չկա ստեղծված, վերցնում ենք առաջին պատահական սենյակը կամ "-"
            if not suitable_rooms:
                return "-"

            for room in suitable_rooms:
                # Ստուգում ենք՝ արդյոք այս սենյակը զբաղված չէ այդ ժամին այլ դասարանի կողմից
                is_busy = any(
                    item for item in current_schedule 
                    if item['Օր'] == day and item['Ժամ'] == hour and item.get('Սենյակ') == room.name
                )
                if not is_busy:
                    return room.name
            return None # Եթե բոլոր սենյակները զբաղված են

        if st.button("🔥 Ստեղծել Խելացի Դասացուցակ", use_container_width=True, type="primary"):
            if not st.session_state.classes or not st.session_state.assignments:
                st.error("❌ Բացակայում են դասարանները կամ ժամերը գեներացման համար:")
            else:
                with st.spinner("🧠 Ալգորիթմը մտածում է... Խնդրում ենք սպասել..."):
                    time.sleep(2.5) 
                    
                    final_schedule = []
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

                            target = class_fund[chosen_candidate_idx]
                            room_to_assign = find_free_room(target.room_type, best_day, next_hour, final_schedule)

                            if room_to_assign is None:
                                continue

                            class_fund.pop(chosen_candidate_idx)
                            
                            t_name = next((t.name for t in st.session_state.teachers if t.id == target.teacher_id), "Անհայտ")
                            subj_name = get_subj_name(target.subject_id)
                            
                            final_schedule.append({
                                "Դասարան": f"{cls.grade}{cls.section}",
                                "Օր": best_day, 
                                "Ժամ": next_hour, 
                                "Առարկա": subj_name,
                                "Ուսուցիչ": t_name,
                                "Սենյակ": room_to_assign
                            })
                            
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
                    st.error("⚠️ Ալգորիթմը խճճվեց բախումների մեջ։ Փորձեք նորից սեղմել կոճակը։")

        if st.session_state.get('schedule'):
            df = pd.DataFrame(st.session_state.schedule)
            st.subheader("📋 Արդյունքներն ըստ Դասարանների")
            
            # Ցիկլով անցնում ենք յուրաքանչյուր դասարանի վրայով
            for c_name in df['Դասարան'].unique():
                with st.expander(f"🏫 Դասարան՝ {c_name}", expanded=True):
                    cls_df = df[df['Դասարան'] == c_name].copy()
                    
                    # Սարքում ենք աղյուսակը դիտելու համար (Pivot Table)
                    pivot = cls_df.pivot(index='Ժամ', columns='Օր', values='Առարկա').fillna("-")
                    
                    # Օրերի ճիշտ հերթականությունը
                    existing_days = [day for day in DAYS_AM if day in pivot.columns]
                    if existing_days:
                        pivot = pivot[[d for d in DAYS_AM if d in existing_days]]

                    st.dataframe(pivot, use_container_width=True)

                    # ✨ ՄԱՆՐԱՄԱՍՆԵՐԻ ԲԱԺԻՆ (Ամբողջությամբ նոր)
                    with st.popover(f"🔍 {c_name} դասարանի մանրամասներ"):
                        st.markdown(f"#### ℹ️ {c_name} - Ուսուցիչներ և Կաբինետներ")
                        
                        # Վերցնում ենք տվյալները հենց գեներացված դասացուցակից
                        if all(col in cls_df.columns for col in ['Առարկա', 'Ուսուցիչ', 'Սենյակ']):
                            # Հեռացնում ենք կրկնությունները, որպեսզի ամեն առարկա մեկ անգամ երևա
                            details = cls_df[['Առարկա', 'Ուսուցիչ', 'Սենյակ']].drop_duplicates()
                            
                            for _, row in details.iterrows():
                                st.markdown(f"📖 **{row['Առարկա']}**")
                                
                                # Ցուցադրում ենք այն սենյակը, որը կցվել է գեներացման ժամանակ
                                room_name = row['Սենյակ'] if row['Սենյակ'] and row['Սենյակ'] != "-" else "Նշված չէ"
                                
                                st.write(f"👨‍🏫 {row['Ուսուցիչ']} | 📍 {room_name}")
                                st.write("---")
                        else:
                            st.warning("⚠️ Տվյալները բացակայում են: Խնդրում ենք նորից գեներացնել:")

                            
            st.divider()
            # PDF-ի գեներացման հատվածը
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

                            st.dataframe(pivot, use_container_width=True)
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

                st.dataframe(pivot, use_container_width=True)
            else: st.warning("Այս ուսուցչի համար դեռևս դասեր չկան բաշխված։")
        else: st.info("Դեռևս չկա գեներացված դասացուցակ կամ գրանցված ուսուցիչ։")


    elif st.session_state.active_tab == "🤖 AI Օգնական":
        st.title("🤖 AI Օգնական (Gemini)")
        st.caption(f"Բարև, **{st.session_state.username}**! Ես քո անձնական AI օգնականն եմ։")

        current_user = st.session_state.username
        if current_user not in st.session_state.chat_histories:
            st.session_state.chat_histories[current_user] = []

        if "pending_proposal" not in st.session_state:
            st.session_state.pending_proposal = None

        # Ցուցադրել չաթի պատմությունը
        for message in st.session_state.chat_histories[current_user]:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        # Եթե կա կախված առաջարկ (Pending Proposal)
        if st.session_state.pending_proposal:
            with st.chat_message("assistant"):
                st.warning("💡 AI-ն ունի առաջարկ։ Ցանկանու՞մ եք տեսնել փոփոխված տարբերակը։")
                col_yes, col_no = st.columns(2)
                
                if col_yes.button("✅ Կիրառել (Տեսնել նոր աղյուսակը)", use_container_width=True):
                    proposal_text = st.session_state.pending_proposal
                    st.session_state.pending_proposal = None
                    
                    with st.spinner("🧠 Գեներացվում է նոր աղյուսակը..."):
                        try:
                            context = "Դու 'Smart Time Table' պրոյեկտի բազմաֆունկցիոնալ AI օգնականն ես։\n"
                            context += "Օգտատերը ՀԱՄԱՁԱՅՆԵՑ քո առաջարկին։ Հիմա արա այդ փոփոխությունը և արդյունքը ցույց տուր ՏԵՔՍՏԱՅԻՆ ՀՈՐԻԶՈՆԱԿԱՆ ԱՂՅՈՒՍԱԿՈՎ (Markdown table)։\n"
                            context += "Աղյուսակում տողերը պետք է լինեն ԺԱՄԵՐԸ (1, 2, 3...), իսկ սյունակները՝ ՕՐԵՐԸ (Երկուշաբթի, Երեքշաբթի...)։\n"
                            
                            if st.session_state.schedule:
                                # 🚀 Տվյալների սեղմում տոկեններ խնայելու համար
                                compact_sch = "\n".join([f"{i['Դասարան']}|{i['Օր']}|{i['Ժամ']}|{i['Առարկա']}" for i in st.session_state.schedule])
                                context += f"Նախնական դասացուցակ (Դասարան|Օր|Ժամ|Առարկա):\n{compact_sch}\n"

                            client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
                            response = client.models.generate_content(
                                model='gemini-2.0-flash',
                                contents=f"{context}\nՔո նախորդ առաջարկը, որին համաձայնեցին՝ {proposal_text}",
                            )
                            response_text = response.text

                            st.session_state.chat_histories[current_user].append({"role": "assistant", "content": response_text})
                            st.rerun()

                        except Exception as e:
                            st.error(f"❌ Սխալ: {str(e)}")

                if col_no.button("❌ Չեղարկել", use_container_width=True):
                    st.session_state.pending_proposal = None
                    st.toast("Առաջարկը չեղարկվեց", icon="🗑️")
                    st.rerun()

        # Օգտատիրոջ նոր հարցումը
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
                            context = "Դու 'Smart Time Table' պրոյեկտի բազմաֆունկցիոնալ AI օգնականն ես։\n"
                            context += f"Դու խոսում ես {current_user}-ի հետ։\n"
                            context += "⚠️ ՔՈ ԴԵՐԵՐԸ ԵՎ ԿԱՆՈՆՆԵՐԸ:\n"
                            context += "1. ℹ️ ՏԵՂԵԿԱՏՈՒ ԲՈՏ: Եթե հարցնում են դասացուցակի մասին, տուր հստակ պատասխան:\n"
                            context += "2. 💡 ԽՈՐՀՐԴԱՏՈՒ: Եթե առաջարկում ես փոփոխություն, մի՛ գծիր աղյուսակը միանգամից, այլ բացատրիր և ասա՝ սեղմեն 'Կիրառել':\n"
                            context += "3. 🛑 Մի՛ փոփոխիր st.session_state.schedule-ը:\n"

                            if st.session_state.schedule:
                                # 🚀 Տվյալների սեղմում
                                compact_sch = "\n".join([f"{i['Դասարան']}|{i['Օր']}|{i['Ժամ']}|{i['Առարկա']}" for i in st.session_state.schedule])
                                context += f"Ներկայիս դասացուցակ (Դասարան|Օր|Ժամ|Առարկա):\n{compact_sch}\n"
                            else:
                                context += "Դեռևս գեներացված դասացուցակ չկա։\n"

                            context += f"Օգտատիրոջ հարցը՝ {prompt}"

                            client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
                            response = client.models.generate_content(
                                model='gemini-2.0-flash',
                                contents=context,
                            )
                            response_text = response.text

                            # Ստուգում ենք՝ արդյոք AI-ն առաջարկ է անում
                            keywords = ["առաջարկ", "փոխել", "տեղափոխ", "swap", "փոփոխություն"]
                            if any(x in response_text.lower() for x in keywords):
                                st.session_state.pending_proposal = response_text

                    except Exception as e:
                        response_text = f"❌ Սխալ տեղի ունեցավ API կանչի ժամանակ: {str(e)}"

                    st.markdown(response_text)
                    st.session_state.chat_histories[current_user].append({"role": "assistant", "content": response_text})
