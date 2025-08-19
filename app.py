# FailForward – 실패 프레임 전환 (학생 × 부모 × 또래) MVP
# 실행: streamlit run app.py

import streamlit as st
import sqlite3
from datetime import datetime
import random, string, os
import hashlib

# ---------- 환경 설정 ----------
# Cloud(스트림릿)에서는 /tmp가 쓰기 가능. 로컬은 현재 폴더에 파일 생성.
DB_PATH = os.environ.get("FF_DB_PATH", "/tmp/failforward.db" if os.path.isdir("/tmp") else "failforward.db")

st.set_page_config(page_title="FailForward – 실패 프레임 전환", page_icon="💬", layout="wide")

# ---------- DB ----------
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
        """)
        con.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL,
            nickname TEXT
        )
        """)
init_db()

def get_con():
    return sqlite3.connect(DB_PATH)

def gen_share_code(n=6):
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=n))

def crisis_detected(text: str) -> bool:
    if not text:
        return False
    keywords = [
        "자살", "죽고", "죽고싶", "목숨", "유서", "스스로 생", "극단적",
        "해치고 싶", "살 의미", "끝내고 싶", "죽을", "숨고 싶", "사라지고 싶"
    ]
    t = text.strip().lower()
    return any(k.lower() in t for k in keywords)

def role_sanitize(role: str) -> str:
    return role if role in {"학생", "부모", "또래"} else "학생"

def hash_pw(pw: str) -> str:
   return hashlib.sha256(pw.encode()).hexdigest()

# ---------- 사이드바 (로그인/회원가입) ----------
user = st.session_state.get("user")
with st.sidebar:
   if not user:
       st.header("로그인 / 회원가입")
       tab_login, tab_signup = st.tabs(["로그인", "회원가입"])
       with tab_login:
           l_user = st.text_input("아이디", key="l_user")
           l_pw = st.text_input("비밀번호", type="password", key="l_pw")
           if st.button("로그인", key="login_btn"):
               with get_con() as con:
                   row = con.execute(
                       "SELECT id, username, role, nickname FROM users WHERE username=? AND password=?",
                       (l_user, hash_pw(l_pw)),
                   ).fetchone()
               if row:
                   st.session_state.user = {
                       "id": row[0],
                       "username": row[1],
                       "role": row[2],
                       "nickname": row[3],
                   }
                   st.success("로그인되었습니다.")
                   st.rerun()
               else:
                   st.error("아이디 또는 비밀번호가 올바르지 않습니다.")
       with tab_signup:
           s_user = st.text_input("아이디", key="s_user")
           s_pw = st.text_input("비밀번호", type="password", key="s_pw")
           s_role = st.selectbox("역할", ["학생", "부모", "또래"], key="s_role")
           s_nick = st.text_input("닉네임", key="s_nick")
           if st.button("회원가입", key="signup_btn"):
               if not s_user or not s_pw:
                   st.error("아이디와 비밀번호를 입력하세요.")
               else:
                   with get_con() as con:
                       exists = con.execute(
                           "SELECT 1 FROM users WHERE username=?", (s_user,)
                       ).fetchone()
                       if exists:
                           st.error("이미 존재하는 아이디입니다.")
                       else:
                           con.execute(
                               "INSERT INTO users(username, password, role, nickname) VALUES (?, ?, ?, ?)",
                               (s_user, hash_pw(s_pw), role_sanitize(s_role), s_nick.strip() or None),
                           )
                           st.success("회원가입 완료! 로그인 해주세요.")
   else:
       st.header("프로필")
       st.write(f"{user['nickname'] or user['username']} ({user['role']})")
       if st.button("로그아웃"):
           del st.session_state["user"]
           st.rerun()

    
st.markdown("---")
st.caption("위기 시: 112 / 자살예방상담전화 1393(24시간) / 지역 정신건강복지센터")

# ---------- 페이지 헤더 ----------
st.title("FailForward 💬")
st.subheader("실패 프레임을 바꾸는 우리 – 학생 × 부모 × 또래 응원 플랫폼 (MVP)")

role = user["role"] if user else None
nickname = user["nickname"] if user else None

