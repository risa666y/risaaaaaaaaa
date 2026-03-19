import streamlit as st
import pandas as pd
import os, json, time

st.set_page_config(page_title="供应商填表系统", layout="wide")

# ===== 路径 =====
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
    df.to_excel(f"{SAVE_DIR}/{tid}.xlsx", index=False)

def load_excel(tid):
    path = f"{SAVE_DIR}/{tid}.xlsx"
    if os.path.exists(path):
        df = pd.read_excel(path, dtype=str)
        df = df.dropna(how="all")
        df.columns = df.columns.str.strip()

        if "供应商简称" in df.columns:
            df["供应商简称"] = df["供应商简称"].astype(str).str.strip()

        if "ID" not in df.columns:
            df.insert(0, "ID", range(len(df)))

        return df
    return None

# ===== 登录 =====
with st.sidebar:
    st.title("🔐 登录")
    u = st.text_input("用户名")

    if st.button("登录"):
        if u.lower() in ADMIN_USERS or u.lower() in USER_MAP:
            st.session_state.user = u.lower()
            st.session_state.last_refresh = time.time()
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

# ===== 管理端侧边栏 =====
with st.sidebar:
    if is_admin:
        st.divider()
        st.subheader("📤 上传表格")

        file = st.file_uploader("上传Excel", type=["xlsx"])

        if file:
            idx = load_json(INDEX_FILE, {})

            if file.name in [i["filename"] for i in idx.values()]:
                st.warning("该表已存在")
            else:
                df = pd.read_excel(file, dtype=str)
                df = df.dropna(how="all")
                df.columns = df.columns.str.strip()

                if "供应商简称" in df.columns:
                    df["供应商简称"] = df["供应商简称"].astype(str).str.strip()

                df.insert(0, "ID", range(len(df)))

                tid = str(int(time.time()))
                save_excel(df, tid)

                idx[tid] = {"filename": file.name, "visible": True}
                save_json(idx, INDEX_FILE)

                st.success("上传成功")
                st.rerun()

        # ===== 表格管理 =====
        st.divider()
        st.subheader("📂 表格管理")

        idx = load_json(INDEX_FILE, {})
        updated = False

        for tid, info in list(idx.items()):
            col1, col2, col3 = st.columns([2,1,1])

            with col1:
                st.write(info["filename"])

            with col2:
                visible = st.checkbox(
                    "显示",
                    value=info.get("visible", True),
                    key=f"vis_{tid}"
                )

                if visible != info.get("visible", True):
                    idx[tid]["visible"] = visible
                    updated = True

            with col3:
                if st.button("删除", key=f"del_{tid}"):
                    os.remove(f"{SAVE_DIR}/{tid}.xlsx")
                    idx.pop(tid)
                    save_json(idx, INDEX_FILE)
                    st.rerun()

        if updated:
            save_json(idx, INDEX_FILE)

# ===== 主界面 =====
st.title("📊 供应商填表系统")

# ===== 管理员自动刷新（已修复不卡登录）=====
if is_admin:
    now = time.time()
    last = st.session_state.get("last_refresh", 0)

    if now - last > 2:
        st.session_state.last_refresh = now
        st.rerun()

# ===== 表格选择 =====
idx = load_json(INDEX_FILE, {})
options, mp = [], {}

for tid, info in idx.items():
    if info.get("visible", True):
        options.append(info["filename"])
        mp[info["filename"]] = tid

if not options:
    st.warning("暂无表格")
    st.stop()

table_name = st.selectbox("选择表格", options)
tid = mp[table_name]

df = load_excel(tid)

# ===== 商家过滤 =====
if not is_admin:
    supplier = USER_MAP[user]

    if "供应商简称" not in df.columns:
        st.error("缺少供应商列")
        st.stop()

    df = df[df["供应商简称"] == supplier]

    if df.empty:
        st.error("没有你的数据")
        st.stop()

# ===== 自动保存 =====
def auto_save():
    path = f"{SAVE_DIR}/{tid}.xlsx"

    df_new = st.session_state["edited_df"]
    df_latest = pd.read_excel(path, dtype=str)

    df_latest.set_index("ID", inplace=True)
    df_new = df_new.set_index("ID")

    if not is_admin:
        supplier = USER_MAP[user]
        df_new = df_new[df_new["供应商简称"] == supplier]

    for i in df_new.index:
        for col in df_new.columns:
            df_latest.loc[i, col] = df_new.loc[i, col]

    df_latest.reset_index().to_excel(path, index=False)

# ===== 表格编辑 =====
edited = st.data_editor(
    df,
    key="edited_df",
    use_container_width=True,
    on_change=auto_save
)
