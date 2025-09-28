import re
import bcrypt


def hash_pass(password):
    # Adding the salt to password
    salt = bcrypt.gensalt()

    # Hashing the password
    hashed = bcrypt.hashpw(password.encode(), salt)
    return hashed.decode()


def validate_pass(input, password):
    return bcrypt.checkpw(input.encode(), password.encode())


def validate_email(email):
    regex = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b"
    if re.fullmatch(regex, email):
        return True
    else:
        return False
