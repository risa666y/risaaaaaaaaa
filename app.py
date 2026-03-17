import streamlit as st
import pandas as pd
import os
import json
import hashlib

st.set_page_config(page_title="多表格管理系统", layout="wide")

# ============== 文件与目录 ==============
SAVE_DIR = "saved_tables"
os.makedirs(SAVE_DIR, exist_ok=True)

INDEX_FILE = f"{SAVE_DIR}/index.json"
SHOW_FILE = f"{SAVE_DIR}/show_tables.json"
SELECT_FILE = f"{SAVE_DIR}/select_options.json"
ANNOUNCE_FILE = f"{SAVE_DIR}/announcements.json"

# ============== 用户配置 ==============
SUPPLIER_CONFIG = {
    "恒尚": ["A小康先森"],
    "福蕾雅": ["严金虹"],
    "杰祥": ["金刚小婷", "杰祥服饰", "x"],
    "纪梵黎": ["代**"]
}
ADMIN_USERS = {"admin"}
USER_MAP = {u: k for k, v in SUPPLIER_CONFIG.items() for u in v}

# ============== 工具函数 ==============
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

# ============== 登录 ==============
if "user" not in st.session_state:
    st.session_state.user = None

if "login_list" not in st.session_state:
    st.session_state.login_list = []

with st.sidebar:
    st.title("登录")
    username = st.selectbox(
        "选择用户名",
        options=st.session_state.login_list + [""],
        index=0 if st.session_state.login_list else -1
    )
    if st.button("登录"):
        if username in ADMIN_USERS or username in USER_MAP:
            st.session_state.user = username
            if username not in st.session_state.login_list:
                st.session_state.login_list.append(username)
            st.experimental_rerun()
        else:
            st.error("用户不存在")
    if st.button("退出"):
        st.session_state.user = None
        st.experimental_rerun()

user = st.session_state.user
if not user:
    st.stop()

is_admin = user in ADMIN_USERS

# ============== 管理端上传表格 ==============
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

# ============== 管理端选择展示表格 ==============
table_options, table_map = get_tables()
if is_admin and table_options:
    st.sidebar.divider()
    st.sidebar.subheader("展示给商家")
    current_show = load_json(SHOW_FILE, [])
    selected_show = st.sidebar.multiselect(
        "选择表格展示给商家",
        options=table_options,
        default=[t for t in current_show if t in table_options],
        key="show_tables_select"
    )
    if st.sidebar.button("保存展示配置"):
        save_json(selected_show, SHOW_FILE)
        st.sidebar.success("✅ 展示配置已保存")

# ============== 管理端下拉选项配置 ==============
if is_admin and table_options:
    st.sidebar.divider()
    st.sidebar.subheader("表格下拉选项配置")
    table_for_select = st.sidebar.selectbox("选择表格", table_options, key="dropdown_table_select")
    tid_select = table_map[table_for_select]
    df_sample = load_excel(tid_select)
    if df_sample is not None:
        cols_for_dropdown = st.sidebar.multiselect(
            "选择列设置下拉",
            df_sample.columns.tolist(),
            key=f"cols_dropdown_{tid_select}"
        )
        dropdown_opts = {}
        select_json = load_json(SELECT_FILE, {})
        for col in cols_for_dropdown:
            val = st.sidebar.text_area(
                f"列 {col} 下拉选项（用逗号分隔）",
                value=",".join(select_json.get(tid_select, {}).get(col, [])),
                key=f"textarea_{tid_select}_{col}"
            )
            dropdown_opts[col] = [v.strip() for v in val.split(",") if v.strip()]
        if st.sidebar.button("保存下拉选项"):
            select_json[tid_select] = dropdown_opts
            save_json(select_json, SELECT_FILE)
            st.sidebar.success("✅ 下拉选项已保存")

# ============== 公告栏 ==============
announce_json = load_json(ANNOUNCE_FILE, {})

# ============== 主页面表格 ==============
# 商家端只显示已配置展示的表格
if not is_admin:
    show_tables = load_json(SHOW_FILE, [])
    table_options = [t for t in table_options if t in show_tables]

if not table_options:
    st.info("暂无可操作表格")
    st.stop()

sel = st.selectbox("选择表格", table_options, key=f"select_{user}")
tid = table_map[sel]
fn = load_json(INDEX_FILE)[tid]["filename"]

st.subheader(f"📝 {fn}")

# 公共公告栏显示
st.markdown("### 📢 公告栏")
if is_admin:
    notice = st.text_area("管理员公告", announce_json.get(tid, ""), height=80, key=f"announce_{tid}")
    if st.button("保存公告", key=f"save_announce_{tid}"):
        announce_json[tid] = notice
        save_json(announce_json, ANNOUNCE_FILE)
        st.success("✅ 公告已保存")
else:
    st.info(announce_json.get(tid, "暂无公告"))

# ============== 加载数据 ==============
df_full = load_excel(tid)
if df_full is None:
    st.error("数据加载失败")
    st.stop()

supplier_name = USER_MAP.get(user) if not is_admin else None
if not is_admin:
    df_edit = df_full[df_full["供应商简称"] == supplier_name].copy()
    if df_edit.empty:
        st.info(f"该表格中暂无 {supplier_name} 的数据")
        st.stop()
else:
    df_edit = df_full.copy()

# 应用下拉选项
select_options = load_json(SELECT_FILE, {})
sel_opts = select_options.get(tid, {})
for col, opts in sel_opts.items():
    if col in df_edit.columns:
        df_edit[col] = pd.Categorical(df_edit[col], categories=opts)

# ============== 可编辑表格 ==============
df_edited = st.data_editor(
    df_edit,
    use_container_width=True,
    height=400,
    key=f"editor_{tid}_{user}",
    disabled=["供应商简称"] if not is_admin else []
)

# ============== 保存逻辑 ==============
st.divider()
if st.button("💾 保存数据", type="primary"):
    try:
        if is_admin:
            save_excel(df_edited, tid)
        else:
            mask = df_full["供应商简称"] == supplier_name
            df_full.loc[mask, :] = df_edited.values
            save_excel(df_full, tid)
        st.success("✅ 保存成功！管理员端已同步")
    except Exception as e:
        st.error(f"保存失败：{str(e)}")
