import logging
import time
from functools import wraps
from typing import Any, Callable, Optional

# 로거 설정
logger = logging.getLogger(__name__)


def setup_logging() -> None:
    """로깅 설정을 초기화합니다."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.FileHandler("imagesearch.log"), logging.StreamHandler()],
    )


def log_performance(func: Callable) -> Callable:
    """함수 실행 시간을 측정하고 로깅하는 데코레이터입니다."""

    @wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            duration = time.time() - start_time
            logger.info(f"{func.__name__} completed in {duration:.2f}s")
            return result
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"{func.__name__} failed after {duration:.2f}s: {e}")
            raise

    return wrapper


def log_embedding_generation(
    image_id: int, status: str, error: Optional[str] = None
) -> None:
    """임베딩 생성 상태를 로깅합니다."""
    if status == "processing":
        logger.info(f"Generating embedding for image {image_id}")
    elif status == "done":
        logger.info(f"Embedding generation completed for image {image_id}")
    elif status == "failed":
        logger.error(f"Embedding generation failed for image {image_id}: {error}")


def log_search_performance(query: str, duration: float, result_count: int) -> None:
    """검색 성능을 로깅합니다."""
    logger.info(
        f"Search completed for '{query}' in {duration:.2f}s, found {result_count} results"
    )


def log_api_usage(api_name: str, success: bool, error: Optional[str] = None) -> None:
    """API 사용량을 로깅합니다."""
    if success:
        logger.info(f"API {api_name} call successful")
    else:
        logger.error(f"API {api_name} call failed: {error}")
