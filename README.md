# 🔐 Secure WireGuard VPN Project

A simple and secure **VPN system** built using the **WireGuard protocol**, designed for learning and demonstration of **networking, VPN architecture, and encrypted communication**.

This project focuses on **VPN setup, routing, firewall configuration, cloud deployment, and traffic verification**, rather than implementing cryptographic algorithms from scratch.

---

## 📌 Project Overview

- Built a **secure VPN tunnel** using WireGuard
- Enabled **encrypted communication** between client and server
- Verified encrypted traffic using **tcpdump / Wireshark**
- Supported **mobile clients** via QR-code based configuration
- Tested on **local systems and cloud environments**
- Designed for **academic and learning purposes**

---

## 🧠 What This Project Demonstrates

- VPN architecture and working principles
- Secure tunneling using modern cryptography
- IP forwarding and NAT configuration
- Firewall rule management using `iptables`
- Cloud-based VPN deployment concepts
- Packet-level verification of encryption

---

## 🔐 Security & Cryptography (Used by WireGuard)

This project uses the **WireGuard VPN protocol**, which internally provides:

- **Encryption:** ChaCha20-Poly1305  
- **Key Exchange:** Curve25519 (Elliptic Curve Diffie-Hellman)  
- **Authentication:** Poly1305 MAC  
- **Key Derivation:** HKDF  
- **Protocol Framework:** Noise Protocol Framework  

⚠️ **Note:**  
The cryptographic algorithms are **provided by WireGuard**. This project does **not implement encryption algorithms manually**, but configures and uses them securely.


📁 Project Structure
secure-wireguard-vpn/
│
├── setup-phone-vpn.sh
│   └─ Shell script to configure WireGuard server,
│      generate keys, start VPN, and display QR code
│
├── simple_vpn.sh
│   └─ Minimal VPN setup script for quick testing
│
├── vpn-lab.py
│   └─ Python-based helper/CLI for managing VPN namespaces
│
├── config/
│   └─ WireGuard configuration files (wg0.conf, client configs)
│
├── keys/
│   └─ Server-side WireGuard keys (demo / regenerated keys)
│
├── phone-keys/
│   └─ Client (mobile) WireGuard keys
│
├── docs/
│   └─ Project documentation and tutorial files
│
├── src/
│   └─ Source code related to VPN logic and automation
│
├── tests/
│   └─ Test scripts and validation files
│
├── venv/
│   └─ Python virtual environment (if Python tools are used)
│
└── README.md
    └─ Project overview, setup instructions, and explanation


---

## ▶️ How to Run the Project

### 1️⃣ Navigate to project directory
```bash
cd /opt/vpn-lab

2️⃣ Make scripts executable (one-time)

chmod +x setup-phone-vpn.sh simple_vpn.sh

3️⃣ Start VPN and generate QR code

sudo ./setup-phone-vpn.sh

This will:

    Generate keys

    Configure WireGuard

    Start the VPN server

    Display a QR code for mobile client setup

📱 Mobile Client Setup (QR Code)

    Install WireGuard app on Android / iOS

    Open the app

    Tap Add Tunnel → Scan from QR code

    Scan the QR code shown in terminal

    Toggle the tunnel ON

🧪 Verify Encrypted Traffic
Check VPN status

sudo wg show

Capture encrypted packets

sudo tcpdump -i eth0 udp port 51820

Expected result:

    Only encrypted UDP packets

    No readable HTTP / DNS traffic

🛑 Stop the VPN

sudo wg-quick down wg0

🎓 Academic Note

This repository may contain demo keys and configurations for learning purposes.

    In real-world production systems, private keys and sensitive configuration files should never be committed to public repositories and must be generated dynamically or stored securely.

🧩 Key Learning Outcomes

    Understanding VPN concepts and tunneling

    Practical exposure to WireGuard

    Linux networking and firewall rules

    Cloud vs local VPN deployment challenges

    Secure traffic verification techniques

📄 Resume Summary (Optional)

    Built a secure cloud-based VPN using WireGuard, configured routing and firewall rules, enabled mobile client access via QR codes, and verified encrypted traffic using packet analysis tools.

🏁 Conclusion

This project provides a hands-on understanding of VPN technology and demonstrates how secure communication is achieved using modern protocols and proper network configuration.
👤 Author

Hitesh Choudhary
📜 Disclaimer

This project is intended for educational and learning purposes only.


---

### ✅ What you should do now
1. Save this as `README.md`
2. Commit and push:
```bash
git add README.md
git commit -m "Add project README"
git push
