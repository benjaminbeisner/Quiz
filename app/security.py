import re
import bcrypt

def get_password_hash(password: str) -> str:
    """Hasht das Passwort sicher mit der nativen bcrypt-Bibliothek."""
    # Passwort in Bytes umwandeln und bei 72 Bytes abschneiden (bcrypt-Limit)
    pwd_bytes = password.encode('utf-8')[:72]
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(pwd_bytes, salt)
    return hashed_password.decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifiziert das Passwort gegen den gespeicherten Hash."""
    pwd_bytes = plain_password.encode('utf-8')[:72]
    hash_bytes = hashed_password.encode('utf-8')
    return bcrypt.checkpw(pwd_bytes, hash_bytes)

def is_password_strong_enough(password: str) -> bool:
    """Prüft auf: Min. 8 Zeichen, Groß-, Kleinbuchstabe, Zahl, Sonderzeichen."""
    pattern = r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[\W_]).{8,}$"
    return bool(re.match(pattern, password))