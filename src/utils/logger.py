import logging
import sys
from pathlib import Path

def setup_logger(name: str, log_file: str = None, level=logging.INFO):
    """
    Configura un logger que escribe en consola y opcionalmente en archivo.
    
    Args:
        name: Nombre del logger (usualmente __name__)
        log_file: Ruta del archivo donde guardar los logs (opcional)
        level: Nivel de logging (logging.DEBUG, logging.INFO, etc.)
    """
    # Formato: [FECHA - NIVEL - MODULO] MENSAJE
    formatter = logging.Formatter(
        fmt='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Evitar duplicar handlers si se llama varias veces
    if logger.hasHandlers():
        logger.handlers.clear()

    # 1. Handler para Consola (Terminal)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # 2. Handler para Archivo (Opcional)
    if log_file:
        # Asegurar que el directorio existe
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_path, encoding='utf-8')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger
