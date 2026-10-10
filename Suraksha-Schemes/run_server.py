#!/usr/bin/env python3
"""
Start the Suraksha WhatsApp RAG Server
Usage:
  # Development (with auto-reload)
  python run_server.py

  # Production
  python run_server.py --prod
"""
import sys
import uvicorn

if __name__ == "__main__":
    is_prod = "--prod" in sys.argv
    
    uvicorn.run(
        "src.whatsapp_server:app",
        host="0.0.0.0",
        port=8000,
        reload=not is_prod,       # Hot-reload in dev
        log_level="info",
        access_log=True,
    )
