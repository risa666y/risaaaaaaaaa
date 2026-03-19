import streamlit as st
import pandas as pd
import os
import json

st.set_page_config(layout="wide")

DATA_DIR = "data"
CONFIG_FILE = "dropdown_config.json"
COLUMN_FILE = "column_visible.json"

os.makedirs(DATA_DIR, exist_ok=True)

# -----------------------
# 初始化
# -----------------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

# -----------------------
# 工具函数
# -----------------------
def load_dropdown_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_dropdown_config(config):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

def load_column_config():
    if os.path.exists(COLUMN_FILE):
        with open(COLUMN_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_column_config(config):
    with open(COLUMN_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

def list_files():
    return [f for f in os.listdir(DATA_DIR) if f.endswith(".xlsx")]

def load_excel(file):
    path = os.path.join(DATA_DIR, file)
    try:
        df = pd.read_excel(path)
    except Exception as e:
        st.error(f"读取失败: {e}")
        return pd.DataFrame()

    if "ID" not in df.columns:
        df.insert(0, "ID", range(len(df)))

    return df.reset_index(drop=True)

def save_excel(file, df):
    path = os.path.join(DATA_DIR, file)
    df.to_excel(path, index=False)

# -----------------------
# 登录
# -----------------------
st.sidebar.title("🔐 登录")

username = st.sidebar.text_input("用户名")

if st.sidebar.button("登录"):
    if username.strip():
        st.session_state.logged_in = True
        st.session_state.user = username
        st.rerun()

if st.sidebar.button("退出"):
    st.session_state.logged_in = False
    st.rerun()

if not st.session_state.logged_in:
    st.warning("请先登录")
    st.stop()

# -----------------------
# 上传
# -----------------------
st.sidebar.title("📤 上传表格")

uploaded = st.sidebar.file_uploader("上传 Excel", type=["xlsx"])

if uploaded:
    save_path = os.path.join(DATA_DIR, uploaded.name)
    with open(save_path, "wb") as f:
        f.write(uploaded.read())
    st.sidebar.success("上传/覆盖成功")

# -----------------------
# 表格管理
# -----------------------
st.sidebar.title("📁 表格管理")

files = list_files()
for f in files:
    st.sidebar.write("✔", f)

# -----------------------
# 下拉配置
# -----------------------
st.sidebar.title("⚙️ 下拉配置")

config = load_dropdown_config()

col_name = st.sidebar.text_input("列名")
options = st.sidebar.text_area("选项（逗号分隔）")

if st.sidebar.button("保存下拉"):
    if col_name and options:
        config[col_name] = [x.strip() for x in options.split(",")]
        save_dropdown_config(config)
        st.sidebar.success("已保存")

if st.sidebar.button("删除下拉"):
    if col_name in config:
        del config[col_name]
        save_dropdown_config(config)
        st.sidebar.success("已删除")

# -----------------------
# 主界面
# -----------------------
st.title("📊 供应商填表系统")

if not files:
    st.warning("请先上传 Excel")
    st.stop()

selected_file = st.selectbox("选择表格", files)

df = load_excel(selected_file)

# -----------------------
# ⭐ 列显示控制（关键功能）
# -----------------------
st.sidebar.title("👁️ 列显示控制")

column_config = load_column_config()

all_cols = df.columns.tolist()

default_cols = column_config.get(selected_file, all_cols)

visible_cols = st.sidebar.multiselect(
    "选择显示列",
    all_cols,
    default=default_cols
)

if st.sidebar.button("保存列配置"):
    column_config[selected_file] = visible_cols
    save_column_config(column_config)
    st.sidebar.success("已保存列配置")

# 显示用 df
df_display = df[visible_cols] if visible_cols else df

# -----------------------
# 自动保存（安全版）
# -----------------------
def auto_save():
    edited = st.session_state["editor"]

    if edited is None or len(edited) == 0:
        return

    if "ID" not in edited.columns:
        return

    full_df = load_excel(selected_file)

    full_df = full_df.set_index("ID")
    edited = edited.set_index("ID")

    full_df.update(edited)

    full_df = full_df.reset_index()

    save_excel(selected_file, full_df)

# -----------------------
# 表格显示
# -----------------------
st.markdown("### ✏️ 编辑数据（自动保存）")

st.data_editor(
    df_display,
    key="editor",
    use_container_width=True,
    height=600,
    num_rows="dynamic",
    on_change=auto_save,
    column_config={
        col: st.column_config.SelectboxColumn(
            options=config.get(col, [])[:200]  # 限制数量避免卡顿
        )
        for col in df_display.columns
        if col in config
    }
)

# -----------------------
# ⭐ CSS 修复（关键）
# -----------------------
st.markdown("""
<style>

/* 表格撑满 */
div[data-testid="stDataEditor"] {
    width: 100% !important;
    overflow-x: auto !important;
}

/* 不换行 */
div[data-testid="stDataEditor"] td {
    white-space: nowrap !important;
}

/* ⭐ 修复下拉滚动 */
ul[role="listbox"] {
    max-height: 300px !important;
    overflow-y: auto !important;
}

</style>
""", unsafe_allow_html=True)
