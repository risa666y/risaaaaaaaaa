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
    return hashlib.md5(name.encode()).hexdigest()[:10]

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
            "messages": [
                {"role": "user", "content": prompt}
            ]
        }

        res = requests.post(url, headers=headers, json=data, timeout=10)

        text = res.json()["choices"][0]["message"]["content"]

        return json.loads(text)

    except:
        return None

# ================= 规则兜底 =================
def local_parse_command(text):
    result = {
        "filters": [],
        "update": {}
    }

    nums = re.findall(r"\d+", text)

    if "库存" in text and ("小于" in text or "低于" in text):
        if nums:
            result["filters"].append({
                "column": "库存",
                "op": "<",
                "value": int(nums[0])
            })

    if "杰祥" in text:
        result["filters"].append({
            "column": "供应商简称",
            "op": "=",
            "value": "杰祥"
        })

    if "缺货" in text:
        result["update"] = {"column": "状态", "value": "缺货"}

    if "已完成" in text:
        result["update"] = {"column": "状态", "value": "已完成"}

    return result

# ================= 上传 =================
st.sidebar.title("上传表格")
file = st.sidebar.file_uploader("上传Excel", type=["xlsx"])

if file:
    df = pd.read_excel(file, dtype=str).fillna("")
    tid = gen_id(file.name)
    save_excel(df, tid)

    idx = load_json(INDEX_FILE, {})
    idx[tid] = {"filename": file.name}
    save_json(idx, INDEX_FILE)

    st.sidebar.success("上传成功")

# ================= 选择 =================
options, mp = get_tables()

if not options:
    st.warning("请先上传表格")
    st.stop()

sel = st.selectbox("选择表格", options)
tid = mp[sel]

df = load_excel(tid)

st.subheader("数据表")
edited = st.data_editor(df, use_container_width=True)

if st.button("保存表格"):
    save_excel(edited, tid)
    st.success("保存成功")

# ================= 🤖 AI =================
st.divider()
st.subheader("🤖 AI助手")

user_input = st.chat_input("比如：把库存小于10的商品改为缺货")

if user_input:
    cmd = deepseek_parse_command(user_input, df.columns.tolist())

    if not cmd:
        st.warning("AI解析失败，使用备用规则")
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
