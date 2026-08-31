from sqlalchemy.engine import CursorResult


def affected_row_count(result: object) -> int:
    """Return the number of rows changed by a SQLAlchemy DML execution."""
    if not isinstance(result, CursorResult):
        raise RuntimeError("database_dml_result_invalid")
    return result.rowcount
