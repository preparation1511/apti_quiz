import streamlit as st
import pandas as pd
import random
import ast
import time
import glob
import os

st.set_page_config(page_title="Multi-CSV Test With Timer", layout="wide")

# ================================================
# LOAD ALL CSVs
# ================================================

import re


    
@st.cache_data

def clean_latex(text):
    """
    Converts [latex]...[/latex] blocks in your text into proper
    Markdown LaTeX syntax for Streamlit: $...$
    """
    if text is None:
        return ""
    # Replace [latex]...[/latex] with $...$
    return re.sub(r'\[latex\](.*?)\[/latex\]', r'$\1$', text)

def load_all_csv(folder="datas"):
    all_files = glob.glob(os.path.join(folder, "*.csv"))
    df_list = []
    for file in all_files: 
        try:
            df = pd.read_csv(file)
            df_list.append(df)
        except:
            st.warning(f"Could not read: {file}")
    if df_list:
        return pd.concat(df_list, ignore_index=True)
    return pd.DataFrame()

df = load_all_csv()

if df.empty:
    st.error("No CSV files found in /data folder!")
    st.stop()

# ================================================
# SESSION STATE INITIALIZATION
# ================================================
if "questions" not in st.session_state:
    st.session_state.questions = []
if "index" not in st.session_state:
    st.session_state.index = 0
if "score" not in st.session_state:
    st.session_state.score = 0
if "time_limit" not in st.session_state:
    st.session_state.time_limit = None
if "start_time" not in st.session_state:
    st.session_state.start_time = None
if "user_answers" not in st.session_state:
    st.session_state.user_answers = []
if "test_completed" not in st.session_state:
    st.session_state.test_completed = False

# ================================================
# START TEST
# ================================================
def start_test():
    N = st.session_state.num_questions
    st.session_state.questions = df.sample(N).to_dict(orient="records")

    st.session_state.index = 0
    st.session_state.score = 0
    st.session_state.user_answers = []
    st.session_state.start_time = time.time()
    st.session_state.test_completed = False

# ================================================
# Parse Image
# ================================================
def parse_images(img_str):
    """
    Convert comma-separated image URLs into a list
    """
    if not img_str or pd.isna(img_str):
        return []
    return [img.strip() for img in img_str.split(",") if img.strip()]


# ================================================
# Parse Options
# ================================================

def parse_options(options_str):
    """
    Converts:
    'A: text | B: text | C: text | D: text'
    → {'A': 'text', 'B': 'text', ...}
    """
    options = {}
    for opt in options_str.split(" | "):
        if ": " in opt:
            key, value = opt.split(": ", 1)
            options[key.strip()] = value.strip()
    return options


# ================================================
# TIMER FUNCTION (COUNTDOWN)
# ================================================
def render_timer():
    if st.session_state.start_time:
        elapsed = int(time.time() - st.session_state.start_time)
        remaining = st.session_state.time_limit - elapsed

        if remaining <= 0:
            st.warning("⏳ Time's Up! Auto-submitted.")
            complete_test()
            st.stop()

        mins = remaining // 60
        secs = remaining % 60
        st.info(f"⏳ Time Remaining: **{mins:02d}:{secs:02d}**")


# ================================================
# END TEST + SHOW RESULTS
# ================================================
def complete_test():
    st.session_state.test_completed = True

    st.success("🎉 Test Completed!")
    st.write(f"## Score: **{st.session_state.score} / {len(st.session_state.questions)}**")

    review = []
    for i, q in enumerate(st.session_state.questions):

        # Safe check — if user didn't answer, use 'Not Answered'
        user_answer = (
            st.session_state.user_answers[i]
            if i < len(st.session_state.user_answers)
            else "Not Answered"
        )

        review.append({
            "Question": q["Question"],
            "Your Answer": user_answer,
            "Correct Answer": q["Correct_Answers"],
            "Answer Link": q["Answer_Link"]
        })

    st.write("### 📘 Review Your Answers")
    st.dataframe(pd.DataFrame(review))

