let token = localStorage.getItem("token");


// =========================
// ELEMENTS
// =========================

const auth = document.getElementById("auth");
const social = document.getElementById("social");

const loginBox = document.getElementById("loginBox");
const registerBox = document.getElementById("registerBox");

const authMessage =
    document.getElementById("authMessage");


// =========================
// INITIALIZE
// =========================

async function init() {

    if (!token) {
        showLogin();
        return;
    }

    try {

        await loadProfile();

        showSocial();

        loadPosts();

    } catch {

        logout();

    }
}

init();


// =========================
// SHOW LOGIN
// =========================

function showLogin() {

    loginBox.classList.remove("hidden");

    registerBox.classList.add("hidden");

    authMessage.textContent = "";
}


// =========================
// SHOW REGISTER
// =========================

function showRegister() {

    loginBox.classList.add("hidden");

    registerBox.classList.remove("hidden");

    authMessage.textContent = "";
}


// =========================
// REGISTER
// =========================

async function register() {

    const username =
        document.getElementById(
            "registerUsername"
        ).value.trim();

    const email =
        document.getElementById(
            "registerEmail"
        ).value.trim();

    const password =
        document.getElementById(
            "registerPassword"
        ).value;


    if (!username || !email || !password) {

        authMessage.textContent =
            "Semua kolom harus diisi.";

        return;
    }


    try {

        const response = await fetch(
            "/api/register",
            {
                method: "POST",

                headers: {
                    "Content-Type":
                        "application/json"
                },

                body: JSON.stringify({
                    username,
                    email,
                    password
                })
            }
        );


        const data =
            await response.json();


        if (!response.ok) {

            authMessage.textContent =
                data.detail;

            return;
        }


        authMessage.textContent =
            "Akun berhasil dibuat!";

        showLogin();

    } catch {

        authMessage.textContent =
            "Server tidak dapat dihubungi.";

    }
}


// =========================
// LOGIN
// =========================

async function login() {

    const username =
        document.getElementById(
            "loginUsername"
        ).value.trim();

    const password =
        document.getElementById(
            "loginPassword"
        ).value;


    try {

        const response = await fetch(
            "/api/login",
            {
                method: "POST",

                headers: {
                    "Content-Type":
                        "application/json"
                },

                body: JSON.stringify({
                    username,
                    password
                })
            }
        );


        const data =
            await response.json();


        if (!response.ok) {

            authMessage.textContent =
                data.detail;

            return;
        }


        token = data.token;

        localStorage.setItem(
            "token",
            token
        );


        showSocial();

        loadProfile();

        loadPosts();

    } catch {

        authMessage.textContent =
            "Server tidak dapat dihubungi.";

    }
}


// =========================
// PROFILE
// =========================

async function loadProfile() {

    const response = await fetch(
        "/api/me",
        {
            headers: {
                Authorization:
                    `Bearer ${token}`
            }
        }
    );


    if (!response.ok) {
        throw new Error("Unauthorized");
    }


    const user =
        await response.json();


    document.getElementById(
        "profileUsername"
    ).textContent = user.username;


    document.getElementById(
        "profileEmail"
    ).textContent = user.email;


    document.getElementById(
        "userArea"
    ).innerHTML = `
        <button onclick="logout()">
            Logout
        </button>
    `;

}


// =========================
// SHOW SOCIAL
// =========================

function showSocial() {

    auth.classList.add("hidden");

    social.classList.remove("hidden");

}


// =========================
// CREATE POST
// =========================

async function createPost() {

    const textarea =
        document.getElementById(
            "postContent"
        );


    const content =
        textarea.value.trim();


    if (!content) return;


    const response = await fetch(
        "/api/posts",
        {
            method: "POST",

            headers: {
                "Content-Type":
                    "application/json",

                Authorization:
                    `Bearer ${token}`
            },

            body: JSON.stringify({
                content
            })
        }
    );


    const data =
        await response.json();


    if (!response.ok) {

        alert(data.detail);

        return;
    }


    textarea.value = "";

    updateCharCount();

    loadPosts();

}


// =========================
// LOAD POSTS
// =========================

