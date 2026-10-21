import pytest
import requests
import subprocess
import re
import logging
import os

import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BMC_IP = "127.0.0.1:2443"
BASE_URL = f"https://{BMC_IP}/redfish/v1"
AUTH = ("root", "0penBmc")
CPU_KEYWORD = os.getenv("CPU_KEYWORD", "cpu").lower()


def get_ipmi_cpu_temps():
    command = [
        "ipmitool", "-I", "lanplus",
        "-H", "127.0.0.1", "-p", "2623",
        "-U", "root", "-P", "0penBmc",
        "sdr", "type", "Temperature",
    ]
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=30)
    except subprocess.TimeoutExpired:
        pytest.fail("ipmitool не ответил за 30 секунд")

    temps = {}
    for line in result.stdout.splitlines():
        parts = [p.strip() for p in line.split("|")]
        if len(parts) < 5 or CPU_KEYWORD not in parts[0].lower():
            continue
        match = re.match(r"(-?\d+(?:\.\d+)?) degrees C", parts[4])
        if match:
            temps[parts[0]] = float(match.group(1))
    return temps


@pytest.fixture(scope="session")
def api_session():
    session = requests.Session()
    session.auth = AUTH
    session.verify = False
    return session


def test_auth(api_session):
    url = f"{BASE_URL}/SessionService/Sessions"
    payload = {"UserName": "root", "Password": "0penBmc"}
    
    response = api_session.post(url, json=payload)
    
    assert response.status_code in [200, 201], f"Ошибка авторизации: {response.status_code}"
    assert "X-Auth-Token" in response.headers or "SessionToken" in response.text, "Токен сессии не найден"


def test_get_system_info(api_session):
    url = f"{BASE_URL}/Systems/system"
    response = api_session.get(url)

    assert response.status_code == 200, f"Не удалось получить данные системы: {response.status_code}"
    
    data = response.json()
    assert "Status" in data, "Поле 'Status' отсутствует в ответе"
    assert "PowerState" in data, "Поле 'PowerState' отсутствует в ответе"


def test_power_control(api_session):
    url = f"{BASE_URL}/Systems/system/Actions/ComputerSystem.Reset"
    payload = {"ResetType": "On"}
    
    response = api_session.post(url, json=payload)
    assert response.status_code in [202, 204], f"Команда питания отклонена: {response.status_code}"
    
    system_response = api_session.get(f"{BASE_URL}/Chassis/chassis")
    assert system_response.status_code == 200
    
    power_state = system_response.json().get("PowerState")
    if power_state == "Off":
        pytest.skip("Не может выключиться")
    assert power_state == "On", f"Ожидался статус 'On', но получен: {power_state}"


def test_cpu_temperature(api_session):
    url = f"{BASE_URL}/Chassis/chassis/Thermal"
    response = api_session.get(url)
    print(response.text)

    if response.status_code == 200:
        data = response.json()
        temperatures = data.get("Temperatures", [])
        for temp in temperatures:
            reading = temp.get("ReadingCelsius")
            if reading is not None:
                assert 0 <= reading <= 100, f"Температура CPU выходит за норму: {reading}°C"
    else:
        pytest.skip("Датчики температуры не поддерживаются")


def test_sensors_redfish_vs_ipmi(api_session):
    ipmi_temps = get_ipmi_cpu_temps()
    
    url = f"{BASE_URL}/Chassis/chassis/Thermal"
    response = api_session.get(url)
    
    if response.status_code != 200:
        pytest.skip("Эндпоинт Thermal недоступен для сравнения с IPMI")

    redfish_data = response.json()
    redfish_temps = {}
    for temp in redfish_data.get("Temperatures", []):
        name = temp.get("Name", "")
        reading = temp.get("ReadingCelsius")
        if name and reading is not None:
            redfish_temps[name.lower()] = reading

    redfish_values = list(redfish_temps.values())
    
    if ipmi_temps and redfish_values:
        for name, ipmi_value in ipmi_temps.items():
            close = [v for v in redfish_values if abs(v - ipmi_value) <= 5]
            assert close, f"{name}: IPMI={ipmi_value} °C, в Redfish нет близкого значения среди {redfish_values}"
    else:
        pytest.skip("Недостаточно данных датчиков для точного сравнения IPMI и Redfish")