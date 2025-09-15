import os
import pymysql
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import pandas as pd
from sentence_transformers import SentenceTransformer
import numpy as np
from dotenv import load_dotenv

load_dotenv()

class TiDBVectorDatabase:
    def __init__(self):
        self.host = os.getenv('TIDB_SERVERLESS_HOST')
        self.port = int(os.getenv('TIDB_SERVERLESS_PORT', '4000'))
        self.user = os.getenv('TIDB_SERVERLESS_USER')
        self.password = os.getenv('TIDB_SERVERLESS_PASSWORD')
        self.database = os.getenv('TIDB_SERVERLESS_DATABASE')

        if not all([self.host, self.user, self.password, self.database]):
            raise ValueError("Missing TiDB credentials in environment variables")

        # Include port in connection string
        self.connection_string = f"mysql+pymysql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}?ssl_verify_cert=true&ssl_verify_identity=true"
        self.engine = create_engine(self.connection_string)
        self.session_maker = sessionmaker(bind=self.engine)

        # Initialize sentence transformer for embeddings
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')

        # Initialize database tables
        self._initialize_tables()

    def _initialize_tables(self):
        """Initialize required tables for the agentic system using exact TiDB queries"""
        with self.engine.connect() as conn:
            # Educational content table with vector search
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS educational_content (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    topic VARCHAR(255) NOT NULL,
                    content TEXT NOT NULL,
                    content_type ENUM('comic', 'template', 'curriculum') DEFAULT 'comic',
                    age_group ENUM('child', 'teen', 'adult') DEFAULT 'child',
                    subject VARCHAR(100),
                    embedding VECTOR(384) COMMENT 'Embedding vector for semantic search',
                    created_at TIMESTAMP DEFAULT '2025-09-16 10:30:00',
                    updated_at TIMESTAMP DEFAULT '2025-09-16 10:30:00',
                    VECTOR INDEX idx_embedding ((VEC_COSINE_DISTANCE(embedding)))
                )
            """))

            # Comic generation history
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS comic_generations (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id VARCHAR(255),
                    topic VARCHAR(255) NOT NULL,
                    comic_style VARCHAR(100),
                    language VARCHAR(10) DEFAULT 'en',
                    status ENUM('pending', 'processing', 'completed', 'failed') DEFAULT 'pending',
                    output_path VARCHAR(500),
                    generation_time_seconds INT,
                    created_at TIMESTAMP DEFAULT '2025-09-16 09:15:00',
                    completed_at TIMESTAMP NULL
                )
            """))

            # Agent execution logs
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS agent_logs (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    generation_id INT,
                    agent_name VARCHAR(100) NOT NULL,
                    step_number INT NOT NULL,
                    input_data TEXT,
                    output_data TEXT,
                    execution_time_ms INT,
                    status ENUM('success', 'error') DEFAULT 'success',
                    error_message TEXT NULL,
                    created_at TIMESTAMP DEFAULT '2025-09-16 09:15:00',
                    FOREIGN KEY (generation_id) REFERENCES comic_generations(id)
                )
            """))

            # Character templates
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS character_templates (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    description TEXT,
                    visual_style VARCHAR(100),
                    personality_traits TEXT,
                    embedding VECTOR(384) COMMENT 'Character description embedding',
                    usage_count INT DEFAULT 0,
                    created_at TIMESTAMP DEFAULT '2025-09-16 08:00:00',
                    VECTOR INDEX idx_character_embedding ((VEC_COSINE_DISTANCE(embedding)))
                )
            """))

            conn.commit()

    def generate_embedding(self, text):
        """Generate embedding for given text"""
        embedding = self.embedding_model.encode(text)
        return embedding.tolist()

    def store_educational_content(self, topic, content, content_type='comic', age_group='child', subject=None):
        """Store educational content with embedding"""
        embedding = self.generate_embedding(f"{topic} {content}")

        with self.engine.connect() as conn:
            result = conn.execute(text("""
                INSERT INTO educational_content (topic, content, content_type, age_group, subject, embedding)
                VALUES (:topic, :content, :content_type, :age_group, :subject, :embedding)
            """), {
                'topic': topic,
                'content': content,
                'content_type': content_type,
                'age_group': age_group,
                'subject': subject,
                'embedding': str(embedding)
            })
            conn.commit()
            return result.lastrowid

    def search_similar_content(self, query, content_type=None, limit=5):
        """Search for similar educational content using vector similarity"""
        query_embedding = self.generate_embedding(query)

        base_query = """
            SELECT id, topic, content, content_type, age_group, subject,
                   VEC_COSINE_DISTANCE(embedding, :query_embedding) as similarity
            FROM educational_content
        """

        conditions = []
        params = {'query_embedding': str(query_embedding)}

        if content_type:
            conditions.append("content_type = :content_type")
            params['content_type'] = content_type

        if conditions:
            base_query += " WHERE " + " AND ".join(conditions)

        base_query += " ORDER BY similarity ASC LIMIT :limit"
        params['limit'] = limit

        with self.engine.connect() as conn:
            result = conn.execute(text(base_query), params)
            return result.fetchall()

    def log_comic_generation(self, user_id, topic, comic_style, language='en'):
        """Log a new comic generation request"""
        with self.engine.connect() as conn:
            result = conn.execute(text("""
                INSERT INTO comic_generations (user_id, topic, comic_style, language, status)
                VALUES (:user_id, :topic, :comic_style, :language, 'processing')
            """), {
                'user_id': user_id,
                'topic': topic,
                'comic_style': comic_style,
                'language': language
            })
            conn.commit()
            return result.lastrowid

    def update_comic_generation_status(self, generation_id, status, output_path=None, generation_time=None):
        """Update comic generation status"""
        with self.engine.connect() as conn:
            update_query = """
                UPDATE comic_generations
                SET status = :status, updated_at = CURRENT_TIMESTAMP
            """
            params = {'generation_id': generation_id, 'status': status}

            if output_path:
                update_query += ", output_path = :output_path"
                params['output_path'] = output_path

            if generation_time:
                update_query += ", generation_time_seconds = :generation_time"
                params['generation_time'] = generation_time

            if status == 'completed':
                update_query += ", completed_at = CURRENT_TIMESTAMP"

            update_query += " WHERE id = :generation_id"

            conn.execute(text(update_query), params)
            conn.commit()

    def log_agent_execution(self, generation_id, agent_name, step_number, input_data, output_data, execution_time_ms, status='success', error_message=None):
        """Log agent execution details"""
        with self.engine.connect() as conn:
            conn.execute(text("""
                INSERT INTO agent_logs (generation_id, agent_name, step_number, input_data, output_data, execution_time_ms, status, error_message)
                VALUES (:generation_id, :agent_name, :step_number, :input_data, :output_data, :execution_time_ms, :status, :error_message)
            """), {
                'generation_id': generation_id,
                'agent_name': agent_name,
                'step_number': step_number,
                'input_data': input_data[:1000] if input_data else None,  # Truncate for storage
                'output_data': output_data[:1000] if output_data else None,
                'execution_time_ms': execution_time_ms,
                'status': status,
                'error_message': error_message
            })
            conn.commit()

    def get_successful_comic_patterns(self, topic_similarity_threshold=0.8, limit=10):
        """Get patterns from successful comic generations for similar topics"""
        with self.engine.connect() as conn:
            result = conn.execute(text("""
                SELECT cg.topic, cg.comic_style, cg.language, cg.generation_time_seconds,
                       COUNT(al.id) as agent_steps,
                       AVG(al.execution_time_ms) as avg_step_time
                FROM comic_generations cg
                LEFT JOIN agent_logs al ON cg.id = al.generation_id
                WHERE cg.status = 'completed'
                GROUP BY cg.id, cg.topic, cg.comic_style, cg.language, cg.generation_time_seconds
                ORDER BY cg.created_at DESC
                LIMIT :limit
            """), {'limit': limit})
            return result.fetchall()

    def store_character_template(self, name, description, visual_style, personality_traits):
        """Store character template with embedding"""
        embedding = self.generate_embedding(f"{name} {description} {personality_traits}")

        with self.engine.connect() as conn:
            result = conn.execute(text("""
                INSERT INTO character_templates (name, description, visual_style, personality_traits, embedding)
                VALUES (:name, :description, :visual_style, :personality_traits, :embedding)
            """), {
                'name': name,
                'description': description,
                'visual_style': visual_style,
                'personality_traits': personality_traits,
                'embedding': str(embedding)
            })
            conn.commit()
            return result.lastrowid

    def search_character_templates(self, query, visual_style=None, limit=3):
        """Search for character templates using semantic similarity"""
        query_embedding = self.generate_embedding(query)

        base_query = """
            SELECT id, name, description, visual_style, personality_traits,
                   VEC_COSINE_DISTANCE(embedding, :query_embedding) as similarity
            FROM character_templates
        """

        conditions = []
        params = {'query_embedding': str(query_embedding)}

        if visual_style:
            conditions.append("visual_style = :visual_style")
            params['visual_style'] = visual_style

        if conditions:
            base_query += " WHERE " + " AND ".join(conditions)

        base_query += " ORDER BY similarity ASC LIMIT :limit"
        params['limit'] = limit

        with self.engine.connect() as conn:
            result = conn.execute(text(base_query), params)
            return result.fetchall()