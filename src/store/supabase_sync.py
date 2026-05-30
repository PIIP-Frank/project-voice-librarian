import io
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


def _load_dotenv() -> None:
    # Walk up from this file until we find a .env
    current = Path(__file__).resolve().parent
    for _ in range(5):
        candidate = current / ".env"
        if candidate.exists():
            with open(candidate, encoding="utf-8") as env_file:
                for line in env_file:
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    key, value = line.split("=", 1)
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")
                    if key and key not in os.environ:
                        os.environ[key] = value
            return
        current = current.parent

_load_dotenv()


def _require_env_value(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def _derive_storage_url(project_url: str) -> str:
    parsed = urllib.parse.urlparse(project_url)
    if not parsed.scheme or not parsed.netloc:
        raise RuntimeError("Invalid SUPABASE_URL; expected a full URL like https://project-ref.supabase.co")
    if parsed.netloc.endswith(".supabase.co"):
        project_ref = parsed.netloc[: -len(".supabase.co")]
        return f"{parsed.scheme}://{project_ref}.storage.supabase.co"
    return project_url.rstrip("/")


SUPABASE_URL = _require_env_value("SUPABASE_URL")
SUPABASE_SERVICE_KEY = _require_env_value("SUPABASE_SERVICE_KEY")
SUPABASE_USER_TABLE = os.getenv("SUPABASE_USER_TABLE", "users")
SUPABASE_SAMPLE_BUCKET = os.getenv("SUPABASE_SAMPLE_BUCKET", "samples")
SUPABASE_STORAGE_URL = os.getenv("SUPABASE_STORAGE_URL", _derive_storage_url(SUPABASE_URL))
print(f"[init] SUPABASE_URL: {SUPABASE_URL}")
print(f"[init] SUPABASE_STORAGE_URL: {SUPABASE_STORAGE_URL}")  # ← add this

def _headers(extra: dict | None = None) -> dict:
    headers = {
        "apikey": SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
        "Accept": "application/json",
    }
    if extra:
        headers.update(extra)
    return headers


def _urlopen(request: urllib.request.Request):
    try:
        return urllib.request.urlopen(request, timeout=20)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"Supabase request failed: {exc.code} {exc.reason} {body}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Supabase connection failed: {exc.reason}") from exc


def fetch_remote_users() -> list[dict]:
    try:
        return _fetch_remote_users(include_password=True)
    except RuntimeError as exc:
        message = str(exc).lower()
        if "password" in message or "unknown" in message:
            return _fetch_remote_users(include_password=False)
        raise


def _fetch_remote_users(include_password: bool = True) -> list[dict]:
    fields = ["username", "role", "preferred_lang"]
    if include_password:
        fields.append("password")
    select = ",".join(fields)
    url = f"{SUPABASE_URL}/rest/v1/{SUPABASE_USER_TABLE}?select={select}"
    request = urllib.request.Request(url, method="GET", headers=_headers())
    response = _urlopen(request)
    data = response.read().decode("utf-8")
    rows = json.loads(data)
    if not include_password:
        for row in rows:
            row.setdefault("password", "")
    return rows


def upsert_users_to_cloud(users: list[dict]) -> None:
    if not users:
        return
    url = f"{SUPABASE_URL}/rest/v1/{SUPABASE_USER_TABLE}?on_conflict=username"
    payload = json.dumps(users).encode("utf-8")
    headers = _headers({"Content-Type": "application/json"})
    request = urllib.request.Request(url, data=payload, method="POST", headers=headers)
    try:
        response = _urlopen(request)
        if response.getcode() not in (200, 201):
            raise RuntimeError(f"Supabase user upsert failed: {response.getcode()}")
    except RuntimeError as exc:
        message = str(exc).lower()
        if "password" in message or "unknown" in message:
            for row in users:
                row.pop("password", None)
            payload = json.dumps(users).encode("utf-8")
            request = urllib.request.Request(url, data=payload, method="POST", headers=headers)
            response = _urlopen(request)
            if response.getcode() not in (200, 201):
                raise RuntimeError(f"Supabase user upsert failed: {response.getcode()}")
        else:
            raise


def list_storage_objects(prefix: str = "") -> list[dict]:
    url = f"{SUPABASE_STORAGE_URL}/storage/v1/object/list/{SUPABASE_SAMPLE_BUCKET}"
    body = json.dumps({"prefix": prefix, "limit": 1000}).encode("utf-8")
    headers = _headers({"Content-Type": "application/json"})
    request = urllib.request.Request(url, data=body, method="POST", headers=headers)
    response = _urlopen(request)
    data = response.read().decode("utf-8")
    return json.loads(data)

def upload_file_to_supabase(path: Path, username: str) -> None:
    object_path = f"{username}/{path.name}"
    safe_path = urllib.parse.quote(object_path, safe="/")
    url = f"{SUPABASE_STORAGE_URL}/storage/v1/object/{SUPABASE_SAMPLE_BUCKET}/{safe_path}"
    print(f"[upload] URL: {url}")          # ← add this
    print(f"[upload] Storage URL: {SUPABASE_STORAGE_URL}")  # ← and this
    with path.open("rb") as handle:
        data = handle.read()
    headers = _headers({"Content-Type": "audio/wav"})
    request = urllib.request.Request(url, data=data, method="PUT", headers=headers)
    response = _urlopen(request)
    if response.getcode() not in (200, 201):
        raise RuntimeError(f"Supabase upload failed: {response.getcode()}")


def download_file_from_supabase(object_path: str) -> bytes:
    safe_path = urllib.parse.quote(object_path, safe="/")
    url = f"{SUPABASE_STORAGE_URL}/storage/v1/object/{SUPABASE_SAMPLE_BUCKET}/{safe_path}"
    request = urllib.request.Request(url, method="GET", headers=_headers())
    response = _urlopen(request)
    return response.read()


def pull_all_samples_to_local(destination_root: Path | None = None) -> int:
    if destination_root is None:
        destination_root = Path("data") / "recordings"
    objects = list_storage_objects(prefix="")
    count = 0
    for entry in objects:
        if isinstance(entry, str):
            name = entry
        elif isinstance(entry, dict):
            name = entry.get("name") or entry.get("id") or ""
        else:
            continue
        if not name or not name.lower().endswith(".wav"):
            continue
        parts = name.split("/")
        if len(parts) < 2:
            continue
        username = parts[0]
        filename = "/".join(parts[1:])
        if not filename:
            continue
        target_dir = destination_root / username
        target_dir.mkdir(parents=True, exist_ok=True)
        data = download_file_from_supabase(name)
        output_path = target_dir / filename
        output_path.write_bytes(data)
        count += 1
    return count
