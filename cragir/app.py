import streamlit as st
import uuid
import random
import pandas as pd
import json
import os
import requests
from dataclasses import dataclass, asdict
from typing import List

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

# --- ՏՎՅԱԼՆԵՐԻ ՊԱՀՊԱՆՈՒՄ (SQL / JSON) ---

def get_supabase_headers():
    # Ստուգում ենք՝ արդյոք secrets-ը գոյություն ունի, թե ոչ, որպեսզի սխալ չտա
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
    data = {
        "subjects": [asdict(s) for s in st.session_state.subjects],
        "teachers": [asdict(t) for t in st.session_state.teachers],
        "classes": [asdict(c) for c in st.session_state.classes],
        "assignments": [asdict(a) for a in st.session_state.assignments],
        "schedule": st.session_state.schedule,
        "subj_pool": st.session_state.subj_pool,
        "teacher_pool": st.session_state.teacher_pool
    }

    # Փորձում ենք պահել Cloud SQL-ում
    headers = get_supabase_headers()
    if headers:
        try:
            url = f"{st.secrets['supabase_url']}/rest/v1/timetable_data"
            payload = {"id": 1, "data": data}
            headers["Prefer"] = "resolution=merge-duplicates"
            requests.post(url, headers=headers, data=json.dumps(payload))
            st.sidebar.success("✅ Տվյալները պահպանվեցին Cloud SQL-ում!")
            return
        except Exception:
            pass

    # Եթե SQL չկա (օրինակ քո համակարգչում), պահում ենք տեղում JSON-ով
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    st.sidebar.warning("⚠️ Պահպանվեց տեղական JSON ֆայլում:")

def load_from_disk():
    # Փորձում ենք կարդալ Cloud SQL-ից
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

    # Եթե չկա SQL-ում, կարդում ենք տեղական JSON-ից
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                parse_data(data)
        except Exception:
            pass

def parse_data(data):
    st.session_state.subjects = [Subject(**s) for s in data.get("subjects", [])]
    st.session_state.teachers = [Teacher(**t) for t in data.get("teachers", [])]
    st.session_state.classes = [ClassGroup(**c) for c in data.get("classes", [])]
    st.session_state.assignments = [Assignment(**a) for a in data.get("assignments", [])]
    st.session_state.schedule = data.get("schedule", None)
    st.session_state.subj_pool = data.get("subj_pool", [])
    st.session_state.teacher_pool = data.get("teacher_pool", [])

# --- INITIALIZATION ---
if "subjects" not in st.session_state:
    st.session_state.update({
        "subjects": [], "teachers": [], "classes": [], "assignments": [], 
        "schedule": None, "subj_pool": [], "teacher_pool": []
    })
    load_from_disk()

def get_subj_name(sid):
    return next((s.name for s in st.session_state.subjects if s.id == sid), "Անհայտ")

def get_subj_complexity(sid):
    return next((s.complexity for s in st.session_state.subjects if s.id == sid), 3)

# --- UI CONFIG ---
st.set_page_config(page_title="Smart Time Table", layout="wide")

st.sidebar.title("🛠️ Կառավարում")
page = st.sidebar.radio("Նավիգացիա", ["📊 Վահանակ", "📚 Առարկաներ", "👩‍🏫 Ուսուցիչներ", "🏫 Դասարաններ", "🚀 Գեներացում", "📂 Վերջին պահպանվածը", "👤 Ուսուցչի Անձնական"])

if st.sidebar.button("💾 Պահպանել Բոլորը", width='stretch'):
    save_to_disk()

# --- ԷՋ 1: 📊 DASHBOARD ---
if page == "📊 Վահանակ":
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

