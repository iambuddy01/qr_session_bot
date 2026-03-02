import asyncio
from utils.qr_login import generate_qr_session

if __name__ == "__main__":
    asyncio.run(generate_qr_session())
