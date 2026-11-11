INSERT INTO users (username, email, password_hash)
SELECT 'alice', 'alice@example.com', '$2b$12$bwG5VX3RcNzmJYjcgsAM8erpiOJ5QrRbMkTBuhzVNwuUiOHK1w1Mu'
WHERE NOT EXISTS (SELECT 1 FROM users WHERE username = 'alice');

INSERT INTO users (username, email, password_hash)
SELECT 'bob', 'bob@example.com', '$2b$12$rdJhRSeXXRFW7uGYS5eKieoCuU.78rucrtroJYdwTrR7kJZZp9t0a'
WHERE NOT EXISTS (SELECT 1 FROM users WHERE username = 'bob');

INSERT INTO posts (user_id, title, body)
SELECT u.id, 'Welcome to my blog', 'This is my very first post.'
FROM users u
WHERE u.username = 'alice'
  AND NOT EXISTS (
      SELECT 1 FROM posts p
      WHERE p.user_id = u.id AND p.title = 'Welcome to my blog'
  );

INSERT INTO posts (user_id, title, body)
SELECT u.id, 'Learning Kubernetes', 'Today I deployed my first pod.'
FROM users u
WHERE u.username = 'alice'
  AND NOT EXISTS (
      SELECT 1 FROM posts p
      WHERE p.user_id = u.id AND p.title = 'Learning Kubernetes'
  );

INSERT INTO posts (user_id, title, body)
SELECT u.id, 'Hello World', 'Just getting started here.'
FROM users u
WHERE u.username = 'bob'
  AND NOT EXISTS (
      SELECT 1 FROM posts p
      WHERE p.user_id = u.id AND p.title = 'Hello World'
  );

INSERT INTO comments (post_id, user_id, body)
SELECT p.id, u.id, 'Nice first post!'
FROM posts p
JOIN users author ON author.id = p.user_id AND author.username = 'alice'
JOIN users u ON u.username = 'bob'
WHERE p.title = 'Welcome to my blog'
  AND NOT EXISTS (
      SELECT 1 FROM comments c
      WHERE c.post_id = p.id AND c.user_id = u.id AND c.body = 'Nice first post!'
  );

INSERT INTO comments (post_id, user_id, body)
SELECT p.id, u.id, 'Welcome aboard!'
FROM posts p
JOIN users author ON author.id = p.user_id AND author.username = 'bob'
JOIN users u ON u.username = 'alice'
WHERE p.title = 'Hello World'
  AND NOT EXISTS (
      SELECT 1 FROM comments c
      WHERE c.post_id = p.id AND c.user_id = u.id AND c.body = 'Welcome aboard!'
  );
