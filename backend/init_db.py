from backend.app import app, db

with app.app_context():
    print("Creating database and tables...")
    db.create_all()
    print("Done! Look for 'kutus_boda.db' now.")