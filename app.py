# ================= 登录 =================
if "user" not in st.session_state:
    st.session_state.user = None

with st.sidebar:
    st.title("🔐 登录")

    st.components.v1.html("""
    <style>
    .login-box { position: relative; }
    .dropdown {
        position: absolute;
        top: 38px;
        left: 0;
        width: 100%;
        background: white;
        border: 1px solid #ddd;
        border-radius: 6px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        max-height: 200px;
        overflow-y: auto;
        display: none;
        z-index: 9999;
    }
    .item { padding: 8px; cursor: pointer; }
    .item:hover { background: #f5f5f5; }
    </style>

    <div class="login-box">
        <input id="user_input" placeholder="请输入用户名" style="width:100%;padding:6px;" />
        <div id="dropdown" class="dropdown"></div>
    </div>

    <button onclick="login()" style="width:100%;margin-top:8px;">登录</button>

    <script>
    const input = document.getElementById("user_input");
    const dropdown = document.getElementById("dropdown");

    let arr = localStorage.getItem("saved_usernames");
    arr = arr ? JSON.parse(arr) : [];

    function renderList(){
        dropdown.innerHTML = "";
        arr.forEach(u => {
            const div = document.createElement("div");
            div.className = "item";
            div.innerText = u;
            div.onclick = () => {
                input.value = u;
                dropdown.style.display = "none";
            };
            dropdown.appendChild(div);
        });
    }

    renderList();

    if(arr.length > 0){
        input.value = arr[arr.length - 1];
    }

    input.addEventListener("focus", () => {
        dropdown.style.display = "block";
    });

    document.addEventListener("click", (e) => {
        if(!e.target.closest(".login-box")){
            dropdown.style.display = "none";
        }
    });

    function login(){
        const val = input.value || "";
        const url = new URL(window.location);
        url.searchParams.set("login_user", val);
        window.location.href = url.toString();
    }

    input.addEventListener("keydown", function(e){
        if(e.key === "Enter"){
            login();
        }
    });
    </script>
    """, height=180)

    # ✅ Python接收
    params = st.experimental_get_query_params()

    if "login_user" in params:
        username = params["login_user"][0].strip()

        if username in ADMIN_USERS or username in USER_MAP:

            # 保存历史
            st.components.v1.html(f"""
            <script>
            let arr = localStorage.getItem("saved_usernames");
            arr = arr ? JSON.parse(arr) : [];

            if(!arr.includes("{username}")) {{
                arr.push("{username}");
            }}

            localStorage.setItem("saved_usernames", JSON.stringify(arr));
            </script>
            """, height=0)

            st.session_state.user = username

            # ⚠️ 清除参数（防止刷新重复登录）
            st.experimental_set_query_params()

            st.rerun()
        else:
            st.error("用户不存在")

    if st.button("退出"):
        st.session_state.user = None
        st.rerun()

user = st.session_state.user
if not user:
    st.stop()
