import streamlit as st
import pandas as pd
import os
import json
import hashlib
from openai import OpenAI

# 🔑 填你的key
client = OpenAI(
    api_key=st.secrets["OPENAI_API_KEY"]
)

st.set_page_config(page_title="多表格AI管理系统", layout="wide")

SAVE_DIR = "saved_tables"
os.makedirs(SAVE_DIR, exist_ok=True)

INDEX_FILE = f"{SAVE_DIR}/index.json"
SHOW_FILE = f"{SAVE_DIR}/show_tables.json"
SELECT_FILE = f"{SAVE_DIR}/select_options.json"

# ================= GPT解析 =================
def gpt_parse_command(user_input, columns):
    prompt = f"""
你是一个数据操作助手，需要把用户的中文指令解析成JSON。

表格字段有：{columns}

只返回JSON，不要解释。

JSON格式：
{{
  "action": "update",
  "filters": [
    {{"column": "列名", "op": "=", "value": "值"}}
  ],
  "update": {{"column": "列名", "value": "新值"}}
}}

支持操作符：
=, <, >, <=, >=

用户指令：
{user_input}
"""
    res = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0
    )

    text = res.choices[0].message.content

    try:
        return json.loads(text)
    except:
        return None

# ================= 用户 =================
SUPPLIER_CONFIG = {
    "恒尚": ["A小康先森"],
    "福蕾雅": ["严金虹"],
    "杰祥": ["金刚小婷", "杰祥服饰", "x"],
    "纪梵黎": ["代**"]
}
ADMIN_USERS = {"admin"}
USER_MAP = {u: k for k, v in SUPPLIER_CONFIG.items() for u in v}

# ================= 工具 =================
def load_json(path, default=None):
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except:
        return {}
    return {} if default is None else default

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

# ================= 登录 =================
if "user" not in st.session_state:
    st.session_state.user = None

with st.sidebar:
    st.title("登录")
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
    st.sidebar.subheader("上传表格")

    files = st.sidebar.file_uploader("上传Excel", type=["xlsx"], accept_multiple_files=True)

    if st.sidebar.button("确认上传"):
        for f in files:
            df = pd.read_excel(f, dtype=str).fillna("")
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

# ================= 表格列表 =================
options, mp = get_tables()

if is_admin:
    st.sidebar.divider()

    if "show_tables" not in st.session_state:
        st.session_state.show_tables = load_json(SHOW_FILE, [])

    selected_labels = st.sidebar.multiselect(
        "展示给商家",
        options,
        default=[l for l in options if mp[l] in st.session_state.show_tables]
    )

    if st.sidebar.button("保存展示"):
        selected_tids = [mp[l] for l in selected_labels]
        st.session_state.show_tables = selected_tids
        save_json(selected_tids, SHOW_FILE)
        st.sidebar.success("已保存")

else:
    show_tids = load_json(SHOW_FILE, [])
    options = [o for o in options if mp[o] in show_tids]

if not options:
    st.warning("没有可显示表格")
    st.stop()

sel = st.selectbox("选择表格", options)
tid = mp[sel]

df = load_excel(tid)

# ================= 表格 =================
st.subheader("数据表")
edited = st.data_editor(df, use_container_width=True)

if st.button("保存"):
    save_excel(edited, tid)
    st.success("保存成功")

# ================= 🤖 AI助手 =================
st.divider()
st.subheader("🤖 AI助手")

user_input = st.chat_input("比如：把库存小于10的商品改为缺货")

if user_input:
    cmd = gpt_parse_command(user_input, df.columns.tolist())

    if not cmd:
        st.error("AI解析失败")
    else:
        df_new = df.copy()

        for f in cmd.get("filters", []):
            col = f["column"]
            op = f["op"]
            val = f["value"]

            if op == "=":
                df_new = df_new[df_new[col] == str(val)]
            else:
                df_new = df_new[
                    pd.to_numeric(df_new[col], errors="coerce")
                    .fillna(0)
                    .astype(float)
                    .pipe(lambda s: eval(f"s {op} {val}"))
                ]

        upd = cmd.get("update", {})
        if upd:
            col = upd["column"]
            val = upd["value"]

            st.warning(f"即将修改 {len(df_new)} 行 → {col} = {val}")

            if st.button("确认执行"):
                df.loc[df_new.index, col] = val
                save_excel(df, tid)
                st.success("修改完成")
