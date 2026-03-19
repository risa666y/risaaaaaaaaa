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

# 小写统一（防止输错）
USER_MAP = {u.lower(): k for k, v in SUPPLIER_CONFIG.items() for u in v}

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
        df = pd.read_excel(path, dtype=str)

        # ✅ 清洗
        df = df.dropna(how="all")
        df.columns = df.columns.astype(str).str.strip()

        if "供应商简称" in df.columns:
            df["供应商简称"] = df["供应商简称"].astype(str).str.strip()

        # ✅ 加ID防错位
        if "ID" not in df.columns:
            df.insert(0, "ID", range(len(df)))

        return df
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
        if u.lower() in ADMIN_USERS or u.lower() in USER_MAP:
            st.session_state.user = u.lower()
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
        df = pd.read_excel(file, dtype=str)

        # 清洗
        df = df.dropna(how="all")
        df.columns = df.columns.astype(str).str.strip()

        if "供应商简称" in df.columns:
            df["供应商简称"] = df["供应商简称"].astype(str).str.strip()

        # 加ID
        df.insert(0, "ID", range(len(df)))

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

if df is None:
    st.error("读取失败")
    st.stop()

# ===== 商家端过滤 =====
if not is_admin:
    supplier = USER_MAP[user].strip()

    st.write("你的供应商：", supplier)  # 可删

    if "供应商简称" not in df.columns:
        st.error("❌ 表格缺少【供应商简称】列")
        st.stop()

    filtered_df = df[df["供应商简称"] == supplier]

    if filtered_df.empty:
        st.error("❌ 没有找到你的数据，请检查名称是否一致")
        st.write("表格中的供应商：", df["供应商简称"].unique())
        st.stop()

    df = filtered_df

# ===== 编辑 =====
edited = st.data_editor(df, use_container_width=True)

# ===== 保存 =====
if st.button("💾 保存"):
    original = load_excel(tid).set_index("ID")
    edited = edited.set_index("ID")

    if not is_admin:
        supplier = USER_MAP[user]

        # 只更新自己行
        for idx in edited.index:
            if edited.loc[idx, "供应商简称"] == supplier:
                for col in original.columns:
                    if pd.notna(original.loc[idx, col]):
                        edited.loc[idx, col] = original.loc[idx, col]

    original.update(edited)
    save_excel(original.reset_index(), tid)

    st.success("保存成功")

# ===== 管理端监控 =====
if is_admin:
    st.divider()
    st.subheader("📊 未填写监控")

    missing = check_missing(load_excel(tid))

    if missing:
        st.error("未填写：" + ", ".join(missing))
    else:
        st.success("全部已完成")

# ===== 提醒 =====
if is_admin and missing:
    msg = st.text_area("提醒内容", "请尽快填写表格")

    if st.button("🚨 发送提醒"):
        remind = load_json(REMIND_FILE, {})

        for supplier in missing:
            users = SUPPLIER_CONFIG.get(supplier, [])
            for u in users:
                remind[u.lower()] = msg

        save_json(remind, REMIND_FILE)
        st.success("已发送")

# ===== 商家提醒 =====
if not is_admin:
    remind = load_json(REMIND_FILE, {})

    if user in remind:
        st.warning(f"📢 管理员提醒：{remind[user]}")
        st.toast("你被提醒了")

        remind.pop(user)
        save_json(remind, REMIND_FILE)
