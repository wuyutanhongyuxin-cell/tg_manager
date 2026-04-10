from src.database.engine import DatabaseManager


def test_ensure_sqlite_parent_dir_creates_missing_directories(tmp_path) -> None:
    db_path = tmp_path / "nested" / "data" / "tg_manager.db"

    DatabaseManager._ensure_sqlite_parent_dir(
        f"sqlite+aiosqlite:///{db_path.as_posix()}"
    )

    assert db_path.parent.exists()


def test_ensure_sqlite_parent_dir_ignores_memory_database(tmp_path) -> None:
    marker = tmp_path / "nested"

    DatabaseManager._ensure_sqlite_parent_dir("sqlite+aiosqlite:///:memory:")

    assert not marker.exists()
