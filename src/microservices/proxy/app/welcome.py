from pathlib import Path
from string import Template

from app.config import settings

# Резолвим путь относительно файла модуля, а не os.getcwd() —
# работает и при запуске из IDE, и в Docker (WORKDIR /app), и из любого cwd.
TEMPLATE_PATH = Path(__file__).parent / "templates" / "welcome.html"

# Читаем один раз при импорте — файл статичный, нет смысла читать на каждый запрос.
WELCOME_TEMPLATE = Template(TEMPLATE_PATH.read_text(encoding="utf-8"))


def render_welcome() -> str:
    """Возвращает готовый HTML с подставленными значениями из Settings."""
    if settings.gradual_migration:
        movies_backend = f"migration {settings.movies_migration_percent}%"
    else:
        movies_backend = "monolith"

    return WELCOME_TEMPLATE.substitute(
        movies_backend=movies_backend,
        gradual_migration="enabled" if settings.gradual_migration else "disabled",
        migration_percent=settings.movies_migration_percent,
    )
