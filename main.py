import dotenv

dotenv.load_dotenv()

import uvicorn

from app.config import Settings
from app.server import create_app

app = create_app()


def main():
    settings = Settings()
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=True,
        env_file=".env",
    )


if __name__ == "__main__":
    main()