# --- ԷՋ 2: ԱՌԱՐԿԱՆԵՐ ---
elif page == "📚 Առարկաներ":
    st.title("📚 Առարկաների Շտեմարան")
    
    col_l, col_r = st.columns([1, 1])
    with col_l:
        with st.form("add_to_pool", clear_on_submit=True):
            st.markdown("### 🆕 Ավելացնել ցուցակում")
            new_name = st.text_input("Առարկայի անուն")
            if st.form_submit_button("Ավելացնել ցանկում", width='stretch'):
                if new_name and new_name not in st.session_state.subj_pool:
                    st.session_state.subj_pool.append(new_name); st.rerun()

    with col_r:
        if st.session_state.subj_pool:
            with st.form("register_subj", clear_on_submit=True):
                st.markdown("### 📋 Գրանցել Առարկան")
                selected = st.selectbox("Ընտրեք ցանկից", st.session_state.subj_pool)
                comp = st.select_slider("Բարդություն (1-5)", options=[1,2,3,4,5], value=3)
                if st.form_submit_button("Գրանցել", width='stretch'):
                    if not any(s.name == selected for s in st.session_state.subjects):
                        st.session_state.subjects.append(Subject(str(uuid.uuid4()), selected, comp)); st.rerun()

    st.divider()
    st.subheader("✅ Գրանցված Առարկաներ")
    for i, s in enumerate(st.session_state.subjects):
        c1, c2 = st.columns([5,1])
        c1.write(f"📖 **{s.name}** (Բարդություն՝ {s.complexity})")
        if c2.button("🗑️", key=f"s_{s.id}"):
            st.session_state.assignments = [a for a in st.session_state.assignments if a.subject_id != s.id]
            st.session_state.subjects.pop(i); st.rerun()

# --- ԷՋ 3: ՈՒՍՈՒՑԻՉՆԵՐ ---
elif page == "👩‍🏫 Ուսուցիչներ":
    st.title("👩‍🏫 Ուսուցիչների Շտեմարան")
    
    col_l, col_r = st.columns([1, 1])
    with col_l:
        with st.form("add_t_pool", clear_on_submit=True):
            st.markdown("### 🆕 Ավելացնել ցուցակում")
            t_name = st.text_input("Ուսուցչի անուն")
            if st.form_submit_button("Ավելացնել ցանկում", width='stretch'):
                if t_name and t_name not in st.session_state.teacher_pool:
                    st.session_state.teacher_pool.append(t_name); st.rerun()

    with col_r:
        if st.session_state.teacher_pool and st.session_state.subjects:
            with st.form("register_teacher", clear_on_submit=True):
                st.markdown("### 📋 Գրանցել Ուսուցչին")
                sel_t = st.selectbox("Ընտրեք ուսուցչին", st.session_state.teacher_pool)
                sel_subjs = st.multiselect("Ընտրեք առարկաները", st.session_state.subjects, format_func=lambda x: x.name)
                if st.form_submit_button("Գրանցել", width='stretch'):
                    if not any(t.name == sel_t for t in st.session_state.teachers):
                        st.session_state.teachers.append(Teacher(str(uuid.uuid4()), sel_t, [s.id for s in sel_subjs])); st.rerun()

    st.divider()
    st.subheader("✅ Գրանցված Ուսուցիչներ")
    for i, t in enumerate(st.session_state.teachers):
        c1, c2 = st.columns([5,1])
        c1.write(f"👤 **{t.name}** — {', '.join([get_subj_name(sid) for sid in t.subject_ids])}")
        if c2.button("🗑️", key=f"t_{t.id}"):
            st.session_state.assignments = [a for a in st.session_state.assignments if a.teacher_id != t.id]
            st.session_state.teachers.pop(i); st.rerun()

