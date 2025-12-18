"""
Utility script to generate secure random keys for API_KEY, JWT_SECRET_KEY, and WEBHOOK_SECRET.
"""

import secrets

def generate_key(name: str, length: int = 32) -> str:
    """Generate a secure random key."""
    key = secrets.token_urlsafe(length)
    return f"{name}={key}"

if __name__ == "__main__":
    print("=" * 60)
    print("Secure Key Generator")
    print("=" * 60)
    print()
    print("Generated keys (copy these to your .env file):")
    print()
    print(generate_key("API_KEY", 32))
    print(generate_key("JWT_SECRET_KEY", 32))
    print(generate_key("WEBHOOK_SECRET", 32))
    print()
    print("=" * 60)
    print("Note: Keep these keys secret! Never commit them to Git.")
    print("=" * 60)

