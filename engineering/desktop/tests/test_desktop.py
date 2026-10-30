import copy
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import time
import uuid
import httpx
import pytest

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / "engineering/.test-output/desktop-tests" / uuid.uuid4().hex
BASE.mkdir(parents=True)
INSTALLER = ROOT / "安装依赖.exe"
LAUNCHER = ROOT / "启动OnlineCOC.exe"

def relative(path):
    return path.relative_to(ROOT).as_posix()

def save(settings, name):
    path = BASE / (name + ".json")
    path.write_text(json.dumps(settings, ensure_ascii=False), encoding="utf-8")
    return path

def run(exe, config, *args, timeout=120):
    result = subprocess.run([str(exe), "--headless", "--config", str(config), *args],
                            capture_output=True, encoding="utf-8", errors="replace", timeout=timeout)
    return result

@pytest.fixture(scope="module")
def installed():
    settings = json.loads((ROOT / "launcher-config.json").read_text(encoding="utf-8"))
    # Reuse only the independently verified archive; this fixture extracts a new Python and builds a fresh venv.
    settings["python"].update(directory=relative(BASE / "python"), cacheFile="engineering/.test-output/launcher-bootstrap/python-3.14.2-amd64.zip")
    settings["dependencies"].update(environmentRoot=relative(BASE / "environments"), wheelDirectory="engineering/.test-output/wheels", offline=True)
    settings["application"].update(dataDirectory=relative(BASE / "data"), openBrowser=False)
    settings["logsDirectory"] = relative(BASE / "logs")
    path = save(settings, "installed")
    result = run(INSTALLER, path, timeout=240)
    assert result.returncode == 0, result.stdout + result.stderr
    return settings, path

def test_fresh_install_and_idempotent_check(installed):
    settings, path = installed
    result = run(INSTALLER, path)
    assert result.returncode == 0 and "无需重复安装" in result.stdout
    result = run(LAUNCHER, path, "--check")
    assert result.returncode == 0 and "DEPENDENCIES_OK 26" in result.stdout


def test_dependency_lock_update_creates_new_environment(installed):
    settings, _ = installed
    changed = copy.deepcopy(settings)
    lock = BASE / "updated.lock"
    lock.write_text((ROOT / settings["dependencies"]["lockFile"]).read_text() + "# update test\n")
    changed["dependencies"]["lockFile"] = relative(lock)
    existing = list((ROOT / settings["dependencies"]["environmentRoot"]).glob("*/onlinecoc-ready.txt"))
    result = run(INSTALLER, save(changed, "updated"))
    assert result.returncode == 0, result.stdout
    markers = list((ROOT / settings["dependencies"]["environmentRoot"]).glob("*/onlinecoc-ready.txt"))
    assert len(markers) == len(existing) + 1 and all(p.exists() for p in existing)


def test_corrupt_package_is_repaired(installed):
    settings, path = installed
    signature = str(ROOT).lower() + "\n" + settings["python"]["version"] + "\n" + settings["python"]["sha256"] + "\n" + (ROOT / settings["dependencies"]["lockFile"]).read_bytes().decode("utf-8-sig")
    name = hashlib.sha256(signature.encode()).hexdigest()[:20]
    marker = ROOT / settings["dependencies"]["environmentRoot"] / name / "onlinecoc-ready.txt"
    metadata = next(marker.parent.glob("Lib/site-packages/fastapi-*.dist-info/METADATA"))
    original = metadata.read_text(encoding="utf-8")
    metadata.write_text(original.replace("Version: 0.162.0", "Version: 0.0.0"), encoding="utf-8")
    assert run(LAUNCHER, path, "--check").returncode == 1
    repaired = run(INSTALLER, path)
    assert repaired.returncode == 0 and "修复" in repaired.stdout, repaired.stdout
    assert run(LAUNCHER, path, "--check").returncode == 0


def test_server_launch_action_shutdown_and_reopen(installed):
    settings, _ = installed
    config = copy.deepcopy(settings)
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0)); port = probe.getsockname()[1]
    config["application"]["port"] = port
    path = save(config, "serve")
    env = os.environ.copy(); env["ONLINECOC_BOOTSTRAP_PASSWORD"] = "desktop-test-password"
    base = f"http://127.0.0.1:{port}"
    for attempt in range(2):
        process = subprocess.Popen([str(LAUNCHER), "--headless", "--config", str(path), "--no-browser", "--run-seconds", "12"],
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding="utf-8", errors="replace", env=env)
        try:
            with httpx.Client(base_url=base, trust_env=False, timeout=15) as client:
                for _ in range(120):
                    if process.poll() is not None:
                        pytest.fail("Launcher exited early: " + process.communicate()[0])
                    try:
                        if client.get("/api/v1/capabilities").status_code == 200:
                            break
                    except httpx.HTTPError:
                        pass
                    time.sleep(.1)
                else:
                    pytest.fail("Launcher startup timeout")
                duplicate = run(INSTALLER, path, "--check")
                assert duplicate.returncode == 1 and "已有" in duplicate.stdout
                client.headers["Origin"] = base
                login = client.post("/api/v1/login", json={"loginName":"player1", "password":"desktop-test-password"})
                assert login.status_code == 200, login.text
                client.headers["X-CSRF-Token"] = login.json()["csrf"]
                view = client.get("/api/v1/view").json()
                assert view["entities"]["actor-player1"]["numbers"]["hp"] == (9 if attempt == 0 else 4)
                if attempt == 0:
                    payload = {"commandId":"desktop-damage", "authorityEpoch":view["authorityEpoch"], "runId":view["runId"],
                               "catalogRevision":view["catalog"]["revision"], "rulesetRevision":view["catalog"]["rulesetRevision"],
                               "op":"action.invoke", "args":{"actionId":"demo.damage", "input":{"actor":"actor-player1", "amount":7}}}
                    response = client.post("/api/v1/commands", json={"protocolVersion":1,"type":"command","requestId":"desktop","roomId":"demo","payload":payload})
                    assert response.json()["status"] == "committed", response.text
            output, errors = process.communicate(timeout=25)
            assert process.returncode == 0 and "服务已停止" in output, output + errors
            with socket.socket() as probe:
                assert probe.connect_ex(("127.0.0.1", port)) != 0
        finally:
            if process.poll() is None:
                process.terminate(); process.wait(timeout=10)


@pytest.mark.parametrize("case", ["path", "hash", "offline-cache"])
def test_invalid_configuration_and_archive(installed, case):
    settings, _ = installed
    changed = copy.deepcopy(settings)
    if case == "path":
        changed["application"]["dataDirectory"] = "../outside"
    else:
        changed["python"]["directory"] = relative(BASE / ("python-" + case))
        if case == "hash":
            bad = BASE / "bad.zip"; bad.write_bytes(b"invalid")
            changed["python"]["cacheFile"] = relative(bad)
        else:
            changed["python"]["cacheFile"] = relative(BASE / "missing.zip")
    result = run(INSTALLER, save(changed, case))
    assert result.returncode == 1
    assert {"path":"越出", "hash":"摘要不匹配", "offline-cache":"离线模式缺少"}[case] in result.stdout + result.stderr


def test_occupied_port_fails_without_stopping_other_service(installed):
    settings, _ = installed
    changed = copy.deepcopy(settings)
    with socket.socket() as occupied:
        occupied.bind(("127.0.0.1", 0)); occupied.listen()
        changed["application"]["port"] = occupied.getsockname()[1]
        result = run(LAUNCHER, save(changed, "busy-port"), "--no-browser", "--run-seconds", "1")
        assert result.returncode == 1 and "端口已被占用" in result.stdout
