"""initial: sessions, messages, practice sets, questions, answers

Revision ID: 0001_initial
Revises:
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

UUID = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    op.create_table(
        "chat_sessions",
        sa.Column("id", UUID, server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", UUID, nullable=False),
        sa.Column("title", sa.String(120), server_default="New chat", nullable=False),
        sa.Column("doc_ids", postgresql.ARRAY(UUID), server_default="{}", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("last_message_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_sessions_user_last_msg", "chat_sessions",
                    ["user_id", sa.text("last_message_at DESC")])

    op.create_table(
        "practice_sets",
        sa.Column("id", UUID, server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("session_id", UUID, nullable=False),
        sa.Column("user_id", UUID, nullable=False),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("doc_ids", postgresql.ARRAY(UUID), server_default="{}", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["session_id"], ["chat_sessions.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_practice_sets_user_created", "practice_sets",
                    ["user_id", sa.text("created_at DESC")])

    op.create_table(
        "chat_messages",
        sa.Column("id", UUID, server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("session_id", UUID, nullable=False),
        sa.Column("user_id", UUID, nullable=False),
        sa.Column("role", sa.String(16), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("intent", sa.String(32), nullable=True),
        sa.Column("citations", postgresql.JSONB(), nullable=True),
        sa.Column("practice_set_id", UUID, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["session_id"], ["chat_sessions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["practice_set_id"], ["practice_sets.id"], ondelete="SET NULL"),
        sa.CheckConstraint("role IN ('user', 'assistant')", name="ck_message_role"),
    )
    op.create_index("ix_messages_session_created", "chat_messages",
                    ["session_id", sa.text("created_at DESC")])

    op.create_table(
        "practice_questions",
        sa.Column("id", UUID, server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("practice_set_id", UUID, nullable=False),
        sa.Column("user_id", UUID, nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("qtype", sa.String(16), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("options", postgresql.JSONB(), nullable=True),
        sa.Column("correct_index", sa.Integer(), nullable=True),
        sa.Column("model_answer", sa.Text(), nullable=True),
        sa.Column("rubric", postgresql.JSONB(), nullable=True),
        sa.Column("sources", postgresql.JSONB(), nullable=True),
        sa.Column("max_marks", sa.Integer(), server_default="10", nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["practice_set_id"], ["practice_sets.id"], ondelete="CASCADE"),
        sa.CheckConstraint(
            "qtype IN ('mcq', 'true_false', 'short', 'structured', 'essay')",
            name="ck_question_type",
        ),
        sa.CheckConstraint(
            "(qtype IN ('mcq','true_false') AND correct_index IS NOT NULL)"
            " OR (qtype NOT IN ('mcq','true_false') AND correct_index IS NULL)",
            name="ck_question_answer_shape",
        ),
    )
    op.create_index("ix_questions_set_position", "practice_questions",
                    ["practice_set_id", "position"])

    op.create_table(
        "practice_answers",
        sa.Column("id", UUID, server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("question_id", UUID, nullable=False),
        sa.Column("user_id", UUID, nullable=False),
        sa.Column("selected_index", sa.Integer(), nullable=True),
        sa.Column("answer_text", sa.Text(), nullable=True),
        sa.Column("marks", sa.Numeric(4, 1), nullable=True),
        sa.Column("is_correct", sa.Boolean(), nullable=True),
        sa.Column("feedback", sa.Text(), nullable=True),
        sa.Column("revealed_answer", sa.Text(), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("marked_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("question_id"),
        sa.ForeignKeyConstraint(["question_id"], ["practice_questions.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_answers_user", "practice_answers", ["user_id"])


def downgrade() -> None:
    op.drop_table("practice_answers")
    op.drop_table("practice_questions")
    op.drop_table("chat_messages")
    op.drop_table("practice_sets")
    op.drop_table("chat_sessions")
