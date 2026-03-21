import streamlit as st
import pandas as pd
import os
import json
import time
import uuid
import sqlite3
from streamlit_js_eval import streamlit_js_eval

st.set_page_config(layout="wide")

SAVE_DIR = "saved_tables"
os.makedirs(SAVE_DIR, exist_ok=True)

DB_FILE = f"{SAVE_DIR}/data.db"

INDEX_FILE = f"{SAVE_DIR}/index.json"
SHOW_FILE = f"{SAVE_DIR}/show_tables.json"
SELECT_FILE = f"{SAVE_DIR}/select_options.json"
PROGRESS_FILE = f"{SAVE_DIR}/progress.json"
NOTICE_FILE = f"{SAVE_DIR}/notice.json"

# ================= 数据库 =================
def get_conn():
    return sqlite3.connect(DB_FILE, check_same_thread=False)

def save_to_db(df, tid):
    with get_conn() as conn:
        df.to_sql(tid, conn, if_exists="replace", index=False)

def load_table(tid):
    with get_conn() as conn:
        try:
            df = pd.read_sql(f"SELECT * FROM '{tid}'", conn)
        except:
            df = pd.DataFrame()

    if not df.empty:
        df = df.fillna("").astype(str)
        df.columns = df.columns.str.strip()

        if "供应商简称" in df.columns:
            df["供应商简称"] = df["供应商简称"].astype(str).str.strip()

        if "ID" not in df.columns:
            df.insert(0, "ID", [uuid.uuid4().hex[:8] for _ in range(len(df))])

    return df

# ================= 用户 =================
SUPPLIER_CONFIG = {
    "纪梵黎": ["代**"], "铭润": ["dryson", "7Zz"], "康林": ["Tau"],
    "卓黎凯": ["杨小方的小方"], "依嘉依": ["陈"], "华中": ["钧之", "木木"],
    "函厦": ["邓红玫"], "凡迪": ["凡迪"], "赛西": ["Z"],
    "泽亿": ["西红柿"], "阿西": ["阿伟"], "锦裳坊": ["汪宝辉"],
    "涅瓦": ["李大大"], "布列瑟侬": ["小趴菜"], "达芬奇": ["宏林仓库"],
    "顺兰": ["雄"], "星尚美": ["7!"], "穆林达": ["苗子"],
    "俏衣人": ["俏依人"], "鸿盛达": ["RONG"], "聚图": ["聚图"],
    "柏雅": ["Hollow City"], "同顺": ["守有"], "云贸": ["Koi"],
    "白蚁": ["我的梦想"], "大行家1": ["大行家1"], "西永": ["西永"],
    "肯蒂": ["Silent"], "天正": ["Tsuki"], "蒂洛诗": ["蒂洛诗"],
    "温士顿": ["ou"], "方元": ["selina"], "洛艾依": ["燕姐"],
    "正气": ["尽欢"], "博果": ["Ai"], "魅裙": ["Eiker"],
    "初纷梦": ["熊妮"], "卡奇豪": ["卡奇豪"], "合凡": ["起风了"],
    "博果尔": ["刘权"], "青罗帐": ["青罗帐"], "金鸣": ["金鸣"],
    "龙馨": ["龙馨"], "独秀": ["老虎"], "恒尚": ["A小康先森"],
    "福蕾雅": ["严金虹"], "杰祥": ["金刚小婷", "杰祥服饰"]
}

ADMIN_USERS = {"RISA"}
USER_MAP = {u: k for k, v in SUPPLIER_CONFIG.items() for u in v}

# ================= 工具 =================
def load_json(path, default):
    if os.path.exists(path):
        return json.load(open(path, "r", encoding="utf-8"))
    return default

def save_json(data, path):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)

def gen_id():
    return uuid.uuid4().hex[:12]

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

query_params = st.query_params
saved_user = query_params.get("user", [None])[0]

if saved_user and not st.session_state.user:
    if saved_user in ADMIN_USERS or saved_user in USER_MAP:
        st.session_state.user = saved_user

