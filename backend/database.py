from sqlmodel import SQLModel, create_engine, Session


sqlite_file_name = "database.db"
sqlite_url = f"sqlite:///{sqlite_file_name}"
engine = create_engine(sqlite_url)


def create_db_and_tables() -> None:
    """在应用启动时统一创建所有数据表。"""
    SQLModel.metadata.create_all(engine)


def get_session():
    """FastAPI 依赖注入使用的 Session 工厂。"""
    with Session(engine) as session:
        yield session

