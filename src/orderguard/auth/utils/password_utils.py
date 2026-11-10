from pwdlib import PasswordHash



password_hasher = PasswordHash.recommended()


async def hash_password(password : str):
    return password_hasher.hash(password=password)



async def verify_password(password : str, hashed_password : str):
    return password_hasher.verify(password=password, hash=hashed_password)
