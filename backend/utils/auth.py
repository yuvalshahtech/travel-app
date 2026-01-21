from passlib.context import CryptContext
# Use argon2 instead of bcrypt
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

def hash_password(password: str):
    """
    Hash the password using argon2. 
    Argon2 is modern, secure, and does not have the 72-character limit of bcrypt.
    """
    return pwd_context.hash(password)
def verify_password(plain_password: str, hashed_password: str):
    """
    Verify a plain password against the stored hash.
    """
    return pwd_context.verify(plain_password, hashed_password)
