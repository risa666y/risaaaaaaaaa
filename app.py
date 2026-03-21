import streamlit as st
import pandas as pd
import os
import json
import time
import uuid
import sqlite3
from streamlit_js_eval import streamlit_js_eval

st.set_page_config(layout="wide")

SAVE_DIR = "saved_tables"
os.makedirs(SAVE_DIR, exist_ok=True)

DB_FILE = f"{SAVE_DIR}/data.db"

INDEX_FILE = f"{SAVE_DIR}/index.json"
SHOW_FILE = f"{SAVE_DIR}/show_tables.json"
SELECT_FILE = f"{SAVE_DIR}/select_options.json"
PROGRESS_FILE = f"{SAVE_DIR}/progress.json"
NOTICE_FILE = f"{SAVE_DIR}/notice.json"

# ================= 数据库 =================
def get_conn():
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL;")  # ✅ 提升并发
    return conn

def save_to_db(df, tid):
    with get_conn() as conn:
        df.to_sql(tid, conn, if_exists="replace", index=False)

def load_table(tid):
    with get_conn() as conn:
        try:
            df = pd.read_sql(f"SELECT * FROM '{tid}'", conn)
        except:
            df = pd.DataFrame()

    if not df.empty:
        df = df.fillna("")
        df.columns = df.columns.str.strip()

        if "供应商简称" in df.columns:
            df["供应商简称"] = df["供应商简称"].astype(str).str.strip()

        if "ID" not in df.columns:
            df.insert(0, "ID", [uuid.uuid4().hex[:8] for _ in range(len(df))])

    return df

# ================= 用户 =================
SUPPLIER_CONFIG = {
    "纪梵黎": ["代**"], "铭润": ["dryson", "7Zz"], "康林": ["Tau"],
    "卓黎凯": ["杨小方的小方"], "依嘉依": ["陈"], "华中": ["钧之", "木木"],
    "函厦": ["邓红玫"], "凡迪": ["凡迪"], "赛西": ["Z"],
    "泽亿": ["西红柿"], "阿西": ["阿伟"], "锦裳坊": ["汪宝辉"],
    "涅瓦": ["李大大"], "布列瑟侬": ["小趴菜"], "达芬奇": ["宏林仓库"],
    "顺兰": ["雄"], "星尚美": ["7!"], "穆林达": ["苗子"],
    "俏衣人": ["俏依人"], "鸿盛达": ["RONG"], "聚图": ["聚图"],
    "柏雅": ["Hollow City"], "同顺": ["守有"], "云贸": ["Koi"],
    "白蚁": ["我的梦想"], "大行家1": ["大行家1"], "西永": ["西永"],
    "肯蒂": ["Silent"], "天正": ["Tsuki"], "蒂洛诗": ["蒂洛诗"],
    "温士顿": ["ou"], "方元": ["selina"], "洛艾依": ["燕姐"],
    "正气": ["尽欢"], "博果": ["Ai"], "魅裙": ["Eiker"],
    "初纷梦": ["熊妮"], "卡奇豪": ["卡奇豪"], "合凡": ["起风了"],
    "博果尔": ["刘权"], "青罗帐": ["青罗帐"], "金鸣": ["金鸣"],
    "龙馨": ["龙馨"], "独秀": ["老虎"], "恒尚": ["A小康先森"],
    "福蕾雅": ["严金虹"], "杰祥": ["金刚小婷", "杰祥服饰"]
}

ADMIN_USERS = {"RISA"}
USER_MAP = {u: k for k, v in SUPPLIER_CONFIG.items() for u in v}

# ================= 工具 =================
def load_json(path, default):
    if os.path.exists(path):
        return json.load(open(path, "r", encoding="utf-8"))
    return default

def save_json(data, path):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)

def gen_id():
    return uuid.uuid4().hex[:12]

def get_tables():
    idx = load_json(INDEX_FILE, {})
    opts, mp = [], {}
    for tid, info in idx.items():
        label = f"{info['upload_time']} | {info['filename']}"
        opts.append(label)
        mp[label] = tid
    return sorted(opts, reverse=True), mp

# ================= 登录状态（核心升级） =================
if "user" not in st.session_state:
    st.session_state.user = None

query_params = st.query_params
saved_user = query_params.get("user", [None])[0]

# 从 localStorage 读取历史用户
history_raw = streamlit_js_eval(
    js_expressions="localStorage.getItem('history_users')",
    key="init_history"
)

history = json.loads(history_raw) if history_raw else []
last_user = history[-1] if history else None

# 恢复优先级：URL > localStorage
restore_user = saved_user or last_user

if restore_user and not st.session_state.user:
    if restore_user in ADMIN_USERS or restore_user in USER_MAP:
        st.session_state.user = restore_user
        st.query_params["user"] = restore_user

# ================= Sidebar 登录 =================
with st.sidebar:
    st.subheader("🔐 登录")

    if st.session_state.user:
        st.success(f"当前用户：{st.session_state.user}")

        if st.button("退出"):
            st.session_state.user = None
            st.query_params.clear()
            streamlit_js_eval(
                js_expressions="localStorage.removeItem('history_users')",
                key="clear_user"
            )
            st.rerun()
    else:
        with st.form("login_form"):
            user_input = st.text_input("登录账号", value=last_user or "")
            submit = st.form_submit_button("登录")

            if submit:
                if user_input in ADMIN_USERS or user_input in USER_MAP:
                    st.session_state.user = user_input
                    st.query_params["user"] = user_input

                    if user_input not in history:
                        history.append(user_input)

                    streamlit_js_eval(
                        js_expressions=f"localStorage.setItem('history_users', '{json.dumps(history)}')",
                        key="set_history"
                    )
                    st.rerun()
                else:
                    st.error("用户不存在")

    # ✅ 刷新按钮（不会掉登录）
    st.subheader("🔄 页面控制")

    if st.button("刷新页面"):
        st.rerun()

    if st.button("强制刷新"):
        streamlit_js_eval(
            js_expressions="location.reload()",
            key="force_refresh"
        )

user = st.session_state.user
if not user:
    st.stop()

is_admin = user in ADMIN_USERS

# ================= 后面所有代码完全不变 =================
# 👉（你原来的所有功能，从上传开始，到自动刷新，全部照旧）
