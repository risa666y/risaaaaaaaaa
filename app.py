import streamlit as st
import pandas as pd
import os
import json
import hashlib

st.set_page_config(page_title="多表格管理系统", layout="wide")

SAVE_DIR = "saved_tables"
os.makedirs(SAVE_DIR, exist_ok=True)

INDEX_FILE = f"{SAVE_DIR}/index.json"
SHOW_FILE = f"{SAVE_DIR}/show_tables.json"
SELECT_FILE = f"{SAVE_DIR}/select_options.json"
NOTICE_FILE = f"{SAVE_DIR}/notice.json"  # 公告栏存储

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
        return pd.read_excel(path, dtype=str).fillna("")
    return None

def get_tables():
    idx = load_json(INDEX_FILE, {})
    opts, mp = [], {}
    for tid, info in idx.items():
        label = f"{info['upload_time']} | {info['filename']}"
        opts.append(label)
        mp[label] = tid
    return sorted(opts, reverse=True), mp

def load_notice():
    return load_json(NOTICE_FILE, {"text": ""}).get("text", "")

def save_notice(text):
    save_json({"text": text}, NOTICE_FILE)

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
    st.sidebar.subheader("上传表格")

    files = st.sidebar.file_uploader("上传Excel", type=["xlsx"], accept_multiple_files=True)

    if st.sidebar.button("确认上传"):
        for f in files:
            df = pd.read_excel(f)
            if "供应商简称" not in df.columns:
                st.sidebar.error(f"{f.name}缺少列")
                continue

            tid = gen_id(f.name)
            save_excel(df, tid)

            idx = load_json(INDEX_FILE, {})
            idx[tid] = {
                "filename": f.name,
                "upload_time": str(pd.Timestamp.now())
            }
            save_json(idx, INDEX_FILE)

        st.sidebar.success("上传完成")

# ================= 表格列表 =================
options, mp = get_tables()

if is_admin:
    st.sidebar.divider()

st.sidebar.subheader("表格列表")
# ✅ 完全保留原有下拉逻辑
selected_label = st.sidebar.selectbox("选择表格查看", options)
selected_tid = mp[selected_label] if selected_label else None

# ================= 公告栏 =================
st.subheader("📢 公告栏")
if is_admin:
    notice_text = st.text_area("编辑公告", value=load_notice(), height=100)
    if st.button("更新公告"):
        save_notice(notice_text)
        st.success("公告已更新")
else:
    st.info(load_notice() or "暂无公告")

# ================= 表格展示 =================
if selected_tid:
    df = load_excel(selected_tid)
    if df is not None:
        st.write(f"显示表格: {selected_label}")
        st.dataframe(df)

        if is_admin:
            if st.button("删除该表格"):
                os.remove(f"{SAVE_DIR}/{selected_tid}.xlsx")
                idx = load_json(INDEX_FILE, {})
                if selected_tid in idx:
                    idx.pop(selected_tid)
                    save_json(idx, INDEX_FILE)
                st.success("删除成功")
                st.experimental_rerun()
    else:
        st.warning("表格文件不存在或已被删除")
