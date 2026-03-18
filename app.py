import streamlit as st
import pandas as pd
import os
import json
import hashlib

st.set_page_config(page_title="表格管理 + 自动催填", layout="wide")

SAVE_DIR = "saved_tables"
os.makedirs(SAVE_DIR, exist_ok=True)

INDEX_FILE = f"{SAVE_DIR}/index.json"

# ================= 用户 =================
SUPPLIER_CONFIG = {
    "恒尚": ["A小康先森"],
    "福蕾雅": ["严金虹"],
    "杰祥": ["金刚小婷", "杰祥服饰", "x"],
    "纪梵黎": ["代**"]
}
ADMIN_USERS = {"admin"}
USER_MAP = {u: k for k, v in SUPPLIER_CONFIG.items() for u in v}

# ================= 工具 =================
def load_json(path, default={}):
    if os.path.exists(path):
        return json.load(open(path, "r", encoding="utf-8"))
    return default

def save_json(data, path):
    json.dump(data, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

def gen_id(name):
    return hashlib.md5((name+str(pd.Timestamp.now())).encode()).hexdigest()[:10]

def save_excel(df, tid):
    df.to_excel(f"{SAVE_DIR}/{tid}.xlsx", index=False)

def load_excel(tid):
    path = f"{SAVE_DIR}/{tid}.xlsx"
    if os.path.exists(path):
        return pd.read_excel(path, dtype=str)
    return None

def get_tables():
    idx = load_json(INDEX_FILE, {})
    opts, mp = [], {}
    for tid, info in idx.items():
        label = f"{info['upload_time']} | {info['filename']}"
        opts.append(label)
        mp[label] = tid
    return sorted(opts, reverse=True), mp

# ================= 填写检测 =================
def check_fill_status(df):
    df = df.replace("", pd.NA)

    total_cells = df.shape[0] * df.shape[1]
    empty_cells = df.isna().sum().sum()

    fill_rate = 1 - empty_cells / total_cells if total_cells > 0 else 1

    missing_users = []
    if "供应商简称" in df.columns:
        missing_rows = df[df.isna().any(axis=1)]
        missing_users = missing_rows["供应商简称"].dropna().tolist()

    return {
        "fill_rate": round(fill_rate * 100, 1),
        "missing_users": list(set(missing_users))
    }

# ================= 催人 =================
def generate_all_reminders(results):
    lines = ["【今日填表提醒】\n"]

    for name, users in results.items():
        if users:
            lines.append(f"📌 {name}：{', '.join(users)}")

    lines.append("\n请尽快完成填写 🙏")

    return "\n".join(lines)

# ================= 登录 =================
if "user" not in st.session_state:
    st.session_state.user = None

with st.sidebar:
    st.title("登录")
    username = st.text_input("用户名")

    if st.button("登录"):
        if username in ADMIN_USERS or username in USER_MAP:
            st.session_state.user = username
            st.rerun()
        else:
            st.error("用户不存在")

    if st.button("退出"):
        st.session_state.user = None
        st.rerun()

user = st.session_state.user
if not user:
    st.stop()

is_admin = user in ADMIN_USERS

# ================= 上传 =================
if is_admin:
    st.sidebar.divider()
    files = st.sidebar.file_uploader("上传Excel", type=["xlsx"], accept_multiple_files=True)

    if st.sidebar.button("确认上传"):
        for f in files:
            df = pd.read_excel(f)

            tid = gen_id(f.name)
            save_excel(df, tid)

            idx = load_json(INDEX_FILE, {})
            idx[tid] = {
                "filename": f.name,
                "upload_time": str(pd.Timestamp.now())
            }
            save_json(idx, INDEX_FILE)

        st.sidebar.success("上传完成")

# ================= 总览（核心） =================
st.subheader("📊 待填写监控")

options, mp = get_tables()

all_missing = {}

for name in options:
    tid = mp[name]
    df = load_excel(tid)

    if df is None:
        continue

    res = check_fill_status(df)

    if res["missing_users"]:
        all_missing[name] = res["missing_users"]

        st.error(f"{name}：未填写 {len(res['missing_users'])} 人")
        st.write("👉", ", ".join(res["missing_users"]))

# ================= 一键催人 =================
st.divider()

if all_missing:
    st.subheader("🚀 一键催所有人")

    if st.button("生成催填消息"):
        msg = generate_all_reminders(all_missing)
        st.session_state["msg"] = msg

if "msg" in st.session_state:
    st.subheader("📢 复制后发群")
    st.code(st.session_state["msg"], language="text")

# ================= 表格查看 =================
st.divider()
st.subheader("📋 表格查看")

if options:
    sel = st.selectbox("选择表格", options)
    tid = mp[sel]

    df = load_excel(tid)

    if not is_admin:
        supplier = USER_MAP[user]
        df = df[df["供应商简称"] == supplier]

    edited = st.data_editor(df, use_container_width=True)

    if st.button("保存"):
        save_excel(edited, tid)
        st.success("已保存")
