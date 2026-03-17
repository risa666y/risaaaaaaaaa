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

# ===================== 供应商及管理员配置 =====================
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
    st.session_state.login_list = list(USER_TO_SUPPLIER.keys()) + list(ADMIN_USERS)

# ===================== 左侧登录及工具栏 =====================
with st.sidebar:
    st.header("🔐 系统登录")
    # 修复 selectbox index 错误
    login_options = st.session_state.login_list.copy()
    if "" not in login_options:
        login_options.append("")  # 保证至少有一个选项
    default_index = 0
    username = st.selectbox(
        "选择用户名",
        options=login_options,
        index=default_index
    )
    col1, col2 = st.columns(2)
    with col1:
        if st.button("登录", use_container_width=True):
            if username in USER_TO_SUPPLIER or username in ADMIN_USERS:
                st.session_state.user = username
                st.success(f"✅ 登录成功：{username}")
                st.rerun()
            else:
                st.error("❌ 用户不存在")
    with col2:
        if st.button("退出登录", use_container_width=True):
            st.session_state.user = None
            st.rerun()

user = st.session_state.user
is_admin = user in ADMIN_USERS if user else False

# ===================== 后续功能保持原样 =====================
# 管理端上传、展示表格配置、多列下拉选项
# 商家端只可编辑空白或可编辑单元格
# 公告栏、保存同步等逻辑不变

# 注意：这里的修复核心就是登录 selectbox 不再出现 -1 索引导致的崩溃
