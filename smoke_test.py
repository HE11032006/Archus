# smoke_test.py: checks your Data and Power layers
# Install once: pip install openai python-dotenv requests
# For the JDBC check: pip install jaydebeapi (and a JDK 11+, set JAVA_HOME in .env)
import os
import uuid

import requests
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
results = []


def check(name, fn):
    try:
        fn()
        results.append(("PASS", name, ""))
    except Exception as error:
        results.append(("FAIL", name, str(error)[:150]))


def need(*names):
    for name in names:
        assert os.environ.get(name), f"{name} is missing from .env"


def zetaris_web():
    url = os.environ.get("ZETARIS_BASE_URL", "http://localhost:3000")
    requests.get(url, timeout=10).raise_for_status()


def zetaris_sql():
    need("ZETARIS_REST_URL", "ZETARIS_ORG_ID", "ZETARIS_API_KEY")
    response = requests.post(
        os.environ["ZETARIS_REST_URL"].rstrip("/") + "/sql-editor/sqls/run",
        headers={
            "Authorization": "Bearer " + os.environ["ZETARIS_API_KEY"],
            "X-Org-ID": os.environ["ZETARIS_ORG_ID"],
            "X-Request-ID": str(uuid.uuid4()),
        },
        json={"queryId": str(uuid.uuid4()), "sql": "SELECT 1", "source": "SqlEditor", "limit": 1},
        timeout=60,
    )
    response.raise_for_status()
    data = response.json().get("data")
    assert data and str(data[0][0]) == "1", "unexpected reply: " + response.text[:80]


def zetaris_rest_login():
    # Signs in like the Zetaris web interface, then runs SELECT 1 through its proxy
    need("ZETARIS_USERNAME", "ZETARIS_PASSWORD")
    base_url = os.environ.get("ZETARIS_BASE_URL", "http://localhost:3000").rstrip("/")
    login = requests.post(
        base_url + "/api/auth/login",
        headers={"X-Request-ID": str(uuid.uuid4())},
        json={"username": os.environ["ZETARIS_USERNAME"], "password": os.environ["ZETARIS_PASSWORD"]},
        timeout=30,
    )
    assert login.ok, f"login failed: HTTP {login.status_code}"
    token = login.json().get("idToken")
    assert token, "login did not return an idToken"

    response = requests.post(
        base_url + "/api/proxy/sql-editor/sqls/run-query",
        headers={
            "Authorization": "Bearer " + token,
            "X-Org-ID": os.environ.get("ZETARIS_ORG_ID", "1"),
            "X-Request-ID": str(uuid.uuid4()),
        },
        json={"sql": "SELECT 1", "limit": 1},
        timeout=60,
    )
    response.raise_for_status()
    data = response.json().get("data")
    assert data and str(data[0][0]) == "1", "unexpected reply: " + response.text[:80]


def zetaris_jdbc_sql():
    # Needs: pip install jaydebeapi, a JDK 11+ (JAVA_HOME) and the Zetaris JDBC driver JAR
    need("ZETARIS_JDBC_JAR", "ZETARIS_JDBC_URL", "ZETARIS_USERNAME", "ZETARIS_PASSWORD")
    import jaydebeapi
    import jpype

    jar = os.environ["ZETARIS_JDBC_JAR"]
    if os.name == "nt" and jar.startswith("/mnt/"):  # a WSL path read by Windows Python
        jar = jar[5].upper() + ":" + jar[6:]
    assert os.path.isfile(jar), f"driver JAR not found: {jar}"
    try:  # JAVA_HOME, else `java` on the PATH (WSL/Linux), else the Windows registry
        jpype.getDefaultJVMPath()
    except jpype.JVMNotFoundException:
        raise AssertionError("no Java found: install a JDK 11+ or set JAVA_HOME in .env") from None

    connection = jaydebeapi.connect(
        "com.zetaris.lightning.jdbc.LightningDriver",
        os.environ["ZETARIS_JDBC_URL"],
        [os.environ["ZETARIS_USERNAME"], os.environ["ZETARIS_PASSWORD"]],
        jar,
    )
    try:
        cursor = connection.cursor()
        cursor.execute("SELECT 1")
        rows = cursor.fetchall()
        assert rows and str(rows[0][0]) == "1", f"unexpected reply: {rows!r}"[:80]
    finally:
        connection.close()


def nemotron():
    need("MODEL_BASE_URL", "MODEL_API_KEY", "NEMOTRON_MODEL")
    client = OpenAI(
        base_url=os.environ["MODEL_BASE_URL"],
        api_key=os.environ["MODEL_API_KEY"],
    )
    reply = client.chat.completions.create(
        model=os.environ["NEMOTRON_MODEL"],
        messages=[{"role": "user", "content": "Reply with the single word: ready"}],
    )
    assert reply.choices, "no reply from the model"


def meterless_nemotron():
    # Same settings as the app: base URL (provider_settings / METERLESS_BASE_URL), token (provider_settings,
    # METERLESS_RUNTIME_TOKEN or <METERLESS_STATE_DIR>/proxy-token) and routing mode (METERLESS_MODEL)
    from app.adapters.meterless_runtime import MeterlessRuntimeProvider

    provider = MeterlessRuntimeProvider()
    assert provider.token, "no Meterless Runtime token: set METERLESS_STATE_DIR or run scripts/meterless.py token"
    text, served = provider.chat_with_meta(
        [{"role": "user", "content": "Reply with the single word: ready"}], model=provider.model
    )
    assert text and text.strip(), f"empty reply from {provider.model} (served by {served})"


check("Data: Zetaris web interface", zetaris_web)
check("Data: Zetaris runs SQL over its REST API", zetaris_sql)
check("Data: Zetaris login and SQL through the web interface", zetaris_rest_login)
check("Data: Zetaris runs SQL over JDBC", zetaris_jdbc_sql)
check("Power: Nemotron replies", nemotron)
check("Power: Nemotron replies through Meterless (Nightshift)", meterless_nemotron)

for status, name, detail in results:
    print(f"{status} {name} {detail}")
