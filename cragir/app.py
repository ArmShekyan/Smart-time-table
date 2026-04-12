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
from datetime import datetime, timedelta
from streamlit_cookies_controller import CookieController
from google import genai
from dotenv import load_dotenv
import hashlib

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
    name: str   
    type: str   
    assigned_class_id: str = None  

@dataclass
class Assignment:
    id: str
    teacher_id: str
    subject_id: str
    class_id: str
    lessons_per_week: int
    room_type: str = "Ընդհանուր"


# --- 📌 Ինստրուկցիայի Թռնող Պատուհան (Modal) ---
@st.dialog("📖 Smart Time Table: Օգտագործողի Ուղեցույց")
def show_instruction_modal():
    st.markdown("""
    Բարի գալուստ **Smart Time Table**՝ դասացուցակի կառավարման ավտոմատացված համակարգ։ 
    Ստորև ներկայացված են համակարգի բոլոր բաժինները և դրանց օգտագործման մանրամասն կանոնները։
    """)

    with st.expander("📊 1. Վահանակ", expanded=True):
        st.markdown("""
        * **Նպատակը.** Տվյալների բազայի ընդհանուր վիճակագրության արտացոլում։
        * **Հնարավորությունները.** Այստեղ կարող եք տեսնել գրանցված ռեսուրսների (ուսուցիչներ, առարկաներ, դասարաններ) քանակական ամփոփումը և դասերի ընդհանուր ծանրաբեռնվածությունը մեկ հայացքով։
        """)

    with st.expander("📚 2. Առարկաներ"):
        st.markdown("""
        * **Գործառույթը.** Ուսումնական առարկաների շտեմարանի ստեղծում։
        * **Կարևոր պայման.** Առարկան ավելացնելիս նշեք դրա **բարդության գործակիցը (1-5)**։ Սա թույլ է տալիս համակարգին առավել բարդ առարկաները տեղադրել օրվա օպտիմալ ժամերին՝ աշակերտների արդյունավետությունը բարձրացնելու նպատակով։
        """)

    with st.expander("👩‍🏫 3. Ուսուցիչներ"):
        st.markdown("""
        * **Գործառույթը.** Դասավանդող անձնակազմի հաշվառում։
        * **Կարգավորում.** Գրանցեք ուսուցչի տվյալները և կցեք այն առարկաները, որոնք նա իրավասու է դասավանդել։ Համակարգը կհետևի, որպեսզի մեկ ուսուցիչը նույն ժամին չունենա երկու տարբեր դասեր։
        """)

    with st.expander("🏫 4. Դասարաններ"):
        st.markdown("""
        * **Գործառույթը.** Դպրոցի դասարանական կազմի սահմանում։
        * **Ինչպե՞ս.** Ավելացրեք դասարանները (օրինակ՝ 10-Ա, 11-Բ)։ Սա հիմք է հանդիսանում հետագայում յուրաքանչյուր խմբի համար անհատականացված ժամաքանակներ սահմանելու համար։
        """)

    with st.expander("🚀 5. Գեներացում"):
        st.markdown("""
        * **Գործառույթը.** Դասացուցակի ավտոմատ կառուցման հիմնական հարթակ։
        * **Գործընթաց.** Այստեղ սահմանվում են շաբաթական ժամաքանակները։ «Ստեղծել Խելացի Դասացուցակ» կոճակը սեղմելիս համակարգը վայրկյանների ընթացքում ստեղծում է գրաֆիկ՝ բացառելով բոլոր հնարավոր համընկնումները։
        * **Արտահանում.** Պատրաստի արդյունքը հասանելի է **PDF** ֆորմատով ներբեռնման և տպագրության համար։
        """)

    with st.expander("📂 6. Վերջին պահպանվածը"):
        st.markdown("""
        * **Գործառույթը.** Ստեղծված դասացուցակների թվային արխիվ։
        * **Օգտագործում.** Այստեղ պահպանվում են նախկինում հաստատված տարբերակները, ինչը թույլ է տալիս ցանկացած պահի վերանայել կամ վերականգնել վերջին աշխատանքային գրաֆիկը։
        """)

    with st.expander("👤 7. Ուսուցչի Անձնական"):
        st.markdown("""
        * **Գործառույթը.** Անհատականացված տեղեկատվական հարթակ ուսուցիչների համար։
        * **Նկարագիր.** Յուրաքանչյուր դասավանդող կարող է ընտրել իր անունը և տեսնել միայն իրեն վերաբերող շաբաթական դասացուցակը՝ առանց ավելորդ տեղեկատվության։
        """)

    with st.expander("🤖 8. AI Օգնական"):
        st.markdown("""
        * **Գործառույթը.** Ինտերակտիվ խորհրդատու՝ հիմնված տվյալների վերլուծության վրա։
        * **Հնարավորություն.** Կարող եք հարցեր ուղղել դասացուցակի վերաբերյալ (օր.՝ «Ո՞ր ժամերն են ազատ», «Ո՞վ է զբաղված 4-րդ ժամին») և ստանալ ակնթարթային պատասխաններ։
        """)

    st.info("☁️ **Անվտանգություն.** Բոլոր փոփոխությունները համախրոնացվում են ամպային բազայի հետ, ինչն ապահովում է տվյալների պահպանվածությունը և հասանելիությունը ցանկացած վայրից։")

    if st.button("Հասկանալի է, անցնենք գործի! ✅", use_container_width=True, type="primary"):
        st.rerun()
        

DB_FILE = "smart_timetable_final.json"
DAYS_AM = ["Երկուշաբթի", "Երեքշաբթի", "Չորեքշաբթի", "Հինգշաբթի", "Ուրբաթ"]




# 1. Բեռնում ենք .env-ը
load_dotenv(override=True)

# 2. Սահմանում ենք DEFAULT_OWNER-ը՝ ՄԻԱՅՆ .env-ից
# Եթե .env-ում չկան OWNER_USER կամ OWNER_PASS, ապա կստանան None
DEFAULT_OWNER = {
    "username": os.getenv("OWNER_USER"), 
    "password": os.getenv("OWNER_PASS"), 
    "role": "owner"
}


# 3. Ստուգում (ըստ ցանկության), որ եթե տվյալները չկան, զգուշացնի
if not DEFAULT_OWNER["username"] or not DEFAULT_OWNER["password"]:
    print("⚠️ Զգուշացում. .env ֆայլում Owner-ի տվյալները բացակայում են:")


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

def hash_password(password):
    """Գաղտնաբառը դարձնում է անհասկանալի Hash կոդ"""
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_user(username, password):
    # 1. ՆԱԽ ՍՏՈՒԳՈՒՄ ԵՆՔ ԼՈԿԱԼ (Admin-ի համար .env-ից)
    # Ուշադրություն. ստուգում ենք սովորական տեքստով, որովհետև .env-ում տեքստ է
    if DEFAULT_OWNER["username"] and username == DEFAULT_OWNER["username"] and password == DEFAULT_OWNER["password"]:
        return DEFAULT_OWNER

    # 2. ԵԹԵ ԼՈԿԱԼ ՉԷ, ԴԻՄՈՒՄ ԵՆՔ SUPABASE-ԻՆ (մնացած օգտատերերի համար)
    # Այստեղ արդեն սարքում ենք Hash, որովհետև բազայում Hash է պահված
    hashed_input = hash_password(password)
    headers = get_supabase_headers()
    
    if headers:
        url = f"{st.secrets['supabase_url']}/rest/v1/users?username=eq.{username}&password=eq.{hashed_input}"
        try:
            # timeout=5-ը թույլ չի տա, որ ծրագիրը կախվի, եթե կապ չլինի
            response = requests.get(url, headers=headers, timeout=5)
            if response.status_code == 200:
                data = response.json()
                if data:
                    return data[0]  # Վերադարձնում է բազայի օգտատիրոջը
        except Exception as e:
            st.warning("⚠️ Բազայի հետ կապ չկա:")
            
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
            "users_list": st.session_state.users_list,
            "teacher_preferences": st.session_state.get('teacher_preferences', {})
        }

        headers = get_supabase_headers()
        final_data = None
        cloud_success = False

        if headers:
            try:
                # Տվյալների ստացում Cloud-ից
                url_get = f"{st.secrets['supabase_url']}/rest/v1/timetable_data?id=eq.1&select=data"
                res = requests.get(url_get, headers=headers)
                
                # ✨ ՈՒՂՂՈՒՄ 1. Ապահով ստանում ենք cloud_data-ն
                raw_res = res.json()
                cloud_data = raw_res[0]["data"] if res.status_code == 200 and raw_res else {}
                
                # Եթե բազայից եկածը dictionary չէ, սարքում ենք դատարկ dictionary
                if not isinstance(cloud_data, dict):
                    cloud_data = {}

                if not force_overwrite:
                    # ✨ ՈՒՂՂՈՒՄ 2. Ապահով Merge (ավելացված է isinstance ստուգում ամեն բաժնի համար)
                    def get_safe_list(key):
                        lst = cloud_data.get(key, [])
                        return lst if isinstance(lst, list) else []

                    final_data = {
                        "subjects": list({**{s.get("id"): s for s in get_safe_list("subjects") if isinstance(s, dict)}, **local_state["subjects"]}.values()),
                        "teachers": list({**{t.get("id"): t for t in get_safe_list("teachers") if isinstance(t, dict)}, **local_state["teachers"]}.values()),
                        "classes": list({**{c.get("id"): c for c in get_safe_list("classes") if isinstance(c, dict)}, **local_state["classes"]}.values()),
                        "rooms": list({**{r.get("id"): r for r in get_safe_list("rooms") if isinstance(r, dict)}, **local_state["rooms"]}.values()),
                        "assignments": list({**{a.get("id"): a for a in get_safe_list("assignments") if isinstance(a, dict)}, **local_state["assignments"]}.values()),
                        "schedule": local_state["schedule"],
                        "subj_pool": list(set(get_safe_list("subj_pool") + local_state["subj_pool"])),
                        "teacher_pool": list(set(get_safe_list("teacher_pool") + local_state["teacher_pool"])),
                        "users_list": local_state["users_list"],
                        "teacher_preferences": {**(cloud_data.get("teacher_preferences", {}) if isinstance(cloud_data.get("teacher_preferences"), dict) else {}), **local_state["teacher_preferences"]}
                    }
                else:
                    # Overwrite վիճակ
                    final_data = {
                        "subjects": list(local_state["subjects"].values()),
                        "teachers": list(local_state["teachers"].values()),
                        "classes": list(local_state["classes"].values()),
                        "rooms": list(local_state["rooms"].values()),
                        "assignments": list(local_state["assignments"].values()),
                        "schedule": local_state["schedule"],
                        "subj_pool": local_state["subj_pool"],
                        "teacher_pool": local_state["teacher_pool"],
                        "users_list": local_state["users_list"],
                        "teacher_preferences": local_state["teacher_preferences"]
                    }

                # ✨ ՈՒՂՂՈՒՄ 3. Պահպանումը PATCH-ով (որպեսզի mapping-ի սխալ չտա)
                url_post = f"{st.secrets['supabase_url']}/rest/v1/timetable_data?id=eq.1"
                payload = {"data": final_data}
                
                headers["Content-Type"] = "application/json"
                headers["Prefer"] = "return=minimal"
                
                resp = requests.patch(url_post, headers=headers, json=payload)
                
                if 200 <= resp.status_code < 300:
                    cloud_success = True
                else:
                    st.error(f"❌ Supabase Error: {resp.status_code} - {resp.text}")
                    
            except Exception as e:
                st.warning(f"⚠️ Կապի խնդիր: {type(e).__name__} - {str(e)}")

        # Եթե Cloud-ը ձախողվեց
        if final_data is None:
            final_data = {k: (list(v.values()) if isinstance(v, dict) else v) for k, v in local_state.items()}

        # Local Backup
        try:
            with open(DB_FILE, "w", encoding="utf-8") as f:
                json.dump(final_data, f, ensure_ascii=False, indent=4)
        except Exception as e:
            st.error(f"❌ Ֆայլի պահպանման սխալ: {e}")

        time.sleep(1) 
        
        if cloud_success:
            st.toast("✅ Սինքրոնացվեց Cloud-ում և Local-ում", icon="🌐")
        else:
            st.toast("💾 Պահպանվեց տեղական backup-ում", icon="📁")

        parse_data(final_data)
        

