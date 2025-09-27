import logging
from core.config import settings

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('app.log') if not settings.DISABLE_FILE_LOGGING else logging.NullHandler()
    ]
)
logger = logging.getLogger(__name__)