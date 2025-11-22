from pathlib import Path
from typing import Callable, Literal, TypedDict, Unpack
from urllib.parse import unquote_plus

import requests


class ImageDefaultContext(TypedDict):
    image_processor_variant: Literal["default"]


class ImageNaverCdnContext(TypedDict):
    image_processor_variant: Literal["cdn"]


class ImageFetchContext(TypedDict):
    image_processor_variant: Literal["fetch"]
    assets_directory: Path
    image_src_prefix: str


ImageContext = ImageDefaultContext | ImageNaverCdnContext | ImageFetchContext


def use_image_processor(context: ImageContext) -> Callable[[str], str]:
    match context["image_processor_variant"]:
        case "default":
            return _identity
        case "cdn":
            return _original_image_url
        case "fetch":
            return lambda src: _fetch_image_processor(src, **context)


def _identity(src: str) -> str:
    return src


def _original_image_url(src: str) -> str:
    return (
        src.split("?")[0]
        .replace("postfiles", "blogfiles")
        .replace(
            "https://mblogvideo-phinf.pstatic.net/", "https://blogfiles.pstatic.net/"
        )
    )


def _fetch_image_processor(src: str, **context: Unpack[ImageFetchContext]) -> str:
    assert context["assets_directory"].is_dir()

    url = _original_image_url(src)

    try:
        # User-Agent 및 Referer 헤더 추가
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': 'https://blog.naver.com/',
            'Accept': 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8',
        }

        response = requests.get(url, headers=headers, timeout=15, allow_redirects=True)
        response.raise_for_status()

        filename = unquote_plus(url.split("/")[-1])

        (context["assets_directory"] / filename).write_bytes(response.content)

        return f"{context['image_src_prefix']}{filename}"

    except requests.exceptions.RequestException as e:
        # 다운로드 실패 시 원본 URL 반환
        print(f"Warning: Failed to fetch image {url}: {e}. Using original URL.")
        return src
    except Exception as e:
        # 파일 쓰기 실패 등 기타 에러
        print(f"Warning: Error processing image {url}: {e}. Using original URL.")
        return src
