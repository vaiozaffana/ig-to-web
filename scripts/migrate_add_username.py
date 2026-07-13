#!/usr/bin/env python
"""
Migration helper untuk menambahkan kolom username ke instagram_posts.
Script ini idempotent - aman dijalankan multiple kali.
"""
from sqlalchemy import create_engine, text, inspect

from app.core.settings import settings


def add_username_column():
    """Add username column to instagram_posts if not exists."""
    engine = create_engine(settings.database_url)
    inspector = inspect(engine)
    
    # Check if column exists
    columns = [col['name'] for col in inspector.get_columns('instagram_posts')]
    
    if 'username' in columns:
        print('ℹ️  Column username already exists in instagram_posts')
        return False
    
    # Add column
    with engine.connect() as conn:
        conn.execute(text('ALTER TABLE instagram_posts ADD COLUMN username VARCHAR'))
        conn.commit()
        print('✅ Column username added to instagram_posts')
        return True


def backfill_username():
    """Backfill username for existing posts without username."""
    from app.models.instagram_post import InstagramPost
    from app.modules.adapters.instagram import instagram_client
    from sqlmodel import Session, select
    from app.models.engine import engine
    
    # Get username dari Instagram
    status = instagram_client.validate_credentials(settings.instagram_account_id)
    username = status.username or settings.instagram_account_id
    
    with Session(engine) as session:
        # Update all posts without username
        posts = session.exec(
            select(InstagramPost).where(InstagramPost.username == None)
        ).all()
        
        if not posts:
            print('ℹ️  All posts already have username')
            return 0
        
        print(f'Backfilling username for {len(posts)} posts...')
        for post in posts:
            post.username = username
            session.add(post)
        session.commit()
        
        print(f'✅ Backfilled {len(posts)} posts with username: {username}')
        return len(posts)


def main():
    print("=" * 70)
    print("Instagram Posts - Add Username Column Migration")
    print("=" * 70)
    print()
    
    # Step 1: Add column
    column_added = add_username_column()
    
    # Step 2: Backfill existing data
    if column_added or settings.instagram_account_id:
        print()
        backfill_username()
    
    print()
    print("=" * 70)
    print("✅ Migration completed successfully")
    print("=" * 70)


if __name__ == "__main__":
    main()
