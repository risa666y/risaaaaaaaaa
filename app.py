import streamlit as st
import pandas as pd
import os
import json
import hashlib
import warnings

warnings.filterwarnings('ignore')

# ===================== 全局配置 =====================
st.set_page_config(
    page_title="多表格管理系统",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 数据目录
SAVE_DIR = os.path.abspath("saved_tables")
os.makedirs(SAVE_DIR, exist_ok=True)
INDEX_FILE = os.path.join(SAVE_DIR, "index.json")
SHOW_TABLES_FILE = os.path.join(SAVE_DIR, "show_tables.json")
SELECT_OPTIONS_FILE = os.path.join(SAVE_DIR, "select_options.json")
ANNOUNCEMENT_FILE = os.path.join(SAVE_DIR, "announcements.json")
LOGIN_FILE = os.path.join(SAVE_DIR, "login_list.json")

# ===================== 用户配置 =====================
SUPPLIER_CONFIG = {
    "恒尚": ["A小康先森"],
    "福蕾雅": ["严金虹"],
    "杰祥": ["金刚小婷", "杰祥服饰", "x"],
    "纪梵黎": ["代**"]
}
ADMIN_USERS = {"admin", "管理员", "Admin", "ADMIN"}
USER_TO_SUPPLIER = {user: supplier for supplier, users in SUPPLIER_CONFIG.items() for user in users}

# ===================== 工具函数 =====================
def generate_table_id(filename):
    ts = pd.Timestamp.now().strftime("%Y%m%d%H%M%S%f")
    h = hashlib.md5((filename+ts).encode()).hexdigest()[:8]
    return f"{filename}_{ts}_{h}"

def safe_load_json(path, default={}):
    if not os.path.exists(path):
        return default
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def safe_save_json(data, path):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_table_data(table_id):
    path = os.path.join(SAVE_DIR, f"{table_id}.xlsx")
    if not os.path.exists(path):
        return None
    return pd.read_excel(path, engine='openpyxl', dtype=str).fillna("")

def save_table_data(df, table_id):
    path = os.path.join(SAVE_DIR, f"{table_id}.xlsx")
    df = df.fillna("").astype(str)
    df.to_excel(path, index=False, engine='openpyxl')
    return True

def get_valid_table_options():
    table_index = safe_load_json(INDEX_FILE)
    groups = {}
    for tid, info in table_index.items():
        path = os.path.join(SAVE_DIR, f"{tid}.xlsx")
        if os.path.exists(path):
            fn = info['filename']
            ut = info.get('upload_time', '')
            if fn not in groups or ut > groups[fn]['upload_time']:
                groups[fn] = {'table_id': tid, 'upload_time': ut, 'info': info}
    opts, mp = [], {}
    for fn, d in groups.items():
        label = f"{d['upload_time']} | {fn}"
        opts.append(label)
        mp[label] = {'table_id': d['table_id'], 'filename': fn}
    return sorted(opts, reverse=True), mp

# ===================== 会话状态 =====================
if 'user' not in st.session_state:
    st.session_state.user = None
if 'announcements' not in st.session_state:
    st.session_state.announcements = safe_load_json(ANNOUNCEMENT_FILE)
if 'select_options' not in st.session_state:
    st.session_state.select_options = safe_load_json(SELECT_OPTIONS_FILE)
if 'login_list' not in st.session_state:
    st.session_state.login_list = safe_load_json(LOGIN_FILE, [])

# ===================== 左侧登录 =====================
with st.sidebar:
    st.header("🔐 系统登录")
    username = st.selectbox("选择用户名", options=st.session_state.login_list + [""])
    if st.button("登录", use_container_width=True):
        if username in USER_TO_SUPPLIER or username in ADMIN_USERS:
            st.session_state.user = username
            if username not in st.session_state.login_list:
                st.session_state.login_list.append(username)
                safe_save_json(st.session_state.login_list, LOGIN_FILE)
            st.rerun()
    if st.button("退出登录", use_container_width=True):
        st.session_state.user = None
        st.rerun()

user = st.session_state.user
is_admin = user in ADMIN_USERS

# ===================== 管理端工具栏 =====================
if user and is_admin:
    st.sidebar.divider()
    
    # 上传表格
    st.sidebar.subheader("📤 上传新表格")
    files = st.sidebar.file_uploader("选择Excel文件（必须包含「供应商简称」列）", type=["xlsx"], accept_multiple_files=True)
    for f in files:
        try:
            df = pd.read_excel(f, engine='openpyxl')
            if "供应商简称" not in df.columns:
                st.sidebar.error(f"❌ {f.name} 缺少「供应商简称」列")
                continue
            tid = generate_table_id(f.name)
            save_table_data(df, tid)
            idx = safe_load_json(INDEX_FILE)
            idx[tid] = {
                'filename': f.name,
                'upload_time': pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
                'row_count': len(df)
            }
            safe_save_json(idx, INDEX_FILE)
            st.sidebar.success(f"✅ 上传成功：{f.name}")
        except Exception as e:
            st.sidebar.error(f"❌ 上传失败：{str(e)}")
    
    st.sidebar.divider()
    
    # 展示给供应商
    st.sidebar.subheader("🗂️ 展示给供应商的表格")
    table_options, table_info_map = get_valid_table_options()
    current_show_tables = safe_load_json(SHOW_TABLES_FILE)
    valid_defaults = [t for t in current_show_tables if t in table_options]
    selected_tables = st.sidebar.multiselect("多选展示表格", options=table_options, default=valid_defaults)
    if st.sidebar.button("保存展示配置", use_container_width=True):
        safe_save_json(selected_tables, SHOW_TABLES_FILE)
        st.sidebar.success("✅ 展示配置已保存")
    
    st.sidebar.divider()
    
    # 下拉选项配置
    st.sidebar.subheader("⚙️ 设置表格下拉选项")
    if table_options:
        table_for_select = st.sidebar.selectbox("选择表格设置下拉列", table_options)
        tid_select = table_info_map[table_for_select]['table_id']
        df_sample = load_table_data(tid_select)
        if df_sample is not None:
            columns_for_dropdown = st.sidebar.multiselect("选择需要下拉的列", df_sample.columns.tolist())
            dropdown_options = {}
            for col in columns_for_dropdown:
                opts = st.sidebar.text_area(f"列 {col} 下拉选项（用逗号分隔）",
                                            value=",".join(st.session_state.select_options.get(tid_select, {}).get(col, [])))
                dropdown_options[col] = [o.strip() for o in opts.split(",") if o.strip()]
            if st.sidebar.button("保存下拉选项"):
                all_opts = safe_load_json(SELECT_OPTIONS_FILE)
                all_opts[tid_select] = dropdown_options
                safe_save_json(all_opts, SELECT_OPTIONS_FILE)
                st.session_state.select_options = all_opts
                st.sidebar.success("✅ 下拉选项已保存")

# ===================== 主页面 =====================
st.title("📊 多表格管理系统")
st.caption("商家可编辑空白单元格、管理员可上传/管理")
st.divider()

if not user:
    st.warning("👈 请先登录")
    st.stop()

# ===================== 表格选择 =====================
table_options, table_map = get_valid_table_options()
if not is_admin:
    show_tables = safe_load_json(SHOW_TABLES_FILE)
    table_options = [t for t in table_options if t in show_tables]

if not table_options:
    st.info("ℹ️ 暂无可操作表格")
    st.stop()

sel = st.selectbox("选择表格", table_options)
tid = table_map[sel]['table_id']
fn = table_map[sel]['filename']
st.subheader(f"📝 {fn}")

# ===================== 公告栏 =====================
st.markdown("### 📢 公告栏")
if is_admin:
    notice = st.text_area("管理员公告", st.session_state.announcements.get(tid, ""), height=80)
    if st.button("保存公告"):
        st.session_state.announcements[tid] = notice
        safe_save_json(st.session_state.announcements, ANNOUNCEMENT_FILE)
        st.success("✅ 公告已保存")
else:
    st.info(st.session_state.announcements.get(tid, "暂无公告"))

# ===================== 加载数据 =====================
df_full = load_table_data(tid)
if df_full is None:
    st.error("❌ 数据加载失败")
    st.stop()

supplier_name = USER_TO_SUPPLIER.get(user) if not is_admin else None
if not is_admin:
    df_edit = df_full[df_full["供应商简称"] == supplier_name].copy()
else:
    df_edit = df_full.copy()

# ===================== 应用下拉选项 =====================
select_options = safe_load_json(SELECT_OPTIONS_FILE)
if not is_admin:
    select_options = select_options.get(tid, {})

for col, opts in select_options.items():
    if col in df_edit.columns:
        df_edit[col] = pd.Categorical(df_edit[col], categories=opts)

# ===================== 可编辑表格 =====================
disabled_cols = []
if not is_admin:
    disabled_cols.append("供应商简称")
    # 非空单元格也不可编辑
    for c in df_edit.columns:
        df_edit[c] = df_edit[c].astype(str)
df_edited = st.data_editor(
    df_edit,
    use_container_width=True,
    height=400,
    key=f"editor_{tid}_{user}",
    disabled=disabled_cols if not is_admin else []
)

# ===================== 保存逻辑 =====================
st.divider()
if st.button("💾 保存数据", type="primary"):
    try:
        if is_admin:
            save_table_data(df_edited, tid)
        else:
            mask = df_full["供应商简称"] == supplier_name
            # 只覆盖空白单元格
            for c in df_edit.columns:
                for i in df_edit.index:
                    if df_full.loc[mask, c].iloc[i] == "":
                        df_full.loc[mask, c].iloc[i] = df_edited.loc[i, c]
            save_table_data(df_full, tid)
        st.success("✅ 保存成功！管理员端已同步")
    except Exception as e:
        st.error(f"❌ 保存失败：{str(e)}")

if is_admin and st.button("🔄 刷新最新数据"):
    st.rerun()
