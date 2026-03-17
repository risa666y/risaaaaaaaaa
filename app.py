# ================= 公共公告栏 =================
ANNOUNCEMENT_FILE = f"{SAVE_DIR}/announcements.json"

def load_announcement():
    if os.path.exists(ANNOUNCEMENT_FILE):
        return json.load(open(ANNOUNCEMENT_FILE, "r", encoding="utf-8"))
    return {}

def save_announcement(data):
    json.dump(data, open(ANNOUNCEMENT_FILE, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

announcements = load_announcement()

st.markdown("### 📢 公共栏")

if is_admin:
    text = st.text_area(
        "编辑公告",
        value=announcements.get(tid, ""),
        height=80
    )
    if st.button("保存公告"):
        announcements[tid] = text
        save_announcement(announcements)
        st.success("公告已保存")
else:
    st.info(announcements.get(tid, "暂无公告"))
