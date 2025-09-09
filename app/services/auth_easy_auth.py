from __future__ import annotations
import base64
import json
from typing import Dict

def get_user_from_easy_auth(headers: Dict[str, str]) -> Dict[str, str]:
    """
    Parses Azure App Service Easy Auth headers (X-MS-CLIENT-PRINCIPAL).
    In production behind Easy Auth, configure the reverse proxy to pass headers to Streamlit.
    """
    pr = headers.get("X-MS-CLIENT-PRINCIPAL")
    if not pr:
        email = headers.get("X-DEBUG-EMAIL") or ""
        name = headers.get("X-DEBUG-NAME") or ""
        oid = headers.get("X-DEBUG-OID") or ""
        if email:
            return {"name": name or email, "email": email, "oid": oid or "debug-oid"}
        raise RuntimeError("Missing Easy Auth principal header.")
    decoded = base64.b64decode(pr)
    data = json.loads(decoded.decode("utf-8"))
    name = data.get("name") or data.get("userDetails") or ""
    email = data.get("userPrincipalName") or ""
    oid = ""
    for c in data.get("claims", []):
        typ = c.get("typ","")
        if typ.endswith("/name"):
            name = c.get("val", name)
        if typ.endswith("/emailaddress") or typ.endswith("/upn"):
            email = c.get("val", email)
        if typ.endswith("/objectidentifier"):
            oid = c.get("val", oid)
    if not email:
        raise RuntimeError("Easy Auth missing email in claims.")
    return {"name": name or email, "email": email, "oid": oid or ""}
