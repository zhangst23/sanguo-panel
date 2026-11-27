from backend.core.database import engine, SessionLocal
from backend.models.base import Base
# Import all models to ensure they are registered with Base.metadata
from backend.models.user import User
from backend.models.site import SharedDatabase, Site
from backend.models.config import GlobalOption
from backend.models.wp_asset import WpAsset
from backend.utils.wp_asset_utils import DEFAULT_OPTION_KEY, DEFAULT_WP_VERSION
from backend.core.security import get_password_hash
from sqlalchemy import inspect, text

def init_db():
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    # Create superuser if not exists
    user = db.query(User).filter(User.username == "admin").first()
    if not user:
        user = User(
            username="admin",
            password_hash=get_password_hash("admin123"),
            is_superuser=True,
            is_active=True
        )
        db.add(user)
        db.commit()
        print("Superuser 'admin' created with password 'admin123'.")
    else:
        print("Superuser 'admin' already exists.")
    # Create default shared database if not exists
    shared_db = db.query(SharedDatabase).filter(SharedDatabase.name == "Default MySQL").first()
    if not shared_db:
        shared_db = SharedDatabase(
            name="Default MySQL",
            db_host="localhost",
            db_port=3306,
            db_name="wp_db",
            # 面板不使用 root 建站；真实密码在启动时由 db_admin 自动生成并写入
            db_user="sanguo_admin",
            db_password="",
            max_table_count=1000,
            status="active"
        )
        db.add(shared_db)
        db.commit()
        print("Default shared database created (admin account provisioned on startup).")
    else:
        # 升级旧数据：不再回退到 root / 空密码
        if shared_db.db_user in ("sanguo_user", "root") and not shared_db.db_password:
            shared_db.db_user = "sanguo_admin"
            db.add(shared_db)
            db.commit()
            print("Default shared database updated to dedicated admin account.")
        print("Default shared database already exists.")

    # Default WordPress version used when creating new sites
    if not db.query(GlobalOption).filter(GlobalOption.option_key == DEFAULT_OPTION_KEY).first():
        db.add(GlobalOption(
            option_key=DEFAULT_OPTION_KEY,
            option_value=DEFAULT_WP_VERSION,
            description="新建站点使用的 WordPress 默认版本",
        ))
        db.commit()
        print(f"Default WordPress version set to {DEFAULT_WP_VERSION}.")

    db.close()

    # Migrate: add columns that may not exist in older DBs
    with engine.connect() as conn:
        inspector = inspect(engine)
        site_cols = [c['name'] for c in inspector.get_columns('sites')]
        if 'discourage_search_engines' not in site_cols:
            conn.execute(text("ALTER TABLE sites ADD COLUMN discourage_search_engines BOOLEAN DEFAULT 1"))
            conn.commit()
            print("Added column 'discourage_search_engines' to sites table.")

    print("Database initialized successfully.")

if __name__ == "__main__":
    init_db()
