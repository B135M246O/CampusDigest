"""Use one primary key and one read mark per user/article.

Revision ID: c41d6a2b0e19
Revises: 4eacd65ddb52
"""
from alembic import op
import sqlalchemy as sa

revision = 'c41d6a2b0e19'
down_revision = '4eacd65ddb52'
branch_labels = None
depends_on = None


def upgrade():
    # Old composite keys allowed repeated read marks; retain the earliest one.
    op.execute(sa.text(
        'DELETE FROM articleuser WHERE id NOT IN '
        '(SELECT MIN(id) FROM articleuser GROUP BY article_id, user_id)'
    ))
    op.drop_constraint('articleuser_pkey', 'articleuser', type_='primary')
    op.create_primary_key('articleuser_pkey', 'articleuser', ['id'])
    op.create_unique_constraint('uq_articleuser_article_user', 'articleuser',
                                ['article_id', 'user_id'])


def downgrade():
    op.drop_constraint('uq_articleuser_article_user', 'articleuser', type_='unique')
    op.drop_constraint('articleuser_pkey', 'articleuser', type_='primary')
    op.create_primary_key('articleuser_pkey', 'articleuser',
                          ['article_id', 'user_id', 'id'])
