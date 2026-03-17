import streamlit as st
import pandas as pd
import os
import json
import hashlib

# ===================== 基础配置 =====================
st.set_page_config(page_title="多表格管理系统", layout="wide")

SAVE_DIR = "saved_tables"
os.makedirs(SAVE_DIR, exist_ok=True)

INDEX_FILE = f"{SAVE_DIR}/index.json"
SHOW_FILE = f"{SAVE_DIR}/show_tables.json"
SELECT_FILE = f"{SAVE_DIR}/select_options.json"

# ===================== 用户配置 =====================
SUPPLIER_CONFIG = {
    "恒尚": ["A小康先森"],
    "福蕾雅": ["严金虹"],
    "杰祥": ["金刚小婷", "杰祥服饰", "x"],
    "纪梵黎": ["代**"]
}
ADMIN_USERS = {"admin"}

USER_MAP = {u: k for k, v in SUPPLIER_CONFIG.items() for u in v}

# ===================== 工具函数 =====================
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

# ===================== 登录 =====================
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

# ===================== 上传（防刷新关键） =====================
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

# ===================== 表格列表 =====================
options, mp = get_tables()

if is_admin:
    st.sidebar.divider()

    # ⭐ 修复多选问题
    if "show_tables" not in st.session_state:
        st.session_state.show_tables = load_json(SHOW_FILE, [])

    selected = st.sidebar.multiselect(
        "展示给商家",
        options,
        default=st.session_state.show_tables
    )

    if st.sidebar.button("保存展示"):
        st.session_state.show_tables = selected
        save_json(selected, SHOW_FILE)
        st.sidebar.success("已保存")

else:
    show = load_json(SHOW_FILE, [])
    options = [o for o in options if o in show]

if not options:
    st.warning("没有表格")
    st.stop()

sel = st.selectbox("选择表格", options)
tid = mp[sel]

df = load_excel(tid)

# ===================== 商家过滤 =====================
if not is_admin:
    supplier = USER_MAP[user]
    df_edit = df[df["供应商简称"] == supplier].copy()
else:
    df_edit = df.copy()

# ===================== 下拉配置 =====================
select_all = load_json(SELECT_FILE, {})
select_cfg = select_all.get(tid, {})

column_config = {}

for col, opts in select_cfg.items():
    if col in df_edit.columns:
        column_config[col] = st.column_config.SelectboxColumn(options=opts)

# ===================== 配置下拉（管理员） =====================
if is_admin:
    st.sidebar.divider()
    st.sidebar.subheader("下拉配置")

    col_select = st.sidebar.multiselect("选择列", df.columns.tolist())

    new_cfg = {}
    for col in col_select:
        txt = st.sidebar.text_area(f"{col}选项", "")
        new_cfg[col] = [i.strip() for i in txt.split(",") if i.strip()]

    if st.sidebar.button("保存下拉"):
        all_cfg = load_json(SELECT_FILE, {})
        all_cfg[tid] = new_cfg
        save_json(all_cfg, SELECT_FILE)
        st.sidebar.success("已保存")
        st.rerun()

# ===================== 表格编辑 =====================
edited = st.data_editor(
    df_edit,
    use_container_width=True,
    column_config=column_config,
    key="editor"
)

# ===================== 保存 =====================
if st.button("保存"):
    if is_admin:
        save_excel(edited, tid)
    else:
        supplier = USER_MAP[user]
        df.loc[df["供应商简称"] == supplier] = edited.values
        save_excel(df, tid)

    st.success("保存成功")
