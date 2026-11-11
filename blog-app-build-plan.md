# Blog Application — Build Plan

This document is the complete specification for building the blog application.
It is written for a coding agent to implement, phase by phase. Each phase must
result in a working, committable state so it can be pushed through the CI/CD
pipeline and visually verified before moving to the next phase.

---

## 1. Tech Stack

- **Backend**: Python 3.11, Flask
- **Database**: MySQL (hosted on AWS RDS, but connect to it the same way locally
  via environment variables — no code should assume RDS specifically)
- **DB driver**: PyMySQL (or mysql-connector-python — agent's choice, pick one
  and use it consistently)
- **Password hashing**: bcrypt
- **Session handling**: Flask's built-in session (signed cookie), not JWT —
  keep this simple
- **Frontend**: Plain HTML, CSS, and vanilla JavaScript — no frontend framework
  (no React/Vue/etc.)
- **Containerization**: Two separate Docker images — one for backend, one for
  frontend. They are deployed as two separate Kubernetes pods.

---

## 2. Folder Structure

Place everything under the existing `application/` folder:

```
application/
├── backend/
│   ├── app.py
│   ├── requirements.txt
│   ├── Dockerfile
│   └── db/
│       ├── schema.sql
│       └── seed.sql
└── frontend/
    ├── index.html
    ├── style.css
    ├── script.js
    └── Dockerfile
```

---

## 3. Database Schema

Three tables, with real relationships between them (not flat/independent tables):

### `users`
- `id` — primary key, auto-increment
- `username` — unique, required
- `email` — unique, required
- `password_hash` — required (bcrypt hash, never store or return plaintext)
- `created_at` — timestamp, defaults to now

### `posts`
- `id` — primary key, auto-increment
- `user_id` — foreign key → `users.id`, cascade delete (deleting a user deletes their posts)
- `title` — required
- `body` — required, long text
- `created_at` — timestamp, defaults to now
- `updated_at` — timestamp, updates on edit

### `comments`
- `id` — primary key, auto-increment
- `post_id` — foreign key → `posts.id`, cascade delete
- `user_id` — foreign key → `users.id`, cascade delete
- `body` — required
- `created_at` — timestamp, defaults to now

Write this schema into `backend/db/schema.sql`.

---

## 4. Security Requirements — non-negotiable

- `password_hash` must **never** appear in any API response, under any
  endpoint, ever — not even to the user who owns the account.
- Passwords must be hashed with bcrypt before storage. Never store or log
  plaintext passwords.
- Emails must be **masked** whenever shown publicly (e.g. on a post's author
  byline, or in a comment's author name). Masking format: show the first 2
  characters of the local part, then `***`, then the domain —
  example: `jo***@example.com` for `john@example.com`.
  A logged-in user may see their own unmasked email on their own profile view
  only — never another user's.
- All write endpoints (create/edit/delete post, create/delete comment) require
  an active logged-in session.
- A user may only edit or delete their **own** posts and comments. Attempting
  to edit/delete someone else's must return a 403, not succeed silently.

---

## 5. Backend API Endpoints

### Health and version (build these first, before anything else)
- `GET /health` — returns 200 OK if the app process is alive. No DB check.
- `GET /health/db` — attempts a DB connection/query, returns 200 if successful,
  500 if not. Used to verify DB connectivity separately from app liveness.
- `GET /version` — returns JSON with the git commit SHA and build timestamp,
  both read from environment variables (`BUILD_SHA`, `BUILD_TIME`) that
  Jenkins will inject at build time. If the env vars are unset, return
  `"unknown"` for each rather than erroring.

### Auth
- `POST /api/register` — body: `username`, `email`, `password`. Hashes the
  password, creates the user. Returns the created user's id, username, and
  email (never the hash).
- `POST /api/login` — body: `username` or `email`, `password`. Verifies the
  hash, starts a session. Returns basic user info on success, 401 on failure.
- `POST /api/logout` — clears the session.
- `GET /api/me` — returns the current logged-in user's own info (unmasked
  email allowed here specifically), or 401 if not logged in.

### Posts
- `GET /api/posts` — list all posts, newest first. Each post includes the
  author's username and **masked** email. No login required.
