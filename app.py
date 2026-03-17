import streamlit as st
import pandas as pd
import os
import json
import hashlib

st.set_page_config(page_title="多表格管理系统", layout="wide")

# ===================== 文件目录 =====================
SAVE_DIR = "saved_tables"
os.makedirs(SAVE_DIR, exist_ok=True)

INDEX_FILE = f"{SAVE_DIR}/index.json"
SHOW_FILE = f"{SAVE_DIR}/show_tables.json"
SELECT_FILE = f"{SAVE_DIR}/select_options.json"
ANNOUNCE_FILE = f"{SAVE_DIR}/announcements.json"

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

# ===================== 会话状态 =====================
if "user" not in st.session_state:
    st.session_state.user = None
if "announcements" not in st.session_state:
    st.session_state.announcements = load_json(ANNOUNCE_FILE, {})

# ===================== 登录 =====================
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

# ===================== 管理端上传表格 =====================
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

# ===================== 管理端展示给商家 =====================
options, mp = get_tables()

if is_admin:
    st.sidebar.divider()
    st.sidebar.subheader("展示给商家表格")
    show_tables = load_json(SHOW_FILE, [])
    selected_show = st.sidebar.multiselect("选择展示表格", options, default=[o for o in options if o in show_tables])
    if st.sidebar.button("保存展示配置"):
        save_json(selected_show, SHOW_FILE)
        st.sidebar.success("保存成功")

# ===================== 管理端下拉选项 =====================
if is_admin:
    st.sidebar.divider()
    st.sidebar.subheader("配置下拉选项")
    if options:
        table_sel = st.sidebar.selectbox("选择表格", options)
        tid_select = mp[table_sel]
        df_sample = load_excel(tid_select)
        if df_sample is not None:
            cols_sel = st.sidebar.multiselect("选择下拉列", df_sample.columns.tolist())
            dropdown_opts = {}
            all_opts = load_json(SELECT_FILE, {})
            for col in cols_sel:
                val = ",".join(all_opts.get(tid_select, {}).get(col, []))
                opts = st.sidebar.text_area(f"{col} 下拉选项（逗号分隔）", val)
                dropdown_opts[col] = [x.strip() for x in opts.split(",") if x.strip()]
            if st.sidebar.button("保存下拉选项"):
                all_opts[tid_select] = dropdown_opts
                save_json(all_opts, SELECT_FILE)
                st.sidebar.success("下拉选项保存成功")

# ===================== 主页面表格 =====================
st.title("📊 多表格管理系统")
st.caption("商家可编辑，管理员可上传/管理")

# 管理端和商家端看到的表格列表
if is_admin:
    display_options = options
else:
    show_tables = load_json(SHOW_FILE, [])
    display_options = [o for o in options if o in show_tables]

if not display_options:
    st.info("暂无可展示表格")
    st.stop()

sel = st.selectbox("选择表格", display_options)
tid = mp[sel]
df_full = load_excel(tid)
if df_full is None:
    st.error("数据加载失败")
    st.stop()

# ===================== 公告栏 =====================
if tid not in st.session_state.announcements:
    st.session_state.announcements[tid] = ""
notice = st.text_area("📢 公告栏", st.session_state.announcements[tid], height=80)
if is_admin and st.button("保存公告"):
    st.session_state.announcements[tid] = notice
    save_json(st.session_state.announcements, ANNOUNCE_FILE)
    st.success("公告已保存")
elif not is_admin:
    st.info(st.session_state.announcements.get(tid, "暂无公告"))

# ===================== 下拉列处理 =====================
all_select_opts = load_json(SELECT_FILE, {})
select_opts = all_select_opts.get(tid, {})

# 商家端只显示自己供应商数据
if not is_admin:
    supplier = USER_MAP[user]
    df_edit = df_full[df_full["供应商简称"] == supplier].copy()
else:
    df_edit = df_full.copy()

# 应用下拉选项
for col, opts in select_opts.items():
    if col in df_edit.columns:
        df_edit[col] = pd.Categorical(df_edit[col], categories=opts)

# ===================== 可编辑表格 =====================
disabled_cols = [] if is_admin else ["供应商简称"]
df_edited = st.data_editor(df_edit, use_container_width=True, disabled=disabled_cols, key=f"{tid}_{user}")

# ===================== 保存逻辑 =====================
if st.button("💾 保存数据"):
    try:
        if is_admin:
            save_excel(df_edited, tid)
        else:
            supplier = USER_MAP[user]
            mask = df_full["供应商简称"] == supplier
            df_full.loc[mask, :] = df_edited.values
            save_excel(df_full, tid)
        st.success("保存成功！管理员端同步更新")
    except Exception as e:
        st.error(f"保存失败: {str(e)}")
