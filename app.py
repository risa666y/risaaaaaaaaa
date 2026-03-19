import streamlit as st
import pandas as pd
import os
import json

st.set_page_config(layout="wide")

DATA_DIR = "data"
CONFIG_FILE = "dropdown_config.json"

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

def list_files():
    return [f for f in os.listdir(DATA_DIR) if f.endswith(".xlsx")]

def load_excel(file):
    path = os.path.join(DATA_DIR, file)
    df = pd.read_excel(path)

    # ⭐ 永不崩溃关键
    if "ID" not in df.columns:
        df.insert(0, "ID", range(len(df)))

    df = df.reset_index(drop=True)
    return df

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

    if not os.path.exists(save_path):
        with open(save_path, "wb") as f:
            f.write(uploaded.read())
        st.sidebar.success("上传成功")
    else:
        st.sidebar.warning("文件已存在")

# -----------------------
# 表格管理
# -----------------------
st.sidebar.title("📁 表格管理")

files = list_files()

for f in files:
    st.sidebar.write("✔", f)

# -----------------------
# 下拉配置（不会再消失）
# -----------------------
st.sidebar.title("⚙️ 下拉配置")

config = load_dropdown_config()

col_name = st.sidebar.text_input("列名")
options = st.sidebar.text_area("选项（逗号分隔）")

if st.sidebar.button("保存配置"):
    if col_name and options:
        config[col_name] = [x.strip() for x in options.split(",")]
        save_dropdown_config(config)
        st.sidebar.success("已保存")

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
# 自动保存（稳定版）
# -----------------------
def auto_save():
    edited = st.session_state["editor"]

    if edited is None or len(edited) == 0:
        return

    if "ID" not in edited.columns:
        return

    edited = edited.copy().reset_index(drop=True)
    old = load_excel(selected_file)

    old = old.set_index("ID")
    edited = edited.set_index("ID")

    old.update(edited)

    old = old.reset_index()

    save_excel(selected_file, old)

# -----------------------
# 表格显示（核心）
# -----------------------
st.markdown("### ✏️ 编辑数据（自动保存）")

st.data_editor(
    df,
    key="editor",
    use_container_width=True,   # ⭐铺满
    height=600,                 # ⭐上下滚动
    num_rows="dynamic",
    on_change=auto_save,
    column_config={
        col: st.column_config.SelectboxColumn(
            options=config.get(col, [])
        )
        for col in df.columns
        if col in config
    }
)

# -----------------------
# ⭐ 正确CSS（关键！！）
# -----------------------
st.markdown("""
<style>

/* 表格撑满 */
div[data-testid="stDataEditor"] {
    width: 100% !important;
}

/* ⭐ 允许横向滚动（关键） */
div[data-testid="stDataEditor"] > div {
    overflow-x: auto !important;
}

/* ⭐ 防止文字被拆碎 */
div[data-testid="stDataEditor"] td {
    white-space: nowrap !important;
}

</style>
""", unsafe_allow_html=True)
