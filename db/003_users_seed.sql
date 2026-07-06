-- ============================================================
-- the-M — User seed script
-- Run AFTER 001_schema.sql and auth_service/SCHEMA.sql
--
-- Users:
--   admin   / admin123   (super_admin)
--   avi     / avi123     (super_admin)
--
-- To apply:
--   docker cp db/003_users_seed.sql them-postgres:/tmp/them_003_users_seed.sql
--   docker exec them-postgres psql -U them -d them -f /tmp/them_003_users_seed.sql
-- ============================================================

-- Ensure roles exist (idempotent)
INSERT INTO auth_service.roles (id, name) VALUES
    (1, 'super_admin'),
    (2, 'developer'),
    (3, 'analyst'),
    (4, 'viewer')
ON CONFLICT (id) DO NOTHING;

-- Reset role id sequence in case of fresh DB
SELECT setval('auth_service.roles_id_seq', (SELECT MAX(id) FROM auth_service.roles));

-- Users (bcrypt hashed passwords, cost factor 12)
--   admin  → admin123
--   avi    → avi123
INSERT INTO auth_service.users (username, name, email, role_id, password_hash, active)
VALUES
    (
        'admin',
        'Administrator',
        'admin@them.local',
        1,
        '$2b$12$DZUNNIwrBXjGksKxfkg0fOqAlvNn47G6hXJ6cOMxP1Bpfiw/ZzVSK',
        true
    ),
    (
        'avi',
        'Avi Cohen',
        'avi.cohen@shift4.com',
        1,
        '$2b$12$oePlJ/q0ncXcv7pM7S7IY.IytHiFztMCcOa1xteo/VjYStx5HOCq6',
        true
    )
ON CONFLICT (username) DO UPDATE SET
    name          = EXCLUDED.name,
    email         = EXCLUDED.email,
    role_id       = EXCLUDED.role_id,
    password_hash = EXCLUDED.password_hash,
    active        = EXCLUDED.active;

-- Reset user id sequence
SELECT setval('auth_service.users_id_seq', (SELECT MAX(id) FROM auth_service.users));
