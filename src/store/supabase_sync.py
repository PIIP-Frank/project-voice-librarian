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
SUPABASE_TRANSLATION_TABLE = os.getenv("SUPABASE_TRANSLATION_TABLE", "word_translations")
SUPABASE_SAMPLE_BUCKET = os.getenv("SUPABASE_SAMPLE_BUCKET", "samples")
SUPABASE_STORAGE_URL = os.getenv("SUPABASE_STORAGE_URL", _derive_storage_url(SUPABASE_URL))
print(f"[init] SUPABASE_URL: {SUPABASE_URL}")
print(f"[init] SUPABASE_TRANSLATION_TABLE: {SUPABASE_TRANSLATION_TABLE}")
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
        print(f"[_urlopen] HTTPError: {exc.code} {exc.reason}")
        print(f"[_urlopen] Body: {body[:500]}")  # Log first 500 chars
        raise RuntimeError(f"Supabase request failed: {exc.code} {exc.reason} {body}") from exc
    except urllib.error.URLError as exc:
        print(f"[_urlopen] URLError: {exc.reason}")
        raise RuntimeError(f"Supabase connection failed: {exc.reason}") from exc
    except Exception as exc:
        print(f"[_urlopen] Unexpected error: {type(exc).__name__}: {exc}")
        raise


def fetch_remote_users() -> list[dict]:
    try:
        return _fetch_remote_users(include_password=True)
    except RuntimeError as exc:
        # message = str(exc).lower()
        # if "password" in message or "unknown" in message:
        #     return _fetch_remote_users(include_password=False)
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
    headers = _headers({"Content-Type": "application/json", "Prefer": "resolution=merge-duplicates"})
    request = urllib.request.Request(url, data=payload, method="POST", headers=headers)
    try:
        print("[upsert_users] Calling _urlopen...")
        response = _urlopen(request)
        print(f"[upsert_users] Response status: {response.status}")
        if response.status not in (200, 201):
            raise RuntimeError(f"Supabase user upsert failed: {response.status}")
    except RuntimeError as exc:
        message = str(exc).lower()
        print(f"[upsert_users] Caught RuntimeError: {message[:100]}")
        if "password" in message or "unknown" in message:
            print("[upsert_users] Retrying without password...")
            for row in users:
                row.pop("password", None)
            payload = json.dumps(users).encode("utf-8")
            request = urllib.request.Request(url, data=payload, method="POST", headers=headers)
            try:
                response = _urlopen(request)
                if response.status not in (200, 201):
                    raise RuntimeError(f"Supabase user upsert failed: {response.status}")
            except RuntimeError as retry_exc:
                print(f"[upsert_users] Retry failed: {retry_exc}")
                raise RuntimeError(f"Supabase user upsert failed (retry): {retry_exc}") from exc
        else:
            print("[upsert_users] Error not password-related, re-raising...")
            raise


def fetch_remote_translations() -> list[dict]:
    url = f"{SUPABASE_URL}/rest/v1/{SUPABASE_TRANSLATION_TABLE}?select=english_word,lang_code,translation"
    request = urllib.request.Request(url, method="GET", headers=_headers())
    response = _urlopen(request)
    return json.loads(response.read().decode("utf-8"))


def upsert_translations_to_cloud(translations: list[dict]) -> None:
    if not translations:
        return
    url = f"{SUPABASE_URL}/rest/v1/{SUPABASE_TRANSLATION_TABLE}?on_conflict=english_word,lang_code"
    payload = json.dumps(translations).encode("utf-8")
    headers = _headers({"Content-Type": "application/json", "Prefer": "resolution=merge-duplicates"})
    request = urllib.request.Request(url, data=payload, method="POST", headers=headers)
    response = _urlopen(request)
    if response.status not in (200, 201):
        raise RuntimeError(f"Supabase translation upsert failed: {response.status}")