- `GET /api/posts/:id` — single post plus its comments. No login required.
- `POST /api/posts` — create a post. Requires login.
- `PUT /api/posts/:id` — edit a post. Requires login, owner only.
- `DELETE /api/posts/:id` — delete a post. Requires login, owner only.

### Comments
- `POST /api/posts/:id/comments` — add a comment to a post. Requires login.
- `DELETE /api/comments/:id` — delete a comment. Requires login, owner only.

---

## 6. Frontend Pages

Plain HTML/JS, calling the backend API via `fetch()`:

- **Home page** — lists all posts (title, masked author, created date),
  links to each post's detail page
- **Post detail page** — full post body, its comments, a comment form
  (if logged in)
- **Register page** — simple form
- **Login page** — simple form
- **Create/Edit post page** — form, only reachable if logged in
- **A small footer on every page** showing the build version info from
  `GET /version` — this is how you visually confirm a new deployment went live

---

## 7. Environment Variables

The backend must read all of the following from environment variables —
nothing hardcoded:

- `DB_HOST`
- `DB_PORT`
- `DB_NAME`
- `DB_USER`
- `DB_PASSWORD`
- `SECRET_KEY` — used to sign session cookies
- `BUILD_SHA` — injected by Jenkins at build time
- `BUILD_TIME` — injected by Jenkins at build time

---

## 8. Initial Dummy Data

Create `backend/db/seed.sql` with the following, so there's visible data
immediately after first deploy:

**Users** (passwords shown here in plaintext only for reference — store as
bcrypt hashes in the actual seed data):
- username: `alice`, email: `alice@example.com`, password: `alice123`
- username: `bob`, email: `bob@example.com`, password: `bob123`

**Posts**:
- By alice: title "Welcome to my blog", body "This is my very first post."
- By alice: title "Learning Kubernetes", body "Today I deployed my first pod."
- By bob: title "Hello World", body "Just getting started here."

**Comments**:
- bob comments on alice's "Welcome to my blog" post: "Nice first post!"
- alice comments on bob's "Hello World" post: "Welcome aboard!"

The seed script should be safe to run multiple times without creating
duplicates (check if data already exists before inserting).

---

## 9. Phased Build Plan

Each phase below should be its own commit and push, so the CI/CD pipeline
runs and the result can be visually checked before moving to the next phase.

| Phase | What to build | How to verify it worked |
|-------|---------------|--------------------------|
| v0.1 | Backend skeleton: `/health` and `/version` only, no DB yet. Frontend: one static page showing "Blog App" + version footer. | Page loads, shows version info, `/health` returns 200 |
| v0.2 | DB connectivity: add `/health/db`, connect to MySQL using env vars | `/health/db` returns 200 when DB is reachable |
| v0.3 | Create `schema.sql` and `seed.sql`, apply schema, run seed data | Querying the DB directly shows the 2 users, 3 posts, 2 comments |
| v0.4 | Auth endpoints: register, login, logout, `/api/me` | Can register a new user and log in via a basic form or curl |
| v0.5 | Posts CRUD (all 5 endpoints), authorization checks on edit/delete | Can create, view, edit, delete a post; editing someone else's post returns 403 |
| v0.6 | Comments CRUD (both endpoints) | Can add and delete a comment, tied to the right post and user |
| v0.7 | Frontend wiring: all pages from Section 6, calling the real API | Full flow works end-to-end from the browser: register → login → create post → comment |
| v0.8 | Email masking verified everywhere it's displayed publicly | No API response anywhere shows an unmasked email except `/api/me` |
| v0.9 | Final polish: confirm `password_hash` never leaks in any response, confirm version footer shows real build info after a Jenkins-built deploy | Manual check of every endpoint's response body |

---

## 10. Rules for the Agent

- Keep the code simple and readable — this is a learning/demo project, not a
  production system. Favor clarity over cleverness.
- Do not add a frontend framework, build tooling, or bundler. Plain files only.
- Do not implement OAuth, third-party login, or JWT. Simple session-based auth
  only, as specified above.
- Do not hardcode any credentials, hostnames, or secrets anywhere in the code.
  Everything configurable must come from environment variables.
- Do not skip the health/version endpoints — they're required for Kubernetes
  probes and for visually confirming deployments later in the pipeline.
- Each phase in Section 9 should be completed and working before starting the
  next one — do not jump ahead or combine phases.
