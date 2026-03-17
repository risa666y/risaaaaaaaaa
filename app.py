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
    return list(table_index.keys())

def update_show_tables(selected_tables):
    safe_save_json(selected_tables, SHOW_TABLES_FILE)

def load_select_options():
    return safe_load_json(SELECT_OPTIONS_FILE, default={})

def save_select_options(options):
    safe_save_json(options, SELECT_OPTIONS_FILE)

# ===================== 页面逻辑 =====================
def main():
    st.title("多表格管理系统")

    username = st.text_input("请输入用户名", value="", key="username")
    if username.strip() == "":
        st.warning("请输入用户名")
        return

    is_admin = username in ADMIN_USERS
    supplier_name = USER_TO_SUPPLIER.get(username, None)

    st.sidebar.write(f"当前用户: {username}")
    st.sidebar.write(f"管理员模式: {is_admin}")

    # ---------------- 管理端 ----------------
    if is_admin:
        st.header("管理端功能")

        # 上传表格
        uploaded_file = st.file_uploader("上传Excel表格", type=["xlsx"])
        if uploaded_file is not None:
            df = pd.read_excel(uploaded_file, engine='openpyxl', dtype=str).fillna("")
            table_id = generate_table_id(uploaded_file.name)
            save_table_data(df, table_id)

            # 更新 index.json
            index_data = safe_load_json(INDEX_FILE)
            index_data[table_id] = uploaded_file.name
            safe_save_json(index_data, INDEX_FILE)

            st.success(f"表格上传成功: {uploaded_file.name}")

        # 选择展示表格
        st.subheader("选择展示给商家端的表格")
        table_options = get_valid_table_options()
        show_tables = safe_load_json(SHOW_TABLES_FILE, default=[])
        selected_tables = st.multiselect("可展示表格", table_options, default=show_tables)
        if st.button("保存展示表格"):
            update_show_tables(selected_tables)
            st.success("展示表格已更新")

        # 配置下拉选项
        st.subheader("配置多列下拉选项")
        table_for_select = st.selectbox("选择表格", table_options)
        if table_for_select:
            df = load_table_data(table_for_select)
            select_options = load_select_options()
            columns = df.columns.tolist()
            for col in columns:
                current_options = select_options.get(table_for_select, {}).get(col, [])
                new_options = st.text_area(f"列 {col} 下拉选项 (逗号分隔)", value=",".join(current_options))
                select_options.setdefault(table_for_select, {})[col] = [x.strip() for x in new_options.split(",") if x.strip()]
            if st.button("保存下拉选项"):
                save_select_options(select_options)
                st.success("下拉选项已保存")

    # ---------------- 商家端 ----------------
    else:
        st.header(f"商家端 - {supplier_name}")

        # 加载展示表格
        show_tables = safe_load_json(SHOW_TABLES_FILE, default=[])
        for table_id in show_tables:
            df = load_table_data(table_id)
            if df is None:
                continue

            st.subheader(f"表格: {table_id}")
            editable_df = df.copy()

            # 加载下拉选项
            select_options = load_select_options()
            options_map = select_options.get(table_id, {})

            # 商家只能修改原本为空的单元格
            for col in df.columns:
                for idx in df.index:
                    cell_val = df.at[idx, col]
                    if cell_val == "":
                        opt_list = options_map.get(col, [])
                        if opt_list:
                            editable_df.at[idx, col] = st.selectbox(f"{col} 行{idx}", [""] + opt_list, key=f"{table_id}_{col}_{idx}")
                        else:
                            editable_df.at[idx, col] = st.text_input(f"{col} 行{idx}", value="", key=f"{table_id}_{col}_{idx}")
                    else:
                        editable_df.at[idx, col] = cell_val  # 已有内容不可修改

            # 保存修改
            if st.button(f"保存表格 {table_id} 修改"):
                save_table_data(editable_df, table_id)
                st.success(f"{table_id} 已同步修改")

if __name__ == "__main__":
    main()
