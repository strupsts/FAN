from sqlalchemy import delete

from app.adapters.outbound.db.sqlalchemy_models import ReceiptItemRow, ReceiptRow
from app.infrastructure.database import create_db_engine, create_session_factory


def main() -> None:
    engine = create_db_engine()
    session_factory = create_session_factory(engine)

    with session_factory() as session:
        session.execute(delete(ReceiptItemRow))
        session.execute(delete(ReceiptRow))
        session.commit()

    print("Database receipts cleared.")


if __name__ == "__main__":
    main()
