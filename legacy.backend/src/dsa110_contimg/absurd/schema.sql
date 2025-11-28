-- Absurd Workflow Manager Database Schema
-- PostgreSQL 12+ required
-- =============================================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE SCHEMA IF NOT EXISTS absurd;

-- =============================================================================
-- Main Tasks Table
-- =============================================================================

CREATE TABLE IF NOT EXISTS absurd.tasks (
    task_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    queue_name TEXT NOT NULL,
    task_name TEXT NOT NULL,
    params JSONB NOT NULL DEFAULT '{}',
    priority INTEGER NOT NULL DEFAULT 0,
    timeout_sec INTEGER,
    
    -- Status tracking
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'claimed', 'completed', 'failed', 'cancelled', 'retrying')),
    worker_id TEXT,
    
    -- Retry tracking
    attempt INTEGER NOT NULL DEFAULT 0,
    max_retries INTEGER NOT NULL DEFAULT 3,
    
    -- Result and error
    result JSONB,
    error TEXT,
    
    -- Timing
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    claimed_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    
    -- Metrics
    wait_time_sec DOUBLE PRECISION,
    execution_time_sec DOUBLE PRECISION
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_tasks_queue_status ON absurd.tasks(queue_name, status);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON absurd.tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_created_at ON absurd.tasks(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_tasks_worker_id ON absurd.tasks(worker_id) WHERE worker_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_tasks_priority ON absurd.tasks(priority DESC, created_at);

-- =============================================================================
-- Stored Functions
-- =============================================================================

-- Function to spawn a new task
CREATE OR REPLACE FUNCTION absurd.spawn_task(
    p_queue_name TEXT,
    p_task_name TEXT,
    p_params JSONB,
    p_priority INTEGER DEFAULT 0,
    p_timeout_sec INTEGER DEFAULT NULL,
    p_max_retries INTEGER DEFAULT 3
) RETURNS UUID AS $$
DECLARE
    v_task_id UUID;
BEGIN
    INSERT INTO absurd.tasks (
        queue_name,
        task_name,
        params,
        priority,
        timeout_sec,
        max_retries,
        status
    ) VALUES (
        p_queue_name,
        p_task_name,
        p_params,
        p_priority,
        p_timeout_sec,
        p_max_retries,
        'pending'
    ) RETURNING task_id INTO v_task_id;
    
    RETURN v_task_id;
END;
$$ LANGUAGE plpgsql;

-- Function to claim a task (worker takes ownership)
CREATE OR REPLACE FUNCTION absurd.claim_task(
    p_queue_name TEXT,
    p_worker_id TEXT
) RETURNS TABLE (
    task_id UUID,
    queue_name TEXT,
    task_name TEXT,
    params JSONB,
    priority INTEGER,
    timeout_sec INTEGER,
    status TEXT,
    worker_id TEXT,
    attempt INTEGER,
    max_retries INTEGER,
    created_at TIMESTAMP WITH TIME ZONE,
    claimed_at TIMESTAMP WITH TIME ZONE
) AS $$
DECLARE
    v_task_id UUID;
BEGIN
    -- Find highest priority pending task and claim it atomically
    UPDATE absurd.tasks
    SET status = 'claimed',
        worker_id = p_worker_id,
        claimed_at = NOW(),
        attempt = attempt + 1
    WHERE absurd.tasks.task_id = (
        SELECT absurd.tasks.task_id
        FROM absurd.tasks
        WHERE absurd.tasks.queue_name = p_queue_name
          AND absurd.tasks.status = 'pending'
        ORDER BY priority DESC, created_at ASC
        LIMIT 1
        FOR UPDATE SKIP LOCKED
    )
    RETURNING absurd.tasks.task_id INTO v_task_id;
    
    -- Return the claimed task
    RETURN QUERY
    SELECT 
        t.task_id,
        t.queue_name,
        t.task_name,
        t.params,
        t.priority,
        t.timeout_sec,
        t.status,
        t.worker_id,
        t.attempt,
        t.max_retries,
        t.created_at,
        t.claimed_at
    FROM absurd.tasks t
    WHERE t.task_id = v_task_id;
END;
$$ LANGUAGE plpgsql;

-- Function to complete a task successfully
CREATE OR REPLACE FUNCTION absurd.complete_task(
    p_task_id UUID,
    p_result JSONB
) RETURNS BOOLEAN AS $$
DECLARE
    v_claimed_at TIMESTAMP WITH TIME ZONE;
    v_execution_time DOUBLE PRECISION;
    v_wait_time DOUBLE PRECISION;
BEGIN
    -- Get claimed_at time for metrics
    SELECT claimed_at, 
           EXTRACT(EPOCH FROM (claimed_at - created_at)),
           EXTRACT(EPOCH FROM (NOW() - claimed_at))
    INTO v_claimed_at, v_wait_time, v_execution_time
    FROM absurd.tasks
    WHERE task_id = p_task_id;
    
    IF NOT FOUND THEN
        RETURN FALSE;
    END IF;
    
    UPDATE absurd.tasks
    SET status = 'completed',
        result = p_result,
        completed_at = NOW(),
        wait_time_sec = v_wait_time,
        execution_time_sec = v_execution_time
    WHERE task_id = p_task_id
      AND status = 'claimed';
    
    RETURN FOUND;
END;
$$ LANGUAGE plpgsql;

-- Function to fail a task
CREATE OR REPLACE FUNCTION absurd.fail_task(
    p_task_id UUID,
    p_error TEXT
) RETURNS BOOLEAN AS $$
DECLARE
    v_claimed_at TIMESTAMP WITH TIME ZONE;
    v_execution_time DOUBLE PRECISION;
    v_wait_time DOUBLE PRECISION;
BEGIN
    -- Get timing for metrics
    SELECT claimed_at,
           EXTRACT(EPOCH FROM (claimed_at - created_at)),
           EXTRACT(EPOCH FROM (NOW() - claimed_at))
    INTO v_claimed_at, v_wait_time, v_execution_time
    FROM absurd.tasks
    WHERE task_id = p_task_id;
    
    IF NOT FOUND THEN
        RETURN FALSE;
    END IF;
    
    UPDATE absurd.tasks
    SET status = 'failed',
        error = p_error,
        completed_at = NOW(),
        wait_time_sec = v_wait_time,
        execution_time_sec = v_execution_time
    WHERE task_id = p_task_id
      AND status = 'claimed';
    
    RETURN FOUND;
END;
$$ LANGUAGE plpgsql;

-- Function to cancel a task
CREATE OR REPLACE FUNCTION absurd.cancel_task(
    p_task_id UUID
) RETURNS BOOLEAN AS $$
BEGIN
    UPDATE absurd.tasks
    SET status = 'cancelled',
        completed_at = NOW()
    WHERE task_id = p_task_id
      AND status IN ('pending', 'retrying');
    
    RETURN FOUND;
END;
$$ LANGUAGE plpgsql;

-- Function to retry a failed task
CREATE OR REPLACE FUNCTION absurd.retry_task(
    p_task_id UUID
) RETURNS BOOLEAN AS $$
BEGIN
    UPDATE absurd.tasks
    SET status = 'pending',
        worker_id = NULL,
        claimed_at = NULL,
        error = NULL
    WHERE task_id = p_task_id
      AND status IN ('failed', 'cancelled')
      AND attempt < max_retries;
    
    RETURN FOUND;
END;
$$ LANGUAGE plpgsql;

-- Function to get queue statistics
CREATE OR REPLACE FUNCTION absurd.get_queue_stats(
    p_queue_name TEXT
) RETURNS TABLE (
    pending INTEGER,
    claimed INTEGER,
    completed INTEGER,
    failed INTEGER,
    cancelled INTEGER,
    retrying INTEGER,
    total INTEGER
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        COUNT(*) FILTER (WHERE status = 'pending')::INTEGER as pending,
        COUNT(*) FILTER (WHERE status = 'claimed')::INTEGER as claimed,
        COUNT(*) FILTER (WHERE status = 'completed')::INTEGER as completed,
        COUNT(*) FILTER (WHERE status = 'failed')::INTEGER as failed,
        COUNT(*) FILTER (WHERE status = 'cancelled')::INTEGER as cancelled,
        COUNT(*) FILTER (WHERE status = 'retrying')::INTEGER as retrying,
        COUNT(*)::INTEGER as total
    FROM absurd.tasks
    WHERE queue_name = p_queue_name;
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- Grant Permissions
-- =============================================================================

-- Grant usage on schema
GRANT USAGE ON SCHEMA absurd TO PUBLIC;

-- Grant permissions on tables
GRANT SELECT, INSERT, UPDATE, DELETE ON absurd.tasks TO PUBLIC;

-- Grant execute on functions
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA absurd TO PUBLIC;

-- =============================================================================
-- Comments
-- =============================================================================

COMMENT ON SCHEMA absurd IS 'Absurd durable task queue system';
COMMENT ON TABLE absurd.tasks IS 'Main task queue table storing all task state';
COMMENT ON FUNCTION absurd.spawn_task IS 'Create a new task in the queue';
COMMENT ON FUNCTION absurd.claim_task IS 'Atomically claim next highest-priority pending task';
COMMENT ON FUNCTION absurd.complete_task IS 'Mark task as completed with result';
COMMENT ON FUNCTION absurd.fail_task IS 'Mark task as failed with error message';
COMMENT ON FUNCTION absurd.cancel_task IS 'Cancel a pending task';
COMMENT ON FUNCTION absurd.retry_task IS 'Retry a failed task (reset to pending)';
COMMENT ON FUNCTION absurd.get_queue_stats IS 'Get task count statistics for a queue';
