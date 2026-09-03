import hashlib
import hmac
import ipaddress
import socket
import time
from urllib.parse import urlparse


def validate_remote_url(value:str):
    parsed=urlparse(value)
    if parsed.scheme not in {"http","https"} or not parsed.hostname:
        raise ValueError("source URL must use http or https")
    if parsed.username or parsed.password:
        raise ValueError("credentials in source URL are forbidden")
    try:
        addresses={item[4][0] for item in socket.getaddrinfo(parsed.hostname,parsed.port or 443,type=socket.SOCK_STREAM)}
    except socket.gaierror as exc:
        raise ValueError("source host cannot be resolved") from exc
    for raw in addresses:
        ip=ipaddress.ip_address(raw)
        if not ip.is_global:
            raise ValueError("private and local source addresses are forbidden")
    return value

def sign_result(job_id:str,filename:str,secret:str,ttl_minutes:int):
    expires=int(time.time()+ttl_minutes*60); payload=f"{job_id}:{filename}:{expires}"
    signature=hmac.new(secret.encode(),payload.encode(),hashlib.sha256).hexdigest()
    return expires,signature

def verify_result(job_id:str,filename:str,expires:int,signature:str,secret:str):
    if expires<int(time.time()): return False
    payload=f"{job_id}:{filename}:{expires}"; expected=hmac.new(secret.encode(),payload.encode(),hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected,signature)
