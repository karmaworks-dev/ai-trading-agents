"""
Database Models for AI Trading Dashboard
==========================================
Handles user authentication and per-user settings persistence
"""

from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import json

db = SQLAlchemy()


class User(db.Model):
    """User model for authentication"""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    tier = db.Column(db.String(20), default='Based')  # Based, Trader, Pro
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)

    # Relationships
    settings = db.relationship('UserSettings', backref='user', uselist=False, cascade='all, delete-orphan')
    secrets = db.relationship('UserSecrets', backref='user', uselist=False, cascade='all, delete-orphan')

    def set_password(self, password):
        """Hash and set user password"""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Check if provided password matches hash"""
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        """Convert user to dictionary"""
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'tier': self.tier,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None
        }


class UserSettings(db.Model):
    """Per-user trading settings"""
    __tablename__ = 'user_settings'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, unique=True, index=True)

    # Chart Settings
    timeframe = db.Column(db.String(10), default='30m')
    days_back = db.Column(db.Integer, default=2)
    sleep_minutes = db.Column(db.Integer, default=15)

    # Mode Settings
    swarm_mode = db.Column(db.String(10), default='single')  # single or swarm

    # Token Settings
    monitored_tokens = db.Column(db.Text, default='["BTC", "ETH", "SOL", "LTC", "AAVE", "AVAX", "HYPE"]')  # JSON array

    # AI Model Settings
    ai_provider = db.Column(db.String(50), default='openrouter')
    ai_model = db.Column(db.String(100), default='nex-agi/deepseek-v3.1-nex-n1:free')
    ai_temperature = db.Column(db.Float, default=0.5)
    ai_max_tokens = db.Column(db.Integer, default=2048)

    # Swarm Models (JSON array of model configs)
    swarm_models = db.Column(db.Text, default='[]')  # JSON array

    # Risk Management Settings
    stop_loss_percent = db.Column(db.Float, default=2.0)  # Stop loss %
    take_profit_percent = db.Column(db.Float, default=5.0)  # Take profit %

    # Position Sizing
    max_position_percentage = db.Column(db.Float, default=90.0)  # Max % per position
    leverage = db.Column(db.Integer, default=20)  # Leverage multiplier
    cash_percentage = db.Column(db.Float, default=10.0)  # Cash reserve %

    # Position Management
    min_age_hours = db.Column(db.Float, default=0.1)  # Min hold time
    min_close_confidence = db.Column(db.Integer, default=70)  # AI confidence to close

    # Confidence Thresholds
    min_single_confidence = db.Column(db.Integer, default=60)  # Single model threshold
    min_swarm_confidence = db.Column(db.Integer, default=65)  # Swarm consensus threshold

    # Money/System Settings (CRITICAL - per user!)
    usd_size = db.Column(db.Float, default=12.0)  # Position size in USD
    max_usd_order_size = db.Column(db.Float, default=12.0)  # Max order size USD
    max_loss_usd = db.Column(db.Float, default=2.0)  # Stop trading if lose $X
    max_gain_usd = db.Column(db.Float, default=3.0)  # Stop trading if gain $X
    minimum_balance_usd = db.Column(db.Float, default=1.0)  # Close all if balance < $X
    use_ai_confirmation = db.Column(db.Boolean, default=True)  # Require AI confirm for exits

    # Timestamps
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def get_monitored_tokens(self):
        """Get monitored tokens as Python list"""
        try:
            return json.loads(self.monitored_tokens) if self.monitored_tokens else []
        except json.JSONDecodeError:
            return []

    def set_monitored_tokens(self, tokens):
        """Set monitored tokens from Python list"""
        self.monitored_tokens = json.dumps(tokens)

    def get_swarm_models(self):
        """Get swarm models as Python list"""
        try:
            return json.loads(self.swarm_models) if self.swarm_models else []
        except json.JSONDecodeError:
            return []

    def set_swarm_models(self, models):
        """Set swarm models from Python list"""
        self.swarm_models = json.dumps(models)

    def to_dict(self):
        """Convert settings to dictionary"""
        return {
            'timeframe': self.timeframe,
            'days_back': self.days_back,
            'sleep_minutes': self.sleep_minutes,
            'swarm_mode': self.swarm_mode,
            'monitored_tokens': self.get_monitored_tokens(),
            'ai_provider': self.ai_provider,
            'ai_model': self.ai_model,
            'ai_temperature': self.ai_temperature,
            'ai_max_tokens': self.ai_max_tokens,
            'swarm_models': self.get_swarm_models(),
            'stop_loss_percent': self.stop_loss_percent,
            'take_profit_percent': self.take_profit_percent,
            'max_position_percentage': self.max_position_percentage,
            'leverage': self.leverage,
            'cash_percentage': self.cash_percentage,
            'min_age_hours': self.min_age_hours,
            'min_close_confidence': self.min_close_confidence,
            'min_single_confidence': self.min_single_confidence,
            'min_swarm_confidence': self.min_swarm_confidence,
            'usd_size': self.usd_size,
            'max_usd_order_size': self.max_usd_order_size,
            'max_loss_usd': self.max_loss_usd,
            'max_gain_usd': self.max_gain_usd,
            'minimum_balance_usd': self.minimum_balance_usd,
            'use_ai_confirmation': self.use_ai_confirmation,
            'last_updated': self.last_updated.isoformat() if self.last_updated else None
        }

    @classmethod
    def create_default_for_user(cls, user_id):
        """Create default settings for a new user"""
        settings = cls(user_id=user_id)
        db.session.add(settings)
        db.session.commit()
        return settings


class UserSecrets(db.Model):
    """Per-user API secrets/keys"""
    __tablename__ = 'user_secrets'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, unique=True, index=True)

    # AI Provider API Keys (encrypted in production!)
    anthropic_key = db.Column(db.Text, nullable=True)
    openai_key = db.Column(db.Text, nullable=True)
    gemini_key = db.Column(db.Text, nullable=True)
    deepseek_key = db.Column(db.Text, nullable=True)
    xai_key = db.Column(db.Text, nullable=True)
    mistral_key = db.Column(db.Text, nullable=True)
    cohere_key = db.Column(db.Text, nullable=True)
    groq_key = db.Column(db.Text, nullable=True)
    perplexity_key = db.Column(db.Text, nullable=True)
    openrouter_key = db.Column(db.Text, nullable=True)

    # Trading/Data API Keys
    hyperliquid_private_key = db.Column(db.Text, nullable=True)
    birdeye_api_key = db.Column(db.Text, nullable=True)
    moondev_api_key = db.Column(db.Text, nullable=True)
    coingecko_api_key = db.Column(db.Text, nullable=True)

    last_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self, show_keys=False):
        """Convert secrets to dictionary

        Args:
            show_keys: If True, show actual keys. If False, show only presence status
        """
        if show_keys:
            return {
                'anthropic_key': self.anthropic_key,
                'openai_key': self.openai_key,
                'gemini_key': self.gemini_key,
                'deepseek_key': self.deepseek_key,
                'xai_key': self.xai_key,
                'mistral_key': self.mistral_key,
                'cohere_key': self.cohere_key,
                'groq_key': self.groq_key,
                'perplexity_key': self.perplexity_key,
                'openrouter_key': self.openrouter_key,
                'hyperliquid_private_key': self.hyperliquid_private_key,
                'birdeye_api_key': self.birdeye_api_key,
                'moondev_api_key': self.moondev_api_key,
                'coingecko_api_key': self.coingecko_api_key,
            }
        else:
            # Return only presence status for security
            return {
                'anthropic_key': bool(self.anthropic_key),
                'openai_key': bool(self.openai_key),
                'gemini_key': bool(self.gemini_key),
                'deepseek_key': bool(self.deepseek_key),
                'xai_key': bool(self.xai_key),
                'mistral_key': bool(self.mistral_key),
                'cohere_key': bool(self.cohere_key),
                'groq_key': bool(self.groq_key),
                'perplexity_key': bool(self.perplexity_key),
                'openrouter_key': bool(self.openrouter_key),
                'hyperliquid_private_key': bool(self.hyperliquid_private_key),
                'birdeye_api_key': bool(self.birdeye_api_key),
                'moondev_api_key': bool(self.moondev_api_key),
                'coingecko_api_key': bool(self.coingecko_api_key),
            }

    @classmethod
    def create_default_for_user(cls, user_id):
        """Create default secrets for a new user"""
        secrets = cls(user_id=user_id)
        db.session.add(secrets)
        db.session.commit()
        return secrets


def init_db(app):
    """Initialize database with Flask app"""
    db.init_app(app)
    with app.app_context():
        db.create_all()
        print("✅ Database initialized")


def migrate_from_json():
    """Migrate existing JSON settings to database for the first user

    This is a one-time migration helper to preserve existing user data
    """
    from src.utils.settings_manager import load_settings as load_json_settings
    from src.utils.secrets_manager import load_secrets as load_json_secrets
    from src.utils.tier_manager import load_tier as load_json_tier
    import os

    # Check if migration already done
    if User.query.first():
        print("⚠️ Users already exist in database, skipping migration")
        return

    print("🔄 Migrating JSON data to database...")

    # Create default user from .env credentials
    username = os.getenv('DASHBOARD_USERNAME', 'admin')
    email = os.getenv('DASHBOARD_EMAIL', 'admin@trading.ai')
    password = os.getenv('DASHBOARD_PASSWORD', 'changeme')

    user = User(username=username, email=email)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    print(f"✅ Created user: {username}")

    # Migrate settings from JSON
    try:
        json_settings = load_json_settings()
        settings = UserSettings(user_id=user.id)

        # Map JSON settings to database
        settings.timeframe = json_settings.get('timeframe', '30m')
        settings.days_back = json_settings.get('days_back', 2)
        settings.sleep_minutes = json_settings.get('sleep_minutes', 15)
        settings.swarm_mode = json_settings.get('swarm_mode', 'single')
        settings.set_monitored_tokens(json_settings.get('monitored_tokens', ['BTC', 'ETH', 'SOL']))
        settings.ai_provider = json_settings.get('ai_provider', 'openrouter')
        settings.ai_model = json_settings.get('ai_model', 'nex-agi/deepseek-v3.1-nex-n1:free')
        settings.ai_temperature = json_settings.get('ai_temperature', 0.5)
        settings.ai_max_tokens = json_settings.get('ai_max_tokens', 2048)
        settings.set_swarm_models(json_settings.get('swarm_models', []))

        db.session.add(settings)
        db.session.commit()
        print("✅ Migrated settings from JSON")
    except Exception as e:
        print(f"⚠️ Could not migrate settings: {e}")
        # Create default settings anyway
        UserSettings.create_default_for_user(user.id)

    # Migrate secrets from JSON
    try:
        json_secrets = load_json_secrets()
        secrets = UserSecrets(user_id=user.id)

        # Map JSON secrets to database
        for key in json_secrets:
            if hasattr(secrets, key):
                setattr(secrets, key, json_secrets[key])

        db.session.add(secrets)
        db.session.commit()
        print("✅ Migrated secrets from JSON")
    except Exception as e:
        print(f"⚠️ Could not migrate secrets: {e}")
        # Create empty secrets anyway
        UserSecrets.create_default_for_user(user.id)

    # Migrate tier from JSON
    try:
        tier = load_json_tier()
        user.tier = tier
        db.session.commit()
        print(f"✅ Migrated tier: {tier}")
    except Exception as e:
        print(f"⚠️ Could not migrate tier: {e}")

    print("🎉 Migration complete!")
