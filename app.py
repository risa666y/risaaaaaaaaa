import streamlit as st
import pandas as pd
import os
import json
import hashlib
import time

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
        df = df.applymap(lambda x: str(x).strip())

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

    # ===== 本地记忆 + 回车登录 =====
    st.components.v1.html("""
    <script>
    const input = window.parent.document.querySelector('input[type="text"]');

    if (input) {
        const saved = localStorage.getItem("saved_usernames");
        if (saved) {
            const arr = JSON.parse(saved);
            if (arr.length > 0) {
                input.value = arr[arr.length - 1];
            }
        }

        input.addEventListener("keydown", function(e) {
            if (e.key === "Enter") {
                const btn = window.parent.document.querySelector('button[kind="secondary"]');
                if (btn) btn.click();
            }
        });
    }
    </script>
    """, height=0)

    username = st.text_input("用户名", key="login_user")

    if st.button("登录"):
        if username in ADMIN_USERS or username in USER_MAP:

            # 写入本地缓存
            st.components.v1.html(f"""
            <script>
            let arr = localStorage.getItem("saved_usernames");
            arr = arr ? JSON.parse(arr) : [];

            if (!arr.includes("{username}")) {{
                arr.push("{username}");
            }}

            localStorage.setItem("saved_usernames", JSON.stringify(arr));
            </script>
            """, height=0)

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

# ================= 展示 / 删除 =================
if is_admin:
    st.sidebar.subheader("👁️ 表格展示")

    show_cfg = load_json(SHOW_FILE, [])
    new_show = []

    for label in options:
        tid_tmp = mp[label]
        if st.sidebar.checkbox(label, value=(tid_tmp in show_cfg)):
            new_show.append(tid_tmp)

    if st.sidebar.button("保存展示"):
        save_json(new_show, SHOW_FILE)
        st.sidebar.success("已保存")
        st.rerun()

    st.sidebar.subheader("🗑 删除表格")
    del_label = st.sidebar.selectbox("选择删除", [""] + options)

    if st.sidebar.button("删除"):
        if del_label:
            tid_del = mp[del_label]

            if os.path.exists(f"{SAVE_DIR}/{tid_del}.xlsx"):
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

# ================= 权限 =================
if not is_admin:
    supplier = USER_MAP[user].strip()
    df_edit = df[df["供应商简称"].str.strip() == supplier].copy()
else:
    df_edit = df.copy()

# ================= 下拉配置 =================
if is_admin:
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

if not is_admin and "供应商简称" in df_edit.columns:
    column_config["供应商简称"] = st.column_config.TextColumn(disabled=True)

for col, opts in select_cfg.items():
    if col in df_edit.columns:
        column_config[col] = st.column_config.SelectboxColumn(options=opts)

# ================= 表格 =================
edited = st.data_editor(
    df_edit,
    use_container_width=True,
    height=600,
    column_config=column_config,
    key=f"editor_{tid}_{user}"
)

# ================= 保存 =================
def auto_save():
    global edited

    if edited is None or edited.empty:
        st.warning("没有可保存的数据")
        return

    full_df = load_excel(tid)

    if is_admin:
        save_excel(edited, tid)
        st.success("保存成功")
        st.rerun()
        return

    supplier = USER_MAP[user].strip()

    for _, row in edited.iterrows():
        for col in edited.columns:
            new_val = str(row[col]).strip()
            if new_val == "":
                continue

            mask = (
                (full_df["ID"] == row["ID"]) &
                (full_df["供应商简称"].str.strip() == supplier)
            )

            full_df.loc[mask, col] = new_val

    save_excel(full_df, tid)

    st.success("✅ 已同步到管理端")
    st.rerun()

if st.button("💾 保存"):
    auto_save()

# ================= 管理端实时刷新 =================
if is_admin:
    auto = st.sidebar.checkbox("开启实时同步", value=True)

    if auto:
        time.sleep(2)
        st.rerun()
