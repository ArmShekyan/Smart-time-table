import streamlit as st
import uuid
import random
import pandas as pd
import json
import os
from dataclasses import dataclass, asdict
from typing import List, Dict

# 1. ՏՎՅԱԼՆԵՐԻ ՄՈԴԵԼՆԵՐ
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
    lessons_per_day: Dict[str, int]

@dataclass
class Assignment:
    id: str
    teacher_id: str
    subject_id: str
    class_id: str
    lessons_per_week: int

# 2. ՖԱՅԼԱՅԻՆ ՊԱՀՊԱՆՄԱՆ ՀԱՄԱԿԱՐԳ
DB_FILE = "database.json"

def save_to_disk():
    data = {
        "subjects": [asdict(s) for s in st.session_state.subjects],
        "teachers": [asdict(t) for t in st.session_state.teachers],
        "classes": [asdict(c) for c in st.session_state.classes],
        "assignments": [asdict(a) for a in st.session_state.assignments],
        "name_suggestions": st.session_state.name_suggestions,
        "teacher_names": st.session_state.teacher_names
    }
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    st.sidebar.success("✅ Տվյալները պահպանվեցին:")

def load_from_disk():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                st.session_state.subjects = [Subject(**s) for s in data.get("subjects", [])]
                st.session_state.teachers = [Teacher(**t) for t in data.get("teachers", [])]
                st.session_state.classes = [ClassGroup(**c) for c in data.get("classes", [])]
                st.session_state.assignments = [Assignment(**a) for a in data.get("assignments", [])]
                st.session_state.name_suggestions = data.get("name_suggestions", [])
                st.session_state.teacher_names = data.get("teacher_names", [])
        except Exception as e:
            st.error(f"Բեռնման սխալ: {e}")

# 3. SESSION STATE ՍԿԶԲՆԱՎՈՐՈՒՄ
if "subjects" not in st.session_state:
    st.session_state.update({
        "subjects": [], "teachers": [], "classes": [], "assignments": [], 
        "schedule": None, "name_suggestions": [], "teacher_names": []
    })
    load_from_disk()

def get_subject_name(sid):
    return next((s.name for s in st.session_state.subjects if s.id == sid), "Անհայտ")

# 4. UI ԿԱՌՈՒՑՎԱԾՔ
st.set_page_config(page_title="Smart School Scheduler", layout="wide")
st.sidebar.title("📅 Կառավարում")
page = st.sidebar.radio("Նավիգացիա", ["Առարկաներ", "Ուսուցիչներ", "Դասարաններ", "Գեներացում"])

st.sidebar.divider()
if st.sidebar.button("💾 Պահպանել բոլորը", use_container_width=True):
    save_to_disk()

# --- ՔԱՅԼ 1: ԱՌԱՐԿԱՆԵՐ ---
if page == "Առարկաներ":
    st.header("📚 Քայլ 1. Առարկաներ")
    with st.form("subj_lib", clear_on_submit=True):
        n_subj = st.text_input("Ավելացնել նոր առարկայի անուն")
        if st.form_submit_button("Ավելացնել ցանկում"):
            if n_subj and n_subj not in st.session_state.name_suggestions:
                st.session_state.name_suggestions.append(n_subj); st.rerun()
            elif n_subj in st.session_state.name_suggestions:
                st.error("Այս անունն արդեն կա ցանկում:")

    if st.session_state.name_suggestions:
        with st.form("subj_reg", clear_on_submit=True):
            sel_n = st.selectbox("Ընտրեք առարկան", options=st.session_state.name_suggestions)
            comp = st.select_slider("Բարդություն", options=[1, 2, 3, 4, 5], value=3)
            if st.form_submit_button("Գրանցել Առարկան"):
                if not any(s.name == sel_n for s in st.session_state.subjects):
                    st.session_state.subjects.append(Subject(str(uuid.uuid4()), sel_n, comp)); st.rerun()
                else:
                    st.error("Այս առարկան արդեն գրանցված է:")

    for i, s in enumerate(st.session_state.subjects):
        c1, c2 = st.columns([5, 1]); c1.write(f"📖 {s.name} (Բարդություն՝ {s.complexity})")
        if c2.button("Ջնջել", key=f"s_{s.id}"):
            st.session_state.subjects.pop(i); st.rerun()

