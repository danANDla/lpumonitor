import telebot
from telebot import types
import props
from datetime import datetime
import time, sched
from selenium import webdriver
import selenium.common.exceptions
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options

HEADLESS_MODE = True
LPU_URL = "https://onlinelpu.ru/gp111po111/record"
specialists = ["Эндокринолог", "Кардиолог"]
resps = {}

bot = None
token = props.token
bots_chat_id = props.bots_chat_id


class Ticket:
    def __init__(self, doctor: str, spec_id: int, tickets_number: int, closest: str):
        self.name = doctor
        self.spec = spec_id
        self.tickets = tickets_number
        self.closest = closest


def driver_init(headless: bool):
    options = Options()
    if headless:
        options.add_argument('-headless')
    options.add_argument('--no-sandbox')
    options.add_argument("--window-size=1920,1200")

    driver = webdriver.Chrome(options=options)
    return driver


def get_element_by_text(d, s: str):
    try:
        return d.find_element(By.XPATH, f"//*[contains(text(), '{s}')]")
    except selenium.common.exceptions.NoSuchElementException or selenium.common.exceptions.UnexpectedAlertPresentException:
        return None


def get_number_of_tickets(d):
    try:
        t = d.find_element(By.CLASS_NAME, "available")
        if t.text == '?':
            return 0
        return int(t.text)
    except selenium.common.exceptions.NoSuchElementException or selenium.common.exceptions.UnexpectedAlertPresentException:
        return 0


def notification(s: str):
    bot.send_message(bots_chat_id, s)
    print("NOTIFICATION: " + s)


def update_tickets(doctor: str, spec_id: int):
    t = doctor.split("\n")
    if len(t) < 2:
        return
    try:
        cached: Ticket = resps[t[0]]
    except KeyError:
        cached = None
    if t[1] == '?':
        pass  # resps[t[0]].append(Ticket(t[0], i, 0, ""))
    else:
        if cached is None or (cached.tickets < int(t[1])):
            spec = specialists[spec_id]
            notification(f"tickets number increased for {t[0]}, spec is {spec}")
        resps.update({t[0]: Ticket(t[0], spec_id, int(t[1]), t[2])})


def fetch_tickets(driver):
    open_all_text = "раскрыть все"
    try:
        driver.get(LPU_URL)
        try:
            WebDriverWait(driver, 4).until(
                EC.presence_of_element_located((By.XPATH, f"//*[contains(text(), '{open_all_text}')]")))
        except selenium.common.exceptions.TimeoutException:
            print("time out")
            pass
    except selenium.common.exceptions.InvalidArgumentException:
        return

    open_all = get_element_by_text(driver, open_all_text)
    if open_all is None:
        print("text not founded")
        return
    open_all.click()

    for i, spec in enumerate(specialists):
        try:
            l = driver.find_element(By.XPATH, f"//*[contains(text(), '{spec}')]/following-sibling::div")
            for ch in l.find_elements(By.XPATH, "*"):
                update_tickets(ch.text, i)

        except selenium.common.exceptions.NoSuchElementException or selenium.common.exceptions.UnexpectedAlertPresentException:
            continue


def print_sep():
    print("-------------")


def print_doctor(doc: Ticket):
    print(doc.name, doc.tickets, doc.closest)


def process(scheduler):
    # schedule the next call first
    print("ITERATION", str(datetime.now()))
    scheduler.enter(60, 1, process, (scheduler,))
    driver = driver_init(HEADLESS_MODE)
    fetch_tickets(driver)
    driver.quit()

    for i, spec in enumerate(specialists):
        print_sep()
        print(spec)
        for key in resps.keys():
            if resps[key].spec == i:
                print_doctor(resps[key])
        print_sep()
        print()


if __name__ == '__main__':
    bot = telebot.TeleBot(token)

    my_scheduler = sched.scheduler(time.time, time.sleep)
    my_scheduler.enter(2, 1, process, (my_scheduler,))
    my_scheduler.run()
