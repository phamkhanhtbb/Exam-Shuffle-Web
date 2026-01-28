import os
from dataclasses import dataclass
from dotenv import load_dotenv

# Load biến môi trường từ file .env
load_dotenv()


@dataclass(frozen=True)
class Settings:
    # Thông tin xác thực AWS
    aws_access_key_id: str
    aws_secret_access_key: str

    # Thông tin hạ tầng
    region: str
    queue_url: str
    table_name: str
    bucket_input: str
    bucket_output: str

    # Cấu hình xử lý (có giá trị mặc định)
    visibility_timeout: int = 120
    heartbeat_seconds: int = 30
    max_attempts: int = 5
    presign_expires_in: int = 3600


def _require_env(name: str) -> str:
    """Bắt buộc phải có biến môi trường, nếu thiếu sẽ báo lỗi ngay"""
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"❌ Thiếu biến môi trường bắt buộc: {name}")
    return value


def load_settings() -> Settings:
    def _env_int(name: str, default: int) -> int:
        raw = os.getenv(name)
        return int(raw) if raw else default

    return Settings(
        aws_access_key_id=_require_env('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=_require_env('AWS_SECRET_ACCESS_KEY'),
        region=_require_env('AWS_REGION'),
        queue_url=_require_env('AWS_SQS_QUEUE_URL'),
        table_name=_require_env('AWS_DYNAMODB_TABLE'),
        bucket_input=_require_env('AWS_S3_BUCKET_INPUT'),
        bucket_output=_require_env('AWS_S3_BUCKET_OUTPUT'),
        visibility_timeout=_env_int('VISIBILITY_TIMEOUT', 120),
        heartbeat_seconds=_env_int('HEARTBEAT_SECONDS', 30),
        max_attempts=_env_int('MAX_ATTEMPTS', 5),
        presign_expires_in=_env_int('PRESIGN_EXPIRES_IN', 3600),
    )


# Khởi tạo settings để các file khác import dùng luôn
settings = load_settings()