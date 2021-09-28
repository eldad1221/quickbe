
from backbone import WebServer, endpoint, Log


@endpoint(path='encrypt')
def encrypt(req: dict):

