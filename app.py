import streamlit as st
import pandas as pd
import os
import json
import time
import uuid

st.set_page_config(layout="wide")

SAVE_DIR = "saved_tables"
os.makedirs(SAVE_DIR, exist_ok=True)

INDEX_FILE = f"{SAVE_DIR}/index.json"
SHOW_FILE = f"{SAVE_DIR}/show_tables.json"
SELECT_FILE = f"{SAVE_DIR}/select_options.json"
PROGRESS_FILE = f"{SAVE_DIR}/progress.json"

# ================= 用户 =================
SUPPLIER_CONFIG = {
    "纪梵黎": ["代**"],
    "铭润": ["dryson", "7Zz"],
    "康林": ["Tau"],
    "卓黎凯": ["杨小方的小方"],
    "依嘉依": ["陈"],
    "华中": ["钧之", "木木"],
    "函厦": ["邓红玫"],
    "凡迪": ["凡迪"],
    "赛西": ["Z"],
    "泽亿": ["西红柿"],
    "阿西": ["阿伟"],
    "锦裳坊": ["汪宝辉"],
    "涅瓦": ["李大大"],
    "布列瑟侬": ["小趴菜"],
    "达芬奇": ["宏林仓库"],
    "顺兰": ["雄"],
    "星尚美": ["7!"],
    "穆林达": ["苗子"],
    "俏衣人": ["俏依人"],
    "鸿盛达": ["RONG"],
    "聚图": ["聚图"],
    "柏雅": ["Hollow City"],
    "同顺": ["守有"],
    "云贸": ["Koi"],
    "白蚁": ["我的梦想"],
    "大行家1": ["大行家1"],
    "西永": ["西永"],
    "肯蒂": ["Silent"],
    "天正": ["Tsuki"],
    "蒂洛诗": ["蒂洛诗"],
    "温士顿": ["ou"],
    "方元": ["selina"],
    "洛艾依": ["燕姐"],
    "正气": ["尽欢"],
    "博果": ["Ai"],
    "魅裙": ["Eiker"],
    "初纷梦": ["熊妮"],
    "卡奇豪": ["卡奇豪"],
    "合凡": ["起风了"],
    "博果尔": ["刘权"],
    "青罗帐": ["青罗帐"],
    "金鸣": ["金鸣"],
    "龙馨": ["龙馨"],
    "独秀": ["老虎"],
    "恒尚": ["A小康先森"],
    "福蕾雅": ["严金虹"],
    "杰祥": ["金刚小婷", "杰祥服饰"]
}

ADMIN_USERS = {"RISA"}
USER_MAP = {u: k for k, v in SUPPLIER_CONFIG.items() for u in v}

all_users = [u for v in SUPPLIER_CONFIG.values() for u in v]
if len(all_users) != len(set(all_users)):
    st.error("⚠️ 存在重复用户名，请检查 SUPPLIER_CONFIG")

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

def gen_id(name):
    return uuid.uuid4().hex[:12]

def save_excel(df, tid):
    path = f"{SAVE_DIR}/{tid}.xlsx"
    if os.path.exists(path):
        backup = f"{SAVE_DIR}/{tid}_{int(time.time())}.bak.xlsx"
        os.rename(path, backup)
    df.to_excel(path, index=False)

def load_excel(tid):
    path = f"{SAVE_DIR}/{tid}.xlsx"
    if os.path.exists(path):
        df = pd.read_excel(path, dtype=str).fillna("")
        df = df.astype(str).apply(lambda col: col.str.strip())
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

if "history_users" not in st.session_state:
    st.session_state.history_users = []

history = st.session_state.history_users

with st.sidebar:
    st.subheader("🔐 登录")

    with st.form("login_form"):
        user_input = st.text_input("登录账号")
        submit = st.form_submit_button("登录")

    if user_input:
        matches = [u for u in history if u.startswith(user_input)]
        if matches:
            st.caption("历史账号：" + " / ".join(matches))

    if submit:
        if user_input in ADMIN_USERS or user_input in USER_MAP:
            st.session_state.user = user_input
            if user_input not in history:
                history.append(user_input)
            st.success("登录成功")
            st.rerun()
        else:
            st.error("用户不存在")

    if st.session_state.user:
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

