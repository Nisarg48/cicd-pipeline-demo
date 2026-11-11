const app = document.getElementById("app");

const state = {
  user: null,
  pendingLogin: null,
  flash: null,
};

let toastTimer;

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function formatDate(value) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleString();
}

async function api(path, options = {}) {
  const requestOptions = {
    ...options,
    headers: {
      Accept: "application/json",
      ...(options.headers || {}),
    },
  };

  if (options.body !== undefined) {
    requestOptions.headers["Content-Type"] = "application/json";
    requestOptions.body = JSON.stringify(options.body);
  }

  const response = await fetch(path, requestOptions);
  const text = await response.text();
  let data = null;

  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = text;
    }
  }

  if (!response.ok) {
    const error = new Error(
      (data && data.error) || `Request failed (${response.status})`
    );
    error.status = response.status;
    throw error;
  }

  return data;
}

function setFormError(form, message) {
  const element = form.querySelector(".form-error");
  if (element) {
    element.textContent = message || "";
  }
}

function showToast(message, kind = "info") {
  const toast = document.getElementById("toast");
  toast.textContent = message;
  toast.className = `toast ${kind}`;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => {
    toast.className = "toast hidden";
  }, 3000);
}

function renderNav() {
  const nav = document.getElementById("nav");

  if (state.user) {
    nav.innerHTML = `
      <a href="#/posts/new">New Post</a>
      <span class="nav-user">${escapeHtml(state.user.username)}</span>
      <button type="button" id="logout-button" class="link-button">Logout</button>
    `;
    document
      .getElementById("logout-button")
      .addEventListener("click", logout);
    return;
  }

  nav.innerHTML = `
    <a href="#/login">Login</a>
    <a href="#/register">Register</a>
  `;
}

async function refreshUser() {
  try {
    state.user = await api("/api/me");
  } catch {
    state.user = null;
  }
}

async function logout() {
  try {
    await api("/api/logout", { method: "POST" });
  } catch (error) {
    showToast(error.message, "error");
  }

  state.user = null;
  renderNav();
  showToast("Logged out.");
  location.hash = "#/";
}

async function renderHome() {
  const posts = await api("/api/posts");

  if (!posts.length) {
    app.innerHTML = `
      <h1>Posts</h1>
      <p class="muted">No posts yet.</p>
    `;
    return;
  }

  app.innerHTML = `
    <div class="page-heading">
      <h1>Posts</h1>
      ${state.user ? '<a class="button" href="#/posts/new">New Post</a>' : ""}
    </div>
    ${posts
      .map(
        (post) => `
          <article class="post-card">
            <h2><a href="#/posts/${post.id}">${escapeHtml(post.title)}</a></h2>
            <p class="meta">By ${escapeHtml(post.author.username)} (${escapeHtml(post.author.email)}) · ${escapeHtml(formatDate(post.created_at))}</p>
            <p class="excerpt">${escapeHtml(post.body.slice(0, 160))}${post.body.length > 160 ? "…" : ""}</p>
          </article>
        `
      )
      .join("")}
  `;
}

