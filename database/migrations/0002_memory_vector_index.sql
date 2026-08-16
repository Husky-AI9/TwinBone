CREATE VECTOR INDEX memories_subject_embedding_idx
    ON memories (tenant_id, subject_id, embedding vector_cosine_ops)
    WITH (min_partition_size = 16, max_partition_size = 128);