# ================= 展示控制（统一逻辑） =================
st.sidebar.subheader("👁️ 表格展示")

show_cfg = load_json(SHOW_FILE, [])
new_show = []

for label in options:
    tid_tmp = mp[label]
    if st.sidebar.checkbox(label, value=(tid_tmp in show_cfg)):
        new_show.append(tid_tmp)

# ✅ 自动保存（关键优化）
if set(new_show) != set(show_cfg):
    save_json(new_show, SHOW_FILE)
    st.sidebar.success("已自动保存")
    st.rerun()

# ================= 删除（仅管理员） =================
if is_admin:
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

# ================= 下拉配置 =================
if is_admin:
    st.sidebar.subheader("⚙️ 下拉配置")

    config_target = st.sidebar.selectbox("选择配置表", options)

    if config_target:
        tid_cfg = mp[config_target]
        df_cfg = load_excel(tid_cfg)

        select_all = load_json(SELECT_FILE, {})
        old_cfg = select_all.get(tid_cfg, {})

        cols = st.sidebar.multiselect(
            "选择列",
            df_cfg.columns.tolist(),
            default=list(old_cfg.keys()),
            key=f"cols_{tid_cfg}"
        )

        new_cfg = {}

        for col in cols:
            default_val = ",".join(old_cfg.get(col, []))
            txt = st.sidebar.text_area(
                f"{col}选项",
                value=default_val,
                key=f"{tid_cfg}_{col}"
            )
            new_cfg[col] = [i.strip() for i in txt.split(",") if i.strip()]

        if st.sidebar.button("保存下拉配置"):
            select_all[tid_cfg] = new_cfg
            save_json(select_all, SELECT_FILE)
            st.sidebar.success("已保存")
            st.rerun()

# ================= ⭐核心：只展示左边勾选的 =================
sels = [o for o in options if mp[o] in show_cfg]

if not sels:
    st.warning("暂无可展示表格")
    st.stop()

# ================= 表格展示 =================
for i, sel in enumerate(sels):

    st.markdown("---")
    with st.expander(f"📄 {sel}", expanded=(i == 0)):

        tid = mp[sel]
        df = load_excel(tid)

        if not is_admin:
            supplier = USER_MAP[user].strip()
            df_edit = df[df["供应商简称"].str.strip() == supplier].copy()
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

            if edited is None or edited.empty:
                st.warning("没有可保存数据")
                continue

            full_df = load_excel(tid)

            if is_admin:
                save_excel(edited, tid)
            else:
                supplier = USER_MAP[user].strip()

                for _, row in edited.iterrows():
                    for col in edited.columns:
                        val = str(row[col]).strip()
                        if val == "":
                            continue

                        mask = (
                            (full_df["ID"] == row["ID"]) &
                            (full_df["供应商简称"].str.strip() == supplier)
                        )

                        full_df.loc[mask, col] = val

                save_excel(full_df, tid)

                progress = load_json(PROGRESS_FILE, {})
                if tid not in progress:
                    progress[tid] = []

                if supplier not in progress[tid]:
                    progress[tid].append(supplier)

                save_json(progress, PROGRESS_FILE)

            st.success("已保存")
            st.rerun()

        # 进度
        if is_admin:
            progress = load_json(PROGRESS_FILE, {})
            done = set(progress.get(tid, []))
            all_s = set(df["供应商简称"].str.strip().unique())
            not_done = all_s - done

            st.success(f"已完成 {len(done)}：{sorted(done)}")
            st.error(f"未完成 {len(not_done)}：{sorted(not_done)}")

# ================= 自动刷新 =================
if is_admin:
    auto = st.sidebar.checkbox("开启实时同步", value=True)
    if auto:
        time.sleep(5)
        st.rerun()
