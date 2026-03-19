import streamlit as st
import pandas as pd
import os
import json
import time

DATA_DIR = "data"
CONFIG_FILE = "select_options.json"
SHOW_FILE = "show_tables.json"

os.makedirs(DATA_DIR, exist_ok=True)

# ================= 登录 =================
st.sidebar.title("🔐 登录")

username = st.sidebar.text_input("用户名")

if st.sidebar.button("登录"):
    st.session_state["user"] = username

if st.sidebar.button("退出"):
    st.session_state.clear()

user = st.session_state.get("user")

# ================= 角色 =================
is_admin = user == "admin"

# ================= 初始化配置 =================
if not os.path.exists(CONFIG_FILE):
    json.dump({}, open(CONFIG_FILE, "w"))

if not os.path.exists(SHOW_FILE):
    json.dump({}, open(SHOW_FILE, "w"))

select_config = json.load(open(CONFIG_FILE))
show_tables = json.load(open(SHOW_FILE))

# ================= 标题 =================
st.title("📊 供应商填表系统")

# ================= 上传 =================
if is_admin:
    st.sidebar.header("📤 上传表格")
    file = st.sidebar.file_uploader("上传Excel", type=["xlsx"])

    if file:
        path = os.path.join(DATA_DIR, file.name)
        if not os.path.exists(path):
            df = pd.read_excel(file)
            df.insert(0, "ID", range(len(df)))  # ✅ 永远有ID
            df.to_excel(path, index=False)

            show_tables[file.name] = True
            json.dump(show_tables, open(SHOW_FILE, "w"))

            st.sidebar.success("上传成功")
        else:
            st.sidebar.warning("文件已存在")

# ================= 表格列表 =================
files = os.listdir(DATA_DIR)

visible_tables = []
st.sidebar.header("📂 表格管理")

for f in files:
    show = show_tables.get(f, True)
    col1, col2 = st.sidebar.columns([1,1])

    with col1:
        checked = st.checkbox(f, value=show, key=f)
        show_tables[f] = checked

    with col2:
        if is_admin:
            if st.button("删", key="del_"+f):
                os.remove(os.path.join(DATA_DIR, f))
                show_tables.pop(f, None)
                st.rerun()

    if checked:
        visible_tables.append(f)

json.dump(show_tables, open(SHOW_FILE, "w"))

# ================= 无表处理 =================
if not visible_tables:
    st.warning("暂无可用表格")
    st.stop()

# ================= 选择表 =================
table_name = st.selectbox("选择表格", visible_tables)

file_path = os.path.join(DATA_DIR, table_name)
df = pd.read_excel(file_path)

# ✅ 防止ID丢失
if "ID" not in df.columns:
    df.insert(0, "ID", range(len(df)))

df = df.fillna("")

# ================= 商家过滤 =================
if not is_admin:
    if "供应商名称" in df.columns:
        df = df[df["供应商名称"] == user]

# ================= 下拉配置 =================
st.sidebar.header("⚙️ 下拉配置")

if is_admin:
    col_name = st.sidebar.text_input("列名")
    options = st.sidebar.text_area("选项（逗号分隔）")

    if st.sidebar.button("保存配置"):
        if col_name and options:
            select_config[col_name] = options.split(",")
            json.dump(select_config, open(CONFIG_FILE, "w"))
            st.sidebar.success("已保存")

# ================= 表格编辑 =================
edited_df = df.copy()

st.write("✏️ 编辑数据（自动保存）")

for i in range(len(df)):
    cols = st.columns(len(df.columns))

    for j, col in enumerate(df.columns):

        value = df.iloc[i][col]

        # 管理员：全可编辑
        if is_admin:
            if col in select_config:
                edited_df.iloc[i, j] = cols[j].selectbox(
                    "", select_config[col],
                    index=select_config[col].index(value) if value in select_config[col] else 0,
                    key=f"{i}_{col}"
                )
            else:
                edited_df.iloc[i, j] = cols[j].text_input(
                    "", value, key=f"{i}_{col}"
                )

        # 商家：只能填空
        else:
            if value == "":
                if col in select_config:
                    edited_df.iloc[i, j] = cols[j].selectbox(
                        "", select_config[col],
                        key=f"{i}_{col}"
                    )
                else:
                    edited_df.iloc[i, j] = cols[j].text_input(
                        "", value, key=f"{i}_{col}"
                    )
            else:
                cols[j].write(value)

# ================= 自动保存（稳定版） =================
def safe_save():
    try:
        full_df = pd.read_excel(file_path)

        if "ID" not in full_df.columns:
            full_df.insert(0, "ID", range(len(full_df)))

        full_df = full_df.set_index("ID")
        edited_df2 = edited_df.set_index("ID")

        full_df.update(edited_df2)

        full_df.reset_index().to_excel(file_path, index=False)

    except Exception as e:
        st.error(f"保存失败: {e}")

# ✅ 每次操作自动保存（无刷新）
safe_save()
