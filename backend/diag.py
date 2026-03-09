import sys
import os
from sqlalchemy import func
sys.path.append(os.getcwd())
from app.database import SessionLocal, Portfolio, ActivityLog, ChatMessage, NewsItem, Trade

def check_db():
    db = SessionLocal()
    try:
        print("--- DIAGNOSTIC BASE DE DONNÉES ---")
        portfolios = db.query(Portfolio).all()
        print(f"Portfolios trouvés: {len(portfolios)}")
        for p in portfolios:
            print(f"  - User: {p.user_id}, Capital: {p.capital}")
            
        chats_count = db.query(ChatMessage.user_id, func.count(ChatMessage.id)).group_by(ChatMessage.user_id).all()
        print(f"\nMessages par utilisateur:")
        for user_id, cnt in chats_count:
            print(f"  - {user_id}: {cnt} messages")
            
        logs = db.query(ActivityLog).order_by(ActivityLog.timestamp.desc()).limit(10).all()
        print(f"\n10 Derniers Logs d'Activité:")
        for l in logs:
            try:
                # Nettoyage pour console Windows
                msg = l.message.encode('ascii', 'ignore').decode('ascii')[:60]
                print(f"  [{l.timestamp}] {l.type}: {msg}...")
            except:
                print(f"  [{l.timestamp}] {l.type}: [Erreur encodage]")
            
        chats = db.query(ChatMessage).order_by(ChatMessage.timestamp.desc()).limit(10).all()
        print(f"\n10 Derniers Messages Chat:")
        for c in chats:
            try:
                msg = c.content.encode('ascii', 'ignore').decode('ascii')[:60]
                print(f"  [{c.timestamp}] {c.role}: {msg}...")
            except:
                print(f"  [{c.timestamp}] {c.role}: [Erreur encodage]")
            
        news = db.query(NewsItem).count()
        print(f"\nNombre total d'actualités: {news}")
        
    except Exception as e:
        print(f"ERREUR DIAG: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    check_db()
