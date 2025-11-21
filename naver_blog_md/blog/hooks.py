import re
from math import ceil
from typing import Iterator, Unpack

import requests
from bs4 import BeautifulSoup, Tag

from naver_blog_md.blog import components as Components
from naver_blog_md.blog import metadata as Metadata
from naver_blog_md.blog.models import PostItem, PostListResponse
from naver_blog_md.fp.lazy_val import lazy_val
from naver_blog_md.markdown.context import MarkdownRenderContext
from naver_blog_md.markdown.models import Block, ImageBlock, ImageGroupBlock, MaterialBlock
from naver_blog_md.markdown.render import blocks_as_markdown
from naver_blog_md.multiprocess.pool import use_map


def use_post(blog_id: str, log_no: int):

    @lazy_val
    def root() -> Tag:
        response = requests.get(
            "https://blog.naver.com/PostView.naver",
            params={"blogId": blog_id, "logNo": log_no},
        )
        return BeautifulSoup(
            _remove_unicode_special_characters(response.text), "html.parser"
        )

    @lazy_val
    def preview_image():
        return _first_image_of_blocks(as_blocks())

    def metadata():
        return Metadata.metadata(
            root(), Metadata.tags(blog_id, log_no), preview_image()
        )

    def as_blocks() -> Iterator[Block]:
        for component in root().select(".se-main-container .se-component"):
            match component["class"][1]:
                case "se-sectionTitle":
                    yield Components.section_title_component(component)
                case "se-image":
                    yield Components.image_component(component)
                case "se-imageGroup":
                    yield Components.image_group_component(component)
                case "se-imageStrip":  # 이미지 스트립 처리 추가
                    yield Components.image_strip_component(component)
                case "se-placesMap":
                    pass
                case "se-quotation":  # 인용구 처리 추가
                    yield Components.quotation_component(component)
                case "se-code":  # 코드 블록 처리 추가
                    yield Components.code_component(component)
                case "se-file":
                    yield Components.file_component(component)
                case "se-horizontalLine":  # 수평선 처리 추가
                    yield Components.horizontal_line_component(component)
                case "se-table":  # 테이블 처리 추가
                    yield Components.table_component(component)
                case "se-text":
                    yield from Components.text_component(component)
                case "se-material":  # Material 처리 추가
                    yield Components.material_component(component)
                case 'se-sticker':
                    pass
                case "se-oglink":
                    pass
                case 'se-oembed':
                    # oembed (YouTube, Twitter 등)를 링크로 변환
                    oembed_data = component.get('data', {})
                    url = oembed_data.get('url') or oembed_data.get('originalUrl')

                    if url:
                        # 링크를 마크다운 텍스트로 변환
                        title = oembed_data.get('title', 'Embedded Content')
                        # TextBlock 형태로 변환하여 yield
                        text_component = {
                            'componentType': 'text',
                            'data': {
                                'text': f'[{title}]({url})\n'
                            }
                        }
                        yield MaterialBlock(text_component)
                case "se-wrappingParagraph":
                    yield Components.wrapping_paragraph_component(component)
                case "se-formula":
                    yield Components.formula_component(component)
                case unknown:
                    raise ValueError(f"Unknown component type: {unknown}")

    def as_markdown(**context: Unpack[MarkdownRenderContext]):
        return blocks_as_markdown(as_blocks(), metadata(), **context)

    return (
        metadata,
        as_markdown,
        as_blocks,
    )


def _first_image_of_blocks(blocks: Iterator[Block]) -> ImageBlock | None:
    try:
        block = next(blocks)
    except StopIteration:
        return None

    match block:
        case ImageBlock(src, alt):
            return ImageBlock(src, alt)
        case ImageGroupBlock(images):
            return ImageBlock(images[0].src, images[0].alt)
        case _:
            return _first_image_of_blocks(blocks)


def use_blog(blog_id: str):
    @lazy_val
    def posts() -> list[PostItem]:
        # 첫 페이지로 실제 총 개수 확인
        first_response = _post_title_list(blog_id, count_per_page=30)  # 페이지당 개수 늘리기

        total_count = first_response.total_count
        count_per_page = first_response.count_per_page

        print(f"Total posts: {total_count}, Count per page: {count_per_page}")

        # 포스트가 없는 경우
        if total_count == 0:
            return []

        # 총 페이지 수 계산
        total_pages = ceil(total_count / count_per_page)

        print(f"Need to fetch {total_pages} pages")

        # 페이지가 1개면 첫 페이지만 반환
        if total_pages == 1:
            return first_response.post_list

        map = use_map(8)

        # 2페이지부터 마지막 페이지까지
        remaining_pages = map(
            lambda page_number: _fetch_page_safe(blog_id, page_number, count_per_page),
            range(2, total_pages + 1),
        )

        # 결과 합치기
        all_posts = first_response.post_list + [
            item
            for items in remaining_pages
            for item in items
        ]

        print(f"Fetched total {len(all_posts)} posts")

        return all_posts

    return (posts,)


def _fetch_page_safe(blog_id: str, page_number: int, count_per_page: int) -> list[PostItem]:
    """페이지를 안전하게 가져오는 헬퍼 함수"""
    try:
        response = _post_title_list(blog_id, page_number, count_per_page=count_per_page)
        return response.post_list
    except Exception as e:
        print(f"Failed to fetch page {page_number}: {e}")
        return []


def _post_title_list(
    blog_id: str, current_page: int = 1, category_no: int = 0, count_per_page: int = 30
):
    response = requests.get(
        "https://blog.naver.com/PostTitleListAsync.naver",
        params={
            "blogId": blog_id,
            "currentPage": current_page,
            "categoryNo": category_no,
            "countPerPage": count_per_page,
        },
    )

    response_text = response.text

    # pagingHtml 제거
    if ',"pagingHtml"' in response_text:
        response_text = response_text.split(',"pagingHtml"')[0] + "}"

    return PostListResponse.model_validate_json(response_text)


def _remove_unicode_special_characters(text: str):
    pattern = r"[\u0000-\u0008\u000b-\u000c\u000e-\u001f\u007f-\u009f\u00ad\u0600-\u0604\u070f\u17b4\u17b5\u200b-\u200f\u2028-\u202f\u2060-\u206f\ufeff\ufff0-\uffff]"
    cleaned_text = re.sub(pattern, "", text)

    return cleaned_text
