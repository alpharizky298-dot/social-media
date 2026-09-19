from fastapi import FastAPI, HTTPException, Header
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import sqlite3
import hashlib
import secrets
from datetime import datetime

app = FastAPI(title="Aether Social")

DB = "database.db"

# =========================
# DATABASE
# =========================

def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    db = get_db()

    db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    db.execute("""
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    """)

    db.execute("""
        CREATE TABLE IF NOT EXISTS likes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            post_id INTEGER NOT NULL,
            UNIQUE(user_id, post_id)
        )
    """)

    db.execute("""
        CREATE TABLE IF NOT EXISTS comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            post_id INTEGER NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    db.commit()
    db.close()


init_db()

# =========================
# SESSION
# =========================

sessions = {}


# =========================
# MODELS
# =========================

class RegisterData(BaseModel):
    username: str
    email: str
    password: str


class LoginData(BaseModel):
    username: str
    password: str


class PostData(BaseModel):
    content: str


class CommentData(BaseModel):
    content: str


# =========================
# PASSWORD
# =========================

def hash_password(password):
    salt = secrets.token_hex(16)

    hashed = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode(),
        salt.encode(),
        100000
    )

    return salt + ":" + hashed.hex()


def verify_password(password, stored):
    try:
        salt, stored_hash = stored.split(":")

        hashed = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode(),
            salt.encode(),
            100000
        )

        return secrets.compare_digest(
            hashed.hex(),
            stored_hash
        )

    except:
        return False


# =========================
# AUTH
# =========================

def get_current_user(authorization):

    if not authorization:
        raise HTTPException(
            status_code=401,
            detail="Login diperlukan"
        )

    token = authorization.replace("Bearer ", "")

    user_id = sessions.get(token)

    if not user_id:
        raise HTTPException(
            status_code=401,
            detail="Session tidak valid"
        )

    return user_id


# =========================
# REGISTER
# =========================

@app.post("/api/register")
def register(data: RegisterData):

    if len(data.username) < 3:
        raise HTTPException(
            status_code=400,
            detail="Username minimal 3 karakter"
        )

    if len(data.password) < 6:
        raise HTTPException(
            status_code=400,
            detail="Password minimal 6 karakter"
        )

    db = get_db()

    existing = db.execute(
        """
        SELECT id FROM users
        WHERE username = ? OR email = ?
        """,
        (data.username, data.email)
    ).fetchone()

    if existing:
        db.close()

        raise HTTPException(
            status_code=400,
            detail="Username atau email sudah digunakan"
        )

    password_hash = hash_password(data.password)

    db.execute(
        """
        INSERT INTO users
        (username, email, password_hash, created_at)
        VALUES (?, ?, ?, ?)
        """,
        (
            data.username,
            data.email,
            password_hash,
            datetime.now().isoformat()
        )
    )

    db.commit()
    db.close()

    return {
        "message": "Akun berhasil dibuat"
    }


# =========================
# LOGIN
# =========================

@app.post("/api/login")
def login(data: LoginData):

    db = get_db()

    user = db.execute(
        """
        SELECT * FROM users
        WHERE username = ?
        """,
        (data.username,)
    ).fetchone()

    db.close()

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Username atau password salah"
        )

    if not verify_password(
        data.password,
        user["password_hash"]
    ):
        raise HTTPException(
            status_code=401,
            detail="Username atau password salah"
        )

    token = secrets.token_urlsafe(32)

    sessions[token] = user["id"]

    return {
        "message": "Login berhasil",
        "token": token,
        "username": user["username"]
    }


# =========================
# ME
# =========================

@app.get("/api/me")
def me(authorization: str = Header(None)):

    user_id = get_current_user(authorization)

    db = get_db()

    user = db.execute(
        """
        SELECT id, username, email, created_at
        FROM users
        WHERE id = ?
        """,
        (user_id,)
    ).fetchone()

    db.close()

    return dict(user)


# =========================
# CREATE POST
# =========================

@app.post("/api/posts")
def create_post(
    data: PostData,
    authorization: str = Header(None)
):

    user_id = get_current_user(authorization)

    content = data.content.strip()

    if not content:
        raise HTTPException(
            status_code=400,
            detail="Postingan tidak boleh kosong"
        )

    if len(content) > 1000:
        raise HTTPException(
            status_code=400,
            detail="Postingan maksimal 1000 karakter"
        )

    db = get_db()

    db.execute(
        """
        INSERT INTO posts
        (user_id, content, created_at)
        VALUES (?, ?, ?)
        """,
        (
            user_id,
            content,
            datetime.now().isoformat()
        )
    )

    db.commit()
    db.close()

    return {
        "message": "Posting berhasil"
    }


# =========================
# GET POSTS
# =========================

@app.get("/api/posts")
def get_posts():

    db = get_db()

    posts = db.execute(
        """
        SELECT
            posts.id,
            posts.content,
            posts.created_at,
            users.username,
            users.id AS user_id,
            COUNT(DISTINCT likes.id) AS likes,
            COUNT(DISTINCT comments.id) AS comments
        FROM posts
        JOIN users
        ON users.id = posts.user_id

        LEFT JOIN likes
        ON likes.post_id = posts.id

        LEFT JOIN comments
        ON comments.post_id = posts.id

        GROUP BY posts.id

        ORDER BY posts.id DESC
        """
    ).fetchall()

    result = [dict(post) for post in posts]

    db.close()

    return result


# =========================
# LIKE
# =========================

@app.post("/api/posts/{post_id}/like")
def like_post(
    post_id: int,
    authorization: str = Header(None)
):

    user_id = get_current_user(authorization)

    db = get_db()

    existing = db.execute(
        """
        SELECT id FROM likes
        WHERE user_id = ? AND post_id = ?
        """,
        (user_id, post_id)
    ).fetchone()

    if existing:

        db.execute(
            """
            DELETE FROM likes
            WHERE user_id = ? AND post_id = ?
            """,
            (user_id, post_id)
        )

        liked = False

    else:

        db.execute(
            """
            INSERT INTO likes
            (user_id, post_id)
            VALUES (?, ?)
            """,
            (user_id, post_id)
        )

        liked = True

    db.commit()

    db.close()

    return {
        "liked": liked
    }


# =========================
# COMMENTS
# =========================

@app.post("/api/posts/{post_id}/comments")
def add_comment(
    post_id: int,
    data: CommentData,
    authorization: str = Header(None)
):

    user_id = get_current_user(authorization)

    content = data.content.strip()

    if not content:
        raise HTTPException(
            status_code=400,
            detail="Komentar kosong"
        )

    db = get_db()

    db.execute(
        """
        INSERT INTO comments
        (user_id, post_id, content, created_at)
        VALUES (?, ?, ?, ?)
        """,
        (
            user_id,
            post_id,
            content,
            datetime.now().isoformat()
        )
    )

    db.commit()
    db.close()

    return {
        "message": "Komentar berhasil"
    }


@app.get("/api/posts/{post_id}/comments")
def get_comments(post_id: int):

    db = get_db()

    comments = db.execute(
        """
        SELECT
            comments.id,
            comments.content,
            comments.created_at,
            users.username
        FROM comments
        JOIN users
        ON users.id = comments.user_id
        WHERE comments.post_id = ?
        ORDER BY comments.id ASC
        """,
        (post_id,)
    ).fetchall()

    result = [dict(comment) for comment in comments]

    db.close()

    return result


# =========================
# LOGOUT
# =========================

@app.post("/api/logout")
def logout(authorization: str = Header(None)):

    if authorization:

        token = authorization.replace(
            "Bearer ",
            ""
        )

        sessions.pop(token, None)

    return {
        "message": "Logout berhasil"
    }


# =========================
# FRONTEND
# =========================

app.mount(
    "/",
    StaticFiles(
        directory="static",
        html=True
    ),
    name="static"
)
