import encodings
import hashlib
import logging
import platform
import random
import string

DEFAULT_ENCODING = encodings.utf_8.getregentry().name

LOGGING_FORMAT = "%(asctime)s %(levelname)s: %(message)s"


def set_logging_level_and_format(level: str, **kwargs):
    logging.basicConfig(level=level, format=LOGGING_FORMAT, **kwargs)


def id_generator(size=8, chars=string.ascii_lowercase + string.digits):
    return "".join(random.choice(chars) for _ in range(size))


def md5sum(str_to_hash: str, encoding: str = DEFAULT_ENCODING):
    md5hash = hashlib.md5()
    md5hash.update(str_to_hash.encode(encoding))
    return md5hash.hexdigest()


def get_pod_name():
    return platform.node()
