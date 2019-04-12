import hashlib
import random
import string


def id_generator(size=8, chars=string.ascii_lowercase + string.digits):
    return ''.join(random.choice(chars) for _ in range(size))


def md5sum(str_to_hash: str, encoding: str = "utf-8"):
    md5hash = hashlib.md5()
    md5hash.update(str_to_hash.encode(encoding))
    return md5hash.hexdigest()
