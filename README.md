<p align="center">
  <img src="logo.png" alt="Glow Browser Logo" width="220" style="border-radius: 20px;"/>
</p>

<h1 align="center">Glow Browser (v10.0)</h1>

<p align="center">
  A highly sandboxed, accountless, privacy-first desktop web browser built over 10 development iterations.
</p>

---

## 🔒 Advanced Security & Technical Architecture

* **Chromium WebEngine Backend:** Powered by the robust PyQt5 WebEngine rendering architecture.
* **Accountless & Zero-Telemetry:** Glow requires no user accounts or registration. To maximize data privacy, the local SQLite database backend strictly stores interface color settings and absolutely zero user browsing history, search metrics, or tracking metadata.
* **Network Privacy:** Single-layer standard VPN configuration utilizing open server protocols paired with built-in WebRTC leak protection via JavaScript injection.
* **Identity Spoofing:** Includes active browser fingerprinting protection and user-agent spoofing features to mask device identity from online trackers.
* **Hardened Sandbox Execution:** 
  * **Downloads Disabled:** File downloading capabilities are completely stripped out to prevent drive-by malware execution.
  * **Local File Access Blocked:** The browser is strictly blocked from opening or executing files from the host PC (`file://` protocols disabled), neutralising local directory traversal vulnerabilities.

## 📈 Project Evolution & Lifecycle
* **v1.0 – v3.0:** Core browser engine setup, tab rendering systems, and window frame architecture.
* **v4.0 – v7.0:** Integration of the sandboxed execution policy (disabling downloads/local files) and SQLite interface customisation (interactive UI setup).
* **v8.0 – v10.0:** Security implementation phase (Cookie sanitization, custom JavaScript hooks for VPN layers, and identity spoofing).

## 🚀 Future Roadmap
* Android companion application currently in active development using Android Studio.

---
*Developed by an independent high school software engineer. Protected under the GNU GPLv3 License.*
