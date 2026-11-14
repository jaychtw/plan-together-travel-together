"""Exercise the actual UI with two isolated browser sessions."""
from playwright.sync_api import expect, sync_playwright

with sync_playwright() as driver:
    browser = driver.chromium.launch()
    a, b = browser.new_page(), browser.new_page(viewport={"width": 390, "height": 844})
    for page in (a, b):
        page.goto("http://127.0.0.1:8000")
    a.get_by_role("button", name="Create New Project").click()
    a.get_by_role("button", name="Generate a random code").click()
    code = a.get_by_label("Project code").input_value()
    assert len(code) == 12
    a.get_by_role("button", name="Continue").click()
    a.get_by_label("Your display name").fill("Alex")
    a.get_by_role("button", name="Open workspace").click()
    b.get_by_role("button", name="繁體中文").click()
    b.get_by_role("button", name="進入現有專案").click()
    b.get_by_label("專案代碼").fill(code.lower())
    b.get_by_role("button", name="繼續").click()
    b.get_by_label("你的顯示名稱").fill("小明")
    b.get_by_role("button", name="開啟工作區").click()
    for page, title, save in [(a, "Train tickets", "Save card"), (b, "逛夜市", "儲存卡片")]:
        page.locator("#title").fill(title)
        page.get_by_role("button", name=save).click()
    for page in (a, b):
        expect(page.locator("#cards li")).to_have_count(2)
        expect(page.locator("#cards")).to_contain_text("小明")
        expect(page.locator("#cards")).to_contain_text("Alex")
    b.reload()
    expect(b.locator("#member")).to_contain_text("小明")
    expect(b.locator("#cards")).to_contain_text("Train tickets")
    browser.close()
