import os

from flask import Flask, redirect, url_for

from .auth import get_current_user


def create_app(test_config=None):
    app = Flask(
        __name__,
        instance_relative_config=True,
        static_folder='../static'
    )

    app.config.from_mapping(
        SECRET_KEY='intracore-ctf-secret-key-2026',
        DATABASE=os.path.join(app.instance_path, 'portal.sqlite3'),
        STORAGE_PATH=os.path.join(os.path.dirname(app.root_path), 'seed_storage'),
    )

    if test_config:
        app.config.from_mapping(test_config)

    os.makedirs(app.instance_path, exist_ok=True)

    from .db import init_app
    init_app(app)

    # 매 요청마다 현재 사용자 로드
    @app.before_request
    def load_user():
        get_current_user()

    # Blueprint 등록
    from .blueprints import (
        auth_bp, dashboard_bp, leaderboard_bp, directory_bp,
        tickets_bp, archive_bp, finance_bp, reports_bp,
        verify_bp, flag_bp
    )
    app.register_blueprint(auth_bp.bp)
    app.register_blueprint(dashboard_bp.bp)
    app.register_blueprint(leaderboard_bp.bp)
    app.register_blueprint(directory_bp.bp)
    app.register_blueprint(tickets_bp.bp)
    app.register_blueprint(archive_bp.bp)
    app.register_blueprint(finance_bp.bp)
    app.register_blueprint(reports_bp.bp)
    app.register_blueprint(verify_bp.bp)
    app.register_blueprint(flag_bp.bp)

    @app.route('/')
    def index():
        return redirect(url_for('auth.login'))

    return app