# --- ՔԱՅԼ 2: ՈՒՍՈՒՑԻՉՆԵՐ (Առանց կրկնությունների) ---
elif page == "Ուսուցիչներ":
    st.header("👩‍🏫 Քայլ 2. Ուսուցիչներ")
    with st.form("t_lib", clear_on_submit=True):
        nt_name = st.text_input("Ավելացնել նոր ուսուցչի անուն")
        if st.form_submit_button("Ավելացնել"):
            if nt_name and nt_name not in st.session_state.teacher_names:
                st.session_state.teacher_names.append(nt_name); st.rerun()
            elif nt_name in st.session_state.teacher_names:
                st.error("Անունն արդեն կա բազայում:")

    if st.session_state.teacher_names and st.session_state.subjects:
        with st.form("t_reg", clear_on_submit=True):
            registered = [t.name for t in st.session_state.teachers]
            available = [n for n in st.session_state.teacher_names if n not in registered]
            if available:
                sel_t = st.selectbox("Ընտրեք ուսուցչին", options=available)
                sel_subjs = st.multiselect("Առարկաներ", st.session_state.subjects, format_func=lambda x: x.name)
                if st.form_submit_button("Գրանցել Ուսուցչին"):
                    if sel_t and sel_subjs:
                        st.session_state.teachers.append(Teacher(str(uuid.uuid4()), sel_t, [s.id for s in sel_subjs]))
                        st.rerun()
            else:
                st.info("Բոլոր ուսուցիչներն արդեն գրանցված են:")

    st.subheader("📋 Գրանցված ուսուցիչներ")
    for i, t in enumerate(st.session_state.teachers):
        c1, c2 = st.columns([5, 1])
        c1.write(f"👤 **{t.name}** — [{', '.join([get_subject_name(sid) for sid in t.subject_ids])}]")
        if c2.button("Ջնջել", key=f"t_{t.id}"):
            st.session_state.teachers.pop(i); st.rerun()

# --- ՔԱՅԼ 3: ԴԱՍԱՐԱՆՆԵՐ ---
elif page == "Դասարաններ":
    st.header("🏫 Քայլ 3. Դասարաններ")
    col1, col2 = st.columns(2)
    with col1:
        with st.form("cl_form", clear_on_submit=True):
            g = st.text_input("Հոսք (tntes, 10)"); s = st.text_input("Բաժին (Ա)")
            if st.form_submit_button("Ավելացնել"):
                if g:
                    st.session_state.classes.append(ClassGroup(str(uuid.uuid4()), g, s, {d:5 for d in ["monday", "tuesday", "wednesday", "thursday", "friday"]}))
                    st.rerun()
    with col2:
        if st.session_state.teachers:
            sel_t = st.selectbox("Ուսուցիչ", st.session_state.teachers, format_func=lambda x: x.name)
            t_subjs = [s for s in st.session_state.subjects if s.id in sel_t.subject_ids]
            with st.form("as_form", clear_on_submit=True):
                sel_c = st.selectbox("Դասարան", st.session_state.classes, format_func=lambda x: f"{x.grade}{x.section}")
                sel_s = st.selectbox("Առարկա", t_subjs, format_func=lambda x: x.name if x else "")
                hrs = st.number_input("Ժամաքանակ", 1, 10, 2)
                if st.form_submit_button("Կապել"):
                    if sel_s:
                        st.session_state.assignments.append(Assignment(str(uuid.uuid4()), sel_t.id, sel_s.id, sel_c.id, hrs))
                        st.rerun()

    st.divider()
    for i, a in enumerate(st.session_state.assignments):
        c_n = next((f"{c.grade}{c.section}" for c in st.session_state.classes if c.id == a.class_id), "")
        t_n = next((t.name for t in st.session_state.teachers if t.id == a.teacher_id), "")
        c1, c2 = st.columns([5, 1]); c1.write(f"📍 {c_n} | {get_subject_name(a.subject_id)} | {t_n} | {a.lessons_per_week} ժամ")
        if c2.button("Ջնջել", key=f"as_{i}"):
            st.session_state.assignments.pop(i); st.rerun()

# --- ՔԱՅԼ 4: ԳԵՆԵՐԱՑՈՒՄ ---
elif page == "Գեներացում":
    st.header("🚀 Գեներացում")
    if st.button("Ստեղծել Դասացուցակ"):
        res = []
        for cls in st.session_state.classes:
            fund = []
            for ass in [a for a in st.session_state.assignments if a.class_id == cls.id]:
                fund.extend([ass] * ass.lessons_per_week)
            random.shuffle(fund)
            idx = 0
            for day in ["monday", "tuesday", "wednesday", "thursday", "friday"]:
                daily = fund[idx : idx + 5]; idx += 5
                daily.sort(key=lambda x: next((s.complexity for s in st.session_state.subjects if s.id == x.subject_id), 3), reverse=True)
                for i, d in enumerate(daily):
                    res.append({"Դասարան": f"{cls.grade}{cls.section}", "Օր": day, "Ժամ": i+1, "Առարկա": get_subject_name(d.subject_id)})
        st.session_state.schedule = res

    if st.session_state.schedule:
        df = pd.DataFrame(st.session_state.schedule)
        for c in df['Դասարան'].unique():
            st.subheader(f"Դասարան՝ {c}")
            st.table(df[df['Դասարան'] == c].pivot(index='Ժամ', columns='Օր', values='Առարկա').fillna("-"))