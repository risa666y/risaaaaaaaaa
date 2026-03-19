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

@st.cache_data
def load_excel_cached(tid):
    path = f"{SAVE_DIR}/{tid}.xlsx"
    if os.path.exists(path):
        df = pd.read_excel(path, dtype=str)
        df = df.dropna(how="all")
        df.columns = df.columns.astype(str).str.strip()

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

        # ===== 上传 =====
        st.divider()
        st.subheader("📤 上传表格")

        file = st.file_uploader("上传Excel", type=["xlsx"])

        if file:
            idx = load_json(INDEX_FILE, {})

            # 防重复上传
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

                idx[tid] = {
                    "filename": file.name,
                    "visible": True,
                    "select_cols": {}
                }
                save_json(idx, INDEX_FILE)

                st.success("上传成功")
                st.rerun()

        # ===== 表格管理（已修复重复问题）=====
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

        # ===== 下拉配置 =====
        st.divider()
        st.subheader("⚙️ 下拉选项配置")

        table_names = [info["filename"] for info in idx.values()]

        if table_names:
            selected_table = st.selectbox("选择表", table_names)

            tid_map = {info["filename"]: tid for tid, info in idx.items()}
            tid_cfg = tid_map[selected_table]

            df_cfg = load_excel_cached(tid_cfg)

            if df_cfg is not None:
                col = st.selectbox("选择列", df_cfg.columns)

                options = st.text_area("输入选项（逗号分隔）")

                if st.button("保存配置"):
                    idx.setdefault(tid_cfg, {})
                    idx[tid_cfg].setdefault("select_cols", {})

                    idx[tid_cfg]["select_cols"][col] = [
                        x.strip() for x in options.split(",") if x.strip()
                    ]

                    save_json(idx, INDEX_FILE)
                    st.success("已保存")

# ===== 主界面 =====
st.title("📊 供应商填表系统")

# 管理员刷新
if is_admin:
    if st.button("🔄 刷新数据"):
        load_excel_cached.clear()
        st.rerun()

# ===== 表格读取 =====
idx = load_json(INDEX_FILE, {})

options = []
mp = {}

for tid, info in idx.items():
    if info.get("visible", True):
        options.append(info["filename"])
        mp[info["filename"]] = tid

if not options:
    st.warning("暂无表格")
    st.stop()

table_name = st.selectbox("选择表格", options)
tid = mp[table_name]

df = load_excel_cached(tid)

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

# ===== 下拉列 =====
select_cols = idx[tid].get("select_cols", {})

column_config = {}
for col, opts in select_cols.items():
    column_config[col] = st.column_config.SelectboxColumn(
        col,
        options=opts
    )

edited = st.data_editor(
    df,
    column_config=column_config,
    use_container_width=True
)

# ===== 保存（锁死 + 无感刷新）=====
if st.button("💾 保存"):

    original = load_excel_cached(tid).set_index("ID")
    edited = edited.set_index("ID")

    if not is_admin:
        supplier = USER_MAP[user]

        for i in edited.index:

            if edited.loc[i, "供应商简称"] != supplier:
                edited.loc[i] = original.loc[i]
                continue

            for col in original.columns:

                old = original.loc[i, col]
                new = edited.loc[i, col]

                if pd.notna(old) and old != "":
                    edited.loc[i, col] = old
                else:
                    edited.loc[i, col] = new

    original.update(edited)
    save_excel(original.reset_index(), tid)

    load_excel_cached.clear()

    st.success("保存成功")
    time.sleep(0.5)
    st.rerun()
