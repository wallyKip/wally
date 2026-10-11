#!/usr/bin/env python3
"""
Eenvoudige helper om notificaties naar de lokale ntfy server te sturen.
"""
import requests
from datetime import datetime

# Pas dit aan als je een andere topic-naam gebruikt
NTFY_URL = "http://localhost:8080/wally"

def stuur_notificatie(bericht, titel="Wally", prioriteit="default", tags=None):
    """
    Stuur een notificatie naar ntfy.
    
    prioriteit: 'min', 'low', 'default', 'high', 'urgent'
    tags: lijst van strings, bv. ['warning', 'fire'] (emoji in de app)
    """
    headers = {
        "Title": titel,
        "Priority": prioriteit,
    }
    if tags:
        headers["Tags"] = ",".join(tags)

    try:
        r = requests.post(
            NTFY_URL,
            data=bericht.encode("utf-8"),
            headers=headers,
            timeout=5,
        )
        return r.status_code == 200
    except Exception as e:
        print(f"[notify] Fout bij versturen: {e}")
        return False


def stuur_met_rem(bericht, titel="Wally", prioriteit="default",
                 tags=None, rem_seconden=3600):
    """
    Stuurt een notificatie, maar maximaal 1x per `rem_seconden`.
    Gebruikt een bestand in /tmp om de laatste verzendtijd bij te houden.
    """
    import os
    import time

    # Bestandsnaam op basis van titel, zodat verschillende meldingen
    # hun eigen rem hebben.
    veilige_titel = "".join(c for c in titel if c.isalnum() or c in "-_")
    rem_file = f"/tmp/wally_notify_{veilige_titel}.txt"

    nu = time.time()
    if os.path.exists(rem_file):
        try:
            with open(rem_file) as f:
                laatste = float(f.read().strip())
            if nu - laatste < rem_seconden:
                return False  # nog in de rem-periode
        except (ValueError, OSError):
            pass

    succes = stuur_notificatie(bericht, titel, prioriteit, tags)
    if succes:
        try:
            with open(rem_file, "w") as f:
                f.write(str(nu))
        except OSError:
            pass
    return succes