with st.sidebar:
    st.subheader("🔐 登录")

    history_raw = streamlit_js_eval(
        js_expressions="localStorage.getItem('history_users')",
        key="get_history"
    )

    history = json.loads(history_raw) if history_raw else []
    last_user = history[-1] if history else ""

    if st.session_state.user:
        st.success(f"当前用户：{st.session_state.user}")
        if st.button("退出"):
            st.session_state.user = None
            st.query_params.clear()
            st.rerun()
    else:
        with st.form("login_form"):
            user_input = st.text_input("登录账号", value=last_user)
            submit = st.form_submit_button("登录")

            if submit:
                if user_input in ADMIN_USERS or user_input in USER_MAP:
                    st.session_state.user = user_input
                    st.query_params["user"] = user_input

                    if user_input not in history:
                        history.append(user_input)

                    streamlit_js_eval(
                        js_expressions=f"localStorage.setItem('history_users', '{json.dumps(history)}')",
                        key="set_history"
                    )
                    st.rerun()
                else:
                    st.error("用户不存在")

user = st.session_state.user
if not user:
    st.stop()

is_admin = user in ADMIN_USERS

# ================= 上传 =================
if is_admin:
    st.sidebar.subheader("📤 上传表格")
    files = st.sidebar.file_uploader("上传Excel", type=["xlsx"], accept_multiple_files=True)

    if files and st.sidebar.button("确认上传"):
        for f in files:
            try:
                df = pd.read_excel(f)
            except:
                st.sidebar.error(f"{f.name} 文件错误")
                continue

            df.columns = df.columns.str.strip()

            if "供应商简称" not in df.columns:
                st.sidebar.error(f"{f.name}缺少供应商列")
                continue

            df["供应商简称"] = df["供应商简称"].astype(str).str.strip()

            df.insert(0, "ID", [uuid.uuid4().hex[:8] for _ in range(len(df))])

            tid = gen_id()
            save_to_db(df, tid)

            idx = load_json(INDEX_FILE, {})
            idx[tid] = {"filename": f.name, "upload_time": str(pd.Timestamp.now())}
            save_json(idx, INDEX_FILE)

        st.sidebar.success("上传完成")
        st.rerun()

# ================= 表格列表 =================
options, mp = get_tables()

# ================= 展示控制 =================
show_cfg = load_json(SHOW_FILE, [])

if is_admin:
    st.sidebar.subheader("👁️ 表格展示")

    new_show = []
    for label in options:
        tid_tmp = mp[label]
        if st.sidebar.checkbox(label, value=(tid_tmp in show_cfg)):
            new_show.append(tid_tmp)

    if set(new_show) != set(show_cfg):
        save_json(new_show, SHOW_FILE)
        st.rerun()

# ================= 删除 =================
if is_admin:
    st.sidebar.subheader("🗑 删除表格")
    del_label = st.sidebar.selectbox("选择删除", [""] + options)

    if st.sidebar.button("删除") and del_label:
        tid_del = mp[del_label]

        with get_conn() as conn:
            conn.execute(f"DROP TABLE IF EXISTS '{tid_del}'")

        idx = load_json(INDEX_FILE, {})
        idx.pop(tid_del, None)
        save_json(idx, INDEX_FILE)

        st.sidebar.success("已删除")
        st.rerun()

# ================= 下拉配置 =================
if is_admin:
    st.sidebar.subheader("⚙️ 下拉配置")

    config_target = st.sidebar.selectbox("选择配置表", options)

    if config_target:
        tid_cfg = mp[config_target]
        df_cfg = load_table(tid_cfg)

        select_all = load_json(SELECT_FILE, {})
        old_cfg = select_all.get(tid_cfg, {})

        cols = st.sidebar.multiselect(
            "选择列",
            df_cfg.columns.tolist(),
            default=list(old_cfg.keys())
        )

        new_cfg = {}

        for col in cols:
            default_val = ",".join(old_cfg.get(col, []))
            txt = st.sidebar.text_area(f"{col}选项", value=default_val)
            new_cfg[col] = [i.strip() for i in txt.split(",") if i.strip()]

        if st.sidebar.button("保存下拉配置"):
            select_all[tid_cfg] = new_cfg
            save_json(select_all, SELECT_FILE)
            st.sidebar.success("已保存")
            st.rerun()

