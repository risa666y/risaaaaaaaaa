import streamlit as st
import pandas as pd
import os
import json
import hashlib

st.set_page_config(layout="wide")

SAVE_DIR = "saved_tables"
os.makedirs(SAVE_DIR, exist_ok=True)

INDEX_FILE = f"{SAVE_DIR}/index.json"
SHOW_FILE = f"{SAVE_DIR}/show_tables.json"
SELECT_FILE = f"{SAVE_DIR}/select_options.json"

# ================= 用户 =================
SUPPLIER_CONFIG = {
    "恒尚": ["A小康先森"],
    "福蕾雅": ["严金虹"],
    "杰祥": ["金刚小婷", "杰祥服饰"]
}
ADMIN_USERS = {"admin"}
USER_MAP = {u: k for k, v in SUPPLIER_CONFIG.items() for u in v}

# ================= 工具 =================
def load_json(path, default):
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
        df = pd.read_excel(path, dtype=str).fillna("")

        # ⭐ 强制ID（永不崩）
        if "ID" not in df.columns:
            df.insert(0, "ID", range(len(df)))

        return df.reset_index(drop=True)
    return pd.DataFrame()

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

with st.sidebar:
    st.title("🔐 登录")
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

# ================= 上传 =================
if is_admin:
    st.sidebar.divider()
    st.sidebar.subheader("📤 上传表格")

    files = st.sidebar.file_uploader("上传Excel", type=["xlsx"], accept_multiple_files=True)

    if st.sidebar.button("确认上传"):
        for f in files:
            df = pd.read_excel(f)

            if "供应商简称" not in df.columns:
                st.sidebar.error(f"{f.name}缺少【供应商简称】列")
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
        st.rerun()

# ================= 表格列表 =================
options, mp = get_tables()

# ================= 展示控制 =================
if is_admin:
    st.sidebar.divider()
    st.sidebar.subheader("👁️ 表格展示控制")

    show_cfg = load_json(SHOW_FILE, [])
    new_show = []

    for label in options:
        tid_tmp = mp[label]
        checked = tid_tmp in show_cfg
        show = st.sidebar.checkbox(label, value=checked)

        if show:
            new_show.append(tid_tmp)

    if st.sidebar.button("保存展示"):
        save_json(new_show, SHOW_FILE)
        st.sidebar.success("已保存")
        st.rerun()

    # 删除
    st.sidebar.subheader("🗑 删除表格")
    del_table = st.sidebar.selectbox("选择删除", [""] + options)

    if st.sidebar.button("删除表格"):
        if del_table:
            tid_del = mp[del_table]
            os.remove(f"{SAVE_DIR}/{tid_del}.xlsx")

            idx = load_json(INDEX_FILE, {})
            idx.pop(tid_del, None)
            save_json(idx, INDEX_FILE)

            st.sidebar.success("已删除")
            st.rerun()

else:
    show_cfg = load_json(SHOW_FILE, [])
    options = [o for o in options if mp[o] in show_cfg]

if not options:
    st.warning("暂无表格")
    st.stop()

# ================= 选表 =================
sel = st.selectbox("选择表格", options)
tid = mp[sel]
df = load_excel(tid)

# ================= 权限过滤 =================
if not is_admin:
    supplier = USER_MAP[user]
    df_edit = df[df["供应商简称"] == supplier].copy()
else:
    df_edit = df.copy()

# ================= 下拉配置 =================
if is_admin:
    st.sidebar.divider()
    st.sidebar.subheader("⚙️ 下拉配置")

    select_all = load_json(SELECT_FILE, {})
    old_cfg = select_all.get(tid, {})

    cols = st.sidebar.multiselect(
        "选择列",
        df.columns.tolist(),
        default=list(old_cfg.keys())
    )

    new_cfg = {}

    for col in cols:
        default_val = ",".join(old_cfg.get(col, []))
        txt = st.sidebar.text_area(f"{col}选项", value=default_val)
        new_cfg[col] = [i.strip() for i in txt.split(",") if i.strip()]

    if st.sidebar.button("保存下拉"):
        select_all[tid] = new_cfg
        save_json(select_all, SELECT_FILE)
        st.sidebar.success("已保存")
        st.rerun()

# ================= 应用下拉 =================
select_all = load_json(SELECT_FILE, {})
select_cfg = select_all.get(tid, {})

column_config = {}

# 锁ID
column_config["ID"] = st.column_config.TextColumn(disabled=True)

# 锁供应商
if not is_admin and "供应商简称" in df_edit.columns:
    column_config["供应商简称"] = st.column_config.TextColumn(disabled=True)

# 下拉
for col, opts in select_cfg.items():
    if col in df_edit.columns:
        column_config[col] = st.column_config.SelectboxColumn(options=opts[:200])

# ================= 表格 =================
edited = st.data_editor(
    df_edit,
    use_container_width=True,
    height=600,
    column_config=column_config,
    num_rows="fixed",  # ⭐ 禁止新增
    key=f"editor_{tid}_{user}"
)

# ================= 保存 =================
def auto_save():
    key = f"editor_{tid}_{user}"

    if key not in st.session_state:
        return

    edited = st.session_state[key]

    # ⭐ 核心修复：类型检查
    if not isinstance(edited, pd.DataFrame):
        return

    if edited.empty:
        return

    if "ID" not in edited.columns:
        st.warning("缺少ID列")
        return

    full_df = load_excel(tid)

    if full_df.empty or "ID" not in full_df.columns:
        st.error("原始数据异常")
        return

    # 管理员
    if is_admin:
        save_excel(edited, tid)
        st.success("保存成功")
        return

    # 商家
    full_df = full_df.set_index("ID")
    edited = edited.set_index("ID")

    for i in edited.index:
        if i not in full_df.index:
            continue

        for col in edited.columns:
            if full_df.loc[i, col] == "":
                full_df.loc[i, col] = edited.loc[i, col]

    full_df = full_df.reset_index()
    save_excel(full_df, tid)

    st.success("保存成功")

# ⭐ 不用 on_click（更稳定）
if st.button("💾 保存"):
    auto_save()