# ---------- 글 작성 ----------
if user:
   with st.expander("✍️ 글 쓰기 (학생/부모/또래 누구나)", expanded=False):
       col1, col2 = st.columns([3, 1])
       with col1:
           category = st.selectbox("카테고리", ["실패담", "감정나눔", "감사/응원"], index=0)
           content = st.text_area("내용", height=150, placeholder="오늘의 실패/배움/감정/감사의 말을 나눠주세요.")
       with col2:
           want_code = st.checkbox("가족과 공유할 '쉐어코드' 생성", value=True)
           anon_post = st.checkbox("익명으로 게시", value=True)

       if st.button("게시하기", type="primary", use_container_width=True):
           if not content.strip():
               st.error("내용을 입력해주세요.")
           else:
               code = gen_share_code() if want_code else None
               with get_con() as con:
                   con.execute(
                       "INSERT INTO posts(created_at, role, nickname, is_anonymous, category, content, share_code) "
                       "VALUES (?, ?, ?, ?, ?, ?, ?)",
                       (datetime.now().isoformat(timespec="seconds"),
                        role, nickname, 1 if anon_post else 0,
                        category, content.strip(), code)
                   )
               st.success("게시되었습니다! 아래 목록에서 확인하세요.")
               if code:
                   st.info(f"이 글의 쉐어코드: **{code}** (가족/친구와 공유하세요)")
               st.rerun()
else:
   st.info("글을 쓰려면 로그인하세요.")

# ---------- 필터 ----------
st.markdown("---")
st.subheader("최근 글")

fc1, fc2, fc3, fc4 = st.columns([1.2, 1.2, 1.8, 1])
with fc1:
    f_cat = st.selectbox("카테고리", ["전체", "실패담", "감정나눔", "감사/응원"], index=0)
with fc2:
    f_role = st.selectbox("작성자", ["전체", "학생", "부모", "또래"], index=0)
with fc3:
    f_code = st.text_input("쉐어코드로 찾기", placeholder="예: ABC123")
with fc4:
    f_text = st.text_input("검색어", placeholder="키워드")

query = """
SELECT id, created_at, role, nickname, is_anonymous, category, content, hearts, is_flagged, share_code
FROM posts WHERE 1=1
"""
params = []
if f_cat != "전체":
    query += " AND category=?"
    params.append(f_cat)
if f_role != "전체":
    query += " AND role=?"

            # 위기 안내
if crisis_detected(pcontent):
                st.error("⚠️ 위기 신호가 감지되었습니다. 즉시 도움을 요청하세요. 112 / 자살예방상담전화 1393(24시간)")
                st.info("교내 상담실/담임/보호자와 상의하세요. 당신은 혼자가 아닙니다.")

            # 댓글 출력
            with get_con() as con:
comments = con.execute(
                    "SELECT id, created_at, role, nickname, is_anonymous, content "
                    "FROM comments WHERE post_id=? ORDER BY id ASC",
                    (pid,)
                ).fetchall()

            st.markdown("**댓글**")
            if not comments:
                st.caption("아직 댓글이 없습니다. 첫 응원을 남겨보세요.")
            else:
                for cid, ctime, crole, cnick, canon, ccontent in comments:
                    who_c = f"{crole} · {(cnick if (canon == 0 and cnick) else '익명')}"
                    st.write(f"- *{who_c}* ({ctime.replace('T', ' ')}): {ccontent}")
                    if crisis_detected(ccontent):
                        st.error("⚠️ 댓글에 위기 신호가 감지되었습니다. 112 / 1393")

            # 댓글 입력
           if user:
               st.markdown("—")
               cc1, cc2 = st.columns([3, 1.2])
               with cc1:
                   new_c = st.text_input(
                       "응원/댓글 남기기",
                       key=f"c_{pid}",
                       placeholder="따뜻한 말 한마디가 큰 힘이 됩니다.",
                   )
               with cc2:
                   anon_c = st.checkbox("익명", value=True, key=f"anon_{pid}")
                   if st.button("댓글 등록", key=f"cbtn_{pid}"):
                       if not new_c.strip():
                           st.warning("댓글 내용을 입력해주세요.")
                       else:
                           with get_con() as con:
                               con.execute(
                                   "INSERT INTO comments(post_id, created_at, role, nickname, is_anonymous, content) "
                                   "VALUES (?, ?, ?, ?, ?, ?)",
                                   (
                                       pid,
                                       datetime.now().isoformat(timespec="seconds"),
                                       role,
                                       nickname,
                                       1 if anon_c else 0,
                                       new_c.strip(),
                                   ),
                               )
                           st.success("댓글이 등록되었습니다.")
                           st.rerun()
           else:
               st.info("댓글을 남기려면 로그인하세요.")

st.markdown("---")
st.caption("© FailForward – 교육용 MVP. 위기 시 112 / 1393 / 지역 정신건강복지센터")
