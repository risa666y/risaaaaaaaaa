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

SAVE_DIR = os.path.abspath("saved_tables")
os.makedirs(SAVE_DIR, exist_ok=True)
INDEX_FILE = os.path.join(SAVE_DIR, "index.json")
SHOW_TABLES_FILE = os.path.join(SAVE_DIR, "show_tables.json")
SELECT_OPTIONS_FILE = os.path.join(SAVE_DIR, "select_options.json")
ANNOUNCEMENT_FILE = os.path.join(SAVE_DIR, "announcements.json")
LOGIN_FILE = os.path.join(SAVE_DIR, "login_users.json")

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
def safe_load_json(path, default={}):
    if not os.path.exists(path):
        return default
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def safe_save_json(data, path):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def generate_table_id(filename):
    ts = pd.Timestamp.now().strftime("%Y%m%d%H%M%S%f")
    h = hashlib.md5((filename+ts).encode()).hexdigest()[:8]
    return f"{filename}_{ts}_{h}"

def load_table_data(table_id):
    path = os.path.join(SAVE_DIR, f"{table_id}.xlsx")
    if not os.path.exists(path):
        return None
    return pd.read_excel(path, engine='openpyxl', dtype=str).fillna("")

def save_table_data(df, table_id):
    path = os.path.join(SAVE_DIR, f"{table_id}.xlsx")
    df.fillna("").astype(str).to_excel(path, index=False, engine='openpyxl')
    return True

def get_valid_table_options():
    table_index = safe_load_json(INDEX_FILE)
    return list(table_index.keys())

def is_admin(user):
    return user in ADMIN_USERS

# ===================== 登录页面 =====================
login_users = safe_load_json(LOGIN_FILE, [])
selected_user = st.sidebar.selectbox("选择用户登录", options=login_users + ["新用户..."])
if selected_user == "新用户...":
    username = st.sidebar.text_input("请输入用户名")
else:
    username = selected_user

if st.sidebar.button("登录") or st.sidebar.button("回车登录"):
    if username not in login_users:
        login_users.append(username)
        safe_save_json(login_users, LOGIN_FILE)
    st.session_state['user'] = username
    st.success(f"已登录: {username}")

if 'user' not in st.session_state:
    st.stop()

current_user = st.session_state['user']
admin_mode = is_admin(current_user)

# ===================== 左侧工具栏 =====================
st.sidebar.markdown("## 工具栏")
selected_tab = st.sidebar.radio("功能", ["上传表格", "展示表格选择", "配置下拉选项", "商家端查看"])

# ===================== 上传表格 =====================
if selected_tab == "上传表格":
    if admin_mode:
        uploaded_file = st.file_uploader("上传Excel表格", type=["xlsx"])
        if uploaded_file:
            table_id = generate_table_id(uploaded_file.name)
            df = pd.read_excel(uploaded_file, engine='openpyxl', dtype=str).fillna("")
            save_table_data(df, table_id)

            table_index = safe_load_json(INDEX_FILE)
            table_index[table_id] = uploaded_file.name
            safe_save_json(table_index, INDEX_FILE)
            st.success(f"表格 {uploaded_file.name} 上传成功")
    else:
        st.warning("仅管理员可上传表格")

# ===================== 展示表格选择 =====================
elif selected_tab == "展示表格选择":
    if admin_mode:
        table_index = safe_load_json(INDEX_FILE)
        selected_tables = safe_load_json(SHOW_TABLES_FILE)
        chosen_tables = st.multiselect("选择展示给商家端的表格", options=list(table_index.keys()), default=selected_tables)
        if st.button("保存展示表格"):
            safe_save_json(chosen_tables, SHOW_TABLES_FILE)
            st.success("展示表格已更新")
    else:
        st.info("仅管理员可配置展示表格")

# ===================== 配置下拉选项 =====================
elif selected_tab == "配置下拉选项":
    if admin_mode:
        table_index = safe_load_json(INDEX_FILE)
        selected_table = st.selectbox("选择表格配置下拉选项", options=list(table_index.keys()))
        if selected_table:
            df = load_table_data(selected_table)
            if df is not None:
                select_options = safe_load_json(SELECT_OPTIONS_FILE)
                select_options.setdefault(selected_table, {})
                for col in df.columns:
                    options = st.text_input(f"列 {col} 下拉选项 (用逗号分隔)", value=",".join(select_options[selected_table].get(col, [])))
                    select_options[selected_table][col] = [o.strip() for o in options.split(",") if o.strip()]
                if st.button("保存下拉选项"):
                    safe_save_json(select_options, SELECT_OPTIONS_FILE)
                    st.success("下拉选项已保存")
    else:
        st.info("仅管理员可配置下拉选项")

# ===================== 商家端查看 =====================
elif selected_tab == "商家端查看":
    table_index = safe_load_json(INDEX_FILE)
    show_tables = safe_load_json(SHOW_TABLES_FILE)
    select_options = safe_load_json(SELECT_OPTIONS_FILE)
    for table_id in show_tables:
        if table_id not in table_index:
            continue
        st.markdown(f"### {table_index[table_id]}")
        df = load_table_data(table_id)
        if df is None:
            st.warning("表格丢失")
            continue

        editable_df = df.copy()
        for col in df.columns:
            if table_id in select_options and col in select_options[table_id]:
                editable_df[col] = st.selectbox(f"{col}", options=[""] + select_options[table_id][col], index=0, key=f"{table_id}_{col}")
            else:
                editable_df[col] = st.text_input(f"{col}", value="", key=f"{table_id}_{col}_txt")

        if st.button(f"保存表格 {table_index[table_id]}"):
            # 仅更新空白单元格或新输入
            for c in df.columns:
                mask = df[c].isna() | (df[c] == "")
                df.loc[mask, c] = editable_df[c]
            save_table_data(df, table_id)
            st.success("已保存修改")
