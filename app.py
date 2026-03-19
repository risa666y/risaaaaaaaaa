import streamlit as st
import pandas as pd
import os, json, time

st.set_page_config(page_title="智能催填系统", layout="wide")

# ===== 路径 =====
SAVE_DIR = "saved_tables"
os.makedirs(SAVE_DIR, exist_ok=True)

INDEX_FILE = f"{SAVE_DIR}/index.json"
REMIND_FILE = f"{SAVE_DIR}/remind.json"

# ===== 用户 =====
SUPPLIER_CONFIG = {
    "恒尚": ["A小康先森"],
    "福蕾雅": ["严金虹"],
    "杰祥": ["金刚小婷", "杰祥服饰", "x"],
}
ADMIN_USERS = {"admin"}
USER_MAP = {u: k for k, v in SUPPLIER_CONFIG.items() for u in v}

# ===== 工具 =====
def load_json(path, default={}):
    if os.path.exists(path):
        return json.load(open(path, "r", encoding="utf-8"))
    return default

def save_json(data, path):
    json.dump(data, open(path, "w", encoding="utf-8"), ensure_ascii=False)

def load_excel(tid):
    path = f"{SAVE_DIR}/{tid}.xlsx"
    if os.path.exists(path):
        return pd.read_excel(path, dtype=str)
    return None

def get_tables():
    idx = load_json(INDEX_FILE, {})
    opts, mp = [], {}
    for tid, info in idx.items():
        label = f"{info['filename']}"
        opts.append(label)
        mp[label] = tid
    return opts, mp

def check_fill_status(df):
    df = df.replace("", pd.NA)
    missing = []
    if "供应商简称" in df.columns:
        missing = df[df.isna().any(axis=1)]["供应商简称"].dropna().tolist()
    return list(set(missing))

# ===== 登录 =====
if "user" not in st.session_state:
    st.session_state.user = None

with st.sidebar:
    st.title("登录")
    u = st.text_input("用户名")

    if st.button("登录"):
        if u in ADMIN_USERS or u in USER_MAP:
            st.session_state.user = u
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

# ===== 页面 =====
st.title("📊 智能催填系统")

options, mp = get_tables()
all_missing = {}

# ===== 数据检测 =====
for name in options:
    df = load_excel(mp[name])
    if df is None:
        continue

    missing = check_fill_status(df)

    if is_admin:
        if missing:
            all_missing[name] = missing
            st.error(f"{name} 未填写：{', '.join(missing)}")
    else:
        supplier = USER_MAP[user]

        if supplier in missing:
            st.error(f"{name} ❌ 你未填写")
            all_missing[name] = [supplier]
        else:
            st.success(f"{name} ✅ 已完成")

# ===== 管理员提醒 =====
if is_admin and all_missing:

    st.divider()
    st.subheader("📢 发布公告提醒")

    custom_msg = st.text_area(
        "提醒内容",
        value="请尽快填写未完成的表格！",
        height=100
    )

    if st.button("🚨 发送提醒"):

        remind = load_json(REMIND_FILE, {})

        for users in all_missing.values():
            for u in users:
                remind[u] = {
                    "msg": custom_msg,
                    "time": str(pd.Timestamp.now())
                }

        save_json(remind, REMIND_FILE)

        st.success("✅ 提醒已发送（商家会弹窗）")

# ===== 🚀 商家端实时公告弹窗 =====
if not is_admin:

    placeholder = st.empty()

    for i in range(60):  # 最多轮询5分钟
        remind = load_json(REMIND_FILE, {})

        if user in remind:

            data = remind[user]
            msg = data.get("msg", "")

            # 🔥 顶部公告栏
            placeholder.markdown(f"""
            <div style="
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                background-color: #ff4b4b;
                color: white;
                padding: 15px;
                text-align: center;
                font-size: 18px;
                font-weight: bold;
                z-index: 9999;
                box-shadow: 0 2px 10px rgba(0,0,0,0.2);
            ">
            📢 管理员通知：{msg}
            </div>
            """, unsafe_allow_html=True)

            st.toast("📢 收到管理员提醒")

            # 清掉（避免重复弹）
            remind.pop(user)
            save_json(remind, REMIND_FILE)

            # 自动消失（5秒）
            time.sleep(5)
            placeholder.empty()

            break

        time.sleep(5)
