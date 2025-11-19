-- Absurd: Durable Task Queue Schema

CREATE SCHEMA IF NOT EXISTS absurd;

-- Queues table
CREATE TABLE IF NOT EXISTS absurd.queues (
    queue_name TEXT PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    description TEXT
);

-- Tasks table
CREATE TABLE IF NOT EXISTS absurd.t_tasks (
    task_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    queue_name TEXT NOT NULL REFERENCES absurd.queues(queue_name),
    task_name TEXT NOT NULL,
    params JSONB NOT NULL DEFAULT '{}',
    priority INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'pending', -- pending, claimed, completed, failed, cancelled
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    claimed_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    worker_id TEXT,
    result JSONB,
    error TEXT,
    retry_count INTEGER NOT NULL DEFAULT 0,
    max_retries INTEGER NOT NULL DEFAULT 3,
    timeout_sec INTEGER NOT NULL DEFAULT 3600,
    last_heartbeat TIMESTAMPTZ
);

-- Index for efficient polling
CREATE INDEX IF NOT EXISTS idx_tasks_poll 
ON absurd.t_tasks (queue_name, priority DESC, created_at ASC) 
WHERE status = 'pending';

-- Create a queue function
CREATE OR REPLACE FUNCTION absurd.create_queue(p_queue_name TEXT)
RETURNS VOID AS $$
BEGIN
    INSERT INTO absurd.queues (queue_name)
    VALUES (p_queue_name)
    ON CONFLICT (queue_name) DO NOTHING;
END;
$$ LANGUAGE plpgsql;

-- Spawn task function
CREATE OR REPLACE FUNCTION absurd.spawn_task(
    p_queue_name TEXT,
    p_task_name TEXT,
    p_params JSONB,
    p_priority INTEGER DEFAULT 0,
    p_timeout_sec INTEGER DEFAULT 3600
)
RETURNS UUID AS $$
DECLARE
    v_task_id UUID;
BEGIN
    INSERT INTO absurd.t_tasks (
        queue_name, task_name, params, priority, timeout_sec
    )
    VALUES (
        p_queue_name, p_task_name, p_params, p_priority, p_timeout_sec
    )
    RETURNING task_id INTO v_task_id;
    
    RETURN v_task_id;
END;
$$ LANGUAGE plpgsql;

-- Claim task function
CREATE OR REPLACE FUNCTION absurd.claim_task(
    p_queue_name TEXT,
    p_worker_id TEXT
)
RETURNS TABLE (
    task_id UUID,
    queue_name TEXT,
    task_name TEXT,
    params JSONB,
    priority INTEGER,
    status TEXT,
    retry_count INTEGER
) AS $$
BEGIN
    RETURN QUERY
    UPDATE absurd.t_tasks
    SET status = 'claimed',
        worker_id = p_worker_id,
        claimed_at = NOW(),
        last_heartbeat = NOW()
    WHERE absurd.t_tasks.task_id = (
        SELECT t.task_id
        FROM absurd.t_tasks t
        WHERE t.queue_name = p_queue_name
          AND t.status = 'pending'
        ORDER BY t.priority DESC, t.created_at ASC
        FOR UPDATE SKIP LOCKED
        LIMIT 1
    )
    RETURNING 
        absurd.t_tasks.task_id,
        absurd.t_tasks.queue_name,
        absurd.t_tasks.task_name,
        absurd.t_tasks.params,
        absurd.t_tasks.priority,
        absurd.t_tasks.status,
        absurd.t_tasks.retry_count;
END;
$$ LANGUAGE plpgsql;

-- Complete task function
CREATE OR REPLACE FUNCTION absurd.complete_task(
    p_task_id UUID,
    p_result JSONB
)
RETURNS VOID AS $$
BEGIN
    UPDATE absurd.t_tasks
    SET status = 'completed',
        completed_at = NOW(),
        result = p_result
    WHERE task_id = p_task_id;
END;
$$ LANGUAGE plpgsql;

-- Fail task function
CREATE OR REPLACE FUNCTION absurd.fail_task(
    p_task_id UUID,
    p_error TEXT
)
RETURNS VOID AS $$
BEGIN
    UPDATE absurd.t_tasks
    SET status = CASE 
            WHEN retry_count < max_retries THEN 'pending' 
            ELSE 'failed' 
        END,
        completed_at = CASE 
            WHEN retry_count < max_retries THEN NULL 
            ELSE NOW() 
        END,
        error = p_error,
        retry_count = retry_count + 1,
        claimed_at = NULL,
        worker_id = NULL
    WHERE task_id = p_task_id;
END;
$$ LANGUAGE plpgsql;

-- Heartbeat function
CREATE OR REPLACE FUNCTION absurd.heartbeat_task(
    p_task_id UUID
)
RETURNS BOOLEAN AS $$
DECLARE
    v_status TEXT;
BEGIN
    UPDATE absurd.t_tasks
    SET last_heartbeat = NOW()
    WHERE task_id = p_task_id
    RETURNING status INTO v_status;
    
    RETURN (v_status = 'claimed');
END;
$$ LANGUAGE plpgsql;