async function loadPosts() {

    const response =
        await fetch("/api/posts");


    const posts =
        await response.json();


    const container =
        document.getElementById(
            "posts"
        );


    container.innerHTML = "";


    posts.forEach(post => {

        const article =
            document.createElement("article");

        article.className = "post";


        const date =
            new Date(
                post.created_at
            ).toLocaleString(
                "id-ID"
            );


        article.innerHTML = `

            <div class="post-header">

                <div class="small-avatar">
                    ${escapeHTML(
                        post.username
                        .charAt(0)
                        .toUpperCase()
                    )}
                </div>

                <div>

                    <div class="post-user">
                        ${escapeHTML(
                            post.username
                        )}
                    </div>

                    <div class="post-date">
                        ${date}
                    </div>

                </div>

            </div>


            <div class="post-content">
                ${escapeHTML(
                    post.content
                )}
            </div>


            <div class="post-actions">

                <button
                    class="action-btn"
                    onclick="likePost(${post.id})"
                >
                    ❤️ ${post.likes}
                </button>

                <button
                    class="action-btn"
                    onclick="toggleComments(${post.id})"
                >
                    💬 ${post.comments}
                </button>

            </div>


            <div
                id="comments-${post.id}"
                class="comments hidden"
            >

                <div
                    id="comment-list-${post.id}"
                ></div>


                <div class="comment-input">

                    <input
                        id="comment-input-${post.id}"
                        placeholder="Tulis komentar..."
                    >

                    <button
                        onclick="addComment(${post.id})"
                    >
                        Kirim
                    </button>

                </div>

            </div>

        `;


        container.appendChild(article);

    });

}


// =========================
// LIKE
// =========================

async function likePost(id) {

    await fetch(
        `/api/posts/${id}/like`,
        {
            method: "POST",

            headers: {
                Authorization:
                    `Bearer ${token}`
            }
        }
    );


    loadPosts();

}


// =========================
// COMMENTS TOGGLE
// =========================

async function toggleComments(id) {

    const box =
        document.getElementById(
            `comments-${id}`
        );


    box.classList.toggle("hidden");


    if (!box.classList.contains("hidden")) {

        loadComments(id);

    }

}


// =========================
// LOAD COMMENTS
// =========================

async function loadComments(id) {

    const response =
        await fetch(
            `/api/posts/${id}/comments`
        );


    const comments =
        await response.json();


    const list =
        document.getElementById(
            `comment-list-${id}`
        );


    list.innerHTML = "";


    comments.forEach(comment => {

        const div =
            document.createElement("div");

        div.className = "comment";


        div.innerHTML = `
            <strong>
                ${escapeHTML(
                    comment.username
                )}
            </strong>

            <span>
                ${escapeHTML(
                    comment.content
                )}
            </span>
        `;


        list.appendChild(div);

    });

}


// =========================
// ADD COMMENT
// =========================

async function addComment(id) {

    const input =
        document.getElementById(
            `comment-input-${id}`
        );


    const content =
        input.value.trim();


    if (!content) return;


    await fetch(
        `/api/posts/${id}/comments`,
        {
            method: "POST",

            headers: {
                "Content-Type":
                    "application/json",

                Authorization:
                    `Bearer ${token}`
            },

            body: JSON.stringify({
                content
            })
        }
    );


    input.value = "";

    loadComments(id);

    loadPosts();

}


// =========================
// LOGOUT
// =========================

async function logout() {

    if (token) {

        await fetch(
            "/api/logout",
            {
                method: "POST",

                headers: {
                    Authorization:
                        `Bearer ${token}`
                }
            }
        );

    }


    localStorage.removeItem(
        "token"
    );

    token = null;

    social.classList.add(
        "hidden"
    );

    auth.classList.remove(
        "hidden"
    );

    showLogin();

}


// =========================
// CHARACTER COUNTER
// =========================

document
    .getElementById("postContent")
    .addEventListener(
        "input",
        updateCharCount
    );


function updateCharCount() {

    const textarea =
        document.getElementById(
            "postContent"
        );


    document.getElementById(
        "charCount"
    ).textContent =
        `${textarea.value.length} / 1000`;

}


// =========================
// SECURITY
// =========================

function escapeHTML(text) {

    const div =
        document.createElement("div");

    div.textContent = text;

    return div.innerHTML;

}
