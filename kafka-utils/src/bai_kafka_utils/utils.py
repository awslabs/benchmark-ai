import encodings
import hashlib
import platform
import random
import string
import uuid

DEFAULT_ENCODING = encodings.utf_8.getregentry().name


def id_generator(size=8, chars=string.ascii_lowercase + string.digits):
    return "".join(random.choice(chars) for _ in range(size))


def md5sum(str_to_hash: str, encoding: str = DEFAULT_ENCODING):
    md5hash = hashlib.md5()
    md5hash.update(str_to_hash.encode(encoding))
    return md5hash.hexdigest()


def generate_uuid():
    return str(uuid.uuid4())


def get_pod_name():
    return platform.node()
