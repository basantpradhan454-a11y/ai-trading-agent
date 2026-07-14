"""FinsageAI — Finsage Academy UI"""
import streamlit as st
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from modules.academy_engine import CURRICULUM, BADGES, get_profile, check_answer, init_user


def render_academy_page():
    init_user()
    profile = get_profile()

    st.markdown("""
    <div style="margin-bottom:20px;">
        <span style="font-size:1.6rem; font-weight:800; background:linear-gradient(90deg,#00d4ff,#7c3aed);
            -webkit-background-clip:text; -webkit-text-fill-color:transparent;">🎓 Finsage Academy</span>
        <p style="color:#5a7a9a; margin-top:4px; font-size:0.9rem;">
            Learn trading step-by-step. Earn XP, unlock levels & badges. Educational only.
        </p>
    </div>
    """, unsafe_allow_html=True)

    max_xp = 1000
    xp_pct = min(profile["xp"] / max_xp, 1.0)
    c1, c2, c3 = st.columns(3)
    c1.metric("⚡ XP Points", f"{profile['xp']} / {max_xp}")
    c2.metric("📚 Level", f"Level {profile['level']}")
    c3.metric("🏅 Badges Earned", len(profile["badges"]))
    st.progress(xp_pct, text=f"Progress: {profile['xp']}/{max_xp} XP")

    if profile["badges"]:
        badge_html = " &nbsp; ".join([f'<span style="background:rgba(0,212,255,0.1); border:1px solid rgba(0,212,255,0.25); border-radius:20px; padding:4px 12px; font-size:0.82rem; color:#00d4ff;">{b}</span>' for b in profile["badges"]])
        st.markdown(f'<div style="margin:8px 0 16px;">{badge_html}</div>', unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["📚 Curriculum", "🎯 Quiz Arena"])

    with tab1:
        level_labels = {
            1: "Level 1 — Basics 🌱",
            2: "Level 2 — Intermediate 📊",
            3: "Level 3 — Advanced 🏆"
        }
        sel_level = st.radio(
            "Select Level", [1, 2, 3],
            format_func=lambda x: level_labels[x] + (" 🔒" if x > profile["level"] else ""),
            horizontal=True, key="academy_level_radio"
        )

        if sel_level > profile["level"]:
            needed = 200 if sel_level == 2 else 500
            st.warning(f"🔒 Level {sel_level} unlocks at {needed} XP. You have {profile['xp']} XP — keep completing quizzes!")
        else:
            lessons = CURRICULUM.get(sel_level, [])
            for lesson in lessons:
                done = lesson["id"] in profile["completed"]
                icon = "✅" if done else "📖"
                with st.expander(f"{icon} {lesson['title']} &nbsp; (+{lesson['xp']} XP)"):
                    st.markdown(lesson["content"])
                    st.markdown("---")
                    st.info(f"📝 Complete the quiz to earn **{lesson['xp']} XP**!")
                    if st.button(f"🎯 Take Quiz", key=f"start_quiz_{lesson['id']}"):
                        st.session_state["current_quiz_lesson"] = lesson["id"]
                        st.session_state["quiz_q_idx"] = 0
                        st.session_state["quiz_submitted"] = False
                        st.rerun()

    with tab2:
        lesson_id = st.session_state.get("current_quiz_lesson")
        if not lesson_id:
            st.markdown("""
            <div style="background:rgba(0,212,255,0.04); border:1px solid rgba(0,212,255,0.12);
                border-radius:14px; padding:32px; text-align:center; color:#5a7a9a;">
                <div style="font-size:2rem; margin-bottom:12px;">🎯</div>
                <div style="font-size:0.95rem;">Go to the <strong style="color:#c8d6e8;">Curriculum</strong> tab,
                open a lesson, and click <strong style="color:#00d4ff;">Take Quiz</strong> to start!</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            lesson = None
            for lv in CURRICULUM.values():
                for l in lv:
                    if l["id"] == lesson_id:
                        lesson = l; break

            if lesson:
                q_idx = st.session_state.get("quiz_q_idx", 0)
                if q_idx < len(lesson["quiz"]):
                    q = lesson["quiz"][q_idx]
                    progress_pct = q_idx / len(lesson["quiz"])
                    st.progress(progress_pct, text=f"Question {q_idx+1} of {len(lesson['quiz'])}")
                    st.markdown(f"""
                    <div style="background:#0f1e35; border:1px solid rgba(0,212,255,0.15);
                        border-radius:14px; padding:24px; margin:12px 0;">
                        <div style="font-size:0.72rem; color:#00d4ff; text-transform:uppercase; letter-spacing:.1em; margin-bottom:12px;">
                            {lesson['title']}
                        </div>
                        <div style="font-size:1.05rem; color:#e2eaf4; font-weight:500; line-height:1.5;">
                            {q['q']}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                    answer = st.radio("Choose your answer:", q["opts"],
                                      key=f"quiz_radio_{lesson_id}_{q_idx}", index=None)

                    submitted = st.session_state.get("quiz_submitted", False)
                    if not submitted:
                        if st.button("✅ Submit Answer", type="primary", key=f"submit_{q_idx}"):
                            if answer is None:
                                st.warning("Please select an answer first!")
                            else:
                                user_choice = answer[0]
                                result = check_answer(lesson_id, q_idx, user_choice)
                                st.session_state["last_result"] = result
                                st.session_state["quiz_submitted"] = True
                                st.rerun()
                    else:
                        result = st.session_state.get("last_result", {})
                        if result.get("correct"):
                            st.success(f"✅ Correct! +{result.get('xp',0)} XP earned!")
                            st.balloons()
                        else:
                            st.error(f"❌ Incorrect. Correct answer: **{q['ans']}**")
                        st.info(f"📖 {result.get('exp', '')}")
                        if result.get("badge"):
                            st.success(f"🏅 Badge Unlocked: **{result['badge']}**!")
                        if st.button("Next Question →", key=f"next_{q_idx}"):
                            st.session_state["quiz_q_idx"] = q_idx + 1
                            st.session_state["quiz_submitted"] = False
                            st.rerun()
                else:
                    st.markdown(f"""
                    <div style="background:rgba(0,212,255,0.05); border:1px solid rgba(0,212,255,0.2);
                        border-radius:14px; padding:32px; text-align:center;">
                        <div style="font-size:2rem; margin-bottom:12px;">🎉</div>
                        <div style="font-size:1.1rem; color:#00d4ff; font-weight:700;">
                            Quiz Complete: {lesson['title']}
                        </div>
                        <div style="color:#5a7a9a; margin-top:8px;">Total XP: {profile['xp']}</div>
                    </div>
                    """, unsafe_allow_html=True)
                    if st.button("📚 Back to Curriculum", use_container_width=True):
                        st.session_state.pop("current_quiz_lesson", None)
                        st.session_state.pop("quiz_q_idx", None)
                        st.session_state.pop("quiz_submitted", None)
                        st.rerun()