def list_storage_objects(prefix: str = "") -> list[dict]:
    url = f"{SUPABASE_STORAGE_URL}/storage/v1/object/list/{SUPABASE_SAMPLE_BUCKET}"
    body = json.dumps({"prefix": prefix, "limit": 1000}).encode("utf-8")
    headers = _headers({"Content-Type": "application/json"})
    request = urllib.request.Request(url, data=body, method="POST", headers=headers)
    print(f"[list_storage_objects] URL: {url}")
    print(f"[list_storage_objects] Prefix: {prefix}")
    response = _urlopen(request)
    data = response.read().decode("utf-8")
    print(f"[list_storage_objects] Raw response: {data[:500]}")
    result = json.loads(data)
    print(f"[list_storage_objects] Parsed result type: {type(result)}, keys: {result.keys() if isinstance(result, dict) else 'N/A'}")
    return result

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
    if response.status not in (200, 201):
        raise RuntimeError(f"Supabase upload failed: {response.status}")


def download_file_from_supabase(object_path: str) -> bytes:
    safe_path = urllib.parse.quote(object_path, safe="/")
    url = f"{SUPABASE_STORAGE_URL}/storage/v1/object/{SUPABASE_SAMPLE_BUCKET}/{safe_path}"
    request = urllib.request.Request(url, method="GET", headers=_headers())
    response = _urlopen(request)
    return response.read()


def pull_all_samples_to_local(username: str | None = None, destination_root: Path | None = None) -> int:
    if destination_root is None:
        destination_root = Path("data") / "recordings"
    
    count = 0
    
    if username:
        # Download for specific user
        print(f"[pull_all_samples] Fetching samples for user: {username}")
        count += _download_user_samples(username, destination_root)
    else:
        # Get all user folders and download from each
        print(f"[pull_all_samples] Fetching all user folders...")
        objects = list_storage_objects(prefix="")
        user_folders = []
        for entry in objects:
            if isinstance(entry, dict):
                folder_name = entry.get("name", "")
                if folder_name and not folder_name.lower().endswith(".wav"):
                    user_folders.append(folder_name)
                    print(f"[pull_all_samples] Found user folder: {folder_name}")
        
        for user_folder in user_folders:
            print(f"[pull_all_samples] Downloading samples for user: {user_folder}")
            count += _download_user_samples(user_folder, destination_root)
    
    print(f"[pull_all_samples] Total downloaded: {count}")
    return count


def _download_user_samples(username: str, destination_root: Path) -> int:
    """Download all .wav files for a specific user from cloud storage."""
    prefix = f"{username}/"
    print(f"[_download_user_samples] Listing files with prefix: {prefix}")
    objects = list_storage_objects(prefix=prefix)
    
    count = 0
    for entry in objects:
        print(f"[_download_user_samples] Processing entry: {entry}")
        if isinstance(entry, dict):
            name = entry.get("name", "")
        elif isinstance(entry, str):
            name = entry
        else:
            continue
        
        if not name:
            print(f"[_download_user_samples] Skipping empty name")
            continue
        
        # Skip folders (entries without extension)
        if not name.lower().endswith(".wav"):
            print(f"[_download_user_samples] Skipping non-wav: {name}")
            continue
        
        # The API returns filenames without the prefix, so reconstruct full path
        # If name is "hello-sample1.wav", full path is "admin/hello-sample1.wav"
        if "/" not in name:
            full_path = f"{username}/{name}"
        else:
            full_path = name
        
        print(f"[_download_user_samples] Full path to download: {full_path}")
        target_dir = destination_root / username
        target_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            data = download_file_from_supabase(full_path)
            output_path = target_dir / name
            output_path.write_bytes(data)
            print(f"[_download_user_samples] ✓ Downloaded {output_path} ({len(data)} bytes)")
            count += 1
        except Exception as e:
            print(f"[_download_user_samples] ✗ Failed to download {full_path}: {e}")
    
    return count
