#!/usr/bin/env python3
"""
START SCRIPT — Choose what to run
===================================
Run this to pick what you want to launch:
    python start.py
"""
import subprocess, sys

print("""
╔══════════════════════════════════════════╗
║   🪷 Pushti Sahayak — Launcher          ║
║   Jai Shri Krishna 🙏                   ║
╠══════════════════════════════════════════╣
║  1. Admin Panel  (manage books & AI)    ║
║  2. Chat App     (for Vaishnavs)        ║
║  3. Run Full Pipeline (process + embed) ║
╚══════════════════════════════════════════╝
""")

choice = input("Enter 1, 2, or 3: ").strip()

if choice == "1":
    print("🚀 Starting Admin Panel at http://localhost:8501")
    subprocess.run([sys.executable, "-m", "streamlit", "run", "admin_panel.py", "--server.port", "8501"])

elif choice == "2":
    print("🚀 Starting Chat App at http://localhost:8502")
    subprocess.run([sys.executable, "-m", "streamlit", "run", "chat_app.py", "--server.port", "8502"])

elif choice == "3":
    print("⚙️ Running full pipeline...")
    for script in ["1_ingest_data.py", "2_create_embeddings.py"]:
        print(f"\n▶ Running {script}...")
        result = subprocess.run([sys.executable, script])
        if result.returncode != 0:
            print(f"❌ {script} failed!")
            break
    else:
        print("\n✅ Pipeline complete! Run option 1 or 2 to use your AI.")
else:
    print("Invalid choice. Please enter 1, 2, or 3.")
