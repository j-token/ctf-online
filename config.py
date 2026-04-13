import os


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'intracore-ctf-secret-key-2026')
    DATABASE = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), 'instance', 'portal.sqlite3'
    )
    STORAGE_PATH = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), 'seed_storage'
    )
