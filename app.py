import streamlit as st
import sqlite3
from datetime import datetime
import random, string

DB_PATH = "failforward.db"

def init_db():
    with sqlite3.connect(DB_PATH) as con:
        con.execute("""
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            role TEXT NOT NULL,
            nickname TEXT,
            is_anonymous INTEGER NOT NULL DEFAULT 1,
            category TEXT,
            content TEXT NOT NULL,
            hearts INTEGER NOT NULL DEFAULT 0,
            is_flagged INTEGER NOT NULL DEFAULT 0,
            share_code TEXT
        )
        """)
        con.execute("""
        CREATE TABLE IF NOT EXISTS comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            role TEXT NOT NULL,
            nickname TEXT,
            is_anonymous INTEGER NOT NULL DEFAULT 1,
            content TEXT NOT NULL,
            FOREIGN KEY(post_id) REFERENCES posts(id) ON DELETE CASCADE
        )
        """)
init_db()

def gen_share_code(n=6):
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=n))

def crisis_detected(text: str) -> bool:
    if not text: return False
    keywords = ["자살","죽고","죽고싶","목숨","유서","스스로 생","극단적","해치고 싶","살 의미","끝내고 싶","죽을","숨고 싶","사라지고 싶"]
    t = text.strip().lower()
    return any(k.lower() in t for k in keywords)

def get_con(): return sqlite3.connect(DB_PATH)

st.set_page_config(page_title="FailForward – 실패 프레임 전환", page_icon="💬", layout="wide")

with st.sidebar:
    st.header("역할 설정")
    role = st.radio("당신의 역할", ["학생","부모","또래"], horizontal=True)
    nickname = st.text_input("닉네임(선택)", max_chars=20)
    is_anon = st.checkbox("익명으로 활동", value=True)
    st.markdown("---")
    st.caption("위기 시: 112 / 자살예방상담전화 1393(24시간)")

st.title("FailForward 💬")
st.subheader("실패 프레임을 바꾸는 우리 – 학생 × 부모 × 또래 응원 플랫폼 (MVP)")

with st.expander("✍️ 글 쓰기", expanded=False):
    col1, col2 = st.columns([3,1])
    with col1:
        category = st.selectbox("카테고리", ["실패담","감정나눔","감사/응원"])
        content = st.text_area("내용", height=150, placeholder="오늘의 실패/배움/감정/감사의 말을 나눠주세요.")
    with col2:
        share_code_opt = st.checkbox("쉐어코드 생성", value=True)
    if st.button("게시하기", type="primary", use_container_width=True):
        if not content.strip():
            st.error("내용을 입력해주세요.")
        else:
            code = gen_share_code() if share_code_opt else None
            with get_con() as con:
                con.execute(
                    "INSERT INTO posts(created_at,role,nickname,is_anonymous,category,content,share_code) VALUES (?,?,?,?,?,?,?)",
                    (datetime.now().isoformat(timespec="seconds"), role, nickname or None, 1 if is_anon else 0, category, content.strip(), code)
                )
            st.success("게시되었습니다!")
            if code:
                st.info(f"이 글의 쉐어코드: **{code}**")

st.markdown("---")
st.subheader("최근 글")
fc1, fc2, fc3, fc4 = st.columns([1.2,1.2,1.8,1])
with fc1: f_cat  = st.selectbox("카테고리", ["전체","실패담","감정나눔","감사/응원"])
with fc2: f_role = st.selectbox("작성자", ["전체","학생","부모","또래"])
with fc3: f_code = st.text_input("쉐어코드", placeholder="예: ABC123")
with fc4: f_text = st.text_input("검색어", placeholder="키워드")

query = "SELECT id,created_at,role,nickname,is_anonymous,category,content,hearts,is_flagged,share_code FROM posts WHERE 1=1"
params = []
if f_cat != "전체":  query += " AND category=?"; params.append(f_cat)
if f_role != "전체": query += " AND role=?";    params.append(f_role)
if f_code:           query += " AND share_code=?"; params.append(f_code.strip().upper())
if f_text:           query += " AND content LIKE ?"; params.append(f"%{f_text.strip()}%")
query += " ORDER BY id DESC"

with get_con() as con:
    posts = con.execute(query, params).fetchall()

if not posts:
    st.info("표시할 글이 없습니다. 첫 글을 남겨보세요!")
else:
    for pid, created_at, prole, pnick, panon, pcat, pcontent, hearts, flagged, share_code in posts:
        with st.container(border=True):
            c1,c2,c3,c4 = st.columns([1,1,2,2])
            with c1: st.caption(f"#{pid}"); st.write(f"**[{pcat}]**")
            with c2:
                who = f"{prole} · {(pnick if (panon==0 and pnick) else '익명')}"
                st.write(who); st.caption(created_at.replace("T"," "))
            with c3:
                if share_code: st.caption(f"쉐어코드: {share_code}")
            with c4:
                b1,b2 = st.columns(2)
                with b1:
                    if st.button(f"응원 ❤️ {hearts}", key=f"h_{pid}"):
                        with get_con() as con:
                            con.execute("UPDATE posts SET hearts=hearts+1 WHERE id=?", (pid,))
                        st.experimental_rerun()
                with b2:
                    if st.button("신고 🚩", key=f"f_{pid}"):
                        with get_con() as con:
                            con.execute("UPDATE posts SET is_flagged=1 WHERE id=?", (pid,))
                        st.warning("신고되었습니다.")
            st.write(pcontent)
            if crisis_detected(pcontent):
                st.error("⚠️ 위기 신호 감지. 112 / 1393에 즉시 연락하세요.")

            with get_con() as con:
                comments = con.execute(
                    "SELECT id,created_at,role,nickname,is_anonymous,content FROM comments WHERE post_id=? ORDER BY id ASC", (pid,)
                ).fetchall()
            st.markdown("**댓글**")
            if not comments:
                st.caption("아직 댓글이 없습니다.")
            else:
                for cid, ctime, crole, cnick, canon, ccontent in comments:
                    who = f"{crole} · {(cnick if (canon==0 and cnick) else '익명')}"
                    st.write(f"- *{who}* ({ctime.replace('T',' ')}): {ccontent}")
                    if crisis_detected(ccontent):
                        st.error("⚠️ 댓글에 위기 신호 감지. 112 / 1393")
            st.markdown("—")
            t1,t2 = st.columns([3,1])
            with t1:
                new_c = st.text_input("응원/댓글 남기기", key=f"c_{pid}", placeholder="따뜻한 말 한마디가 큰 힘이 됩니다.")
            with t2:
                if st.button("댓글 등록", key=f"cb_{pid}"):
                    if not new_c.strip():
                        st.warning("댓글 내용을 입력해주세요.")
                    else:
                        with get_con() as con:
                            con.execute(
                                "INSERT INTO comments(post_id,created_at,role,nickname,is_anonymous,content) VALUES (?,?,?,?,?,?)",
                                (pid, datetime.now().isoformat(timespec="seconds"), role, nickname or None, 1, new_c.strip())
                            )
                        st.success("댓글이 등록되었습니다.")
                        st.experimental_rerun()

st.markdown("---")
st.caption("© FailForward – 교육용 MVP. 위기 시 112 / 1393 / 지역 정신건강복지센터")
