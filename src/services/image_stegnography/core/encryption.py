"""
Encryption utilities for steganography operations
"""

import os
from typing import Optional, Tuple
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt


def derive_key(password: str, salt: bytes) -> bytes:
    """
    Derive encryption key from password using Scrypt KDF
    
    Args:
        password: User password
        salt: Random salt for key derivation
        
    Returns:
        Derived encryption key
    """
    kdf = Scrypt(salt=salt, length=32, n=2**14, r=8, p=1)
    return kdf.derive(password.encode("utf-8"))


def encrypt_data(data: bytes, password: str) -> Tuple[bytes, bytes, bytes]:
    """
    Encrypt data using AES-GCM with derived key
    
    Args:
        data: Data to encrypt
        password: Password for encryption
        
    Returns:
        Tuple of (encrypted_data, salt, nonce)
    """
    salt = os.urandom(16)
    key = derive_key(password, salt)
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)
    encrypted = aesgcm.encrypt(nonce, data, None)
    return encrypted, salt, nonce


def decrypt_data(encrypted_data: bytes, password: str, salt: bytes, nonce: bytes) -> bytes:
    """
    Decrypt data using AES-GCM with derived key
    
    Args:
        encrypted_data: Data to decrypt
        password: Password for decryption
        salt: Salt used for key derivation
        nonce: Nonce used for encryption
        
    Returns:
        Decrypted data
        
    Raises:
        ValueError: If decryption fails (wrong password or corrupted data)
    """
    try:
        key = derive_key(password, salt)
        aesgcm = AESGCM(key)
        return aesgcm.decrypt(nonce, encrypted_data, None)
    except Exception as e:
        raise ValueError("Invalid password or corrupted payload") from e


def encrypt_if_needed(data: bytes, password: Optional[str]) -> Tuple[bytes, bytes, bytes]:
    """
    Conditionally encrypt data if password is provided
    
    Args:
        data: Data to potentially encrypt
        password: Optional password for encryption
        
    Returns:
        Tuple of (processed_data, salt, nonce)
    """
    if not password:
        return data, b"", b""
    return encrypt_data(data, password)


def decrypt_if_needed(data: bytes, password: Optional[str], salt: bytes, nonce: bytes) -> bytes:
    """
    Conditionally decrypt data if password was used
    
    Args:
        data: Data to potentially decrypt
        password: Optional password for decryption
        salt: Salt used for key derivation
        nonce: Nonce used for encryption
        
    Returns:
        Decrypted or original data
    """
    if not password:
        return data
    return decrypt_data(data, password, salt, nonce)
