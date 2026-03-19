import streamlit as st
import pandas as pd
import os, json, time

st.set_page_config(page_title="供应商填表系统", layout="wide")

# ===== 路径 =====
SAVE_DIR = "saved_tables"
os.makedirs(SAVE_DIR, exist_ok=True)

INDEX_FILE = f"{SAVE_DIR}/index.json"
REMIND_FILE = f"{SAVE_DIR}/remind.json"

# ===== 用户 =====
SUPPLIER_CONFIG = {
    "恒尚": ["A小康先森"],
    "福蕾雅": ["严金虹"],
    "杰祥": ["金刚小婷", "杰祥服饰"],
}
ADMIN_USERS = {"admin"}
USER_MAP = {u: k for k, v in SUPPLIER_CONFIG.items() for u in v}

# ===== 工具 =====
def load_json(path, default={}):
    if os.path.exists(path):
        return json.load(open(path, "r", encoding="utf-8"))
    return default

def save_json(data, path):
    json.dump(data, open(path, "w", encoding="utf-8"), ensure_ascii=False)

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
        label = info["filename"]
        opts.append(label)
        mp[label] = tid
    return opts, mp

def check_missing(df):
    df = df.replace("", pd.NA)
    if "供应商简称" not in df.columns:
        return []
    missing = df[df.isna().any(axis=1)]["供应商简称"].dropna().tolist()
    return list(set(missing))

# ===== 登录 =====
if "user" not in st.session_state:
    st.session_state.user = None

with st.sidebar:
    st.title("登录")
    u = st.text_input("用户名")

    if st.button("登录"):
        if u in ADMIN_USERS or u in USER_MAP:
            st.session_state.user = u
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

st.title("📊 供应商填表系统")

# ===== 管理端上传 =====
if is_admin:
    st.subheader("📤 上传表格")

    file = st.file_uploader("上传Excel", type=["xlsx"])

    if file:
        df = pd.read_excel(file)

        tid = str(int(time.time()))
        save_excel(df, tid)

        idx = load_json(INDEX_FILE, {})
        idx[tid] = {"filename": file.name}
        save_json(idx, INDEX_FILE)

        st.success("上传成功")

# ===== 表格选择 =====
options, mp = get_tables()

if not options:
    st.warning("⚠️ 还没有表格，请管理员上传")
    st.stop()

table_name = st.selectbox("选择表格", options)
tid = mp[table_name]

df = load_excel(tid)

# ===== 商家端过滤 =====
if not is_admin:
    supplier = USER_MAP[user]
    df = df[df["供应商简称"] == supplier]

# ===== 限制只能填空白 =====
editable_df = df.copy()

for col in df.columns:
    editable_df[col] = df[col]

edited = st.data_editor(editable_df, use_container_width=True)

# ===== 保存逻辑（限制修改）=====
if st.button("💾 保存"):
    original = load_excel(tid)

    if not is_admin:
        supplier = USER_MAP[user]

        for i in range(len(original)):
            if original.loc[i, "供应商简称"] == supplier:
                for col in original.columns:
                    if pd.notna(original.loc[i, col]):
                        edited.loc[i, col] = original.loc[i, col]

    save_excel(edited, tid)
    st.success("保存成功")

# ===== 管理端监控 =====
missing = check_missing(load_excel(tid))

if is_admin:
    st.divider()
    st.subheader("📊 未填写监控")

    if missing:
        st.error("未填写：" + ", ".join(missing))
    else:
        st.success("全部已完成")

# ===== 管理端提醒 =====
if is_admin and missing:
    msg = st.text_area("提醒内容", "请尽快填写表格")

    if st.button("🚨 发送提醒"):
        remind = load_json(REMIND_FILE, {})

        for u in missing:
            remind[u] = msg

        save_json(remind, REMIND_FILE)
        st.success("已发送")

# ===== 商家弹窗 =====
if not is_admin:
    placeholder = st.empty()

    for _ in range(30):
        remind = load_json(REMIND_FILE, {})

        if user in remind:
            placeholder.warning(f"📢 管理员提醒：{remind[user]}")
            st.toast("你被提醒了")

            remind.pop(user)
            save_json(remind, REMIND_FILE)

            time.sleep(5)
            placeholder.empty()
            break

        time.sleep(3)