# --- ԷՋ 4: ԴԱՍԱՐԱՆՆԵՐ ---
elif page == "🏫 Դասարաններ":
    st.title("🏫 Դասարաններ և Ժամեր")
    
    col1, col2 = st.columns(2)
    with col1:
        with st.form("cl_form", clear_on_submit=True):
            st.markdown("### 🆕 Նոր Դասարան")
            g = st.text_input("Հոսք (օր. ԱԲ)")
            s = st.text_input("Թիվ/Տառ (օր. 1 կամ Ա)")
            if st.form_submit_button("Ավելացնել", width='stretch'):
                if g and s: st.session_state.classes.append(ClassGroup(str(uuid.uuid4()), g, s)); st.rerun()

    with col2:
        if st.session_state.teachers and st.session_state.classes:
            with st.form("as_form", clear_on_submit=True):
                st.markdown("### 🔗 Կապել Դասարանին")
                sel_c = st.selectbox("Դասարան", st.session_state.classes, format_func=lambda x: f"{x.grade}{x.section}")
                sel_t = st.selectbox("Ուսուցիչ", st.session_state.teachers, format_func=lambda x: x.name)
                t_subjs = [sub for sub in st.session_state.subjects if sub.id in sel_t.subject_ids]
                sel_s = st.selectbox("Առարկա", t_subjs, format_func=lambda x: x.name if x else "")
                hrs = st.number_input("Շաբաթական ժամեր", 1, 10, 2)
                if st.form_submit_button("Կապել", width='stretch'):
                    current_hrs = sum(a.lessons_per_week for a in st.session_state.assignments if a.class_id == sel_c.id)
                    if current_hrs + hrs > 35:
                        st.error("❌ Դասարանը չի կարող 35 ժամից ավել ունենալ։")
                    elif any(a.class_id == sel_c.id and a.subject_id == sel_s.id for a in st.session_state.assignments):
                        st.error("⚠️ Այս առարկան արդեն ունի ուսուցիչ այս դասարանում։")
                    else:
                        st.session_state.assignments.append(Assignment(str(uuid.uuid4()), sel_t.id, sel_s.id, sel_c.id, hrs)); st.rerun()

    st.divider()
    st.subheader("✅ Շաբաթական Ժամերի Բաշխում")
    for i, a in enumerate(st.session_state.assignments):
        cls_obj = next((c for c in st.session_state.classes if c.id == a.class_id), None)
        t_obj = next((t for t in st.session_state.teachers if t.id == a.teacher_id), None)
        if cls_obj and t_obj:
            c1, c2 = st.columns([5,1])
            c1.write(f"📍 **{cls_obj.grade}{cls_obj.section}** | {get_subj_name(a.subject_id)} | {t_obj.name} | {a.lessons_per_week} ժամ")
            if c2.button("🗑️", key=f"as_{i}"):
                st.session_state.assignments.pop(i); st.rerun()

# --- ԷՋ 5: ԳԵՆԵՐԱՑՈՒՄ ---
elif page == "🚀 Գեներացում":
    st.title("🚀 Գեներացում")
    
    if st.button("🔥 Ստեղծել Խելացի Դասացուցակ", width='stretch', type="primary"):
        final_schedule = []
        teacher_occupancy = {d: {h: set() for h in range(1, 8)} for d in DAYS_AM}
        
        for cls in st.session_state.classes:
            class_fund = []
            weekly_subject_hours = {}
            assignments_for_cls = [a for a in st.session_state.assignments if a.class_id == cls.id]
            for ass in assignments_for_cls:
                class_fund.extend([ass] * ass.lessons_per_week)
                weekly_subject_hours[ass.subject_id] = ass.lessons_per_week
            
            class_fund.sort(key=lambda x: get_subj_complexity(x.subject_id), reverse=True)
            class_day_counts = {d: 0 for d in DAYS_AM}
            
            timeout = 0
            while class_fund and timeout < 3000:
                timeout += 1
                min_count = min(class_day_counts.values())
                lightest_days = [d for d in DAYS_AM if class_day_counts[d] == min_count]
                best_day = random.choice(lightest_days)
                
                if class_day_counts[best_day] >= 7:
                    break 
                
                next_hour = class_day_counts[best_day] + 1
                chosen_candidate_idx = -1
                
                for idx, candidate in enumerate(class_fund):
                    subj_name = get_subj_name(candidate.subject_id)
                    already_has_today = any(
                        s["Դասարան"] == f"{cls.grade}{cls.section}" and s["Օր"] == best_day and s["Առարկա"].startswith(subj_name)
                        for s in final_schedule
                    )
                    
                    if weekly_subject_hours.get(candidate.subject_id, 0) <= 5 and already_has_today:
                        continue 

                    if candidate.teacher_id not in teacher_occupancy[best_day][next_hour]:
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
                class_day_counts[best_day] += 1

        st.session_state.schedule = final_schedule
        st.success("✅ Հաջողությամբ գեներացվեց")

    if st.session_state.schedule:
        df = pd.DataFrame(st.session_state.schedule)
        st.subheader("📋 Արդյունքներն ըստ Դասարանների")
        for c in df['Դասարան'].unique():
            with st.expander(f"🏫 Դասարան՝ {c}", expanded=True):
                cls_df = df[df['Դասարան'] == c].copy()
                cls_df['Առարկա'] = cls_df['Առարկա'].apply(lambda x: x.split(" (")[0])
                pivot = cls_df.pivot(index='Ժամ', columns='Օր', values='Առարկա').fillna("-")
                st.dataframe(pivot, width='stretch')

