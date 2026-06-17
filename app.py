import streamlit as st
import time
import pandas as pd
from backend.database import ProjectDB
from backend.services.llm_service import LLMService
from backend.services.jira_service import JiraService

# Page Configuration
st.set_page_config(
    page_title="AI Sprint Architect",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize Backend Layer
db = ProjectDB()
llm = LLMService()

# Global Premium Style Injection
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&family=Plus+Jakarta+Sans:wght@300;400;500;600;700&display=swap');
    
    /* Global Font overrides */
    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', sans-serif;
    }
    
    h1, h2, h3, h4, h5, h6 {
        font-family: 'Outfit', sans-serif;
        letter-spacing: -0.02em;
    }

    /* Glassmorphic custom headers and cards */
    .glass-header {
        background: rgba(18, 22, 33, 0.65);
        backdrop-filter: blur(12px);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 16px;
        padding: 24px;
        margin-bottom: 25px;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.3);
    }
    
    .glass-card {
        background: rgba(255, 255, 255, 0.02);
        backdrop-filter: blur(8px);
        border: 1px solid rgba(255, 255, 255, 0.06);
        border-radius: 12px;
        padding: 16px;
        margin-bottom: 12px;
        transition: all 0.3s ease;
    }
    
    .glass-card:hover {
        border-color: rgba(99, 102, 241, 0.35);
        transform: translateY(-2px);
    }

    /* Status Badges */
    .badge {
        padding: 4px 8px;
        border-radius: 6px;
        font-size: 0.72rem;
        font-weight: 600;
        text-transform: uppercase;
        display: inline-block;
        margin-right: 6px;
        border: 1px solid transparent;
    }
    .badge-high { background-color: rgba(239, 68, 68, 0.15); color: #f87171; border-color: rgba(239, 68, 68, 0.25); }
    .badge-medium { background-color: rgba(245, 158, 11, 0.15); color: #fbbf24; border-color: rgba(245, 158, 11, 0.25); }
    .badge-low { background-color: rgba(16, 185, 129, 0.15); color: #34d399; border-color: rgba(16, 185, 129, 0.25); }
    
    .badge-functional { background-color: rgba(99, 102, 241, 0.15); color: #a5b4fc; border-color: rgba(99, 102, 241, 0.25); }
    .badge-non-functional { background-color: rgba(236, 72, 153, 0.15); color: #f9a8d4; border-color: rgba(236, 72, 153, 0.25); }
    .badge-integration { background-color: rgba(6, 182, 212, 0.15); color: #67e8f9; border-color: rgba(6, 182, 212, 0.25); }

    /* Terminal logs box */
    .terminal-box {
        background-color: #05070a !important;
        border: 1.5px solid #1f2937 !important;
        color: #34d399 !important;
        font-family: 'Courier New', Courier, monospace !important;
        font-size: 0.82rem !important;
        padding: 15px !important;
        border-radius: 8px !important;
    }
</style>
""", unsafe_allow_html=True)

# State Management
if "active_project_id" not in st.session_state:
    st.session_state.active_project_id = None
if "creating_project" not in st.session_state:
    st.session_state.creating_project = False
if "navigated_stage" not in st.session_state:
    st.session_state.navigated_stage = 1

# Sidebar Structure
st.sidebar.markdown("<div style='text-align: center; padding: 10px 0;'><h2>⚡ Sprint Architect</h2></div>", unsafe_allow_html=True)

if st.sidebar.button("➕ Create New Project", use_container_width=True, type="primary"):
    st.session_state.creating_project = True
    st.session_state.active_project_id = None
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.markdown("### Projects List")

projects = db.list_projects()
if projects:
    for p in projects:
        col1, col2 = st.sidebar.columns([4, 1])
        is_active = p["id"] == st.session_state.active_project_id
        
        btn_label = f"📁 {p['name']} (Stage {p['current_stage']}/5)"
        if is_active:
            btn_label = f"👉 {p['name']} (Stage {p['current_stage']}/5)"
            
        if col1.button(btn_label, key=f"sel_{p['id']}", use_container_width=True):
            st.session_state.active_project_id = p["id"]
            st.session_state.creating_project = False
            project_data = db.get_project(p["id"])
            st.session_state.navigated_stage = project_data.get("current_stage", 1)
            st.rerun()
            
        if col2.button("🗑️", key=f"del_{p['id']}", help="Delete Project"):
            if db.delete_project(p["id"]):
                if st.session_state.active_project_id == p["id"]:
                    st.session_state.active_project_id = None
                st.rerun()
else:
    st.sidebar.info("No active projects. Create one above.")

# --- RENDERING ENGINE ---

# 1. Project Creation Wizard
if st.session_state.creating_project:
    st.markdown("<div class='glass-header'><h2>➕ Create New Project</h2><p style='color:var(--text-muted); margin:0;'>Analyze meeting conversations and generate sprint schedules instantly.</p></div>", unsafe_allow_html=True)
    
    with st.container(border=True):
        proj_name = st.text_input("Project Name", placeholder="e.g. Eco Chase Travel App")
        
        tab_file, tab_paste = st.tabs(["📤 Upload TXT File", "📝 Copy / Paste Transcript"])
        transcript_content = ""
        
        with tab_file:
            uploaded_file = st.file_uploader("Choose meeting transcript file (.txt)", type=["txt"])
            if uploaded_file is not None:
                transcript_content = uploaded_file.read().decode("utf-8")
                st.success(f"✓ Uploaded {uploaded_file.name} successfully!")
                
        with tab_paste:
            paste_txt = st.text_area("Paste Client Discovery Transcript", height=250, placeholder="Paste dialogue...")
            if paste_txt.strip():
                transcript_content = paste_txt
                
        st.markdown("---")
        col_btn1, col_btn2 = st.columns([1, 6])
        if col_btn1.button("Create Project", type="primary"):
            if not proj_name.strip():
                st.error("Project name is required.")
            elif not transcript_content.strip():
                st.error("Transcript content cannot be empty. Please upload a file or paste text.")
            else:
                new_p = db.create_project(proj_name.strip(), transcript_content.strip())
                st.session_state.active_project_id = new_p["id"]
                st.session_state.navigated_stage = 1
                st.session_state.creating_project = False
                st.rerun()
        if col_btn2.button("Cancel"):
            st.session_state.creating_project = False
            st.rerun()

# 2. Main Active Dashboard
elif st.session_state.active_project_id:
    project = db.get_project(st.session_state.active_project_id)
    if not project:
        st.session_state.active_project_id = None
        st.rerun()
        
    # Header Banner
    st.markdown(f"""
    <div class='glass-header'>
        <div style='display:flex; justify-content:space-between; align-items:center;'>
            <div>
                <h1 style='margin:0; color:var(--text-main);'>{project['name']}</h1>
                <span style='font-size:0.8rem; color:var(--text-dark);'>ID: {project['id']}</span>
            </div>
            <div>
                <span class='badge badge-functional' style='padding:6px 12px;'>Stage {project['current_stage']}/5 Active</span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Progress Stage indicator bar
    cols = st.columns(5)
    stages = [
        (1, "Stage 1", "Transcript Parsing"),
        (2, "Stage 2", "Clarification Loop"),
        (3, "Stage 3", "Scope of Work"),
        (4, "Stage 4", "Sprint Planning"),
        (5, "Stage 5", "Jira Integration")
    ]
    
    # Navigation checks
    current_proj_stage = project.get("current_stage", 1)
    if st.session_state.navigated_stage > current_proj_stage:
        st.session_state.navigated_stage = current_proj_stage
        
    for idx, (num, label, title) in enumerate(stages):
        status = project["stage_status"].get(str(num), "locked")
        
        symbol = "🔒"
        if status == "completed":
            symbol = "✓"
        elif num == current_proj_stage:
            symbol = "⚡"
            
        btn_txt = f"{symbol} {label}\n{title}"
        
        # Color coding active stage
        is_current_view = st.session_state.navigated_stage == num
        
        if cols[idx].button(btn_txt, key=f"nav_btn_{num}", use_container_width=True, disabled=(status == "locked"), type="primary" if is_current_view else "secondary"):
            st.session_state.navigated_stage = num
            st.rerun()
            
    st.markdown("---")
    active_stage = st.session_state.navigated_stage
    
    # STAGE 1: PARSING EXTRACTION
    if active_stage == 1:
        st.subheader("Stage 1 — Transcript Fact Extraction")
        
        data = project.get("stage1_data")
        if not data:
            st.info("Transcript has not been analyzed yet. Run parsing to begin.")
            if st.button("🚀 Analyze Transcript with AI", type="primary", use_container_width=True):
                with st.spinner("AI is analyzing requirements, modules, constraints, and unknowns..."):
                    try:
                        parsed = llm.parse_transcript(project["transcript"])
                        db.update_project(project["id"], {"stage1_data": parsed})
                        st.rerun()
                    except Exception as e:
                        st.error(str(e))
        else:
            # Identity Metrics
            col_id1, col_id2, col_id3 = st.columns(3)
            with col_id1:
                st.markdown(f"<div class='glass-card'><strong>Project Name:</strong><br/><span style='color:var(--primary); font-size:1.1rem; font-weight:600;'>{data.get('project_name', 'N/A')}</span></div>", unsafe_allow_html=True)
            with col_id2:
                st.markdown(f"<div class='glass-card'><strong>Client Name:</strong><br/><span style='font-size:1.1rem; font-weight:600;'>{data.get('client_name', 'N/A')}</span></div>", unsafe_allow_html=True)
            with col_id3:
                st.markdown(f"<div class='glass-card'><strong>Vendor Name:</strong><br/><span style='font-size:1.1rem; font-weight:600;'>{data.get('vendor_name', 'N/A')}</span></div>", unsafe_allow_html=True)
                
            # Confidence indicators
            with st.expander("🔍 Fact Extraction Confidence Analysis"):
                for ci in data.get("confidence_indicators", []):
                    lvl = ci.get("level", "High")
                    field = ci.get("field_name", "")
                    reason = ci.get("reasoning", "")
                    
                    badge_style = "badge-high" if lvl == "Low" else ("badge-medium" if lvl == "Medium" else "badge-low")
                    st.markdown(f"**{field}**: <span class='badge {badge_style}'>{lvl}</span> - {reason}", unsafe_allow_html=True)
            
            # Content tabs
            tab_mod, tab_req, tab_int, tab_gaps = st.tabs(["📁 Extracted Modules", "⚙️ Requirements", "🔌 Integrations", "⚠️ Constraints & Gaps"])
            
            with tab_mod:
                col_mod = st.columns(3)
                for i, mod in enumerate(data.get("modules", [])):
                    prio = mod.get("priority", "Medium")
                    badge_style = f"badge-{prio.lower()}"
                    with col_mod[i % 3]:
                        st.markdown(f"""
                        <div class='glass-card' style='min-height: 180px; display:flex; flex-direction:column; justify-content:space-between;'>
                            <div>
                                <div style='display:flex; justify-content:space-between; align-items:center;'>
                                    <strong>{mod.get('name')}</strong>
                                    <span class='badge {badge_style}'>{prio}</span>
                                </div>
                                <p style='font-size:0.85rem; color:var(--text-muted); margin-top:8px;'>{mod.get('description')}</p>
                            </div>
                            {f"<div style='font-size:0.75rem; color:var(--warning); font-weight:600; margin-top:6px;'>Deadline: {mod.get('deadline')}</div>" if mod.get('deadline') else ''}
                        </div>
                        """, unsafe_allow_html=True)
                        
            with tab_req:
                for req in data.get("requirements", []):
                    rtype = req.get("type", "Functional")
                    badge_style = f"badge-{rtype.lower().replace('_', '-')}"
                    st.markdown(f"""
                    <div class='glass-card' style='display:flex; justify-content:space-between; align-items:center;'>
                        <div>
                            <span style='font-size:0.9rem; font-weight:550;'>{req.get('description')}</span><br/>
                            <span style='font-size:0.75rem; color:var(--text-dark);'>Module: {req.get('module')}</span>
                        </div>
                        <span class='badge {badge_style}'>{rtype}</span>
                    </div>
                    """, unsafe_allow_html=True)
                    
            with tab_int:
                col_int = st.columns(3)
                for i, integ in enumerate(data.get("integrations", [])):
                    with col_int[i % 3]:
                        st.markdown(f"""
                        <div class='glass-card'>
                            <strong style='color:var(--accent);'>{integ.get('name')}</strong>
                            <p style='font-size:0.85rem; color:var(--text-muted); margin-top:6px;'>{integ.get('description')}</p>
                        </div>
                        """, unsafe_allow_html=True)
                if not data.get("integrations"):
                    st.info("No external integrations detected.")
                    
            with tab_gaps:
                col_g1, col_g2, col_g3 = st.columns(3)
                with col_g1:
                    st.markdown("##### Constraints")
                    for c in data.get("constraints", []):
                        st.write(f"- {c.get('description')}")
                    if not data.get("constraints"): st.caption("None detected.")
                with col_g2:
                    st.markdown("##### Assumptions")
                    for a in data.get("assumptions", []):
                        st.write(f"- {a.get('description')}")
                    if not data.get("assumptions"): st.caption("None detected.")
                with col_g3:
                    st.markdown("##### Gaps / Unknowns")
                    for u in data.get("unknowns", []):
                        st.write(f"- {u.get('description')}")
                    if not data.get("unknowns"): st.caption("None detected.")
                    
            # Natural language tweaks form
            st.markdown("---")
            with st.form("tweak_extraction_form", clear_on_submit=True):
                st.markdown("💬 **Tweak Fact Extraction**")
                correction = st.text_input("Enter changes (e.g. 'Add module X priority as High', 'Change client name to Y')")
                tweak_sub = st.form_submit_button("Update Extraction")
                
                if tweak_sub and correction.strip():
                    with st.spinner("AI is applying corrections..."):
                        try:
                            parsed = llm.parse_transcript(project["transcript"], correction, data)
                            db.update_project(project["id"], {"stage1_data": parsed})
                            st.success("Changes incorporated!")
                            st.rerun()
                        except Exception as e:
                            st.error(str(e))
                            
            # Approve Stage 1 Gate
            st.markdown("---")
            if st.button("✓ Approve Facts & Unlock Stage 2", type="primary", use_container_width=True):
                with st.spinner("Locking details and generating clarifications..."):
                    try:
                        clarifications = llm.generate_clarifications(project["transcript"], data)
                        db.update_project(project["id"], {
                            "current_stage": 2,
                            "stage_status": {
                                "1": "completed",
                                "2": "active",
                                "3": "locked",
                                "4": "locked",
                                "5": "locked"
                            },
                            "stage2_data": {
                                "questions": clarifications.get("questions", []),
                                "custom_qa": []
                            }
                        })
                        st.session_state.navigated_stage = 2
                        st.rerun()
                    except Exception as e:
                        st.error(str(e))
                        
    # STAGE 2: CLARIFICATION LOOP
    elif active_stage == 2:
        st.subheader("Stage 2 — Clarification Loop")
        
        stage2 = project.get("stage2_data", {})
        questions = stage2.get("questions", [])
        custom_qa = stage2.get("custom_qa", [])
        
        col_q1, col_q2 = st.columns([1.8, 1])
        
        with col_q1:
            st.markdown("### Targeted Questions")
            for idx, q in enumerate(questions):
                status = q.get("status", "pending")
                is_res = status == "resolved"
                is_skip = status == "skipped"
                is_fup = status == "follow_up"
                
                badge_class = "badge-low" if is_res else ("badge-medium" if is_skip else ("badge-high" if is_fup else "badge-functional"))
                badge_label = "Resolved" if is_res else ("Skipped" if is_skip else ("Follow Up" if is_fup else "Pending"))
                
                with st.container(border=True):
                    # Header with beautiful colored badge
                    st.markdown(f"""
                    <div style='display:flex; justify-content:space-between; align-items:center; font-size:0.75rem; color:var(--text-dark); margin-bottom:6px;'>
                        <span>Question {idx+1}</span>
                        <span class='badge {badge_class}'>{badge_label.upper()}</span>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    title_prefix = "✅ " if is_res else ("⚠️ " if is_skip else ("💬 " if is_fup else "❓ "))
                    st.markdown(f"**{title_prefix}{q['question']}**")
                    
                    if q.get("transcript_citation"):
                        st.info(f"Citation: \"{q['transcript_citation']}\"")
                    st.caption(f"Reason asked: {q['explanation']}")
                    
                    if is_fup and q.get("follow_up_question"):
                        st.warning(f"AI Follow-up: {q['follow_up_question']}")
                        
                    if not is_res and not is_skip:
                        with st.form(key=f"ans_form_{q['question_id']}", clear_on_submit=True, border=False):
                            ans_val = st.text_input("Your Answer", placeholder="Type your answer here...")
                            
                            col_ans1, col_ans2 = st.columns([1, 4])
                            submit_clicked = col_ans1.form_submit_button("Submit Answer")
                            if submit_clicked and ans_val.strip():
                                if is_fup:
                                    # Resolve immediately in the second round to prevent infinite loop
                                    q["answer"] = f"Original: {q.get('answer')} | Follow-up: {ans_val}"
                                    q["status"] = "resolved"
                                    db.update_project(project["id"], {"stage2_data": stage2})
                                    st.rerun()
                                else:
                                    with st.spinner("AI checking response..."):
                                        try:
                                            res = llm.generate_follow_up(project["transcript"], q["question"], ans_val)
                                            q["answer"] = ans_val
                                            if res.get("resolved"):
                                                q["status"] = "resolved"
                                            else:
                                                q["status"] = "follow_up"
                                                q["follow_up_question"] = res.get("follow_up_question")
                                                q["explanation"] = res.get("explanation")
                                            db.update_project(project["id"], {"stage2_data": stage2})
                                            st.rerun()
                                        except Exception as e:
                                            st.error(str(e))
                                    
                        with st.expander("Skip question..."):
                            with st.form(key=f"skip_form_{q['question_id']}", clear_on_submit=True, border=False):
                                reason = st.text_input("Skip reason (e.g. Out of scope)")
                                if st.form_submit_button("Confirm Skip") and reason.strip():
                                    q["status"] = "skipped"
                                    q["skip_reason"] = reason
                                    db.update_project(project["id"], {"stage2_data": stage2})
                                    st.rerun()
                    else:
                        if is_res:
                            st.success(f"Answer: {q['answer']}")
                        if is_skip:
                            st.markdown(f"*Skipped: {q['skip_reason']}*")
                            
        with col_q2:
            st.markdown("### Custom Q&A Verification")
            
            with st.container(border=True):
                with st.form(key="custom_q_form", clear_on_submit=True, border=False):
                    custom_q = st.text_area("Ask custom question", placeholder="e.g. Can we fit Z module in Sprint 2?")
                    if st.form_submit_button("Ask AI", type="secondary") and custom_q.strip():
                        with st.spinner("Analyzing scope..."):
                            try:
                                ans = llm.answer_custom_question(custom_q, project["stage1_data"], questions)
                                custom_qa.append({"user_question": custom_q, "answer": ans.get("answer")})
                                db.update_project(project["id"], {"stage2_data": stage2})
                                st.rerun()
                            except Exception as e:
                                st.error(str(e))
            
            st.markdown("#### Conversation History")
            for item in custom_qa:
                with st.container(border=True):
                    st.markdown(f"**Q:** {item['user_question']}")
                    st.markdown(f"**A:** {item['answer']}")
            if not custom_qa:
                st.caption("No custom questions asked.")
                
        # Done Stage 2 Gate
        st.markdown("---")
        if st.button("✓ Done & Generate Scope of Work", type="primary", use_container_width=True):
            with st.spinner("Compiling facts and Q&A to draft SoW..."):
                try:
                    sow_res = llm.generate_sow(project["transcript"], project["stage1_data"], questions, custom_qa)
                    db.update_project(project["id"], {
                        "current_stage": 3,
                        "stage_status": {
                            "1": "completed",
                            "2": "completed",
                            "3": "active",
                            "4": "locked",
                            "5": "locked"
                        },
                        "stage3_data": {
                            "sow_markdown": sow_res.get("sow_markdown", ""),
                            "feedback_rounds": 0,
                            "changelog": sow_res.get("changelog", ["Initial Draft"])
                        }
                    })
                    st.session_state.navigated_stage = 3
                    st.rerun()
                except Exception as e:
                    st.error(str(e))
                    
    # STAGE 3: SCOPE OF WORK
    elif active_stage == 3:
        st.subheader("Stage 3 — Scope of Work")
        
        s3 = project.get("stage3_data", {})
        sow_md = s3.get("sow_markdown", "")
        rounds = s3.get("feedback_rounds", 0)
        changelog = s3.get("changelog", [])
        
        col_s1, col_s2 = st.columns([1.8, 1])
        
        with col_s1:
            st.markdown("### Document Preview")
            with st.container(border=True):
                st.markdown(sow_md)
            st.download_button("📥 Download SoW (.md)", data=sow_md, file_name=f"{project['name']}_SoW.md")
            
        with col_s2:
            st.markdown("### Refinement Feedback")
            
            with st.form("sow_feedback_form", clear_on_submit=True):
                feedback_txt = st.text_area("Suggest revisions", placeholder="e.g. Add compliance security rules, change timelines...")
                feed_sub = st.form_submit_button("Submit Revision")
                
                if feed_sub and feedback_txt.strip():
                    with st.spinner("AI incorporating feedback..."):
                        try:
                            res = llm.generate_sow(
                                project["transcript"],
                                project["stage1_data"],
                                project["stage2_data"].get("questions", []),
                                project["stage2_data"].get("custom_qa", []),
                                feedback=feedback_txt,
                                previous_sow=sow_md
                            )
                            s3["sow_markdown"] = res.get("sow_markdown", "")
                            s3["feedback_rounds"] = rounds + 1
                            s3["changelog"] = res.get("changelog", []) + changelog
                            db.update_project(project["id"], {"stage3_data": s3})
                            st.success("SoW updated!")
                            st.rerun()
                        except Exception as e:
                            st.error(str(e))
                            
            st.markdown("#### Document Changelog")
            for log in changelog:
                st.caption(f"- {log}")
            if not changelog:
                st.caption("No edits logged.")
                
            # Gate restriction
            st.markdown("---")
            if rounds < 1:
                st.warning("⚠️ **Refinement Required:** You must run at least **one round of feedback** before you can approve the SoW.")
                
            if st.button("✓ Approve Scope of Work & Plan Sprints", type="primary", use_container_width=True, disabled=(rounds < 1)):
                with st.spinner("AI breaking down deliverables into Sprints..."):
                    try:
                        sprints_res = llm.generate_sprints(sow_md, project["stage1_data"])
                        db.update_project(project["id"], {
                            "current_stage": 4,
                            "stage_status": {
                                "1": "completed",
                                "2": "completed",
                                "3": "completed",
                                "4": "active",
                                "5": "locked"
                            },
                            "stage4_data": {
                                "sprints": sprints_res.get("sprints", [])
                            }
                        })
                        st.session_state.navigated_stage = 4
                        st.rerun()
                    except Exception as e:
                        st.error(str(e))
                        
    # STAGE 4: SPRINT PLANNING
    elif active_stage == 4:
        st.subheader("Stage 4 — Sprint Planner & Audits")
        
        s4 = project.get("stage4_data", {})
        sprints = s4.get("sprints", [])
        
        # Validation checks
        alerts = []
        task_sprint_map = {}
        task_map = {}
        
        for s_idx, s in enumerate(sprints):
            for t in s.get("tasks", []):
                task_sprint_map[t["id"]] = s_idx
                task_map[t["id"]] = t
                
        for s_idx, s in enumerate(sprints):
            tasks = s.get("tasks", [])
            points = sum(t.get("story_points", 0) for t in tasks)
            if points > 40:
                alerts.append(f"⚠️ **{s['name']}** exceeds the maximum 40 Story Points limit (Current: {points} SP)")
                
            for t in tasks:
                for dep in t.get("dependencies", []):
                    dep_s_idx = task_sprint_map.get(dep)
                    if dep_s_idx is not None and dep_s_idx > s_idx:
                        dep_t = task_map.get(dep)
                        dep_title = dep_t["title"] if dep_t else dep
                        alerts.append(f"🚨 **Dependency Alert:** Task '{t['title']}' depends on '{dep_title}' which is scheduled in a later sprint ({sprints[dep_s_idx]['name']})")
                        
        if alerts:
            st.error("\n\n".join(alerts))
            
        # Board Layout
        cols_board = st.columns(len(sprints))
        
        for s_idx, s in enumerate(sprints):
            tasks = s.get("tasks", [])
            points = sum(t.get("story_points", 0) for t in tasks)
            points_exceeded = points > 40
            
            with cols_board[s_idx]:
                st.markdown(f"#### {s['name']}")
                st.caption(f"Goal: {s.get('goal')}")
                st.markdown(f"**Story Points:** {points}/40 SP")
                
                for t in tasks:
                    with st.container(border=True):
                        st.markdown(f"**{t['title']}**")
                        st.caption(t.get("description", ""))
                        st.markdown(f"`{t['id']}` • {t['story_points']} SP • Module: `{t.get('module')}`")
                        
                        if t.get("dependencies"):
                            st.caption(f"Depends: {', '.join(t['dependencies'])}")
                            
                        # Rescheduling dropdown
                        sprint_options = [f"Sprint {i+1}" for i in range(len(sprints))]
                        moved_val = st.selectbox(
                            "Schedule:",
                            sprint_options,
                            index=s_idx,
                            key=f"sc_mv_{t['id']}"
                        )
                        target_idx = sprint_options.index(moved_val)
                        if target_idx != s_idx:
                            sprints[s_idx]["tasks"].remove(t)
                            sprints[target_idx]["tasks"].append(t)
                            db.update_project(project["id"], {"stage4_data": {"sprints": sprints}})
                            st.rerun()
                            
        st.markdown("---")
        if st.button("✓ Approve Sprint Plan", type="primary", use_container_width=True):
            db.update_project(project["id"], {
                "current_stage": 5,
                "stage_status": {
                    "1": "completed",
                    "2": "completed",
                    "3": "completed",
                    "4": "completed",
                    "5": "active"
                }
            })
            st.session_state.navigated_stage = 5
            st.rerun()
            
    # STAGE 5: JIRA SYNC
    elif active_stage == 5:
        st.subheader("Stage 5 — Jira Sync")
        
        s5 = project.get("stage5_data", {})
        config = s5.get("jira_config", {})
        status = s5.get("sync_status", "not_started")
        logs = s5.get("sync_logs", [])
        
        col_j1, col_j2 = st.columns([1.2, 1.8])
        
        with col_j1:
            st.markdown("### Credentials")
            j_dom = st.text_input("Domain URL", value=config.get("domain", ""), placeholder="company.atlassian.net")
            j_email = st.text_input("Email", value=config.get("email", ""), placeholder="you@company.com")
            j_tok = st.text_input("API Token", value=config.get("api_token", ""), type="password", placeholder="Token...")
            j_key = st.text_input("Project Key", value=config.get("project_key", ""), placeholder="SOW")
            
            current_config = {
                "domain": j_dom,
                "email": j_email,
                "api_token": j_tok,
                "project_key": j_key
            }
            
            # Connection testing
            if st.button("Test Connection", use_container_width=True):
                if not j_dom or not j_email or not j_tok or not j_key:
                    st.error("All credential fields are required.")
                else:
                    with st.spinner("Verifying credentials..."):
                        jira = JiraService(j_dom, j_email, j_tok, j_key)
                        ok, msg = jira.test_connection()
                        if ok:
                            st.success(msg)
                            st.session_state.jira_tested_streamlit = True
                        else:
                            st.error(msg)
                            st.session_state.jira_tested_streamlit = False
                            
            tested = st.session_state.get("jira_tested_streamlit", False)
            
            # Sync buttons
            if tested:
                sync_label = "Force Re-sync to Jira" if status == "completed" else "Confirm & Push to Jira"
                if st.button(sync_label, type="primary", use_container_width=True):
                    st.session_state.syncing_active_streamlit = True
                    s5["sync_status"] = "syncing"
                    s5["jira_config"] = current_config
                    s5["sync_logs"] = [{"message": "Initiating sync sequence...", "status": "info"}]
                    db.update_project(project["id"], {"stage5_data": s5})
                    st.rerun()
                    
        with col_j2:
            st.markdown("### Sync Terminal Logs")
            
            if st.session_state.get("syncing_active_streamlit", False):
                st.session_state.syncing_active_streamlit = False
                
                terminal = st.empty()
                log_lines = []
                
                def log(msg, stat="info"):
                    log_lines.append({"message": msg, "status": stat})
                    formatted = "\n".join(f"> [{l['status'].upper()}] {l['message']}" for l in log_lines)
                    terminal.code(formatted)
                    # Update DB in real time
                    db.update_project(project["id"], {
                        "stage5_data": {
                            "jira_config": current_config,
                            "sync_status": "syncing",
                            "sync_logs": log_lines
                        }
                    })

                try:
                    jira = JiraService(j_dom, j_email, j_tok, j_key)
                    log("Starting Jira sync sequence...")
                    
                    log("Discovering project Scrum Board...")
                    board_id = jira.get_board_id()
                    if board_id:
                        log(f"Scrum Board discovered: Board ID {board_id}", "success")
                    else:
                        log("No Scrum board discovered. Proceeding with Epics/Issues, Sprints will be skipped.", "warning")
                        
                    # Create Epics
                    modules = project.get("stage1_data", {}).get("modules", [])
                    epic_map = {}
                    for idx, mod in enumerate(modules):
                        name = mod["name"]
                        log(f"Creating Epic for module '{name}' ({idx+1}/{len(modules)})...")
                        try:
                            epic_key = jira.create_epic(name, mod.get("description", ""))
                            epic_map[name] = epic_key
                            log(f"Created Epic Key: {epic_key}", "success")
                        except Exception as e:
                            log(f"Failed to create Epic: {str(e)}", "error")
                            
                    # Sprints & Issues
                    sprints = project.get("stage4_data", {}).get("sprints", [])
                    for sprint in sprints:
                        s_name = sprint["name"]
                        s_tasks = sprint.get("tasks", [])
                        
                        sprint_id = None
                        if board_id:
                            log(f"Creating Sprint '{s_name}'...")
                            try:
                                sprint_id = jira.create_sprint(s_name, sprint.get("goal", ""), board_id)
                                log(f"Created Sprint ID: {sprint_id}", "success")
                            except Exception as e:
                                log(f"Failed creating Sprint: {str(e)}", "error")
                                
                        created_keys = []
                        for t in s_tasks:
                            log(f"Creating issue '{t['title']}'...")
                            epic_key = epic_map.get(t.get("module"))
                            try:
                                key = jira.create_issue(t["title"], t.get("description", ""), t.get("type", "Story"), t.get("priority", "Medium"), epic_key)
                                t["jira_key"] = key
                                created_keys.append(key)
                                log(f"Created Issue Key: {key}", "success")
                            except Exception as e:
                                log(f"Failed to create issue: {str(e)}", "error")
                                
                        db.update_project(project["id"], {"stage4_data": {"sprints": sprints}})
                        
                        if sprint_id and created_keys:
                            log(f"Linking {len(created_keys)} issues to sprint {sprint_id}...")
                            try:
                                jira.add_issues_to_sprint(sprint_id, created_keys)
                                log(f"Linked issues to Sprint '{s_name}' successfully.", "success")
                            except Exception as e:
                                log(f"Failed linking to sprint: {str(e)}", "error")
                                
                    log("Jira synchronization completed successfully!", "success")
                    db.update_project(project["id"], {
                        "stage5_data": {
                            "jira_config": current_config,
                            "sync_status": "completed",
                            "sync_logs": log_lines
                        }
                    })
                    st.rerun()
                except Exception as e:
                    log(f"Critical error during sync: {str(e)}", "error")
                    db.update_project(project["id"], {
                        "stage5_data": {
                            "jira_config": current_config,
                            "sync_status": "failed",
                            "sync_logs": log_lines
                        }
                    })
                    st.rerun()
            else:
                # Render previous run static logs
                if logs:
                    formatted = "\n".join(f"> [{l['status'].upper()}] {l['message']}" for l in logs)
                    st.code(formatted)
                else:
                    st.info("Terminal idle. Test connection and trigger sync to view execution logs.")
                    
            # Complete Sync summary
            if status == "completed":
                st.markdown("### Jira Issue Keys Mapping")
                
                mapping_rows = []
                sprints = project.get("stage4_data", {}).get("sprints", [])
                for sprint in sprints:
                    for t in sprint.get("tasks", []):
                        jira_key = t.get("jira_key", "N/A")
                        link = f"{j_dom}/browse/{jira_key}" if j_dom else ""
                        mapping_rows.append({
                            "Sprint": sprint["name"],
                            "Task Title": t["title"],
                            "Jira Key": jira_key,
                            "Link": link
                        })
                        
                st.dataframe(mapping_rows, use_container_width=True)
else:
    # Landing Placeholder Panel
    st.markdown("<div style='text-align: center; padding: 100px 30px;'><h2>⚡ Welcome to AI Sprint Planner</h2><p style='color:var(--text-muted); font-size:1rem; max-width:600px; margin: 15px auto;'>Select an active project from the sidebar list, or click <strong>Create New Project</strong> at the top of the sidebar to parse meeting transcripts and schedule sprint tasks instantly.</p></div>", unsafe_allow_html=True)
