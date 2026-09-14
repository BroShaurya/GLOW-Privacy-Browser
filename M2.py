import sys
import os
import sqlite3
import urllib.parse
import urllib.request
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtWebEngineWidgets import *
from PyQt5 import QtNetwork

# --- ROBUST PATH FIXER FOR ONEDIR & ONEFILE ---
def resource_path(relative_path):
    try:
        # PyInstaller onefile temp folder
        base_path = sys._MEIPASS
    except Exception:
        # PyInstaller onedir or normal script execution
        if getattr(sys, 'frozen', False):
            base_path = os.path.dirname(sys.executable)
        else:
            base_path = os.path.abspath(".") 
    return os.path.join(base_path, relative_path)

class SmartUrlBar(QLineEdit):
    def focusInEvent(self, event):
        super().focusInEvent(event)
        self.selectAll() 
    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        self.selectAll()

class CustomWebEngineView(QWebEngineView):
    def wheelEvent(self, event):
        if QApplication.keyboardModifiers() == Qt.ControlModifier:
            if event.angleDelta().y() > 0:
                self.setZoomFactor(self.zoomFactor() + 0.15)
            else:
                self.setZoomFactor(max(0.25, self.zoomFactor() - 0.15))
        else:
            super().wheelEvent(event)

class MyBrowser(QMainWindow):
    def __init__(self):
        super(MyBrowser, self).__init__()
        
        self.webrtc_blocked = False 
        self.vpn_enabled = False 
        self.setWindowTitle('Glow') 
        
        # --- SET APP WINDOW ICON ---
        icon_path = resource_path("2GX_LOGO.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        
        self.init_db()

        # --- UI SETUP ---
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self.close_current_tab)
        self.setCentralWidget(self.tabs)

        self.navbar = QToolBar()
        self.navbar.setMovable(True) 
        self.addToolBar(self.navbar)

        for icon, slot in [("\u2B98", lambda: self.tabs.currentWidget().back()), 
                           ("\u2B9A", lambda: self.tabs.currentWidget().forward()), 
                           ('\u27F3', lambda: self.tabs.currentWidget().reload())]:
            action = QAction(icon, self)
            action.triggered.connect(slot)
            self.navbar.addAction(action)

        home_btn = QAction('Home', self)
        home_btn.triggered.connect(self.navigate_home)
        self.navbar.addAction(home_btn)

        newTab_btn = QAction('+', self)
        newTab_btn.triggered.connect(lambda: self.add_newTab())
        self.navbar.addAction(newTab_btn)

        self.menu_btn = QToolButton()
        self.menu_btn.setText("⋮")
        self.menu_btn.setPopupMode(QToolButton.InstantPopup)
        self.navbar.addWidget(self.menu_btn)

        self.url_bar = SmartUrlBar()
        self.url_bar.setPlaceholderText('Enter URL or search...')
        self.url_bar.returnPressed.connect(self.navigate_to_url)
        self.navbar.addWidget(self.url_bar)
        
        # --- FIXED HOME URL PATH ---
        self.home_url = QUrl.fromLocalFile(resource_path("home2.html"))
        self.tabs.currentChanged.connect(self.update_menu)
        
        self.zoom_in_shortcut = QShortcut(QKeySequence("Ctrl++"), self)
        self.zoom_in_shortcut.activated.connect(self.zoom_in)
        
        self.zoom_in_alt_shortcut = QShortcut(QKeySequence("Ctrl+="), self)
        self.zoom_in_alt_shortcut.activated.connect(self.zoom_in)
        
        self.zoom_out_shortcut = QShortcut(QKeySequence("Ctrl+-"), self)
        self.zoom_out_shortcut.activated.connect(self.zoom_out)
        
        self.zoom_reset_shortcut = QShortcut(QKeySequence("Ctrl+0"), self)
        self.zoom_reset_shortcut.activated.connect(self.zoom_reset)
        
        self.apply_last_saved_color() 
        self.add_newTab()
        self.showMaximized()

    def zoom_in(self):
        browser = self.tabs.currentWidget()
        if browser: browser.setZoomFactor(browser.zoomFactor() + 0.15)

    def zoom_out(self):
        browser = self.tabs.currentWidget()
        if browser: browser.setZoomFactor(max(0.25, browser.zoomFactor() - 0.15))

    def zoom_reset(self):
        browser = self.tabs.currentWidget()
        if browser: browser.setZoomFactor(1.0) 

    # --- SMART HTTPS PROXY TESTER & VPN TOGGLE ---
    def toggle_vpn(self):
        self.vpn_enabled = not self.vpn_enabled

        if self.vpn_enabled:
            current_tab = self.tabs.currentWidget()
            if current_tab:
                current_tab.page().runJavaScript("console.log('Searching for a stable HTTPS-compatible proxy...');")
            
            proxy_endpoint = None
            try:
                # Request elite proxies that support SSL/HTTPS
                api_url = "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http&timeout=2000&country=all&ssl=yes&anonymity=elite"
                req = urllib.request.urlopen(api_url, timeout=3)
                proxies = req.read().decode('utf-8').strip().split('\r\n')
                
                # Test up to the top 15 proxies to find one that handles secure traffic
                for p in proxies[:15]:
                    p = p.strip()
                    if p and ":" in p and len(p.split(":")) == 2:
                        try:
                            proxy_handler = urllib.request.ProxyHandler({'http': p, 'https': p})
                            opener = urllib.request.build_opener(proxy_handler)
                            test_req = opener.open("https://www.google.com", timeout=2)
                            if test_req.code == 200:
                                proxy_endpoint = p
                                break # Found a working HTTPS proxy!
                        except:
                            continue # Try next proxy if this one fails
            except Exception as e:
                print(f"Proxy search error: {e}")

            if proxy_endpoint:
                os.environ['http_proxy'] = f"http://{proxy_endpoint}"
                os.environ['https_proxy'] = f"http://{proxy_endpoint}"
                
                proxy_host, proxy_port = proxy_endpoint.split(":")
                proxy = QtNetwork.QNetworkProxy()
                proxy.setType(QtNetwork.QNetworkProxy.HttpProxy)
                proxy.setHostName(proxy_host)
                proxy.setPort(int(proxy_port))
                QtNetwork.QNetworkProxy.setApplicationProxy(proxy)
                print(f"VPN Active via verified HTTPS Proxy: {proxy_endpoint}")
            else:
                self.vpn_enabled = False
                print("Could not find a stable HTTPS proxy. VPN remains OFF.")
                if current_tab:
                    current_tab.page().runJavaScript("alert('No stable HTTPS proxy found. VPN is OFF. Try turning it on again.');")
                return

            if not self.webrtc_blocked:
                self.toggle_webrtc()
        else:
            os.environ.pop('http_proxy', None)
            os.environ.pop('https_proxy', None)
            QtNetwork.QNetworkProxy.setApplicationProxy(QtNetwork.QNetworkProxy(QtNetwork.QNetworkProxy.NoProxy))
            print("VPN Deactivated (Direct Connection)")

        for i in range(self.tabs.count()):
            self.tabs.widget(i).reload()
            
        self.update_menu(self.tabs.currentIndex())

    def toggle_webrtc(self):
        self.webrtc_blocked = not self.webrtc_blocked
        for i in range(self.tabs.count()):
            browser = self.tabs.widget(i)
            browser.settings().setAttribute(QWebEngineSettings.WebRTCPublicInterfacesOnly, self.webrtc_blocked)
            self.setup_stealth_script(browser)
            browser.reload()
        self.update_menu(self.tabs.currentIndex())

    def setup_stealth_script(self, browser):
        browser.page().scripts().clear()
        if self.webrtc_blocked:
            s = QWebEngineScript()
            s.setName("webrtc_stealth")
            s.setInjectionPoint(QWebEngineScript.DocumentCreation)
            s.setWorldId(QWebEngineScript.MainWorld)
            s.setRunsOnSubFrames(True)
            js_code = """
                ['RTCPeerConnection', 'webkitRTCPeerConnection', 'mozRTCPeerConnection'].forEach(function(name) {
                    if (window[name]) {
                        window[name] = function() {
                            return {
                                createDataChannel: function() {},
                                createOffer: function() {},
                                setLocalDescription: function() {},
                                close: function() {}
                            };
                        };
                    }
                });
            """
            s.setSourceCode(js_code)
            browser.page().scripts().insert(s)

    def pick_new_color(self):
        color = QColorDialog.getColor()
        if color.isValid(): self.apply_and_save_color(color.name())

    def apply_and_save_color(self, hex_color):
        base_color = QColor(hex_color)
        r, g, b = base_color.red(), base_color.green(), base_color.blue()
        brightness = (r * 299 + g * 587 + b * 114) / 1000
        is_dark = brightness < 128
        
        if is_dark:
            bg, surface, active, hover, border = base_color.name(), base_color.lighter(135).name(), base_color.lighter(170).name(), base_color.lighter(200).name(), base_color.lighter(160).name()
            text, active_text = "#FFFFFF", "#FFFFFF"
        else:
            bg, surface, active, hover, border = base_color.name(), base_color.darker(115).name(), "#FFFFFF", base_color.darker(125).name(), base_color.darker(140).name()
            text, active_text = "#222222", "#000000"    

        master_style = f"""
            QMainWindow, QTabWidget, QTabWidget::pane {{ background-color: {bg}; border: none; }}
            QTabBar {{ background-color: {bg}; }}
            QToolBar {{ background-color: {bg}; spacing: 12px; padding: 10px; border-bottom: 2px solid {border}; }}
            QToolButton {{ font-size: 26px; font-weight: bold; color: {text}; background-color: {surface}; padding: 8px 16px; border: 2px solid {border}; border-radius: 8px; }}
            QToolButton:hover {{ background-color: {hover}; border: 2px solid {text}; }}
            QToolButton::menu-indicator {{ image: none; }}
            QLineEdit {{ font-size: 18px; padding: 10px 18px; border: 2px solid {border}; border-radius: 20px; background-color: {surface}; color: {text}; }}
            QLineEdit:focus {{ border: 2px solid {text}; background-color: {active}; color: {active_text}; }}
            QTabBar::tab {{ font-size: 18px; padding: 12px 20px; min-width: 150px; background-color: {surface}; color: {text}; border: 2px solid {border}; border-bottom: none; border-top-left-radius: 12px; border-top-right-radius: 12px; margin-top: 5px; margin-right: 4px; }}
            QTabBar::tab:selected {{ background-color: {active}; color: {active_text}; font-weight: bold; border: 2px solid {text}; border-bottom: none; margin-top: 0px; }}
            QTabBar::tab:hover:!selected {{ background-color: {hover}; border: 2px solid {text}; border-bottom: none; }}
        """
        self.setStyleSheet(master_style)

        browser = self.tabs.currentWidget()
        if browser:
            browser.page().runJavaScript(f"if(window.changeBgColor) {{ changeBgColor('{hex_color}'); }}")

        with sqlite3.connect('color_history.db') as conn:
            conn.execute("INSERT OR REPLACE INTO color_log (id, hex_value) VALUES (1, ?)", (hex_color,))
            conn.commit()

    def apply_last_saved_color(self):
        try:
            with sqlite3.connect('color_history.db') as conn:
                res = conn.execute("SELECT hex_value FROM color_log WHERE id = 1").fetchone()
                if res: self.apply_and_save_color(res[0])
                else: self.apply_and_save_color("#F0F0F0") 
        except: 
            self.apply_and_save_color("#F0F0F0")

    def add_newTab(self, qurl=None):
        browser = CustomWebEngineView()
        browser.page().setBackgroundColor(Qt.transparent)
        browser.setZoomFactor(1.00)
        
        browser.urlChanged.connect(lambda q: self.update_url_bar(q, browser))
        browser.urlChanged.connect(lambda q: self.update_tab_title(q, browser))
        browser.loadFinished.connect(self.block_ads)
        browser.loadFinished.connect(lambda ok, b=browser: self.apply_color_to_browser(ok, b))
        
        browser.settings().setAttribute(QWebEngineSettings.WebRTCPublicInterfacesOnly, self.webrtc_blocked)
        self.setup_stealth_script(browser)

        browser.setUrl(qurl if qurl else self.home_url)
        i = self.tabs.addTab(browser, "New Tab")
        self.tabs.setCurrentIndex(i)

    def apply_color_to_browser(self, ok, browser):
        if not ok: return
        if browser.url().isLocalFile():
            try:
                with sqlite3.connect('color_history.db') as conn:
                    res = conn.execute("SELECT hex_value FROM color_log WHERE id = 1").fetchone()
                    if res:
                        hex_color = res[0]
                        browser.page().runJavaScript(f"if(window.changeBgColor) {{ changeBgColor('{hex_color}'); }}")
            except: pass

    def update_tab_title(self, q, browser):
        index = self.tabs.indexOf(browser)
        if index == -1: return
        if q.isLocalFile():
            self.tabs.setTabText(index, "Home")
            return
        full_url = q.toString()
        parsed = urllib.parse.urlparse(full_url)
        if "google.com" in parsed.netloc and "/search" in parsed.path:
            queries = urllib.parse.parse_qs(parsed.query)
            display_text = "Google Search"
            for key in ['q', 'text', 'query']:
                if key in queries:
                    display_text = queries[key][0]
                    break
        else:
            display_text = parsed.netloc.replace("www.", "")
        if len(display_text) > 22: display_text = display_text[:19] + "..."
        self.tabs.setTabText(index, display_text)

    def update_url_bar(self, q, browser):
        if browser != self.tabs.currentWidget(): return
        if q.isLocalFile(): self.url_bar.setText("")
        else: self.url_bar.setText(q.toString())

    def update_menu(self, index):
        self.menu = QMenu(self)
        self.menu.addAction("🎨 Customize Background").triggered.connect(self.pick_new_color)
        self.menu.addSeparator()
        
        vpn_status = "🌐 VPN: ON" if self.vpn_enabled else "🌐 VPN: OFF"
        self.menu.addAction(vpn_status).triggered.connect(self.toggle_vpn)
        
        status = "🛡️ WebRTC: Enabled" if self.webrtc_blocked else "🔓 WebRTC: Disabled"
        self.menu.addAction(status).triggered.connect(self.toggle_webrtc)
        
        self.menu.addSeparator()
        privacy_action = self.menu.addAction("Privacy Policy")
        privacy_action.triggered.connect(lambda: self.load_content("DISCLAIMER AND TERMS OF USE.html", is_local=True))     
        self.menu_btn.setMenu(self.menu)

    def load_content(self, path_or_url, is_local=True):
        current_tab = self.tabs.currentWidget()
        if not current_tab: return
        url = QUrl.fromLocalFile(resource_path(path_or_url)) if is_local else QUrl(path_or_url)
        current_tab.setUrl(url)

    def navigate_to_url(self):
        text = self.url_bar.text().strip()
        if not text: return
        if "." in text and " " not in text:
            url = text if text.startswith(("http://", "https://")) else "https://" + text
        else:
            url = "https://google.com/search?q=" + urllib.parse.quote(text)
        self.tabs.currentWidget().setUrl(QUrl(url))

    def navigate_home(self): self.tabs.currentWidget().setUrl(self.home_url)
    def close_current_tab(self, i): 
        if self.tabs.count() > 1: self.tabs.removeTab(i)
        else: self.tabs.currentWidget().setUrl(self.home_url)

    def init_db(self):
        with sqlite3.connect('color_history.db') as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS color_log (id INTEGER PRIMARY KEY, hex_value TEXT)")

    def block_ads(self):
       browser = self.sender() 
       if not browser: return
       script = """
                (function() {
                    if (window.isAdBlockerRunning) return;
                    window.isAdBlockerRunning = true;
                    const adSelectors = ['.ads', '.ad', '#ad', '.ad-box', '.ad-container', '.ad-unit', '[id^="google_ads"]', 'ins.adsbygoogle', 'div[data-ad-unit]', 'aside[class*="ad"]', 'ytd-ad-slot-renderer', '.ytp-ad-overlay-container', 'sponsored'];
                    const cleanPage = () => {
                        adSelectors.forEach(s => { document.querySelectorAll(s).forEach(el => { el.style.setProperty('display', 'none', 'important'); }); });
                        const video = document.querySelector('video');
                        if (video && document.querySelector('.ad-showing')) { video.currentTime = video.duration || 0; }
                        const skip = document.querySelector('.ytp-ad-skip-button, .ytp-skip-ad-button');
                        if (skip) skip.click();
                    };
                    const observer = new MutationObserver(cleanPage);
                    observer.observe(document.documentElement, { childList: true, subtree: true });
                    cleanPage();
                })();
                """
       browser.page().runJavaScript(script)

if __name__ == "__main__":
    sys.argv.append("--force-webrtc-ip-handling-policy=disable_non_proxied_udp")
    app = QApplication(sys.argv)
    
    profile = QWebEngineProfile.defaultProfile()
    profile.setHttpUserAgent("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Gecko/120.0.0.0 Safari/537.36")
    
    settings = QWebEngineSettings.globalSettings()
    settings.setAttribute(QWebEngineSettings.JavascriptEnabled, True)
    settings.setAttribute(QWebEngineSettings.LocalStorageEnabled, True)
    settings.setAttribute(QWebEngineSettings.WebGLEnabled, True)
    settings.setAttribute(QWebEngineSettings.AllowRunningInsecureContent, False)
    
    window = MyBrowser()
    window.show()
    sys.exit(app.exec_())
