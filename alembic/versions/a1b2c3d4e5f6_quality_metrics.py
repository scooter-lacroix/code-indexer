"""Add quality metrics and evaluation tables

Revision ID: a1b2c3d4e5f6
Revises: 80b65a437638
Create Date: 2025-12-31 02:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "80b65a437638"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema with quality metrics tables."""

    # Create eval_runs table for tracking evaluation runs
    op.create_table(
        "eval_runs",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column(
            "run_type", sa.String(), nullable=False
        ),  # 'manual', 'automated', 'ab_test'
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("query_count", sa.Integer(), nullable=False, default=0),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column(
            "status", sa.String(), nullable=False, default="running"
        ),  # 'running', 'completed', 'failed'
        sa.Column("config_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_eval_runs_run_type"), "eval_runs", ["run_type"], unique=False
    )
    op.create_index(op.f("ix_eval_runs_status"), "eval_runs", ["status"], unique=False)
    op.create_index(
        op.f("ix_eval_runs_started_at"), "eval_runs", ["started_at"], unique=False
    )

    # Create eval_query_results table for storing individual query results
    op.create_table(
        "eval_query_results",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("eval_run_id", sa.String(), nullable=False),
        sa.Column("query_text", sa.Text(), nullable=False),
        sa.Column(
            "query_type", sa.String(), nullable=False
        ),  # 'semantic', 'regex', 'hybrid'
        sa.Column(
            "confidence", sa.Float(), nullable=True
        ),  # Query type detection confidence
        sa.Column(
            "backend_used", sa.String(), nullable=False
        ),  # 'faiss', 'elasticsearch', 'zoekt', 'merged'
        sa.Column("result_count", sa.Integer(), nullable=False, default=0),
        sa.Column("latency_ms", sa.Float(), nullable=True),
        sa.Column(
            "recall_at_k", sa.Float(), nullable=True
        ),  # Recall@K for labeled queries
        sa.Column("precision_at_k", sa.Float(), nullable=True),  # Precision@K
        sa.Column("mrr", sa.Float(), nullable=True),  # Mean Reciprocal Rank
        sa.Column(
            "relevance_scores_json", sa.JSON(), nullable=True
        ),  # User feedback scores
        sa.Column("is_relevant_predicted", sa.Boolean(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("executed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["eval_run_id"], ["eval_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_eval_query_results_eval_run_id"),
        "eval_query_results",
        ["eval_run_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_eval_query_results_query_type"),
        "eval_query_results",
        ["query_type"],
        unique=False,
    )
    op.create_index(
        op.f("ix_eval_query_results_backend_used"),
        "eval_query_results",
        ["backend_used"],
        unique=False,
    )
    op.create_index(
        op.f("ix_eval_query_results_executed_at"),
        "eval_query_results",
        ["executed_at"],
        unique=False,
    )

    # Create quality_metrics_aggregated table for aggregated metrics
    op.create_table(
        "quality_metrics_aggregated",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column(
            "metric_type", sa.String(), nullable=False
        ),  # 'recall', 'precision', 'mrr', 'latency'
        sa.Column(
            "aggregation_period", sa.String(), nullable=False
        ),  # 'hourly', 'daily', 'weekly'
        sa.Column("period_start", sa.DateTime(), nullable=False),
        sa.Column("period_end", sa.DateTime(), nullable=False),
        sa.Column(
            "backend", sa.String(), nullable=True
        ),  # NULL for aggregated across backends
        sa.Column("query_type", sa.String(), nullable=True),  # NULL for all query types
        sa.Column("sample_count", sa.Integer(), nullable=False, default=0),
        sa.Column("mean_value", sa.Float(), nullable=True),
        sa.Column("min_value", sa.Float(), nullable=True),
        sa.Column("max_value", sa.Float(), nullable=True),
        sa.Column("p50_value", sa.Float(), nullable=True),
        sa.Column("p95_value", sa.Float(), nullable=True),
        sa.Column("p99_value", sa.Float(), nullable=True),
        sa.Column("std_dev", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "metric_type", "aggregation_period", "period_start", "backend", "query_type"
        ),
    )
    op.create_index(
        op.f("ix_quality_metrics_metric_type"),
        "quality_metrics_aggregated",
        ["metric_type"],
        unique=False,
    )
    op.create_index(
        op.f("ix_quality_metrics_period"),
        "quality_metrics_aggregated",
        ["period_start", "period_end"],
        unique=False,
    )

    # Create ab_tests table for A/B testing framework
    op.create_table(
        "ab_tests",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("strategy_a", sa.String(), nullable=False),  # Configuration A
        sa.Column("strategy_b", sa.String(), nullable=False),  # Configuration B
        sa.Column(
            "traffic_split", sa.Float(), nullable=False, default=0.5
        ),  # 0.5 = 50/50 split
        sa.Column(
            "status", sa.String(), nullable=False, default="draft"
        ),  # 'draft', 'running', 'paused', 'completed'
        sa.Column("start_date", sa.DateTime(), nullable=True),
        sa.Column("end_date", sa.DateTime(), nullable=True),
        sa.Column(
            "winner", sa.String(), nullable=True
        ),  # 'a', 'b', or NULL if no winner
        sa.Column("results_summary", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_ab_tests_status"), "ab_tests", ["status"], unique=False)
    op.create_index(
        op.f("ix_ab_tests_start_date"), "ab_tests", ["start_date"], unique=False
    )

    # Create user_feedback table for user feedback collection
    op.create_table(
        "user_feedback",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("query_text", sa.Text(), nullable=True),
        sa.Column("file_path", sa.String(), nullable=True),
        sa.Column("line_number", sa.Integer(), nullable=True),
        sa.Column("rating", sa.Integer(), nullable=True),  # 1-5 rating
        sa.Column("is_relevant", sa.Boolean(), nullable=True),  # Thumbs up/down
        sa.Column(
            "feedback_type", sa.String(), nullable=False
        ),  # 'rating', 'relevance', 'correction'
        sa.Column("session_id", sa.String(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_user_feedback_created_at"),
        "user_feedback",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_user_feedback_feedback_type"),
        "user_feedback",
        ["feedback_type"],
        unique=False,
    )
    op.create_index(
        op.f("ix_user_feedback_session_id"),
        "user_feedback",
        ["session_id"],
        unique=False,
    )

    # Create search_thresholds table for quality thresholds and alerting
    op.create_table(
        "search_thresholds",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column(
            "metric_name", sa.String(), nullable=False
        ),  # 'recall', 'latency', 'error_rate'
        sa.Column(
            "threshold_type", sa.String(), nullable=False
        ),  # 'min', 'max', 'target'
        sa.Column("threshold_value", sa.Float(), nullable=False),
        sa.Column(
            "severity", sa.String(), nullable=False, default="warning"
        ),  # 'info', 'warning', 'critical'
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("last_triggered_at", sa.DateTime(), nullable=True),
        sa.Column("trigger_count", sa.Integer(), nullable=False, default=0),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("metric_name", "threshold_type"),
    )
    op.create_index(
        op.f("ix_search_thresholds_is_active"),
        "search_thresholds",
        ["is_active"],
        unique=False,
    )

    # Create quality_alerts table for storing threshold violations
    op.create_table(
        "quality_alerts",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("threshold_id", sa.String(), nullable=False),
        sa.Column("metric_name", sa.String(), nullable=False),
        sa.Column(
            "alert_type", sa.String(), nullable=False
        ),  # 'threshold_exceeded', 'regression_detected'
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("current_value", sa.Float(), nullable=True),
        sa.Column("threshold_value", sa.Float(), nullable=True),
        sa.Column(
            "status", sa.String(), nullable=False, default="active"
        ),  # 'active', 'acknowledged', 'resolved'
        sa.Column("acknowledged_by", sa.String(), nullable=True),
        sa.Column("acknowledged_at", sa.DateTime(), nullable=True),
        sa.Column("resolved_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["threshold_id"], ["search_thresholds.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_quality_alerts_status"), "quality_alerts", ["status"], unique=False
    )
    op.create_index(
        op.f("ix_quality_alerts_created_at"),
        "quality_alerts",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_quality_alerts_metric_name"),
        "quality_alerts",
        ["metric_name"],
        unique=False,
    )

    # Create query_type_stats table for query type detection statistics
    op.create_table(
        "query_type_stats",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("date", sa.DateTime(), nullable=False),
        sa.Column("total_queries", sa.Integer(), nullable=False, default=0),
        sa.Column("semantic_count", sa.Integer(), nullable=False, default=0),
        sa.Column("regex_count", sa.Integer(), nullable=False, default=0),
        sa.Column("hybrid_count", sa.Integer(), nullable=False, default=0),
        sa.Column("detection_confidence_avg", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("date"),
    )
    op.create_index(
        op.f("ix_query_type_stats_date"), "query_type_stats", ["date"], unique=False
    )


def downgrade() -> None:
    """Downgrade schema - remove quality metrics tables."""

    # Drop in reverse order due to foreign key dependencies
    op.drop_index(op.f("ix_query_type_stats_date"), table_name="query_type_stats")
    op.drop_table("query_type_stats")

    op.drop_index(op.f("ix_quality_alerts_metric_name"), table_name="quality_alerts")
    op.drop_index(op.f("ix_quality_alerts_created_at"), table_name="quality_alerts")
    op.drop_index(op.f("ix_quality_alerts_status"), table_name="quality_alerts")
    op.drop_table("quality_alerts")

    op.drop_index(
        op.f("ix_search_thresholds_is_active"), table_name="search_thresholds"
    )
    op.drop_table("search_thresholds")

    op.drop_index(op.f("ix_user_feedback_session_id"), table_name="user_feedback")
    op.drop_index(op.f("ix_user_feedback_feedback_type"), table_name="user_feedback")
    op.drop_index(op.f("ix_user_feedback_created_at"), table_name="user_feedback")
    op.drop_table("user_feedback")

    op.drop_index(op.f("ix_ab_tests_start_date"), table_name="ab_tests")
    op.drop_index(op.f("ix_ab_tests_status"), table_name="ab_tests")
    op.drop_table("ab_tests")

    op.drop_index(
        op.f("ix_quality_metrics_period"), table_name="quality_metrics_aggregated"
    )
    op.drop_index(
        op.f("ix_quality_metrics_metric_type"), table_name="quality_metrics_aggregated"
    )
    op.drop_table("quality_metrics_aggregated")

    op.drop_index(
        op.f("ix_eval_query_results_executed_at"), table_name="eval_query_results"
    )
    op.drop_index(
        op.f("ix_eval_query_results_backend_used"), table_name="eval_query_results"
    )
    op.drop_index(
        op.f("ix_eval_query_results_query_type"), table_name="eval_query_results"
    )
    op.drop_index(
        op.f("ix_eval_query_results_eval_run_id"), table_name="eval_query_results"
    )
    op.drop_table("eval_query_results")

    op.drop_index(op.f("ix_eval_runs_started_at"), table_name="eval_runs")
    op.drop_index(op.f("ix_eval_runs_status"), table_name="eval_runs")
    op.drop_index(op.f("ix_eval_runs_run_type"), table_name="eval_runs")
    op.drop_table("eval_runs")