# ================================================
# RENDER QUESTION
# ================================================
def render_question(q):
    # --- Question text ---
    st.markdown(
        f"### Q{st.session_state.index + 1}. {clean_latex(q.get('Question', ''))}"
    )

    # --- Show images if present ---
    images = parse_images(q.get("Images", ""))
    if images:
        for img in images:
            try:
                st.image(img, use_container_width=True)
            except TypeError:
                st.image(img, width=700)

    # --- Correct answers (list) ---
    try:
        correct = ast.literal_eval(q.get("Correct_Answers", "[]"))
    except Exception:
        correct = []

    if not isinstance(correct, list):
        correct = [correct]

    correct = [str(c).strip() for c in correct]

    # =========================
    # Check options
    # =========================
    options_raw = q.get("Options", "")

    # =====================================================
    # CASE 1: NO OPTIONS → INPUT TYPE QUESTION
    # =====================================================
    if not isinstance(options_raw, str) or options_raw.strip() == "" or options_raw in ['""""', '""']:

        user_input = st.text_input(
            "Enter your answer:",
            key=f"input_{st.session_state.index}"
        )

        if user_input == "":
            return None, correct

        user_input = user_input.strip()

        return user_input, correct

    # =====================================================
    # CASE 2: OPTIONS PRESENT → MCQ
    # =====================================================
    options = parse_options(options_raw)

    if not options:
        st.warning("No valid options found.")
        return None, correct

    keys = list(options.keys())

    # -------- MULTI-CORRECT MCQ --------
    if len(correct) > 1:
        user_answers = []

        for key in keys:
            cb_key = f"multi_{st.session_state.index}_{key}"
            if st.checkbox(
                clean_latex(f"{key}. {options[key]}"),
                key=cb_key
            ):
                user_answers.append(key)

        return user_answers, correct

    # -------- SINGLE-CORRECT MCQ --------
    ans = st.radio(
        "Choose one:",
        keys,
        format_func=lambda x: clean_latex(f"{x}. {options[x]}"),
        key=f"single_{st.session_state.index}"
    )

    return ans, correct




# ================================================
# CHECK IF CORRECT
# ================================================
def is_correct(user_answer, correct):
    # Normalize everything to strings
    correct_list = [str(c).strip() for c in correct]

    # -------- Numeric / integer --------
    if isinstance(user_answer, str):
        return user_answer.strip() in correct_list

    # -------- Multi-correct: user_answer is a list --------
    if isinstance(user_answer, list):
        user = sorted([str(a).strip() for a in user_answer])
        corr = sorted(correct_list)
        return user == corr

    return False




# ================================================
# MAIN UI
# ================================================
st.title("📝 Multi-CSV Test Generator with Timer")

# START SCREEN
if len(st.session_state.questions) == 0 and not st.session_state.test_completed:
    st.write("### Configure your test")

    st.session_state.num_questions = st.number_input(
        "How many questions?",
        min_value=1,
        max_value=len(df),
        value=5
    )

    time_minutes = st.number_input(
        "Enter timer duration (in minutes):",
        min_value=1,
        max_value=180,
        value=10
    )

    st.session_state.time_limit = time_minutes * 60  # convert to seconds

    if st.button("Start Test"):
        start_test()
        st.rerun()

    st.stop()


# IF TEST ALREADY COMPLETED
if st.session_state.test_completed:
    complete_test()
    if st.button("Restart Test"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()
    st.stop()

# ACTIVE TEST SCREEN
render_timer()

current_q = st.session_state.questions[st.session_state.index]
user_answer, correct = render_question(current_q)

# if st.button("Next"):
#     st.session_state.user_answers.append(user_answer)

#     if is_correct(user_answer, correct):
#         st.session_state.score += 1

#     st.session_state.index += 1

#     if st.session_state.index >= len(st.session_state.questions):
#         complete_test()
#         st.stop()


# --- Navigation Buttons ---
col1, col2, col3 = st.columns(3)

# Save current answer first
if "user_answers" not in st.session_state:
    st.session_state.user_answers = []

# Make sure the list has the right length
while len(st.session_state.user_answers) <= st.session_state.index:
    st.session_state.user_answers.append(None)

st.session_state.user_answers[st.session_state.index] = user_answer

# Back button
if col1.button("⬅ Back", disabled=st.session_state.index == 0):
    st.session_state.index -= 1
    st.rerun()

# Next or Submit button
if st.session_state.index == len(st.session_state.questions) - 1:
    if col3.button("Submit Test"):
        # Calculate final score
        st.session_state.score = 0
        for ans, q in zip(st.session_state.user_answers, st.session_state.questions):
            correct = ast.literal_eval(q["Correct_Answers"])
            if is_correct(ans, correct):
                st.session_state.score += 1
        complete_test()
        st.stop()
else:
    if col3.button("Next ➡"):
        st.session_state.index += 1
        st.rerun()