def reset_all_data():
    with st.spinner("🚨 Ամբողջական ջնջում..."):
        # Նախապատրաստում ենք դատարկ տվյալները
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
                # 1. Ջնջում ենք Cloud-ում
                url = f"{st.secrets['supabase_url']}/rest/v1/timetable_data"
                payload = {"id": 1, "data": data}
                headers["Prefer"] = "resolution=merge-duplicates"
                requests.post(url, headers=headers, data=json.dumps(payload))

                # 2. Զրոյացնում ենք թարմացման տվյալները
                update_url = f"{st.secrets['supabase_url']}/rest/v1/global_updates?id=eq.1"
                reset_update = {
                    "last_update": "--:--", 
                    "updated_by": "Ոչ ոք"
                }
                requests.patch(update_url, headers=headers, json=reset_update)

                # Հաղորդագրություն և թարմացում
                st.toast("💥 Բազան զրոյացվեց Cloud-ում:", icon="💣")
                time.sleep(1)
                st.rerun()
                return
            except Exception:
                pass

        # Եթե Cloud-ը չաշխատի, պահպանում ենք տեղական ֆայլում
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        
        st.toast("💥 Բազան զրոյացվեց տեղական ֆայլում:", icon="💣")
        time.sleep(1)
        st.rerun()


