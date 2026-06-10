from app.infrastructure.database import create_all_tables


def main() -> None:
    create_all_tables()
    print("Database tables created.")


if __name__ == "__main__":
    main()
