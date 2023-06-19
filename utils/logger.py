import logging
from logging import handlers


def init_discord_logger(filename: str = "discord.log", log_level: int = logging.INFO,
                        max_bytes: int = 10455040, backup_count: int = 5):
    discord_logger = logging.getLogger("discord")
    discord_logger.propagate = False
    discord_logger.setLevel(log_level)
    logging.getLogger('discord.http').setLevel(logging.INFO)
    handler = handlers.RotatingFileHandler(
        filename=filename,
        encoding='utf-8',
        maxBytes=max_bytes,  # 10 MiB
        backupCount=backup_count
    )
    dt_fmt = '%Y-%m-%d %H:%M:%S'
    formatter = logging.Formatter('[{asctime}] [{levelname:<8}] {name}: {message}', dt_fmt, style='{')
    handler.setFormatter(formatter)
    discord_logger.addHandler(handler)
    return


