from sqlalchemy import create_engine, text, inspect
from app.config import DATABASE_URL
from app.database import Base, engine as db_engine

def migrate_db():
    parsed_url = DATABASE_URL
    if parsed_url.startswith("postgres://"):
        parsed_url = parsed_url.replace("postgres://", "postgresql://", 1)
    
    print(f">>> DB DOCTOR: Vérification de la base de données... ({parsed_url.split('@')[-1] if '@' in parsed_url else 'SQLite'})")
    engine = create_engine(parsed_url)
    
    # 1. Création des tables manquantes
    try:
        Base.metadata.create_all(bind=engine)
        print("Étape 1: Tables créées ou déjà présentes.")
    except Exception as e:
        print(f"Erreur lors de create_all: {e}")

    inspector = inspect(engine)
    
    # 2. Ajout des colonnes manquantes dans 'news'
    news_columns = [
        ("source_type", "VARCHAR(20) DEFAULT 'RSS'"),
        ("importance_weight", "FLOAT DEFAULT 1.0"),
        ("raw_content", "TEXT")
    ]
    
    existing_news_cols = [c["name"] for c in inspector.get_columns("news")] if "news" in inspector.get_table_names() else []
    
    with engine.connect() as conn:
        for col_name, col_type in news_columns:
            if col_name not in existing_news_cols:
                try:
                    print(f"Étape 2: Ajout de la colonne {col_name} à la table 'news'...")
                    conn.execute(text(f"ALTER TABLE news ADD COLUMN {col_name} {col_type}"))
                    conn.commit()
                except Exception as e:
                    print(f"Avertissement migration news.{col_name}: {e}")

    # 3. Ajout de 'reference_id' dans 'activity_logs'
    log_columns = [
        ("reference_id", "INTEGER")
    ]
    
    existing_log_cols = [c["name"] for c in inspector.get_columns("activity_logs")] if "activity_logs" in inspector.get_table_names() else []
    
    with engine.connect() as conn:
        for col_name, col_type in log_columns:
            if col_name not in existing_log_cols:
                try:
                    print(f"Étape 3: Ajout de la colonne {col_name} à la table 'activity_logs'...")
                    conn.execute(text(f"ALTER TABLE activity_logs ADD COLUMN {col_name} {col_type}"))
                    conn.commit()
                    print(f"Succès: {col_name} ajoutée.")
                except Exception as e:
                    print(f"Avertissement migration activity_logs.{col_name}: {e}")

if __name__ == "__main__":
    migrate_db()
