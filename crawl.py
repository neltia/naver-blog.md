from pathlib import Path
from typing import Any
from datetime import datetime
import time
import re
from naver_blog_md import (
    use_blog,
    use_post,
    with_fetched_local_images  # Fetch images into local directory while rendering
)


def crawl(blog_id: str, posts_directory: Path, assets_directory: Path):
    # 디렉토리가 없으면 생성
    posts_directory.mkdir(parents=True, exist_ok=True)
    assets_directory.mkdir(parents=True, exist_ok=True)

    (posts,) = use_blog(blog_id)

    for post in posts():
        try:
            # 파일명 미리 생성하여 존재 여부 확인
            metadata, as_markdown, _ = use_post(blog_id, post.log_no)
            filename = to_filename(metadata())
            markdown_file = posts_directory / f"{filename}.md"

            # 이미 파일이 존재하면 건너뛰기
            if markdown_file.exists():
                print(f"[*] Skipping: {filename}.md (already exists)")
                continue

            # 파일이 없으면 크롤링 진행
            post_assets_directory = assets_directory / filename
            post_assets_directory.mkdir(exist_ok=True)

            render_context = with_fetched_local_images(
                num_workers=8,
                assets_directory=post_assets_directory,
                image_src_prefix=f"assets/{filename}/",
            )

            markdown = as_markdown(**render_context)
            markdown_file.write_text(markdown, encoding='utf-8')
            print(f"[*] Saved: {filename}.md")

            time.sleep(0.2)

        except ValueError as e:
            if "Unknown component type" in str(e):
                print(f"[*]  Skipped post due to unsupported component: {e}")
                continue
            raise
        except OSError as e:
            if "Too many open files" in str(e):
                print("[*]  Too many files open, waiting 2 seconds...")
                time.sleep(2)  # 파일들이 닫힐 때까지 대기
                continue
            raise
        except Exception as e:
            print(f"[*] Error processing post {post.log_no}: {e}")
            continue


def to_filename(metadata: dict[Any, Any]) -> str:
    """
    메타데이터로부터 파일명 생성
    형식: YYYY-MM-DD-sanitized-title
    예: 2025-11-09-python-rss-llm-api
    """
    # 날짜 추출
    pub_date = metadata.get("pubDate")
    if isinstance(pub_date, datetime):
        date_str = pub_date.strftime("%Y-%m-%d")
    else:
        date_str = datetime.now().strftime("%Y-%m-%d")

    # 제목 추출 및 정제
    title = metadata.get("title", "untitled")
    sanitized = title.lower()
    sanitized = re.sub(r'[^\w\s가-힣-]', ' ', sanitized)
    sanitized = re.sub(r'\s+', '-', sanitized.strip())
    sanitized = re.sub(r'-+', '-', sanitized)

    # 파일명 길이 제한
    max_length = 100
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length].rsplit('-', 1)[0]

    filename = f"{date_str}-{sanitized}"
    return filename


if __name__ == "__main__":
    from dotenv import load_dotenv
    import os

    load_dotenv()

    blog_id = os.getenv("NAVER_BLOG_ID", "")
    crawl(blog_id, Path("posts"), Path("assets"))
