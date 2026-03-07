from sqlalchemy import create_engine, text
from app.config import DATABASE_URL

def migrate_news_table():
    parsed_url = DATABASE_URL
    if parsed_url.startswith("postgres://"):
        parsed_url = parsed_url.replace("postgres://", "postgresql://", 1)
    
    print(f"Début de la migration sur {parsed_url.split('@')[-1] if '@' in parsed_url else 'DB locale'}")
    engine = create_engine(parsed_url)
    
    columns_to_add = [
        ("source_type", "VARCHAR(20) DEFAULT 'RSS'"),
        ("importance_weight", "FLOAT DEFAULT 1.0"),
        ("raw_content", "TEXT")
    ]
    
    with engine.connect() as conn:
        for col_name, col_type in columns_to_add:
            try:
                # On tente d'ajouter la colonne
                conn.execute(text(f"ALTER TABLE news ADD COLUMN {col_name} {col_type}"))
                conn.commit()
                print(f"Migration réussie : Colonne {col_name} ajoutée.")
            except Exception as e:
                # Erreur attendue si la colonne existe déjà (OperationalError)
                print(f"Info migration : La colonne {col_name} n'a pas été ajoutée (existe déjà ou erreur mineure).")

if __name__ == "__main__":
    migrate_news_table()
