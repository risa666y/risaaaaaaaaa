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
ANNOUNCEMENT_FILE = f"{SAVE_DIR}/announcements.json"

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

# ================= 登录 =================
if "user" not in st.session_state:
    st.session_state.user = None

if "announcements" not in st.session_state:
    st.session_state.announcements = load_json(ANNOUNCEMENT_FILE, {})

with st.sidebar:
    st.title("登录")
    username = st.text_input("用户名", key="login_username")

    if st.button("登录", key="login_btn"):
        if username in ADMIN_USERS or username in USER_MAP:
            st.session_state.user = username
            st.experimental_rerun()
        else:
            st.error("用户不存在")

    if st.button("退出", key="logout_btn"):
        st.session_state.user = None
        st.experimental_rerun()

user = st.session_state.user
if not user:
    st.stop()

is_admin = user in ADMIN_USERS

# ================= 上传 =================
if is_admin:
    st.sidebar.divider()
    st.sidebar.subheader("上传表格")

    files = st.sidebar.file_uploader("上传Excel", type=["xlsx"], accept_multiple_files=True, key="upload_files")

    if st.sidebar.button("确认上传", key="upload_btn"):
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

# 管理端选择展示表格
if is_admin:
    st.sidebar.divider()
    st.sidebar.subheader("展示给商家端的表格")
    show_tables = load_json(SHOW_FILE, [])
    selected = st.sidebar.multiselect("选择展示表格", options, default=show_tables, key="show_multiselect")
    if st.sidebar.button("保存展示配置", key="show_save_btn"):
        save_json(selected, SHOW_FILE)
        st.sidebar.success("展示配置已保存")

# ================= 选择表格 =================
# 商家端只显示被允许展示的表格
if not is_admin:
    allowed = load_json(SHOW_FILE, [])
    options = [o for o in options if o in allowed]

if not options:
    st.info("暂无可操作表格")
    st.stop()

sel = st.selectbox("选择表格", options, key="table_select")
tid = mp[sel]
fn = load_json(INDEX_FILE)[tid]["filename"]

# ================= 公告栏 =================
st.markdown(f"### 📢 公告栏 - {fn}")
notice_text = st.session_state.announcements.get(tid, "")
if is_admin:
    new_notice = st.text_area("编辑公告", notice_text, key=f"notice_{tid}")
    if st.button("保存公告", key=f"save_notice_{tid}"):
        st.session_state.announcements[tid] = new_notice
        save_json(st.session_state.announcements, ANNOUNCEMENT_FILE)
        st.success("公告已保存")
else:
    st.info(notice_text or "暂无公告")

# ================= 加载数据 =================
df_full = load_excel(tid)
if df_full is None:
    st.error("数据加载失败")
    st.stop()

if not is_admin:
    supplier_name = USER_MAP.get(user)
    df_edit = df_full[df_full["供应商简称"] == supplier_name].copy()
    if df_edit.empty:
        st.info(f"该表格中暂无 {supplier_name} 的数据")
        st.stop()
else:
    df_edit = df_full.copy()

# ================= 下拉选项 =================
select_options = load_json(SELECT_FILE)
table_select_options = select_options.get(tid, {})

for col, opts in table_select_options.items():
    if col in df_edit.columns:
        df_edit[col] = pd.Categorical(df_edit[col], categories=opts)

# ================= 可编辑表格 =================
df_edited = st.data_editor(df_edit, use_container_width=True, key=f"editor_{tid}_{user}", disabled=["供应商简称"] if not is_admin else [])

# ================= 保存 =================
if st.button("保存数据", type="primary", key=f"save_data_{tid}_{user}"):
    if is_admin:
        save_excel(df_edited, tid)
    else:
        supplier_name = USER_MAP.get(user)
        mask = df_full["供应商简称"] == supplier_name
        df_full.loc[mask, :] = df_edited.values
        save_excel(df_full, tid)
    st.success("保存成功！")
