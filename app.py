import streamlit as st
import pandas as pd
import os
import json
import hashlib
import re
import requests

st.set_page_config(page_title="AI多表格管理系统", layout="wide")

SAVE_DIR = "saved_tables"
os.makedirs(SAVE_DIR, exist_ok=True)

INDEX_FILE = f"{SAVE_DIR}/index.json"
SHOW_FILE = f"{SAVE_DIR}/show_tables.json"

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
            return json.load(open(path, "r", encoding="utf-8"))
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
        label = f"{info['filename']}"
        opts.append(label)
        mp[label] = tid
    return opts, mp

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

# ================= DeepSeek =================
def deepseek_parse_command(user_input, columns):
    try:
        url = "https://api.deepseek.com/chat/completions"

        headers = {
            "Authorization": f"Bearer {st.secrets['DEEPSEEK_API_KEY']}",
            "Content-Type": "application/json"
        }

        prompt = f"""
你是一个数据操作助手，需要把用户的中文指令解析成JSON。

表字段：{columns}

只返回JSON：
{{
  "filters": [{{"column": "列名", "op": "=", "value": "值"}}],
  "update": {{"column": "列名", "value": "新值"}}
}}

用户指令：
{user_input}
"""

        data = {
            "model": "deepseek-chat",
            "messages": [{"role": "user", "content": prompt}]
        }

        res = requests.post(url, headers=headers, json=data, timeout=10)
        text = res.json()["choices"][0]["message"]["content"]

        return json.loads(text)

    except:
        return None

# ================= 规则兜底 =================
def local_parse_command(text):
    result = {"filters": [], "update": {}}
    nums = re.findall(r"\d+", text)

    if "库存" in text and ("小于" in text or "低于" in text):
        if nums:
            result["filters"].append({"column": "库存", "op": "<", "value": int(nums[0])})

    if "杰祥" in text:
        result["filters"].append({"column": "供应商简称", "op": "=", "value": "杰祥"})

    if "缺货" in text:
        result["update"] = {"column": "状态", "value": "缺货"}

    if "已完成" in text:
        result["update"] = {"column": "状态", "value": "已完成"}

    return result

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
            idx[tid] = {"filename": f.name}
            save_json(idx, INDEX_FILE)

        st.sidebar.success("上传完成")

# ================= 表格 =================
options, mp = get_tables()

if not options:
    st.warning("没有表格")
    st.stop()

sel = st.selectbox("选择表格", options)
tid = mp[sel]

df = load_excel(tid)

# 商家过滤
if not is_admin:
    supplier = USER_MAP[user]
    df_edit = df[df["供应商简称"] == supplier].copy()
else:
    df_edit = df.copy()

st.subheader("数据表")
edited = st.data_editor(df_edit, use_container_width=True)

# 保存
if st.button("保存"):
    if is_admin:
        save_excel(edited, tid)
    else:
        supplier = USER_MAP[user]
        df.loc[df["供应商简称"] == supplier] = edited.values
        save_excel(df, tid)

    st.success("保存成功")

# ================= AI =================
st.divider()
st.subheader("🤖 AI助手")

user_input = st.chat_input("比如：把库存小于10的商品改为缺货")

if user_input:
    cmd = deepseek_parse_command(user_input, df.columns.tolist())

    if not cmd:
        st.warning("AI失败，使用规则模式")
        cmd = local_parse_command(user_input)

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
