-- chat/schema.sql — Persistance des conversations
-- Projets + Conversations + Messages (comme Claude)
--
-- epistememory continue de fonctionner en parallele pour le recall
-- semantique. Ici c'est l'historique structuré, navigable.

-- 1. Projets — conteneurs thematiques
CREATE TABLE IF NOT EXISTS chat_projects (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        TEXT NOT NULL,
    description TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_chat_projects_updated
    ON chat_projects (updated_at DESC);

-- 2. Conversations — appartiennent a un projet (ou pas)
CREATE TABLE IF NOT EXISTS chat_conversations (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id  UUID REFERENCES chat_projects(id) ON DELETE SET NULL,
    title       TEXT NOT NULL DEFAULT 'Nouvelle conversation',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_chat_conversations_project
    ON chat_conversations (project_id, updated_at DESC);

CREATE INDEX IF NOT EXISTS idx_chat_conversations_updated
    ON chat_conversations (updated_at DESC);

-- 3. Messages — le contenu des echanges
CREATE TABLE IF NOT EXISTS chat_messages (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES chat_conversations(id) ON DELETE CASCADE,
    role            TEXT NOT NULL CHECK (role IN ('user', 'etz', 'system')),
    content         TEXT NOT NULL,
    metadata        JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_chat_messages_conversation
    ON chat_messages (conversation_id, created_at ASC);
