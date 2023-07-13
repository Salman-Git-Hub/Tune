import logging
from logging import handlers


def init_discord_logger(filename: str = "discord.log", log_level: int = logging.INFO):
    discord_logger = logging.getLogger("discord")
    discord_logger.propagate = False
    discord_logger.setLevel(log_level)
    logging.getLogger('discord.http').setLevel(logging.INFO)
    handler = handlers.RotatingFileHandler(
        filename=filename,
        encoding='utf-8',
        maxBytes=1024 * 1024 * 5,  # 5 MiB
        backupCount=5
    )
    dt_fmt = '%Y-%m-%d %H:%M:%S'
    formatter = logging.Formatter('[{asctime}] [{levelname:<8}] {name}: {message}', dt_fmt, style='{')
    handler.setFormatter(formatter)
    discord_logger.addHandler(handler)
    return
