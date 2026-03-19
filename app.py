import streamlit as st
import pandas as pd
import os, json, time

st.set_page_config(page_title="供应商填表系统", layout="wide")

# ========= 路径 =========
SAVE_DIR = "saved_tables"
os.makedirs(SAVE_DIR, exist_ok=True)

INDEX_FILE = f"{SAVE_DIR}/index.json"
SELECT_FILE = f"{SAVE_DIR}/select_options.json"
SHOW_FILE = f"{SAVE_DIR}/show_tables.json"

# ========= 用户 =========
SUPPLIER_CONFIG = {
    "恒尚": ["A小康先森"],
    "福蕾雅": ["严金虹"],
    "杰祥": ["金刚小婷", "杰祥服饰"],
}
ADMIN_USERS = {"admin"}
USER_MAP = {u: k for k, v in SUPPLIER_CONFIG.items() for u in v}

# ========= 工具 =========
def load_json(path, default={}):
    if os.path.exists(path):
        try:
            return json.load(open(path, "r", encoding="utf-8"))
        except:
            return default
    return default

def save_json(data, path):
    json.dump(data, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

def save_excel(df, tid):
    df.to_excel(f"{SAVE_DIR}/{tid}.xlsx", index=False)

def load_excel(tid):
    path = f"{SAVE_DIR}/{tid}.xlsx"
    if os.path.exists(path):
        return pd.read_excel(path, dtype=str)
    return pd.DataFrame()

def get_tables():
    idx = load_json(INDEX_FILE, {})
    show = load_json(SHOW_FILE, {})

    opts, mp = [], {}

    for tid, info in idx.items():
        path = f"{SAVE_DIR}/{tid}.xlsx"
        if not os.path.exists(path):
            continue

        if show.get(tid, True) is False:
            continue

        name = info.get("filename", tid)
        opts.append(name)
        mp[name] = tid

    return opts, mp

# ========= 登录 =========
if "user" not in st.session_state:
    st.session_state.user = None

with st.sidebar:
    st.title("🔐 登录")
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

# ========= 上传 =========
with st.sidebar:
    st.divider()
    st.subheader("📤 上传表格")

    file = st.file_uploader("上传Excel", type=["xlsx"])

    if file:
        idx = load_json(INDEX_FILE, {})

        # 防重复
        for t, info in idx.items():
            if info["filename"] == file.name:
                st.warning("⚠️ 表格已存在")
                break
        else:
            tid = str(int(time.time()))
            df = pd.read_excel(file, dtype=str)

            # 自动补ID
            if "ID" not in df.columns:
                df.insert(0, "ID", range(len(df)))

            save_excel(df, tid)

            idx[tid] = {"filename": file.name}
            save_json(idx, INDEX_FILE)

            st.success("上传成功")
            st.rerun()

# ========= 表格管理 =========
with st.sidebar:
    st.divider()
    st.subheader("📂 表格管理")

    idx = load_json(INDEX_FILE, {})
    show = load_json(SHOW_FILE, {})

    for tid, info in list(idx.items()):
        col1, col2 = st.columns([3,1])

        with col1:
            visible = st.checkbox(
                info["filename"],
                value=show.get(tid, True),
                key=f"show_{tid}"
            )
            show[tid] = visible

        with col2:
            if st.button("删", key=f"del_{tid}"):
                idx.pop(tid)
                show.pop(tid, None)
                path = f"{SAVE_DIR}/{tid}.xlsx"
                if os.path.exists(path):
                    os.remove(path)
                save_json(idx, INDEX_FILE)
                save_json(show, SHOW_FILE)
                st.rerun()

    save_json(show, SHOW_FILE)

# ========= 获取表 =========
table_list, tid_map = get_tables()

if not table_list:
    st.warning("⚠️ 没有可用表格，请上传")
    st.stop()

table_name = st.selectbox("选择表格", table_list)
tid = tid_map.get(table_name)

if not tid:
    st.error("❌ 表格异常")
    st.stop()

df = load_excel(tid)

# ========= 下拉配置 =========
select_cfg = load_json(SELECT_FILE, {})
table_cfg = select_cfg.get(tid, {})

# ========= 管理端配置下拉 =========
if is_admin:
    with st.sidebar:
        st.divider()
        st.subheader("⚙️ 下拉配置")

        col = st.selectbox("选择列", df.columns)

        opts = st.text_area("选项（逗号分隔）")

        if st.button("保存配置"):
            table_cfg[col] = [i.strip() for i in opts.split(",") if i.strip()]
            select_cfg[tid] = table_cfg
            save_json(select_cfg, SELECT_FILE)
            st.success("已保存")

# ========= 商家过滤 =========
if not is_admin:
    supplier = USER_MAP[user]
    df = df[df["供应商简称"] == supplier]

# ========= 构建列配置 =========
col_config = {}

for c in df.columns:
    if c in table_cfg:
        col_config[c] = st.column_config.SelectboxColumn(
            options=table_cfg[c]
        )

# ========= 自动保存 =========
def auto_save():
    new_df = st.session_state["editor"]

    full = load_excel(tid)

    if "ID" not in full.columns or "ID" not in new_df.columns:
        return

    full = full.set_index("ID")
    new_df = new_df.set_index("ID")

    if not is_admin:
        supplier = USER_MAP[user]
        new_df = new_df[new_df["供应商简称"] == supplier]

        # 只允许填空
        for idx in new_df.index:
            for col in new_df.columns:
                if pd.notna(full.loc[idx, col]):
                    new_df.loc[idx, col] = full.loc[idx, col]

    full.update(new_df)
    full.reset_index(inplace=True)

    save_excel(full, tid)

# ========= 编辑表 =========
edited = st.data_editor(
    df,
    key="editor",
    column_config=col_config,
    use_container_width=True,
    on_change=auto_save
)

# ========= 手动刷新 =========
st.button("🔄 刷新数据", on_click=lambda: st.rerun())

# ========= 管理端监控 =========
if is_admin:
    st.divider()
    st.subheader("📊 填写监控")

    df_full = load_excel(tid)
    missing = df_full[df_full.isna().any(axis=1)]["供应商简称"].dropna().unique()

    if len(missing) > 0:
        st.error("未完成：" + ",".join(missing))
    else:
        st.success("全部完成")