async function renderPost(postId) {
  const post = await api(`/api/posts/${postId}`);
  const isOwner = state.user && state.user.id === post.author.id;

  app.innerHTML = `
    <article class="post">
      <h1>${escapeHtml(post.title)}</h1>
      <p class="meta">By ${escapeHtml(post.author.username)} (${escapeHtml(post.author.email)}) · ${escapeHtml(formatDate(post.created_at))}</p>
      <div class="post-body">${escapeHtml(post.body).replaceAll("\n", "<br>")}</div>
      ${
        isOwner
          ? `
            <div class="actions">
              <a class="button" href="#/posts/${post.id}/edit">Edit</a>
              <button type="button" class="button danger" id="delete-post">Delete</button>
            </div>
          `
          : ""
      }
    </article>

    <section class="comments">
      <h2>Comments (${post.comments.length})</h2>
      ${
        post.comments.length
          ? post.comments
              .map((comment) => {
                const canDelete =
                  state.user && state.user.id === comment.author.id;
                return `
                  <div class="comment">
                    <p class="meta">${escapeHtml(comment.author.username)} (${escapeHtml(comment.author.email)}) · ${escapeHtml(formatDate(comment.created_at))}</p>
                    <p class="comment-body">${escapeHtml(comment.body).replaceAll("\n", "<br>")}</p>
                    ${
                      canDelete
                        ? `<button type="button" class="link-button danger-text" data-delete-comment="${comment.id}">Delete</button>`
                        : ""
                    }
                  </div>
                `;
              })
              .join("")
          : '<p class="muted">No comments yet.</p>'
      }

      ${
        state.user
          ? `
            <form id="comment-form" class="form">
              <label for="comment-body">Add a comment</label>
              <textarea id="comment-body" name="body" rows="3" required></textarea>
              <p class="form-error" role="alert"></p>
              <button type="submit">Post comment</button>
            </form>
          `
          : '<p class="muted"><a href="#/login">Log in</a> to comment.</p>'
      }
    </section>
  `;

  if (isOwner) {
    document
      .getElementById("delete-post")
      .addEventListener("click", async () => {
        if (!confirm("Delete this post?")) {
          return;
        }

        try {
          await api(`/api/posts/${post.id}`, { method: "DELETE" });
          showToast("Post deleted.");
          location.hash = "#/";
        } catch (error) {
          showToast(error.message, "error");
        }
      });
  }

  const commentForm = document.getElementById("comment-form");
  if (commentForm) {
    commentForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      setFormError(commentForm, "");

      const body = commentForm.elements.body.value.trim();
      if (!body) {
        setFormError(commentForm, "Comment cannot be empty.");
        return;
      }

      try {
        await api(`/api/posts/${post.id}/comments`, {
          method: "POST",
          body: { body },
        });
        showToast("Comment added.");
        await renderPost(post.id);
      } catch (error) {
        if (error.status === 401) {
          state.user = null;
          renderNav();
          setFormError(commentForm, "Please log in again.");
          return;
        }
        setFormError(commentForm, error.message);
      }
    });
  }

  document.querySelectorAll("[data-delete-comment]").forEach((button) => {
    button.addEventListener("click", async () => {
      if (!confirm("Delete this comment?")) {
        return;
      }

      try {
        await api(`/api/comments/${button.dataset.deleteComment}`, {
          method: "DELETE",
        });
        showToast("Comment deleted.");
        await renderPost(post.id);
      } catch (error) {
        showToast(error.message, "error");
      }
    });
  });
}

function renderRegister() {
  if (state.user) {
    location.hash = "#/";
    return;
  }

  app.innerHTML = `
    <h1>Register</h1>
    <form id="register-form" class="form">
      <label for="register-username">Username</label>
      <input id="register-username" name="username" autocomplete="username" required>
      <label for="register-email">Email</label>
      <input id="register-email" name="email" type="email" autocomplete="email" required>
      <label for="register-password">Password</label>
      <input id="register-password" name="password" type="password" autocomplete="new-password" required>
      <p class="form-error" role="alert"></p>
      <button type="submit">Create account</button>
    </form>
    <p class="muted">Already have an account? <a href="#/login">Log in</a>.</p>
  `;

  const form = document.getElementById("register-form");
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    setFormError(form, "");

    const username = form.elements.username.value.trim();
    const email = form.elements.email.value.trim();
    const password = form.elements.password.value;

    try {
      await api("/api/register", {
        method: "POST",
        body: { username, email, password },
      });
      state.pendingLogin = { username };
      state.flash = "Account created. Please log in.";
      location.hash = "#/login";
    } catch (error) {
      setFormError(form, error.message);
    }
  });
}