def manual_refresh():
    with st.spinner("🔄 Տվյալները թարմացվում են Cloud-ից..."):
        time.sleep(1.5)
        headers = get_supabase_headers()
        if headers:
            try:
                url = f"{st.secrets['supabase_url']}/rest/v1/timetable_data?id=eq.1&select=data"
                response = requests.get(url, headers=headers)
                
                if response.status_code == 200:
                    raw_json = response.json()
                    
                    if isinstance(raw_json, list) and len(raw_json) > 0:
                        data = raw_json[0]["data"]
                        
                        # 1. Բեռնում ենք բոլոր թարմ տվյալները
                        parse_data(data)
                        
                        # ✨ ՈՒՂՂՈՒՄ. Հեռացրել ենք st.session_state.schedule = [] տողը,
                        # որպեսզի պահպանված դասացուցակը ՉՋՆՋՎԻ թարմացման ժամանակ:
                        
                        st.session_state.teacher_preferences = data.get('teacher_preferences', {})
                        
                        if "v_bot_view" in st.session_state:
                            del st.session_state["v_bot_view"]
                        
                        if st.session_state.classes:
                            st.session_state.v_bot_view = st.session_state.classes[0]
                            
                        st.toast("✅ Տվյալները թարմ են:", icon="🔄")
                        st.rerun()
                        return
            except Exception as e:
                pass

        # Local Backup հատվածը
        if os.path.exists(DB_FILE):
            try:
                with open(DB_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    
                    parse_data(data)
                    
                    # ✨ ՈՒՂՂՈՒՄ. Այստեղ նույնպես հեռացրել ենք դատարկման տողը
                    st.session_state.teacher_preferences = data.get('teacher_preferences', {})
                    
                    if "v_bot_view" in st.session_state:
                        del st.session_state["v_bot_view"]
                    if st.session_state.classes:
                        st.session_state.v_bot_view = st.session_state.classes[0]
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
    /* 1. ՖՈՆ ԵՎ ՍԱՅԴԲԱՐ */
    .stApp { 
        background-color: #02060c !important; 
    }
    
    /* ՇԱՐԺՎՈՂ ԵԶՐԱԳԾԵՐԻ ԷՖԵԿՏ (Էջի շուրջը պտտվող լույսեր) */
    [data-testid="stAppViewContainer"]::after {
        content: "";
        position: fixed;
        top: 0; left: 0; right: 0; bottom: 0;
        border: 3px solid transparent;
        background: linear-gradient(#02060c, #02060c) padding-box,
                    conic-gradient(from var(--angle), #0055ff, transparent, #0055ff, transparent, #0055ff) border-box;
        z-index: 9999;
        pointer-events: none;
        animation: rotateBorder 4s linear infinite;
    }

    @property --angle {
        syntax: '<angle>';
        initial-value: 0deg;
        inherits: false;
    }

    @keyframes rotateBorder {
        to { --angle: 360deg; }
    }

    [data-testid="stSidebar"] {
        background-color: #050a12 !important;
        border-right: 1px solid rgba(0, 119, 255, 0.1) !important;
        z-index: 10000; /* Որպեսզի սայդբարը լինի լույսից վերև */
    }
    [data-testid="stSidebarNav"] { background-color: transparent !important; }
    
    /* 2. ՄԵՏՐԻԿԱՆԵՐԻ ՄՈՒԳ ԿԱՊՈՒՅՏ ԹՎԵՐ */
    [data-testid="stMetricValue"] {
        color: #0055ff !important; 
        font-weight: 800 !important; 
        font-size: 34px !important;
        text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.2);
    }

    /* 3. ԿՈՃԱԿՆԵՐԻ ՈՃԸ */
    div.stButton > button, div.stFormSubmitButton > button {
        border-radius: 12px !important;
        border: 1px solid rgba(0, 85, 255, 0.3) !important;
        background-color: #0a121e !important;
        color: #ccd6f6 !important;
        padding: 10px 20px !important;
        transition: all 0.3s ease-in-out !important;
        font-weight: 600 !important;
    }

    /* 4. ԿՈՃԱԿՆԵՐԻ ՀՈՎԵՐ (HOVER) */
    div.stButton > button:hover, div.stFormSubmitButton > button:hover {
        border: 1px solid #0055ff !important;
        color: #0055ff !important; 
        background-color: #0d1726 !important;
        box-shadow: 0 0 15px rgba(0, 85, 255, 0.3) !important; 
        text-shadow: 0 0 10px rgba(0, 85, 255, 0.5) !important; 
        transform: translateY(-1px);
    }

    /* 5. ԺԱՄԻ ԵՎ ԱՄՍԱԹՎԻ ՍԻՄԵՏՐԻԿ ՈՃԸ */
    .time-wrapper {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
    }
    .date-val {
        color: #0055ff !important;
        font-size: 16px !important;
        font-weight: 800 !important;
        letter-spacing: 1px;
        margin-bottom: -5px !important;
    }
    .hour-val {
        color: #0055ff !important;
        font-size: 40px !important;
        font-weight: 900 !important;
        line-height: 1.1;
    }

    /* 6. DISABLED ՎԻՃԱԿ */
    div.stButton > button:disabled {
        background-color: #161b22 !important;
        color: #484f58 !important;
        border: 1px solid #30363d !important;
        opacity: 0.6 !important;
    }

    /* 7. ԷՔՍՊԱՆԴԵՐՆԵՐ */
    .streamlit-expanderHeader {
        background-color: #0a121e !important;
        border: 1px solid rgba(255, 255, 255, 0.05) !important;
        border-radius: 10px !important;
        color: white !important;
    }
            
    /* 8. ԷՋԻ ՍԱՀՈՒՆ ՀԱՅՏՆՎԵԼՈՒ ԱՆԻՄԱՑԻԱ */
    @keyframes pageEntrance {
        from { 
            opacity: 0; 
            transform: translateY(15px); 
            filter: blur(5px);
        }
        to { 
            opacity: 1; 
            transform: translateY(0); 
            filter: blur(0);
        }
    }

    .stMainBlockContainer {
        animation: pageEntrance 1.5s ease-out;
    }

    [data-testid="stSidebarUserContent"] {
        animation: pageEntrance 1s ease-in-out;
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
        "room_occupancy": {}, # 🛡️ ԱՅՍ ՏՈՂԸ՝ սենյակների զբաղվածությունը ստուգելու համար
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
if not st.session_state.get('logged_in', False):
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
        st.rerun()

# --- 🚪 ԼՈԳԻՆԻ ԷՋ ---
if not st.session_state.get('logged_in', False):
    _, center_col, _ = st.columns([1, 2, 1])

    with center_col:
        st.markdown("<br><br>", unsafe_allow_html=True)
        
        with st.container(border=True):
            # Թարմացված դիզայն՝ հարմարվող գծով
            st.markdown(
                """
                <div style='text-align: center; padding-bottom: 20px;'>
                    <h1 style='color: #0077ff; font-weight: 800; letter-spacing: 5px; font-size: 30px; margin-bottom: 10px;'>
                        SMART TIME TABLE
                    </h1>
                    <div style='display: inline-block; border-bottom: 2px solid #0077ff; padding-bottom: 10px; box-shadow: 0 4px 8px -4px #0077ff;'>
                        <p style='color: #8b949e; font-size: 14px; font-weight: 300; margin: 0;'>
                            Մուտք գործեք համակարգ՝ աշխատանքը շարունակելու համար
                        </p>
                    </div>
                </div>
                """, 
                unsafe_allow_html=True
            )
            
            with st.form("login_panel", clear_on_submit=False):
                username_input = st.text_input("👤 Օգտատիրոջ անուն", placeholder="Մուտքագրեք username-ը")
                password_input = st.text_input("🔒 Գաղտնաբառ", type="password", placeholder="Ներմուծեք ձեր գաղտնաբառը")
                
                st.markdown("<br>", unsafe_allow_html=True)
                
                submit_login = st.form_submit_button("ՀԱՍՏԱՏԵԼ ՄՈՒՏՔԸ", use_container_width=True)

            # --- ՔՈ ՏՐԱՄԱԲԱՆՈՒԹՅՈՒՆԸ (ԱՆՓՈՓՈԽ) ---
            if submit_login:
                if not username_input or not password_input:
                    st.error("⚠️ Խնդրում ենք լրացնել բոլոր դաշտերը:")
                else:
                    user = check_user(username_input, password_input)
                    if user:
                        st.session_state.logged_in = True
                        st.session_state.username = user['username']
                        st.session_state.user_role = user['role']
                        
                        cookies.set("saved_username", user['username'])
                        cookies.set("saved_role", user['role'])
                        
                        st.session_state.show_readme = True 
                        
                        if user['role'] in ['owner', 'admin', 'subject_editor', 'teacher_editor']:
                            st.session_state.active_tab = "📊 Վահանակ"
                        else:
                            st.session_state.active_tab = "📂 Վերջին պահպանվածը"

                        st.toast(f"🎉 Բարի վերադարձ, {username_input}!", icon="🚀")
                        time.sleep(1.5)
                        st.rerun()
                    else:
                        error_placeholder = st.empty() # Ստեղծում ենք դատարկ տեղ
                        error_placeholder.error("❌ Տվյալները սխալ են") # Ցույց ենք տալիս սխալը
                        time.sleep(1.5) # Սպասում ենք 1.5 վայրկյան
                        error_placeholder.empty() # Մաքրում ենք այդ տեղը
                
    st.stop()


if st.session_state.get("show_readme", False):
    st.session_state.show_readme = False
    show_instruction_modal()


def get_subj_name(sid):
    return next((s.name for s in st.session_state.subjects if s.id == sid), "Անհայտ")

def get_subj_complexity(sid):
    return next((s.complexity for s in st.session_state.subjects if s.id == sid), 3)

def pdf_shorten_name(name):
    name = str(name).strip()
    
    if "AI" in name.upper() or "PYTHON" in name.upper():
        return name.split(" (")[0]
    
    # Շեմը բարձրացրինք 20, որպեսզի Հայոց պատմությունը չկրճատվի
    if len(name) > 20: 
        words = name.split()
        if len(words) >= 2:
            return ".".join([w[0].upper() for w in words]) + "."
            
    return name


def generate_pdf(schedule_data):
    # Landscape կողմնորոշում
    pdf = FPDF(orientation='L', unit='mm', format='A4') 
    pdf.add_page()
    
    font_path = "cragir/arial.ttf"
    pdf.add_font('Armenian', '', font_path)
    
    # 1. Գլխավոր Վերնագիր (ավելի փոքր բացատով)
    pdf.set_font('Armenian', '', 18)
    pdf.cell(0, 12, txt="Դպրոցական Դասացուցակ", ln=True, align='C')
    pdf.ln(2)

    classes = sorted(list(set(item['Դասարան'] for item in schedule_data)))
    days = ["Երկուշաբթի", "Երեքշաբթի", "Չորեքշաբթի", "Հինգշաբթի", "Ուրբաթ"]

    for class_name in classes:
        # Խելացի էջադրում՝ ստուգում ենք, որ աղյուսակը չկիսվի
        if pdf.get_y() > 160: 
            pdf.add_page()
            pdf.ln(5)

        # Դասարանի վերնագիր (ավելի փոքր)
        pdf.set_font('Armenian', '', 12)
        pdf.set_text_color(50, 50, 50)
        pdf.cell(0, 8, f"Դասարան՝ {class_name}", ln=True, align='L')
        
        # Աղյուսակի գլխամաս (Օրերը) - Բարձրությունը 8մմ
        pdf.set_font('Armenian', '', 9)
        pdf.set_text_color(0, 0, 0)
        pdf.set_fill_color(230, 230, 230) 
        
        pdf.cell(12, 8, "Ժամ", 1, 0, 'C', True)
        for day in days:
            pdf.cell(48, 8, day, 1, 0, 'C', True)
        pdf.ln()

        # Լրացնում ենք ժամերը - Բարձրությունը 8մմ
        pdf.set_font('Armenian', '', 9)
        
        class_lessons = [item for item in schedule_data if item['Դասարան'] == class_name]
        if class_lessons:
            max_hour = max([int(item['Ժամ']) for item in class_lessons])
            
            for hour in range(1, max_hour + 1):
                has_any_lesson = any(int(item['Ժամ']) == hour for item in class_lessons)
                if not has_any_lesson:
                    continue
                    
                pdf.cell(12, 8, str(hour), 1, 0, 'C')
                
                for day in days:
                    subject = ""
                    for item in class_lessons:
                        if item['Օր'] == day and int(item['Ժամ']) == hour:
                            subject = item['Առարկա']
                            break
                    pdf.cell(48, 8, subject, 1, 0, 'C')
                pdf.ln()
        
        pdf.ln(8) # Փոքրացրած բացատ դասարանների միջև

    return bytes(pdf.output())


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


if st.sidebar.button("🔄 Թարմացնել Տվյալները", use_container_width=True):
    manual_refresh()

st.sidebar.divider()


def on_page_change():
    st.session_state.active_page = "normal"
    st.session_state.active_tab = st.session_state.nav_radio

available_pages = []

if st.session_state.user_role in ['owner', 'admin']:
    available_pages = ["📊 Վահանակ", "📚 Առարկաներ", "👩‍🏫 Ուսուցիչներ", "🏫 Դասարաններ", "🚀 Գեներացում", "📂 Վերջին պահպանվածը", "👤 Ուսուցչի Անձնական", "🤖 AI Օգնական"]
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


if st.sidebar.button("💾 Պահպանել Բոլորը", use_container_width=True, type="primary"):
    save_to_disk() # Քո հին ֆունկցիան
    
    # --- Թարմացնում ենք ժամը REST API-ով ---
    url = f"{st.secrets['supabase_url']}/rest/v1/global_updates?id=eq.1"
    headers = {
        "apikey": st.secrets["supabase_key"],
        "Authorization": f"Bearer {st.secrets['supabase_key']}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal"
    }
    
    # Հայաստանի ժամը և ամսաթիվը (UTC+4)
    arm_time = (datetime.utcnow() + timedelta(hours=4)).strftime("%d.%m.%Y | %H:%M")

    data = {
        "last_update": arm_time,
        "updated_by": st.session_state.get('username', 'Unknown')
    }
    
    try:
        # PATCH հարցում ենք անում տվյալը թարմացնելու համար
        response = requests.patch(url, headers=headers, json=data)
        
        # Ստեղծում ենք դատարկ տեղ sidebar-ում հաղորդագրության համար
        msg_area = st.sidebar.empty()
        
        if response.status_code in [200, 204]:
            msg_area.success(f"🕒 Պահպանվեց և ժամը թարմացվեց՝ {arm_time}")
            time.sleep(1.2) # Մի փոքր սպասում ենք, որ օգտատերը տեսնի Success-ը
            msg_area.empty()
            
            # ✨ ԱՅՍՏԵՂ Է ԼՈՒԾՈՒՄԸ. Թարմացնում ենք ամբողջ էջը
            st.rerun() 
        else:
            st.sidebar.error("❌ Բազայի հետ կապի սխալ:")
            
    except Exception as e:
        st.sidebar.error(f"⚠️ Սխալ: {e}")


if st.session_state.user_role == 'owner':
    st.sidebar.divider()
    st.sidebar.markdown("<h3 style='color: #dc3545;'>⚠️ Վտանգավոր Գոտի</h3>", unsafe_allow_html=True)
    
    # Checkbox-ը իր key-ով
    confirm_reset = st.sidebar.checkbox("Հաստատում եմ ամբողջական ջնջումը", key="reset_checkbox")
    
    # Օգտագործում ենք on_click, որը կաշխատի button-ը սեղմելուց հետո, բայց rerun-ից առաջ
    if st.sidebar.button("🚨 Զրոյացնել Ամբողջ Բազան", 
                         type="primary", 
                         use_container_width=True, 
                         disabled=not confirm_reset,
                         on_click=lambda: st.session_state.update({"reset_checkbox": False})):
        
        reset_all_data() # Քո ջնջելու ֆունկցիան
        st.rerun()

st.sidebar.divider()


if st.session_state.user_role in ['owner', 'admin']:
    if st.sidebar.button("👥 Օգտատերերի Կառավարում", use_container_width=True):
        st.session_state.active_page = "👥 Օգտատերեր"
        st.rerun()

    if st.session_state.user_role == 'owner':
        if st.sidebar.button("🚀 Մասսայական Ավելացում", use_container_width=True):
            st.session_state.active_page = "🚀 Մասսայական"
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
            # Ավելացված է type="password", որ գրելիս չերևա
            new_p = st.text_input("Password", type="password")
            
            roles_list = ["user", "subject_editor", "teacher_editor", "admin"]
            new_r = st.selectbox("Դերը", roles_list)
            
            if st.form_submit_button("Ավելացնել Օգտատեր", use_container_width=True):
                if new_u and new_p:
                    # Ստուգում ենք տեղական ցուցակում, որ նույն անունով մարդ չլինի
                    if not any(u.get('username') == new_u for u in st.session_state.users_list):
                        
                        # ✨ Գաղտնաբառի հաշավորում նախքան ուղարկելը
                        hashed_password = hash_password(new_p)
                        
                        new_user_data = {
                            "username": new_u, 
                            "password": hashed_password, 
                            "role": new_r
                        }
                        
                        headers = get_supabase_headers()
                        if headers:
                            try:
                                url = f"{st.secrets['supabase_url']}/rest/v1/users"
                                response = requests.post(url, headers=headers, data=json.dumps(new_user_data))
                                
                                if response.status_code in [200, 201]:
                                    # Միայն հաջողության դեպքում ենք ավելացնում տեղական ցուցակում
                                    st.session_state.users_list.append(new_user_data)
                                    st.toast(f"✅ Օգտատեր {new_u}-ն ավելացվեց բազայում", icon="👤")
                                    time.sleep(0.5)
                                    st.rerun()
                                else:
                                    st.error(f"Սխալ բազայում պահպանելիս: {response.text}")
                            except Exception as e:
                                st.error(f"Կապի սխալ: {e}")
                    else:
                        st.warning("Այսպիսի Username արդեն կա:")
                else:
                    st.error("Լրացրեք բոլոր դաշտերը:")

    st.divider()
    
    if st.button("🔄 Թարմացնել Ցուցակը", use_container_width=True):
        refresh_users_only()

    st.subheader("📋 Գրանցված Օգտատերեր")
    
    # Օգտատերերի ցուցադրում
    for i, u in enumerate(st.session_state.users_list):
        with st.container(border=True):
            c1, c2, c3 = st.columns([3, 3, 1])
            c1.markdown(f"👤 **{u['username']}**")
            c2.markdown(f"🎭 Դերը՝ <span style='color: #0d6efd;'>{u['role']}</span>", unsafe_allow_html=True)
            
            # Ջնջելու իրավունքների ստուգում
            can_delete = True
            if u['username'] == st.session_state.get('username') or u['role'] == 'owner':
                can_delete = False 
            elif u['role'] == 'admin' and st.session_state.get('user_role') != 'owner':
                can_delete = False
                    
            if can_delete:
                if c3.button("🗑️", key=f"del_user_{i}"):
                    confirm_delete_user_modal(i)

elif st.session_state.active_page == "🚀 Մասսայական" and st.session_state.user_role == 'owner':
    st.title("🚀 Տվյալների Մասսայական Ավելացում")

    col1, col2 = st.columns(2)

    with col1:
        with st.container(border=True):
            st.subheader("👨‍🏫 Ուսուցիչներ")
            with st.form("bulk_teachers_form", clear_on_submit=True):
                raw_t = st.text_area("Մուտքագրեք անունները (ստորակետով)", key="bulk_page_t")
                submit_t = st.form_submit_button("Ավելացնել Ուսուցիչներին", use_container_width=True, type="primary")
                
                if submit_t and raw_t:
                    names = [n.strip() for n in raw_t.replace(',', '\n').split('\n') if n.strip()]
                    added = 0
                    errors = []

                    for name in names:
                        # Ստուգում ենք՝ արդյոք անունն արդեն կա pool-ում
                        if any(existing.lower() == name.lower() for existing in st.session_state.teacher_pool):
                            errors.append(name)
                        else:
                            st.session_state.teacher_pool.append(name)
                            added += 1
                    
                    # Եթե կան արդեն գրանցված անուններ, ցույց ենք տալիս կարմիրով
                    for err_name in errors:
                        st.error(f"❌ '{err_name}' ուսուցիչը արդեն գրանցված է ցանկում:")

                    if added > 0:
                        save_to_disk()
                        msg = st.empty()
                        msg.success(f"✅ {added} նոր անուն ավելացվեց:")
                        time.sleep(1.5)
                        msg.empty()
                        st.rerun()

    with col2:
        with st.container(border=True):
            st.subheader("📚 Առարկաներ")
            with st.form("bulk_subjects_form", clear_on_submit=True):
                raw_s = st.text_area("Մուտքագրեք առարկաները (ստորակետով)", key="bulk_page_s")
                submit_s = st.form_submit_button("Ավելացնել Առարկաները", use_container_width=True, type="primary")
                
                if submit_s and raw_s:
                    subjs = [s.strip() for s in raw_s.replace(',', '\n').split('\n') if s.strip()]
                    added_s = 0
                    s_errors = []

                    for s_name in subjs:
                        # Ստուգում ենք առարկաների համար
                        if any(existing.lower() == s_name.lower() for existing in st.session_state.subj_pool):
                            s_errors.append(s_name)
                        else:
                            st.session_state.subj_pool.append(s_name)
                            added_s += 1
                    
                    for err_s in s_errors:
                        st.error(f"❌ '{err_s}' առարկան արդեն գրանցված է ցանկում:")

                    if added_s > 0:
                        save_to_disk()
                        msg = st.empty()
                        msg.success(f"✅ {added_s} նոր առարկա ավելացվեց:")
                        time.sleep(1.5)
                        msg.empty()
                        st.rerun()
                    

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
            # 1. Սարքում ենք անունների ցուցակը
            class_options = ["🌐 Բոլոր դասարանները"] + [f"{c.grade}{c.section}" for c in st.session_state.classes]
            
            # 2. Հիշողության մեջ պահում ենք ընտրված դասարանի ԱՆՈՒՆԸ
            if "selected_analysis_class_name" not in st.session_state:
                st.session_state.selected_analysis_class_name = "🌐 Բոլոր դասարանները"

            # 3. Գտնում ենք current_idx-ը ըստ անվան
            try:
                current_idx = class_options.index(st.session_state.selected_analysis_class_name)
            except (ValueError, IndexError):
                current_idx = 0

            # 4. Selectbox-ը
            selected_class = st.selectbox(
                "🔍 Ընտրեք դասարանը՝ գրաֆիկները ֆիլտրելու համար", 
                class_options,
                index=current_idx,
                key="analysis_class_selector"
            )

            # 5. Թարմացնում ենք հիշողությունը
            st.session_state.selected_analysis_class_name = selected_class
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
                teacher_data = []
                for t in st.session_state.teachers:
                    # Ստանում ենք առարկաների անունների ցուցակը ըստ ID-ների
                    subj_names = [get_subj_name(sid) for sid in t.subject_ids]
                    # Միացնում ենք իրար ստորակետով
                    names_str = ", ".join(subj_names) if subj_names else "Առարկա չկա"
                    
                    teacher_data.append({
                        "Անուն": t.name, 
                        "Առարկաներ": names_str
                    })
                    
                df_t = pd.DataFrame(teacher_data)
                st.dataframe(df_t, use_container_width=True, hide_index=True)
            else: 
                st.caption("Ուսուցիչներ գրանցված չեն:")


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

        # --- ԱՋ ՍՅՈՒՆ: Գրանցել Առարկան ---
        with col_r:
            with st.container(border=True):
                # Ֆիլտրում ենք pool-ը, որպեսզի ցույց տանք միայն չգրանցված առարկաները
                registered_subj_names = [s.name.lower() for s in st.session_state.subjects]
                available_subjs = [s for s in st.session_state.subj_pool if s.lower() not in registered_subj_names]

                if available_subjs:
                    header_col, edit_col = st.columns([0.85, 0.15])
                    
                    with header_col:
                        st.markdown("### 📋 Գրանցել Առարկան")
                        
                    with edit_col:
                        with st.popover("✏️", help="Կառավարել ցանկը"):
                            st.write("🗑️ Ջնջել առարկան ցանկից")
                            subject_to_del = st.selectbox(
                                "Ընտրեք ջնջվողը", 
                                options=st.session_state.subj_pool, 
                                key="del_from_pool_key"
                            )
                            if st.button("Հաստատել ջնջումը", type="primary", use_container_width=True, key="confirm_del_subj_btn"):
                                if subject_to_del in st.session_state.subj_pool:
                                    st.session_state.subj_pool.remove(subject_to_del)
                                    save_to_disk(force_overwrite=True) 
                                    st.toast(f"🗑️ {subject_to_del}-ը հեռացվեց")
                                    time.sleep(1)
                                    st.rerun()

                    with st.form("register_subj", clear_on_submit=True):
                        # Օգտագործում ենք ֆիլտրված ցուցակը (available_subjs)
                        selected = st.selectbox("Ընտրեք ցանկից", available_subjs)
                        comp = st.select_slider("Բարդություն (1-5)", options=[1, 2, 3, 4, 5], value=3)
                        
                        if st.form_submit_button("Գրանցել", use_container_width=True):
                            clean_selected = selected.strip()
                            if any(s.name.lower() == clean_selected.lower() for s in st.session_state.subjects):
                                st.error(f"❌ {clean_selected} առարկան արդեն գրանցված է:")
                            else:
                                new_subject = Subject(id=str(uuid.uuid4()), name=clean_selected, complexity=comp)
                                st.session_state.subjects.append(new_subject)
                                
                                # Հեռացնում ենք pool-ից
                                if selected in st.session_state.subj_pool:
                                    st.session_state.subj_pool.remove(selected)
                                    
                                save_to_disk()
                                st.toast(f"✅ Առարկան գրանցվեց:", icon="📚")
                                st.rerun()
                else:
                    st.info("ℹ️ Բոլոր առարկաները գրանցված են կամ ցանկը դեռ դատարկ է:")

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
                        if t_name.lower() in [name.lower() for name in st.session_state.teacher_pool]:
                            st.error(f"❌ '{t_name}' անունով ուսուցիչ արդեն կա ցուցակում:")
                        else:
                            st.session_state.teacher_pool.append(t_name)
                            save_to_disk()
                            st.toast(f"👤 {t_name}-ն ավելացվեց ցանկում", icon="📝")
                            st.rerun()
                    else:
                        st.warning("⚠️ Մուտքագրեք անունը:")


            # --- ՀԱՏՈՒԿ ԱՐՏՈՆՈՒԹՅՈՒՆՆԵՐԻ ԲԱԺԻՆ ---
            st.markdown("<br>", unsafe_allow_html=True)
            
            with st.popover("💎 Հատուկ Արտոնությունների Բաժին", use_container_width=True):
                h_col, e_col = st.columns([0.85, 0.15])
                with h_col:
                    st.markdown("##### 🗓️ Ուսուցչի հարմար օրերը")
                with e_col:
                    with st.popover("✏️"):
                        prefs = st.session_state.get('teacher_preferences', {})
                        if prefs:
                            t_clear = st.selectbox("Ուսուցիչ", options=list(prefs.keys()), key="clr_pref")
                            if st.button("Ջնջել", type="primary"):
                                del st.session_state.teacher_preferences[t_clear]
                                save_to_disk(force_overwrite=True)
                                st.rerun()
                        else:
                            st.caption("Դատարկ է")

                with st.form("pref_form", clear_on_submit=True):
                    target_t = st.selectbox("Ընտրեք ուսուցչին", 
                                            options=[t.name for t in st.session_state.teachers])
                    
                    days_list = ["Երկուշաբթի", "Երեքշաբթի", "Չորեքշաբթի", "Հինգշաբթի", "Ուրբաթ"]
                    selected_days = st.multiselect("Ընտրեք օրերը", options=days_list, max_selections=4)

                    if st.form_submit_button("Գրանցել օրերը", use_container_width=True):
                        # Ստուգում ենք՝ արդյոք այս ուսուցիչն արդեն ունի գրանցված օրեր
                        existing_prefs = st.session_state.get('teacher_preferences', {})
                        
                        if target_t in existing_prefs:
                            st.error(f"❌ {target_t}-ն արդեն ունի գրանցված արտոնություն: Նորը գրանցելու համար նախ հեռացրեք հինը մատիտի (✏️) օգնությամբ:")
                        elif target_t and selected_days:
                            if 'teacher_preferences' not in st.session_state:
                                st.session_state.teacher_preferences = {}
                            
                            st.session_state.teacher_preferences[target_t] = selected_days
                            save_to_disk()
                            
                            st.toast(f"✅ {target_t}-ին հարմար օրերը գրանցվեցին")
                            st.rerun()
                        else:
                            st.warning("⚠️ Ընտրեք ուսուցչին և օրերը:")

        # --- ԱՋ ՍՅՈՒՆ: Գրանցել Ուսուցչին (Առարկաների հետ) ---
        with col_r:
            with st.container(border=True):
                # Ֆիլտրում ենք pool-ը, որպեսզի ցույց տանք միայն չգրանցվածներին
                registered_teacher_names = [t.name.lower() for t in st.session_state.teachers]
                available_teachers = [t for t in st.session_state.teacher_pool if t.lower() not in registered_teacher_names]

                if available_teachers and st.session_state.subjects:
                    header_col, edit_col = st.columns([0.85, 0.15])
                    
                    with header_col:
                        st.markdown("### 📋 Գրանցել Ուսուցչին")
                        
                    with edit_col:
                        with st.popover("✏️", help="Կառավարել ցանկը"):
                            st.write("🗑️ Ջնջել ցանկից")
                            teacher_to_del = st.selectbox(
                                    "Ընտրեք ջնջվողին", 
                                    options=sorted(
                                        st.session_state.teacher_pool, 
                                        key=lambda x: int(x.split('(')[-1].replace(')', '')) if '(' in x else 999
                                    ), 
                                    key="del_teacher_from_pool_select" 
                                )

                            if st.button("Հաստատել ջնջումը", type="primary", use_container_width=True, key="unique_del_t_btn"):
                                if teacher_to_del in st.session_state.teacher_pool:
                                    st.session_state.teacher_pool.remove(teacher_to_del)
                                    save_to_disk(force_overwrite=True) 
                                    st.toast(f"🗑️ {teacher_to_del}-ը հեռացվեց")
                                    time.sleep(1)
                                    st.rerun()

                    with st.form("register_teacher", clear_on_submit=True):
                        # Օգտագործում ենք ֆիլտրված ցուցակը (available_teachers)
                        # Վերցնում ենք փակագծից հետո եղած մասը, հանում ենք վերջին փակագիծը ու դարձնում թիվ
                        sel_t = st.selectbox("Ընտրեք ուսուցչին", sorted(available_teachers, key=lambda x: int(x.split('(')[-1].replace(')', ''))))
                        sel_subjs = st.multiselect("Ընտրեք առարկաները", st.session_state.subjects, format_func=lambda x: x.name)
                        
                        if st.form_submit_button("Գրանցել", use_container_width=True):
                            clean_name = sel_t.strip()
                            
                            # Կրկնակի ստուգում անվտանգության համար
                            if any(t.name.lower() == clean_name.lower() for t in st.session_state.teachers):
                                st.error(f"❌ {clean_name}-ն արդեն գրանցված է:")
                            elif not sel_subjs:
                                st.warning("⚠️ Ընտրեք առնվազն մեկ առարկա:")
                            else:
                                new_teacher = Teacher(id=str(uuid.uuid4()), name=clean_name, subject_ids=[s.id for s in sel_subjs])
                                st.session_state.teachers.append(new_teacher)
                                
                                # Հեռացնում ենք pool-ից
                                if sel_t in st.session_state.teacher_pool:
                                    st.session_state.teacher_pool.remove(sel_t)
                                
                                save_to_disk()
                                st.toast(f"✅ Ուսուցիչը գրանցվեց", icon="👩‍🏫")
                                st.rerun()
                
                elif not st.session_state.subjects:
                    st.info("ℹ️ Ուսուցիչ գրանցելու համար նախ պետք է գրանցել առնվազն մեկ առարկա:")
                else:
                    st.info("ℹ️ Բոլոր ուսուցիչները գրանցված են կամ ցանկը դատարկ է:")
 
                
        st.divider()
        st.subheader("📋 Դիտել Ուսուցիչներն ըստ Առարկաների")

        # --- ՈՒՍՈՒՑԻՉՆԵՐԻ ՑՈՒՑԱԿ ԵՎ ՖԻԼՏՐԱՑԻԱ ---
        if st.session_state.subjects and st.session_state.teachers:
            all_subjects_option = Subject(id="all", name="🌐 Բոլոր Առարկաները", complexity=0)
            subject_options = [all_subjects_option] + st.session_state.subjects

            # 1. Որոշում ենք current_idx-ը՝ օգտագործելով պահված ID-ն
            if "selected_filter_subj_id" not in st.session_state:
                st.session_state.selected_filter_subj_id = "all"

            current_idx = 0
            for i, subj in enumerate(subject_options):
                if subj.id == st.session_state.selected_filter_subj_id:
                    current_idx = i
                    break

            # 2. Selectbox-ը՝ index պարամետրով
            selected_subject_view = st.selectbox(
                "🔍 Ֆիլտրել ըստ առարկայի", 
                subject_options, 
                index=current_idx,
                format_func=lambda x: x.name,
                key="teacher_filter_selectbox"
            )

            # 3. Թարմացնում ենք հիշողությունը հենց ընտրությունը փոխվի
            if selected_subject_view:
                st.session_state.selected_filter_subj_id = selected_subject_view.id

            # --- Ֆիլտրման տրամաբանություն (մնում է նույնը) ---
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
                        
                        if c2.button("🗑️", key=f"t_view_{t.id}"):
                            st.session_state.assignments = [a for a in st.session_state.assignments if a.teacher_id != t.id]
                            st.session_state.teachers = [teacher for teacher in st.session_state.teachers if teacher.id != t.id]
                            save_to_disk(force_overwrite=True)
                            st.toast(f"🗑️ Ուսուցիչը ջնջվեց", icon="👩‍🏫")
                            st.rerun()
            else:
                st.info(f"ℹ️ {selected_subject_view.name} առարկայի համար դեռ ոչ մի ուսուցիչ չկա գրանցված։")
        else:
            st.info("ℹ️ Դեռևս չկան գրանցված առարկաներ կամ ուսուցիչներ։")
            

    elif st.session_state.active_tab == "🏫 Դասարաններ":
        st.title("🏫 Դասարաններ և Ժամեր")

        # --- 1. ԴԱՍԱՐԱՆՆԵՐԻ ՍՏԵՂԾՈՒՄ ԵՎ ԿԱՊԵՐ ---
        col1, col2 = st.columns(2)
        
        with col1:
            with st.form("class_form", clear_on_submit=True):
                st.markdown("### 🆕 Նոր Դասարան")
                g = st.text_input("Դասարան (օր. 10)").strip()
                s = st.text_input("Թիվ/Տառ (օր. Ա)").strip()
                
                if st.form_submit_button("Ավելացնել Դասարան", use_container_width=True):
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
                # Օգտագործում ենք container, որպեսզի ձախ կողմի պես border ունենա
                with st.container(border=True):
                    st.markdown("### 🔗 Կապել Դասարանին")
                    
                    # 1. Հաշվարկի համար վերցնում ենք ընթացիկ դասարանը
                    temp_c = st.session_state.get("c_sel_main", st.session_state.classes[0])
                    current_total = sum(a.lessons_per_week for a in st.session_state.assignments if a.class_id == temp_c.id)
                    max_allowed = 35
                    left = max_allowed - current_total
                    
                    st.info(f"📊 {temp_c.grade}{temp_c.section} դասարանում լրացված է՝ {current_total} / {max_allowed} ժամ")

                    sel_t = st.selectbox("👩‍🏫 Ընտրեք Ուսուցչին", 
                                        sorted(st.session_state.teachers, key=lambda x: int(x.name.split('(')[-1].replace(')', '')) if '(' in x.name else 999), 
                                        format_func=lambda x: x.name, 
                                        key="t_sel_main")
                    
                    sel_c = st.selectbox("🏫 Ընտրեք Դասարանը", 
                                        st.session_state.classes, 
                                        format_func=lambda x: f"{x.grade}{x.section}",
                                        key="c_sel_main")

                    all_teacher_subjs = [sub for sub in st.session_state.subjects if sub.id in sel_t.subject_ids]
                    assigned_subject_ids = [a.subject_id for a in st.session_state.assignments if a.class_id == sel_c.id]
                    available_subjs = [s for s in all_teacher_subjs if s.id not in assigned_subject_ids]

                    if available_subjs:
                        if left <= 0:
                            st.error(f"🚫 {max_allowed} ժամը լրացել է:")
                        else:
                            with st.form("as_form", clear_on_submit=True):
                                sel_s = st.selectbox("📚 Առարկա", available_subjs, format_func=lambda x: x.name)
                                hrs = st.number_input("📅 Շաբաթական ժամեր", 1, max(1, left), min(2, max(1, left)))
                                
                                if st.form_submit_button("Հաստատել Կապը", use_container_width=True, type="primary"):
                                    import uuid
                                    new_ass = Assignment(
                                        id=str(uuid.uuid4()), 
                                        teacher_id=sel_t.id, 
                                        subject_id=sel_s.id, 
                                        class_id=sel_c.id, 
                                        lessons_per_week=hrs,
                                        room_type="Ավտոմատ"
                                    )
                                    st.session_state.assignments.append(new_ass)
                                    save_to_disk()
                                    st.success(f"✅ {sel_s.name}-ը կապվեց {sel_c.grade}{sel_c.section}-ին")
                                    st.rerun()
                    else:
                        st.warning(f"⚠️ {sel_t.name}-ի բոլոր առարկաներն արդեն նշանակված են {sel_c.grade}{sel_c.section} դասարանում:")
            else:
                st.info("💡 Կապեր ստեղծելու համար նախ ավելացրեք ուսուցիչներ և դասարաններ:")

        # --- 2. ԴԱՍԱՐԱՆՆԵՐԻ ՑՈՒՑԱԿ ԵՎ ՀԵՌԱՑՈՒՄ ---
        st.divider()
        st.markdown("### 📋 Գոյություն ունեցող դասարաններ")
        if st.session_state.classes:
            for c in st.session_state.classes:
                col_c1, col_c2 = st.columns([5, 1])
                col_c1.markdown(f"🏫 **{c.grade}{c.section}** դասարան")
                if col_c2.button("🗑️", key=f"del_cls_{c.id}"):
                    st.session_state.classes = [x for x in st.session_state.classes if x.id != c.id]
                    st.session_state.assignments = [a for a in st.session_state.assignments if a.class_id != c.id]
                    save_to_disk(force_overwrite=True)
                    st.rerun()
        else:
            st.write("Դեռևս դասարաններ չկան:")

        # --- 3. ԴԻՏԵԼ ԿԱՊԵՐԸ (ԺԱՄԵՐԸ) ---
        st.divider() 
        st.markdown("### 🔍 Դիտել Ժամերի Բաշխումը")

        if st.session_state.classes:
            # 1. Սկզբից ստուգում ենք՝ արդյո՞ք արդեն ունենք ընտրված ID մեր "հիշողության" մեջ
            # Եթե առաջին անգամն է, վերցնում ենք առաջին դասարանի ID-ն
            if "selected_class_id" not in st.session_state:
                st.session_state.selected_class_id = st.session_state.classes[0].id

            # 2. Գտնում ենք, թե այդ ID-ն որերորդն է նոր (թարմացված) ցուցակում
            current_idx = 0
            for i, cls in enumerate(st.session_state.classes):
                if cls.id == st.session_state.selected_class_id:
                    current_idx = i
                    break

            # 3. Selectbox-ը՝ մեր գտած ինդեքսով
            view_c = st.selectbox(
                "Ընտրեք դասարանը՝ կապերը տեսնելու համար", 
                st.session_state.classes, 
                index=current_idx,
                format_func=lambda x: f"{x.grade}{x.section}", 
                key="class_selector_widget"
            )

            # 4. Հենց օգտատերը փոխի ընտրությունը, թարմացնում ենք մեր "հիշողության" ID-ն
            if view_c:
                st.session_state.selected_class_id = view_c.id
            
            filtered = [a for a in st.session_state.assignments if a.class_id == view_c.id]
            
            if filtered:
                for a in filtered:
                    t_obj = next((t for t in st.session_state.teachers if t.id == a.teacher_id), None)
                    s_obj = next((s for s in st.session_state.subjects if s.id == a.subject_id), None)
                    
                    with st.container(border=True):
                        c1, c2 = st.columns([5, 1])
                        subj_n = s_obj.name if s_obj else 'Անհայտ'
                        teach_n = t_obj.name if t_obj else 'Ուսուցիչ'
                        c1.markdown(f"🔹 **{subj_n}** — {teach_n} — `{a.lessons_per_week} ժամ`")
                        
                        if c2.button("🗑️", key=f"del_as_btn_{a.id}"):
                            st.session_state.assignments = [x for x in st.session_state.assignments if x.id != a.id]
                            save_to_disk(force_overwrite=True) 
                            st.rerun()
            else:
                st.info(f"ℹ️ **{view_c.grade}{view_c.section}** դասարանի համար դեռևս ժամեր նշանակված չեն:")
            

    elif st.session_state.active_tab == "🚀 Գեներացում":
        # --- ՎԵՐՆԱԳԻՐ ԵՎ ՋՆՋԵԼՈՒ ԿՈՃԱԿ ---
        col_title, col_delete = st.columns([0.8, 0.2])
        
        with col_title:
            st.title("🚀 Դասացուցակի Գեներացում")
            
        with col_delete:
            # Ստեղծում ենք popover, որը կծառայի որպես հաստատման պատուհան
            with st.popover("🗑️ Ջնջել", use_container_width=True, help="Ջնջել դասացուցակը"):
                st.warning("Վստա՞հ ես, որ ուզում ես ջնջել դասացուցակը:")
                
                # Իրական ջնջելու կոճակը popover-ի ներսում
                if st.button("Այո, ջնջել", type="primary", use_container_width=True):
                    placeholder = st.empty()
                    
                    if not st.session_state.schedule:
                        placeholder.warning("Դեռևս չկա գեներացված դասացուցակ ջնջելու համար:")
                        import time
                        time.sleep(1.5)
                        placeholder.empty()
                    else:
                        st.session_state.schedule = []
                        
                        headers = {
                            "apikey": st.secrets["supabase_key"],
                            "Authorization": f"Bearer {st.secrets['supabase_key']}",
                            "Content-Type": "application/json",
                            "Prefer": "return=minimal"
                        }
                        
                        updated_payload = {
                            "data": {
                                "classes": [c.__dict__ if hasattr(c, '__dict__') else c for c in st.session_state.classes],
                                "teachers": [t.__dict__ if hasattr(t, '__dict__') else t for t in st.session_state.teachers],
                                "subjects": [s.__dict__ if hasattr(s, '__dict__') else s for s in st.session_state.subjects],
                                "assignments": [a.__dict__ if hasattr(a, '__dict__') else a for a in st.session_state.assignments],
                                "schedule": [], 
                                "last_update": datetime.now().strftime("%d.%m.%Y | %H:%M")
                            }
                        }
                        
                        try:
                            url = f"{st.secrets['supabase_url']}/rest/v1/timetable_data?id=eq.1"
                            requests.patch(url, headers=headers, json=updated_payload)
                            st.toast("✅ Դասացուցակը հեռացվեց", icon="🗑️")
                            import time
                            time.sleep(1.5)
                            st.rerun()
                        except Exception as e:
                            st.error(f"Սխալ ջնջելիս: {e}")

        # --- ՔՈ ՕՐԻԳԻՆԱԼ CSS-Ը ---
        st.markdown("""
            <style>
                div[data-testid="stTable"] table { width: 100% !important; table-layout: fixed !important; }
                div[data-testid="stTable"] td, div[data-testid="stTable"] th {
                    text-align: center !important;
                    vertical-align: middle !important;
                    height: 50px !important;
                    border: 1px solid #444 !important;
                    word-wrap: break-word !important;
                }
                div[data-testid="stTable"] th:first-child, div[data-testid="stTable"] td:first-child {
                    width: 60px !important;
                    background-color: #1e1e1e !important;
                }
            </style>
        """, unsafe_allow_html=True)

        if "show_tables" not in st.session_state:
            st.session_state.show_tables = True

        # --- ՔՈ ՕՐԻԳԻՆԱԼ ՖՈՒՆԿՑԻԱՆԵՐԸ ԵՎ ԱԼԳՈՐԻԹՄԸ ---
        def get_auto_room(subj_name, class_label):
            s_name = str(subj_name).lower()
            if "python" in s_name or "ai" in s_name:
                return "Fast"
            elif "թգհգ" in s_name or "tghg" in s_name:
                return "Ինֆորմատիկայի սենյակ"
            else:
                return f"{class_label} class"

        if st.button("🔥 Ստեղծել Խելացի Դասացուցակ", use_container_width=True, type="primary"):
            if not st.session_state.classes or not st.session_state.assignments:
                st.error("❌ Բացակայում են դասարանները կամ ժամերը գեներացման համար:")
            else:
                max_attempts = 200 
                with st.spinner(f"🧠 Ալգորիթմը համեմատում է լավագույն տարբերակները ({max_attempts} փորձ)..."):
                    teacher_prefs = st.session_state.get('teacher_preferences', {})
                    
                    # Լավագույնին պահելու համար
                    best_overall_schedule = []
                    best_score = -1
                    best_attempt_num = 0
                    fail_reason = "" 

                    for attempt in range(max_attempts):
                        teacher_occupancy = {d: {h: set() for h in range(1, 8)} for d in DAYS_AM}
                        class_occupancy = {d: {h: set() for h in range(1, 8)} for d in DAYS_AM}
                        room_occupancy = {d: {h: set() for h in range(1, 8)} for d in DAYS_AM}
                        class_daily_subjects = {cls.id: {d: [] for d in DAYS_AM} for cls in st.session_state.classes}
                        current_attempt_schedule = []
                        
                        shuffled_classes = list(st.session_state.classes)
                        random.shuffle(shuffled_classes)
                        
                        generation_failed = False
                        current_score = 0 # Այս փորձի միավորը
                        
                        for cls in shuffled_classes:
                            class_label = f"{cls.grade}{cls.section}"
                            class_fund = []
                            assignments_for_cls = [a for a in st.session_state.assignments if a.class_id == cls.id]
                            
                            for ass in assignments_for_cls:
                                class_fund.extend([ass] * ass.lessons_per_week)
                            
                            # ՍՈՐՏԱՎՈՐՈՒՄ ԸՍՏ ԲԱՐԴՈՒԹՅԱՆ
                            class_fund.sort(key=lambda x: get_subj_complexity(x.subject_id), reverse=True)

                            class_day_counts = {d: 0 for d in DAYS_AM}
                            timeout = 0
                            
                            while class_fund and timeout < 2000:
                                timeout += 1
                                candidate = class_fund[0]
                                subj_name = get_subj_name(candidate.subject_id)
                                subj_complexity = get_subj_complexity(candidate.subject_id)
                                t_name = next((t.name for t in st.session_state.teachers if t.id == candidate.teacher_id), "Անհայտ")
                                
                                possible_days = []
                                if t_name in teacher_prefs:
                                    possible_days = [d for d in teacher_prefs[t_name] if class_day_counts[d] < 7]
                                
                                if not possible_days:
                                    min_count = min(class_day_counts.values())
                                    possible_days = [d for d in DAYS_AM if class_day_counts[d] == min_count and class_day_counts[d] < 7]

                                if not possible_days: 
                                    timeout = 2000
                                    break

                                best_day = random.choice(possible_days)
                                
                                # ԺԱՄԵՐԻ ԸՆՏՐՈՒԹՅՈՒՆ ԸՍՏ ԲԱՐԴՈՒԹՅԱՆ
                                if subj_complexity >= 4:
                                    available_hours = [1, 2, 3, 4, 5, 6, 7]
                                else:
                                    available_hours = list(range(1, 8))
                                    random.shuffle(available_hours)
                                
                                found_slot = False
                                for next_hour in available_hours:
                                    if class_label in class_occupancy[best_day][next_hour]: continue
                                    room_to_check = get_auto_room(subj_name, class_label)
                                    
                                    if (candidate.teacher_id not in teacher_occupancy[best_day][next_hour] and 
                                        room_to_check not in room_occupancy[best_day][next_hour]):
                                        
                                        subj_name_low = subj_name.lower()
                                        subj_count_today = class_daily_subjects[cls.id][best_day].count(subj_name)
                                        is_double_allowed = ("python" in subj_name_low or "ai" in subj_name_low or candidate.lessons_per_week >= 6)

                                        if (is_double_allowed and subj_count_today < 2) or (not is_double_allowed and subj_count_today < 1):
                                            # ՀԱՇՎՈՒՄ ԵՆՔ ՄԻԱՎՈՐՆԵՐԸ (Գնահատում ենք որակը)
                                            if next_hour <= 3 and subj_complexity >= 4:
                                                current_score += 15 # Բարձր միավոր բարդ առարկաներին առաջին ժամերին դնելու համար
                                            elif next_hour >= 6 and subj_complexity <= 2:
                                                current_score += 5 # Թեթև առարկաները վերջին ժամերին

                                            target = class_fund.pop(0)
                                            current_attempt_schedule.append({
                                                "Դասարան": class_label, "Օր": best_day, "Ժամ": next_hour, 
                                                "Առարկա": subj_name, "Ուսուցիչ": t_name, "Սենյակ": room_to_check
                                            })
                                            
                                            teacher_occupancy[best_day][next_hour].add(target.teacher_id)
                                            class_occupancy[best_day][next_hour].add(class_label)
                                            room_occupancy[best_day][next_hour].add(room_to_check)
                                            class_daily_subjects[cls.id][best_day].append(subj_name)
                                            class_day_counts[best_day] += 1
                                            found_slot = True
                                            break
                                
                                if not found_slot:
                                    continue 

                            if timeout >= 2000:
                                remaining = list(set([get_subj_name(a.subject_id) for a in class_fund]))
                                fail_reason = f"Դասարան՝ {class_label} | Չտեղավորված՝ {', '.join(remaining)}"
                                generation_failed = True
                                break
                        
                        # Եթե գեներացիան հաջողվեց, համեմատում ենք լավագույնի հետ
                        if not generation_failed:
                            if current_score > best_score:
                                best_score = current_score
                                best_overall_schedule = current_attempt_schedule
                                best_attempt_num = attempt + 1

                    if best_overall_schedule:
                        st.session_state.schedule = best_overall_schedule
                        st.success(f"🎉 Լավագույն տարբերակը գտնված է: Փորձ №{best_attempt_num}")
                        st.balloons()
                    else:
                        st.error(f"⚠️ Գեներացումը ձախողվեց {max_attempts} փորձից հետո:")
                        st.info(f"🔍 Վերջին խնդիրը. {fail_reason}")


        # --- ԳԵՆԵՐԱՑՈՒՄ ԷՋԻ ՍԿԻԶԲ (Ստուգում) ---
        if not st.session_state.get('schedule') or len(st.session_state.schedule) == 0:
            st.info("ℹ️ Դեռևս գեներացված դասացուցակ չկա: Սեղմեք «Ստեղծել Խելացի Դասացուցակ» կոճակը նորը ստեղծելու համար:")
        else:
            # 📊 ԱՐԴՅՈՒՆՔՆԵՐԻ ՑՈՒՑԱԴՐՈՒՄ
            if st.session_state.get('schedule'):
                st.divider()
                
                # 🔘 TOGGLE ԿՈՃԱԿ՝ ԹԱՔՑՆԵԼՈՒ / ՑՈՒՅՑ ՏԱԼՈՒ ՀԱՄԱՐ
                t_btn_text = "🙈 Թաքցնել բոլոր աղյուսակները" if st.session_state.show_tables else "📋 Ցուցադրել բոլոր աղյուսակները"
                if st.button(t_btn_text, use_container_width=True):
                    st.session_state.show_tables = not st.session_state.show_tables
                    st.rerun()

                # Եթե True է, ցուցադրում ենք աղյուսակները
                if st.session_state.show_tables:
                    df = pd.DataFrame(st.session_state.schedule)
                    st.subheader("📋 Արդյունքներն ըստ Դասարանների")
                    
                    for c_name in df['Դասարան'].unique():
                        with st.expander(f"🏫 Դասարան՝ {c_name}", expanded=True):
                            cls_df = df[df['Դասարան'] == c_name].copy()
                            
                            # ✨ Ցուցադրում ենք ՄԻԱՅՆ առարկան (առանց սենյակի)
                            cls_df['Cell'] = cls_df['Առարկա'] 
                            
                            pivot = cls_df.pivot(index='Ժամ', columns='Օր', values='Cell').fillna("-")
                            
                            existing_days = [day for day in DAYS_AM if day in pivot.columns]
                            if existing_days:
                                # Ապահովում ենք շաբաթվա օրերի ճիշտ հերթականությունը
                                pivot = pivot.reindex(columns=[d for d in DAYS_AM if d in existing_days])

                            st.dataframe(pivot, use_container_width=True)

                            # Մանրամասները պահում ենք Popover-ի մեջ
                            with st.popover(f"🔍 {c_name} դասարանի մանրամասներ"):
                                details = cls_df[['Առարկա', 'Ուսուցիչ', 'Սենյակ']].drop_duplicates()
                                for _, row in details.iterrows():
                                    st.markdown(f"📖 **{row['Առարկա']}**")
                                    st.write(f"👨‍🏫 {row['Ուսուցիչ']} | 📍 {row['Սենյակ']}")
                                    st.write("---")
                else:
                    st.info("💡 Աղյուսակները թաքցված են։")


           # 2. Քո PDF ներբեռնման հատվածը փոխիր այսպես.
            st.divider()
            try:
                # ✨ Ստեղծում ենք ժամանակավոր ցուցակ PDF-ի համար
                pdf_schedule = []
                for item in st.session_state.schedule:
                    new_item = item.copy() # Պատճենում ենք, որ բնօրինակը չփոխվի
                    new_item['Առարկա'] = pdf_shorten_name(new_item['Առարկա'])
                    pdf_schedule.append(new_item)

                # Գեներացնում ենք PDF-ը կրճատված տարբերակով
                pdf_data = generate_pdf(pdf_schedule) 
                
                st.download_button(
                    label="📥 Ներբեռնել PDF",
                    data=pdf_data, 
                    file_name="School_Timetable.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
            except Exception as e:
                st.error(f"PDF-ի սխալ: {e}")


    elif st.session_state.active_tab == "📂 Վերջին պահպանվածը":
        # 1. Վերցնում ենք թարմացման տվյալները Supabase-ից 
        try:
            read_url = f"{st.secrets['supabase_url']}/rest/v1/global_updates?id=eq.1&select=*"
            headers = {
                "apikey": st.secrets["supabase_key"],
                "Authorization": f"Bearer {st.secrets['supabase_key']}"
            }
            resp = requests.get(read_url, headers=headers).json()
            raw_time = resp[0]['last_update']  # Սա բերում է "05.04.2026 | 18:24" տիպի տեքստ
            
            if " | " in raw_time:
                db_date, db_hour = raw_time.split(" | ")
            else:
                db_date, db_hour = "", raw_time
                
            db_user = resp[0]['updated_by']
        except Exception as e:
            db_date, db_hour, db_user = "", "--:--", "Անհայտ"

        # 2. Դասավորում ենք Վերնագիրը և Ժամը
        col_title, col_time = st.columns([1.3, 1.2]) 
        
        with col_title:
            st.title("📂 Պահպանված Դասացուցակ")
            
        with col_time:
            st.markdown(f"""
                <div style="display:flex; justify-content:center; align-items:center; padding:10px; border-radius:12px; background:rgba(0,85,255,0.05); border:1px solid rgba(0,85,255,0.1);">
                    <div style="text-align:right; margin-right:15px;">
                        <p style="margin:0; font-size:12px; color:#0055ff; font-weight:800;">ՎԵՐՋԻՆ ՊԱՀՊԱՆՈՒՄ</p>
                        <p style="margin:0; font-size:14px; color:#ffffff;">հեղինակ՝ <span style="color:#00ff00;">{db_user}</span></p>
                    </div>
                    <div style="display:flex; align-items:center; border-left:1px solid rgba(0,85,255,0.2); padding-left:15px;">
                        <div class="time-wrapper">
                            <span class="date-val" style="font-size:13px !important;">{db_date}</span>
                            <span class="hour-val" style="font-size:28px !important;">{db_hour}</span>
                        </div>
                    </div>
                </div>
            """, unsafe_allow_html=True)

        # 3. Ցուցադրման տրամաբանությունը
        if st.session_state.schedule:
            df = pd.DataFrame(st.session_state.schedule)
            all_grades = sorted(list(set([c.grade for c in st.session_state.classes])))
            
            if all_grades:
                if "selected_view_grade" not in st.session_state:
                    st.session_state.selected_view_grade = all_grades[0]

                try:
                    current_idx = all_grades.index(st.session_state.selected_view_grade)
                except (ValueError, IndexError):
                    current_idx = 0

                sel_grade = st.selectbox(
                    "Ընտրեք դասարանը", 
                    all_grades, 
                    index=current_idx,
                    key="grade_view_selector"
                )

                st.session_state.selected_view_grade = sel_grade

                # --- ՃՇՏՎԱԾ ՍՏՈՒԳՈՒՄ ---
                # Վերցնում ենք տվյալ թվի տակ եղած բոլոր հնարավոր դասարանները (10Ա, 10Բ...)
                full_classes_in_grade = [f"{c.grade}{c.section}" for c in st.session_state.classes if c.grade == sel_grade]
                filled_classes = df['Դասարան'].unique()
                
                # Պարզում ենք՝ արդյոք տվյալ grade-ի տակ գոնե մի լրացված դասարան կա
                actually_filled_in_this_grade = [c for c in full_classes_in_grade if c in filled_classes]

                if not actually_filled_in_this_grade:
                    # Միայն եթե ՈՉ ՄԻ դասարան լրացված չէ տվյալ թվի համար
                    st.warning(f"⚠️ Դեռևս {sel_grade}-րդ դասարանների համար դասացուցակ կազմված չէ")
                else:
                    # Եթե կան լրացված դասարաններ, ցուցադրում ենք դրանք
                    for cls in full_classes_in_grade:
                        cls_data = df[df['Դասարան'] == cls]
                        if not cls_data.empty:
                            with st.expander(f"🏫 Դասարան՝ {cls}", expanded=True):
                                cls_df_clean = cls_data.copy()
                                cls_df_clean['Առարկա'] = cls_df_clean['Առարկա'].apply(lambda x: str(x).split(" (")[0])
                                
                                pivot = cls_df_clean.pivot(index='Ժամ', columns='Օր', values='Առարկա').fillna("-")
                                
                                existing_days = [day for day in DAYS_AM if day in pivot.columns]
                                if existing_days:
                                    pivot = pivot[existing_days]

                                st.dataframe(pivot, use_container_width=True)
            else: 
                st.info("Դեռ դասարաններ չկան")
        else: 
            st.info("Պահպանված տվյալներ չկան")


    elif st.session_state.active_tab == "👤 Ուսուցչի Անձնական":
        st.title("👤 Ուսուցչի Շաբաթվա Գրաֆիկ")
        
        # Ստուգում ենք՝ արդյոք ունենք դասացուցակ և ուսուցիչներ
        if st.session_state.get('schedule') and st.session_state.get('teachers'):
            
            # 1. Հիշողության մեջ պահում ենք ընտրված ուսուցչի ID-ն
            if "selected_personal_t_id" not in st.session_state:
                st.session_state.selected_personal_t_id = st.session_state.teachers[0].id

            # 2. Գտնում ենք current_idx-ը ըստ ID-ի
            current_idx = 0
            for i, t in enumerate(st.session_state.teachers):
                if t.id == st.session_state.selected_personal_t_id:
                    current_idx = i
                    break

            # 3. Ուսուցչի ընտրություն (Selectbox)
            sel_t = st.selectbox(
                "Ընտրեք ուսուցչին", 
                st.session_state.teachers, 
                index=current_idx,
                format_func=lambda x: x.name,
                key="personal_teacher_selector"
            )

            # 4. Թարմացնում ենք ID-ն session_state-ում
            if sel_t:
                st.session_state.selected_personal_t_id = sel_t.id

            # Գրաֆիկի ցուցադրում
            df = pd.DataFrame(st.session_state.schedule)
            t_data = df[df['Ուսուցիչ'] == sel_t.name]
            
            if not t_data.empty:
                t_data_clean = t_data.copy()
                
                # Ձևավորում ենք ցուցադրվող տեքստը
                t_data_clean['Ցուցադրում'] = t_data_clean['Դասարան'] + " - " + \
                                            t_data_clean['Առարկա'].apply(lambda x: str(x).split(" (")[0])
                
                # Սարքում ենք Pivot աղյուսակը
                pivot = t_data_clean.pivot(index='Ժամ', columns='Օր', values='Ցուցադրում').fillna("-")
                
                # Ապահովում ենք օրերի ճիշտ հերթականությունը
                existing_days = [day for day in DAYS_AM if day in pivot.columns]
                if existing_days:
                    pivot = pivot[existing_days]
                
                st.dataframe(pivot, use_container_width=True)
                st.info(f"💡 Ցուցադրված է {sel_t.name}-ի դասացուցակը:")
            else:
                st.warning(f"⚠️ {sel_t.name}-ի համար դեռևս դասեր չկան բաշխված։")
        else:
            st.info("ℹ️ Դեռևս չկա գեներացված դասացուցակ կամ գրանցված ուսուցիչ։")


    elif st.session_state.active_tab == "🤖 AI Օգնական":
        st.title("🤖 AI Օգնական (Gemini)")
        st.caption(f"Բարև, **{st.session_state.username}**!")

        current_user = st.session_state.username
        if current_user not in st.session_state.chat_histories:
            st.session_state.chat_histories[current_user] = []
        
        if "pending_proposal" not in st.session_state:
            st.session_state.pending_proposal = None
        if "last_ai_response" not in st.session_state:
            st.session_state.last_ai_response = None
        if "confirmed_class" not in st.session_state:
            st.session_state.confirmed_class = None

        classes = list(set([i['Դասարան'] for i in st.session_state.schedule])) if st.session_state.schedule else []

        if not st.session_state.confirmed_class:
            if classes:
                grade_levels = sorted(list(set([c.split()[0].strip('ԱբԳդ ') for c in classes if c])))
                col1, col2 = st.columns(2)
                with col1:
                    selected_level = st.selectbox("📅 Ընտրեք հոսքը", grade_levels)
                filtered_sub_classes = sorted([c for c in classes if c.startswith(selected_level)])
                with col2:
                    target_class = st.selectbox("🎯 Ընտրեք կոնկրետ դասարանը", filtered_sub_classes)
                
                st.warning(f"⚠️ Վստա՞հ եք, որ ուզում եք ընտրել **{target_class}** դասարանը: Հաստատելուց հետո այն հնարավոր չի լինի փոխել այս զրույցի ընթացքում:")
                if st.button("✅ Հաստատել և սկսել", use_container_width=True):
                    st.session_state.confirmed_class = target_class
                    st.rerun()
            else:
                st.info("Դեռ գեներացված դասացուցակ չկա:")
                st.stop()
        else:
            selected_class = st.session_state.confirmed_class
            col_header, col_reset = st.columns([4, 1])
            col_header.success(f"Ակտիվ դասարան՝ **{selected_class}**")
            
            if col_reset.button("🔄 Reset", help="Փոխել դասարանը"):
                st.session_state.confirmed_class = None
                st.session_state.chat_histories[current_user] = [] 
                st.rerun()

            with st.expander(f"📊 Ցուցադրել {selected_class} դասարանի դասացուցակը"):
                class_schedule = [i for i in st.session_state.schedule if i['Դասարան'] == selected_class]
                if class_schedule:
                    days = ["Երկուշաբթի", "Երեքշաբթի", "Չորեքշաբթի", "Հինգշաբթի", "Ուրբաթ"]
                    table_header = "| Ժամ | " + " | ".join(days) + " |"
                    table_divider = "| :--- | " + " | ".join([":---"] * 5) + " |"
                    
                    rows = []
                    for h in range(1, 8): 
                        row = f"| {h} |"
                        for day in days:
                            subject = next((item['Առարկա'] for item in class_schedule if item['Օր'] == day and int(item['Ժամ']) == h), "-")
                            row += f" {subject} |"
                        rows.append(row)
                    
                    full_table = table_header + "\n" + table_divider + "\n" + "\n".join(rows)
                    st.markdown(full_table)
                else:
                    st.write("Այս դասարանի համար տվյալներ չեն գտնվել:")

            filtered_data = [i for i in st.session_state.schedule if i['Դասարան'] == selected_class]
            # Ամբողջական տվյալները՝ որպեսզի AI-ը տեսնի այլ դասարանների զբաղվածությունը
            full_schedule_context = "\n".join([f"{i['Դասարան']}|{i['Օր']}|{i['Ժամ']}|{i['Առարկա']}" for i in st.session_state.schedule])

            for message in st.session_state.chat_histories[current_user]:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])

            if st.session_state.pending_proposal:
                with st.chat_message("assistant"):
                    st.info(st.session_state.last_ai_response)
                    st.warning(f"💡 Կիրառե՞նք այս փոփոխությունը {selected_class} դասարանի համար։")
                    
                    col_yes, col_no = st.columns(2)
                    
                    if col_yes.button("✅ Այո, կիրառել", use_container_width=True):
                        with st.spinner("🧠 Փոփոխվում է..."):
                            try:
                                context = f"Apply these changes ONLY for {selected_class}. Use full schedule to avoid teacher conflicts. Output ONLY the new schedule for {selected_class} as Markdown table."
                                client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
                                response = client.models.generate_content(
                                    model='gemini-2.5-flash',
                                    contents=f"{context}\nFull Data:\n{full_schedule_context}\nProposal: {st.session_state.pending_proposal}",
                                    config={'max_output_tokens': 30000, 'temperature': 0.1}
                                )
                                
                                st.session_state.chat_histories[current_user].append({"role": "assistant", "content": f"✅ Փոփոխությունը կատարված է {selected_class} համար:\n\n{response.text}"})
                                st.session_state.pending_proposal = None
                                st.session_state.last_ai_response = None
                                st.rerun()
                            except Exception as e:
                                st.error(f"Սխալ: {e}")

                    if col_no.button("❌ Ոչ, չեղարկել", use_container_width=True):
                        st.session_state.chat_histories[current_user].append({"role": "assistant", "content": "Փոփոխությունը չեղարկվեց։"})
                        st.session_state.pending_proposal = None
                        st.session_state.last_ai_response = None
                        st.rerun()

            if prompt := st.chat_input("Հարցրու դասացուցակի մասին...", disabled=st.session_state.pending_proposal is not None):
                st.session_state.chat_histories[current_user].append({"role": "user", "content": prompt})
                
                with st.chat_message("user"):
                    st.markdown(prompt)

                with st.chat_message("assistant"):
                    with st.spinner("🧠 Մտածում եմ..."):
                        try:
                            system_prompt = (
                                f"Դու 'Smart Time Table' օգնականն ես: Աշխատում ես {selected_class} դասարանի հետ: "
                                "1. Պատասխանիր հակիրճ հայերենով: "
                                "2. Հաշվի առ ամբողջ դպրոցի զբաղվածությունը (Full Data), որպեսզի նույն ուսուցիչը նույն ժամին երկու տեղ չլինի: "
                                "3. Եթե ցույց ես տալիս դասացուցակը, օգտագործիր Markdown աղյուսակ: "
                                "4. Եթե առաջարկում ես փոփոխություն, վերջում ավելացրու '[PROPOSAL]':"
                                "5. ԱՄԵՆԱԿԱՐԵՎՈՐԸ. Առաջարկիր միայն այնպիսի տարբերակներ, որոնք ԶՐՈՅԱԿԱՆ ՀԱՄԸՆԿՆՈՒՄ (conflict) ունեն այլ դասարանների հետ: "
                                    "Ընտրիր լավագույն և ամենաանվտանգ լուծումը բոլոր հնարավոր տարբերակներից:"
                            )
                            
                            full_prompt = f"{system_prompt}\n\nFull Schedule Data:\n{full_schedule_context}\n\nTarget Class: {selected_class}\nUser: {prompt}"

                            client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
                            response = client.models.generate_content(
                                model='gemini-2.5-flash', 
                                contents=full_prompt,
                                config={'max_output_tokens': 30000, 'temperature': 0.7}
                            )
                            
                            response_text = response.text
                            if "[PROPOSAL]" in response_text:
                                clean_text = response_text.replace("[PROPOSAL]", "").strip()
                                st.session_state.pending_proposal = clean_text
                                st.session_state.last_ai_response = clean_text
                                st.rerun()
                            else:
                                st.session_state.chat_histories[current_user].append({"role": "assistant", "content": response_text})
                                st.markdown(response_text)
                        except Exception as e:
                            st.error(f"API Error: {e}")
