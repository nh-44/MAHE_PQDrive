import oqs

KYBER_ALG = "Kyber512"

def generate_keypair():
    """
    Generate a Kyber public/private keypair.
    Returns (public_key_bytes, private_key_bytes)
    """
    with oqs.KeyEncapsulation(KYBER_ALG) as kem:
        public_key = kem.generate_keypair()
        private_key = kem.export_secret_key()
    return public_key, private_key


def encapsulate(public_key: bytes):
    """
    OTA server side: encapsulate a session key using the vehicle's public key.
    Returns (ciphertext, session_key)
    """
    with oqs.KeyEncapsulation(KYBER_ALG) as kem:
        ciphertext, session_key = kem.encap_secret(public_key)
    return ciphertext, session_key


def decapsulate(private_key: bytes, ciphertext: bytes):
    """
    Vehicle side: decapsulate to recover the session key.
    Returns session_key_bytes
    """
    with oqs.KeyEncapsulation(KYBER_ALG, secret_key=private_key) as kem:
        session_key = kem.decap_secret(ciphertext)
    return session_key


def verify_session(private_key: bytes, ciphertext: bytes, expected_key: bytes) -> bool:
    """
    Checks that decapsulated key matches what the server sent.
    Returns True if session is valid.
    """
    recovered = decapsulate(private_key, ciphertext)
    return recovered == expected_key