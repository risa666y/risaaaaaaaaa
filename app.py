import streamlit as st
import pandas as pd
import os
import json
import hashlib
import re
import shutil
import requests

# 解决部署问题
os.environ["STREAMLIT_SERVER_FILE_WATCHER_TYPE"] = "none"

st.set_page_config(page_title="AI表格系统（DeepSeek版）", layout="wide")

SAVE_DIR = "saved_tables"
os.makedirs(SAVE_DIR, exist_ok=True)

INDEX_FILE = f"{SAVE_DIR}/index.json"
LOG_FILE = f"{SAVE_DIR}/logs.json"

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
        opts.append(info["filename"])
        mp[info["filename"]] = tid
    return opts, mp

# ================= 日志 =================
def add_log(user, tid, action, detail):
    logs = load_json(LOG_FILE, [])
    logs.insert(0, {
        "time": str(pd.Timestamp.now()),
        "user": user,
        "table": tid,
        "action": action,
        "detail": detail
    })
    save_json(logs, LOG_FILE)

# ================= 备份 =================
def backup_table(tid):
    src = f"{SAVE_DIR}/{tid}.xlsx"
    dst = f"{SAVE_DIR}/{tid}_backup.xlsx"
    if os.path.exists(src):
        shutil.copy(src, dst)

# ================= 列匹配 =================
def match_column(col, columns):
    if col in columns:
        return col
    for c in columns:
        if col in c or c in col:
            return c
    return None

# ================= 本地AI（兜底） =================
def local_parse(text):
    result = {"filters": [], "update": {}}

    if m := re.search(r"库存.*小于(\d+)", text):
        result["filters"].append({"column": "库存", "op": "<", "value": m.group(1)})

    if m := re.search(r"库存.*大于(\d+)", text):
        result["filters"].append({"column": "库存", "op": ">", "value": m.group(1)})

    if m := re.search(r"改为(.+)", text):
        result["update"] = {"column": "状态", "value": m.group(1)}

    return result

# ================= DeepSeek =================
def deepseek_parse(user_input, columns):
    try:
        url = "https://api.deepseek.com/v1/chat/completions"

        headers = {
            "Authorization": f"Bearer {st.secrets['DEEPSEEK_API_KEY']}",
            "Content-Type": "application/json"
        }

        prompt = f"""
你是表格AI助手，把用户指令解析为JSON：

列：{columns}

格式：
{{
 "filters":[{{"column":"列","op":"<","value":"值"}}],
 "update":{{"column":"列","value":"值"}}
}}

用户：{user_input}
"""

        data = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": "你是JSON解析器"},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0
        }

        res = requests.post(url, headers=headers, json=data)
        text = res.json()["choices"][0]["message"]["content"]

        return json.loads(text)

    except:
        return None

# ================= 登录 =================
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

# ================= 上传 =================
if is_admin:
    st.sidebar.subheader("上传表格")
    files = st.sidebar.file_uploader("上传Excel", type=["xlsx"], accept_multiple_files=True)

    if st.sidebar.button("确认上传"):
        for f in files:
            df = pd.read_excel(f, dtype=str).fillna("")
            tid = gen_id(f.name)
            save_excel(df, tid)

            idx = load_json(INDEX_FILE, {})
            idx[tid] = {"filename": f.name}
            save_json(idx, INDEX_FILE)

        st.success("上传完成")

# ================= 表格 =================
options, mp = get_tables()
if not options:
    st.warning("没有表格")
    st.stop()

sel = st.selectbox("选择表格", options)
tid = mp[sel]

df = load_excel(tid)

if not is_admin:
    supplier = USER_MAP[user]
    df_edit = df[df["供应商简称"] == supplier].copy()
else:
    df_edit = df.copy()

st.subheader("数据表")
edited = st.data_editor(df_edit, use_container_width=True)

# 保存
if st.button("保存"):
    backup_table(tid)

    if is_admin:
        save_excel(edited, tid)
    else:
        df.loc[df["供应商简称"] == supplier] = edited.values
        save_excel(df, tid)

    add_log(user, tid, "手动修改", f"{len(edited)}行")
    st.success("保存成功")

# ================= AI =================
st.divider()
st.subheader("🤖 AI助手")

msg = st.text_input("输入：把库存小于10的商品改为缺货")

if msg:
    cmd = deepseek_parse(msg, df.columns.tolist())

    if not cmd:
        st.warning("AI失败，使用本地规则")
        cmd = local_parse(msg)

    df_new = df.copy()

    for f in cmd.get("filters", []):
        col = match_column(f["column"], df.columns)
        if not col:
            st.error("列不存在")
            st.stop()

        df_new = df_new[
            pd.to_numeric(df_new[col], errors="coerce")
            .fillna(0)
            .astype(float)
            .pipe(lambda s: eval(f"s {f['op']} {f['value']}"))
        ]

    upd = cmd.get("update", {})
    col = match_column(upd.get("column", ""), df.columns)

    if not col:
        st.error("更新列错误")
        st.stop()

    val = upd.get("value")

    st.warning(f"将修改 {len(df_new)} 行 → {col} = {val}")

    if st.button("确认执行"):
        backup_table(tid)
        df.loc[df_new.index, col] = val
        save_excel(df, tid)

        add_log(user, tid, "AI修改", f"{len(df_new)}行 {col}={val}")
        st.success("修改完成")

# ================= 回滚 =================
st.divider()
st.subheader("⏪ 回滚")

if st.button("恢复上一次"):
    b = f"{SAVE_DIR}/{tid}_backup.xlsx"
    if os.path.exists(b):
        shutil.copy(b, f"{SAVE_DIR}/{tid}.xlsx")
        add_log(user, tid, "回滚", "恢复成功")
        st.success("已恢复")
    else:
        st.warning("无备份")

# ================= 日志 =================
if is_admin:
    st.divider()
    st.subheader("📋 操作日志")

    logs = load_json(LOG_FILE, [])
    if logs:
        st.dataframe(pd.DataFrame(logs))
    else:
        st.info("暂无日志")
