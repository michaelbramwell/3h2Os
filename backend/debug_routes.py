from app.main import app
import json

for route in app.routes:
    if hasattr(route, "methods"):
        print(f"{route.methods} {route.path}")
    else:
        print(f"MOUNT {route.path}")
