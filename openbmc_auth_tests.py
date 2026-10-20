import os
import re
import time

import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.firefox.options import Options

BMC_URL = "https://localhost:2443"
USER = "root"
PASSWORD = "0penBmc"

LOCK_USER = "locktest"
LOCK_PASSWORD = "TestPass123"

WAIT = 15

@pytest.fixture
def driver():
    options = Options()
    options.add_argument("--ignore-certificate-errors")

    browser = webdriver.Firefox(options=options)
    browser.maximize_window()
    yield browser
    browser.quit()


def login(driver, username, password):
    driver.get(BMC_URL + "/#/login")

    wait = WebDriverWait(driver, WAIT)
    wait.until(EC.presence_of_element_located((By.ID, "username")))

    driver.find_element(By.ID, "username").send_keys(username)
    driver.find_element(By.ID, "password").send_keys(password)
    driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()


def wait_until_logged_in(driver):
    WebDriverWait(driver, WAIT).until(lambda d: "login" not in d.current_url)


def open_page(driver, path):
    driver.get(BMC_URL + path)
    time.sleep(3)


def test_login_success(driver):
    login(driver, USER, PASSWORD)
    wait_until_logged_in(driver)

    assert "login" not in driver.current_url


def test_login_wrong_password(driver):
    login(driver, USER, "wrong_password_123")
    time.sleep(3)

    assert "login" in driver.current_url


def test_account_lockout(driver):
    for _ in range(5):
        login(driver, LOCK_USER, "wrong_password_123")
        time.sleep(2)

    login(driver, LOCK_USER, LOCK_PASSWORD)
    time.sleep(3)

    assert "login" in driver.current_url


def test_inventory_is_displayed(driver):
    login(driver, USER, PASSWORD)
    wait_until_logged_in(driver)

    open_page(driver, "/#/hardware-status/inventory")
    page_text = driver.find_element(By.TAG_NAME, "body").text.lower()

    keywords = ["bmc manager", "dimm", "processor", "cpu", "fan", "power supply", "system"]
    found = [word for word in keywords if word in page_text]

    assert found, "На странице инвентаря не найдено ни одного компонента"


def test_temperature_in_range(driver):
    login(driver, USER, PASSWORD)
    wait_until_logged_in(driver)

    open_page(driver, "/#/hardware-status/sensors")
    page_text = driver.find_element(By.TAG_NAME, "body").text

    temperatures = [float(t) for t in re.findall(r"(-?\d+(?:\.\d+)?)\s*°C", page_text)]

    assert temperatures, "На странице датчиков не найдено значений температуры"
    for t in temperatures:
        assert 0 <= t <= 100, f"Температура {t} °C вне допустимого диапазона"