# ================= 展示 =================
sels = [o for o in options if mp[o] in show_cfg]

if not sels:
    st.warning("暂无可展示表格")
    st.stop()

for i, sel in enumerate(sels):

    st.markdown("---")
    with st.expander(f"📄 {sel}", expanded=(i == 0)):

        tid = mp[sel]
        df = load_table(tid)

        # 公告
        notice_all = load_json(NOTICE_FILE, {})
        notice_text = notice_all.get(tid, "")

        st.markdown("### 📢 公告")

        if is_admin:
            new_notice = st.text_area("编辑公告", value=notice_text, key=f"notice_{tid}")
            if st.button(f"保存公告_{tid}"):
                notice_all[tid] = new_notice
                save_json(notice_all, NOTICE_FILE)
                st.rerun()
        else:
            st.info(notice_text if notice_text else "暂无公告")

        # ================= 填写进度 =================
        progress_all = load_json(PROGRESS_FILE, {})
        done_list = progress_all.get(tid, [])

        all_suppliers = list(SUPPLIER_CONFIG.keys())
        done_suppliers = done_list
        todo_suppliers = [s for s in all_suppliers if s not in done_suppliers]

        st.markdown("### 📊 填写进度")

        col1, col2 = st.columns(2)

        with col1:
            st.success(f"✅ 已填写（{len(done_suppliers)}）")
            st.write("、".join(done_suppliers) if done_suppliers else "暂无")

        with col2:
            st.warning(f"❌ 未填写（{len(todo_suppliers)}）")
            st.write("、".join(todo_suppliers) if todo_suppliers else "全部完成 🎉")

        # 表格
        if not is_admin:
            supplier = USER_MAP[user].strip()
            df_edit = df[
                df["供应商简称"].astype(str).str.contains(supplier, case=False, na=False)
            ].copy()

            if supplier in done_suppliers:
                st.success("你已完成填写 ✅")
            else:
                st.warning("你还未填写 ❗")

        else:
            df_edit = df.copy()

        select_all = load_json(SELECT_FILE, {})
        select_cfg = select_all.get(tid, {})

        column_config = {}

        if not is_admin and "供应商简称" in df_edit.columns:
            column_config["供应商简称"] = st.column_config.TextColumn(disabled=True)

        for col, opts in select_cfg.items():
            if col in df_edit.columns:
                column_config[col] = st.column_config.SelectboxColumn(options=opts)

        edited = st.data_editor(
            df_edit,
            use_container_width=True,
            height=500,
            column_config=column_config,
            key=f"editor_{tid}_{user}"
        )

        if st.button(f"💾 保存：{sel}", key=f"save_{tid}"):

            with get_conn() as conn:

                if is_admin:
                    edited.to_sql(tid, conn, if_exists="replace", index=False)

                else:
                    supplier = USER_MAP[user].strip()

                    original_df = df_edit.set_index("ID")
                    edited_df = edited.set_index("ID")

                    changed_mask = edited_df.ne(original_df)
                    changed_rows = changed_mask.any(axis=1)
                    rows_to_update = edited_df[changed_rows]

                    conn.execute("BEGIN")

                    for rid, row in rows_to_update.iterrows():
                        changed_cols = changed_mask.loc[rid]
                        cols_to_update = changed_cols[changed_cols].index.tolist()

                        for col in cols_to_update:
                            if col not in original_df.columns:
                                continue

                            val = str(row[col]).strip()

                            conn.execute(f"""
                                UPDATE '{tid}'
                                SET "{col}" = ?
                                WHERE ID = ? AND "供应商简称" LIKE ?
                            """, (val, rid, f"%{supplier}%"))

                    conn.commit()

                    progress = load_json(PROGRESS_FILE, {})
                    progress.setdefault(tid, [])
                    if supplier not in progress[tid]:
                        progress[tid].append(supplier)

                    save_json(progress, PROGRESS_FILE)

            st.success("已保存")
            st.rerun()

# ================= 自动刷新 =================
if is_admin:
    auto = st.sidebar.checkbox("开启实时同步", value=True)
    if auto:
        time.sleep(5)
        st.rerun()