function renderLogin() {
  if (state.user) {
    location.hash = "#/";
    return;
  }

  const pending = state.pendingLogin;
  const flash = state.flash;
  state.pendingLogin = null;
  state.flash = null;

  app.innerHTML = `
    <h1>Login</h1>
    ${flash ? `<p class="notice">${escapeHtml(flash)}</p>` : ""}
    <form id="login-form" class="form">
      <label for="login-username">Username or email</label>
      <input id="login-username" name="username" autocomplete="username" value="${escapeHtml(pending ? pending.username : "")}" required>
      <label for="login-password">Password</label>
      <input id="login-password" name="password" type="password" autocomplete="current-password" required>
      <p class="form-error" role="alert"></p>
      <button type="submit">Log in</button>
    </form>
    <p class="muted">Need an account? <a href="#/register">Register</a>.</p>
  `;

  const form = document.getElementById("login-form");
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    setFormError(form, "");

    const username = form.elements.username.value.trim();
    const password = form.elements.password.value;

    try {
      state.user = await api("/api/login", {
        method: "POST",
        body: { username, password },
      });
      renderNav();
      showToast(`Welcome, ${state.user.username}.`);
      location.hash = "#/";
    } catch (error) {
      setFormError(form, error.message);
    }
  });
}

async function renderEditor(postId) {
  if (!state.user) {
    state.flash = "Please log in to write a post.";
    location.hash = "#/login";
    return;
  }

  let post = null;
  if (postId) {
    post = await api(`/api/posts/${postId}`);
    if (post.author.id !== state.user.id) {
      throw new Error("You can only edit your own posts.");
    }
  }

  app.innerHTML = `
    <h1>${post ? "Edit post" : "New post"}</h1>
    <form id="post-form" class="form">
      <label for="post-title">Title</label>
      <input id="post-title" name="title" value="${post ? escapeHtml(post.title) : ""}" required>
      <label for="post-body">Body</label>
      <textarea id="post-body" name="body" rows="8" required>${post ? escapeHtml(post.body) : ""}</textarea>
      <p class="form-error" role="alert"></p>
      <button type="submit">${post ? "Save changes" : "Publish post"}</button>
    </form>
  `;

  const form = document.getElementById("post-form");
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    setFormError(form, "");

    const title = form.elements.title.value.trim();
    const body = form.elements.body.value.trim();

    try {
      const result = post
        ? await api(`/api/posts/${post.id}`, {
            method: "PUT",
            body: { title, body },
          })
        : await api("/api/posts", {
            method: "POST",
            body: { title, body },
          });

      showToast(post ? "Post updated." : "Post published.");
      location.hash = `#/posts/${result.id}`;
    } catch (error) {
      setFormError(form, error.message);
    }
  });
}

async function route() {
  const hash = location.hash.replace(/^#/, "");
  const parts = hash.split("/").filter(Boolean);

  app.innerHTML = '<p class="muted">Loading…</p>';

  try {
    if (parts.length === 0) {
      await renderHome();
    } else if (parts[0] === "login") {
      renderLogin();
    } else if (parts[0] === "register") {
      renderRegister();
    } else if (parts[0] === "posts" && parts[1] === "new") {
      await renderEditor(null);
    } else if (parts[0] === "posts" && parts[1] && parts[2] === "edit") {
      await renderEditor(parts[1]);
    } else if (parts[0] === "posts" && parts[1]) {
      await renderPost(parts[1]);
    } else {
      app.innerHTML = '<h1>Not found</h1><p><a href="#/">Go home</a>.</p>';
    }
  } catch (error) {
    if (error.status === 404) {
      app.innerHTML = '<h1>Not found</h1><p><a href="#/">Go home</a>.</p>';
      return;
    }

    if (error.status === 401) {
      state.user = null;
      renderNav();
      state.flash = "Please log in to continue.";
      location.hash = "#/login";
      return;
    }

    app.innerHTML = `<h1>Something went wrong</h1><p class="error">${escapeHtml(error.message)}</p>`;
  }
}

async function loadVersion() {
  const shaElement = document.getElementById("build-sha");
  const timeElement = document.getElementById("build-time");

  try {
    const data = await api("/version");
    shaElement.textContent = data.sha || "unknown";
    timeElement.textContent = data.build_time || "unknown";
  } catch (error) {
    shaElement.textContent = "unknown";
    timeElement.textContent = "unknown";
    console.error("Failed to load version info:", error);
  }
}

async function init() {
  await refreshUser();
  renderNav();
  await loadVersion();
  window.addEventListener("hashchange", route);
  await route();
}

init();
