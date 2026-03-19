import streamlit as st
import pandas as pd
import os, json, time

st.set_page_config(page_title="供应商填表系统", layout="wide")

SAVE_DIR = "saved_tables"
os.makedirs(SAVE_DIR, exist_ok=True)
INDEX_FILE = f"{SAVE_DIR}/index.json"

# ===== 用户 =====
SUPPLIER_CONFIG = {
    "恒尚": ["A小康先森"],
    "福蕾雅": ["严金虹"],
    "杰祥": ["金刚小婷", "杰祥服饰"],
}
ADMIN_USERS = {"admin"}
USER_MAP = {u.lower(): k for k, v in SUPPLIER_CONFIG.items() for u in v}

# ===== 工具 =====
def load_json(path, default={}):
    if os.path.exists(path):
        return json.load(open(path, "r", encoding="utf-8"))
    return default

def save_json(data, path):
    json.dump(data, open(path, "w", encoding="utf-8"), ensure_ascii=False)

def save_excel(df, tid):
    path = f"{SAVE_DIR}/{tid}.xlsx"
    df.to_excel(path, index=False)

def load_excel(tid):
    path = f"{SAVE_DIR}/{tid}.xlsx"
    if not os.path.exists(path):
        return None

    df = pd.read_excel(path, dtype=str)
    df = df.dropna(how="all")
    df.columns = df.columns.str.strip()

    if "供应商简称" in df.columns:
        df["供应商简称"] = df["供应商简称"].astype(str).str.strip()

    if "ID" not in df.columns:
        df.insert(0, "ID", range(len(df)))

    df["ID"] = df["ID"].astype(str)
    return df

# ===== 登录 =====
with st.sidebar:
    st.title("登录")
    u = st.text_input("用户名")

    if st.button("登录"):
        if u.lower() in ADMIN_USERS or u.lower() in USER_MAP:
            st.session_state.user = u.lower()
            st.rerun()
        else:
            st.error("用户不存在")

    if st.button("退出"):
        st.session_state.user = None
        st.rerun()

user = st.session_state.get("user")
if not user:
    st.stop()

is_admin = user in ADMIN_USERS

# ===== 上传 =====
with st.sidebar:
    if is_admin:
        st.subheader("上传表格")
        file = st.file_uploader("上传Excel", type=["xlsx"])

        if file:
            idx = load_json(INDEX_FILE, {})
            df = pd.read_excel(file, dtype=str)
            df.insert(0, "ID", range(len(df)))

            tid = str(int(time.time()))
            save_excel(df, tid)

            idx[tid] = {"filename": file.name, "visible": True}
            save_json(idx, INDEX_FILE)

            st.success("上传成功")
            st.rerun()

# ===== 表格选择 =====
idx = load_json(INDEX_FILE, {})
options = [i["filename"] for i in idx.values()]
tid_map = {i["filename"]: k for k, i in idx.items()}

table_name = st.selectbox("选择表格", options)
tid = tid_map[table_name]

df = load_excel(tid)

# ===== 商家过滤 =====
if not is_admin:
    supplier = USER_MAP[user]
    df = df[df["供应商简称"] == supplier]

if df is None or df.empty:
    st.warning("无数据")
    st.stop()

# ===== 版本控制 =====
file_path = f"{SAVE_DIR}/{tid}.xlsx"
file_mtime = os.path.getmtime(file_path)

if "last_mtime" not in st.session_state:
    st.session_state.last_mtime = file_mtime

# ===== 编辑器 =====
edited = st.data_editor(df, use_container_width=True, key="editor")

# ===== 自动保存（企业稳定版）=====
if not edited.equals(df):

    # 冲突检测
    current_mtime = os.path.getmtime(file_path)

    if current_mtime != st.session_state.last_mtime:
        st.warning("⚠️ 数据已被他人修改，已自动刷新")
        st.rerun()

    df_latest = pd.read_excel(file_path, dtype=str)
    df_latest.set_index("ID", inplace=True)

    edited = edited.set_index("ID")

    # 商家限制
    if not is_admin:
        edited = edited[edited["供应商简称"] == supplier]

    # 只更新变化值
    for i in edited.index:
        for col in edited.columns:
            if df_latest.loc[i, col] != edited.loc[i, col]:
                df_latest.loc[i, col] = edited.loc[i, col]

    df_latest.reset_index().to_excel(file_path, index=False)

    st.session_state.last_mtime = os.path.getmtime(file_path)

    st.toast("已自动保存")