# --- ԷՋ 6: ՎԵՐՋԻՆ ՊԱՀՊԱՆՎԱԾԸ ---
elif page == "📂 Վերջին պահպանվածը":
    st.title("📂 Պահպանված Դասացուցակ")
    if st.session_state.schedule:
        df = pd.DataFrame(st.session_state.schedule)
        all_grades = sorted(list(set([c.grade for c in st.session_state.classes])))
        if all_grades:
            sel_grade = st.selectbox("Ընտրեք հոսքը", all_grades)
            for cls in [f"{c.grade}{c.section}" for c in st.session_state.classes if c.grade == sel_grade]:
                cls_data = df[df['Դասարան'] == cls]
                if not cls_data.empty:
                    st.subheader(f"🏫 Դասարան՝ {cls}")
                    cls_df_clean = cls_data.copy()
                    cls_df_clean['Առարկա'] = cls_df_clean['Առարկա'].apply(lambda x: x.split(" (")[0])
                    pivot = cls_df_clean.pivot(index='Ժամ', columns='Օր', values='Առարկա').fillna("-")
                    st.dataframe(pivot, width='stretch')
        else: st.info("Դեռ դասարաններ չկան")
    else: st.info("Պահպանված տվյալներ չկան")

# --- ԷՋ 7: ՈՒՍՈՒՑՉԻ ԱՆՁՆԱԿԱՆ ---
elif page == "👤 Ուսուցչի Անձնական":
    st.title("👤 Ուսուցչի Շաբաթվա Գրաֆիկ")
    if st.session_state.schedule and st.session_state.teachers:
        df = pd.DataFrame(st.session_state.schedule)
        sel_t = st.selectbox("Ընտրեք ուսուցչին", st.session_state.teachers, format_func=lambda x: x.name)
        t_data = df[df['Առարկա'].str.contains(sel_t.name)]
        if not t_data.empty:
            t_data_clean = t_data.copy()
            t_data_clean['Ցուցադրում'] = t_data_clean['Դասարան'] + " - " + t_data_clean['Առարկա'].apply(lambda x: x.split(" (")[0])
            pivot = t_data_clean.pivot(index='Ժամ', columns='Օր', values='Ցուցադրում').fillna("-")
            st.dataframe(pivot, width='stretch')
        else: st.warning("Այս ուսուցչի համար դեռևս դասեր չկան բաշխված։")
    else: st.info("Դեռևս չկա գեներացված դասացուցակ կամ գրանցված ուսուցիչ։")

# py -m streamlit run app.py
# ctrl c - cancel