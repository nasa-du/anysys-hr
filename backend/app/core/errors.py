import logging
from typing import Any

from fastapi import Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


def translate_validation_error(error: dict[str, Any]) -> str:
    """Translate a Pydantic validation error into a user-facing Chinese message."""
    error_type = str(error.get("type", ""))
    original_message = str(error.get("msg", ""))
    context: dict[str, Any] = error.get("ctx") or {}

    if error_type == "missing":
        return "此字段为必填项"
    if error_type == "string_too_short":
        return f"长度不能少于 {context.get('min_length', 1)} 个字符"
    if error_type == "string_too_long":
        return f"长度不能超过 {context.get('max_length')} 个字符"
    if error_type in {"string_type", "string_unicode", "bytes_type"}:
        return "请输入文本"
    if error_type == "value_error" and "email address" in original_message:
        return "请输入有效的邮箱地址"
    if error_type in {"uuid_parsing", "uuid_type"}:
        return "请输入有效的 UUID"
    if error_type in {"int_parsing", "int_type"}:
        return "请输入有效的整数"
    if error_type in {"float_parsing", "float_type"}:
        return "请输入有效的数字"
    if error_type in {"bool_parsing", "bool_type"}:
        return "请输入有效的布尔值"
    if error_type in {"list_type", "tuple_type", "set_type"}:
        return "请输入列表"
    if error_type == "greater_than_equal":
        return f"不能小于 {context.get('ge')}"
    if error_type == "greater_than":
        return f"必须大于 {context.get('gt')}"
    if error_type == "less_than_equal":
        return f"不能大于 {context.get('le')}"
    if error_type == "less_than":
        return f"必须小于 {context.get('lt')}"
    if error_type in {"dict_type", "model_type"}:
        return "输入格式不正确"
    if error_type == "json_invalid":
        return "请求内容不是有效的 JSON"
    return "输入值无效"


async def validation_exception_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    assert isinstance(exc, RequestValidationError)
    logger.info(
        "Request validation failed for %s %s: %s",
        request.method,
        request.url.path,
        [
            {
                "loc": error.get("loc"),
                "type": error.get("type"),
                "msg": error.get("msg"),
                "ctx": error.get("ctx"),
            }
            for error in exc.errors()
        ],
    )
    errors = []
    for error in exc.errors():
        translated_error = dict(error)
        translated_error["msg"] = translate_validation_error(error)
        errors.append(translated_error)
    return JSONResponse(
        status_code=422,
        content={"detail": jsonable_encoder(errors)},
    )
