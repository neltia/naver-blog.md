from typing import Any, Iterator, Unpack

import yaml

from naver_blog_md.markdown.context import MarkdownRenderContext, with_default
from naver_blog_md.markdown.image import use_image_processor
from naver_blog_md.markdown.models import (
    Block,
    CodeBlock,
    FileBlock,
    HorizontalLineBlock,
    ImageBlock,
    ImageGroupBlock,
    ParagraphBlock,
    SectionTitleBlock,
    QuotationBlock,
    TableBlock,
    MaterialBlock,
    FormulaBlock
)
from naver_blog_md.multiprocess.pool import use_map


def blocks_as_markdown(
    blocks: Iterator[Block],
    front_matter: dict[Any, Any] | None = None,
    result: str = "",
    **context: Unpack[MarkdownRenderContext],
) -> str:

    if front_matter is not None and result == "":
        result = _front_matter_as_yaml(front_matter, **context)

    map = use_map(context["num_workers"])

    rendered_blocks = map(
        lambda block: _block_as_markdown(block, **context),
        blocks,
    )

    return (result + "".join(rendered_blocks)).strip() + "\n"


def _block_as_markdown(
    block: Block,
    **context: Unpack[MarkdownRenderContext],
) -> str:
    processed_image_src = _use_image_processor_with_fallback(**context)

    match block:
        case SectionTitleBlock(text):
            return f"## {text.strip()}\n\n"
        case ParagraphBlock(text="") | ParagraphBlock(text="\n"):
            return ""
        case ParagraphBlock(text):
            return f"{text.strip()}\n\n"
        case QuotationBlock(text="", cite=""):
            return ""
        case QuotationBlock(text, cite=""):
            # 인용구 마크다운 형식으로 변환
            quote_lines = text.strip().split('\n')
            formatted_quote = '\n'.join(f"> {line}" for line in quote_lines)
            return f"{formatted_quote}\n\n"
        case QuotationBlock(text, cite):
            # 출처가 있는 경우
            quote_lines = text.strip().split('\n')
            formatted_quote = '\n'.join(f"> {line}" for line in quote_lines)
            return f"{formatted_quote}\n>\n> — {cite}\n\n"
        case CodeBlock(code=""):
            return ""
        case CodeBlock(code, language=""):
            # 언어 정보 없는 코드 블록
            return f"```\n{code.strip()}\n```\n\n"
        case CodeBlock(code, language):
            # 언어 정보 있는 코드 블록
            return f"```{language}\n{code.strip()}\n```\n\n"
        case FileBlock(filename="", file_url=""):
            return ""
        case FileBlock(filename, file_url):
            # 마크다운 링크 형식으로 첨부파일 표시
            return f"📎 [{filename}]({file_url})\n\n"
        case HorizontalLineBlock():
            # 마크다운 수평선 (3가지 방식 모두 가능, 여기서는 --- 사용)
            return "---\n\n"
        # _block_as_markdown 함수의 match 문에 추가:
        case FormulaBlock(formula=""):
            return ""
        case FormulaBlock(formula, display_mode=True):
            # 블록 수식 (display mode) - $$ ... $$
            return f"$$\n{formula}\n$$\n\n"
        case FormulaBlock(formula, display_mode=False):
            # 인라인 수식 - $ ... $
            return f"${formula}$\n\n"
        case TableBlock(headers=[], rows=[]):
            return ""
        case TableBlock(headers, rows):
            # 마크다운 테이블 생성
            if not headers:
                return ""

            # 헤더 행
            header_line = "| " + " | ".join(headers) + " |"
            # 구분선
            separator_line = "| " + " | ".join(["---"] * len(headers)) + " |"

            # 데이터 행들
            data_lines = []
            for row in rows:
                # 헤더 개수와 맞추기 위해 부족한 셀은 빈 문자열로 채움
                padded_row = row + [""] * (len(headers) - len(row))
                # 헤더보다 많은 셀은 제거
                padded_row = padded_row[:len(headers)]
                data_lines.append("| " + " | ".join(padded_row) + " |")

            # 전체 테이블 조합
            table = "\n".join([header_line, separator_line] + data_lines)
            return f"{table}\n\n"
        case MaterialBlock(content=""):
            # 빈 Material 블록은 무시
            return ""
        case MaterialBlock(content):
            # Material 컨텐츠가 있으면 인용구 형태로 표시 (선택사항)
            # 또는 그냥 무시하려면 return "" 사용
            return f"> [Material] {content}\n\n"
        case ImageBlock(src=""):
            return ""
        case ImageBlock(src, alt):
            return f"![{alt}]({processed_image_src(src)})\n\n"
        case ImageGroupBlock([]):
            return ""
        case ImageGroupBlock(images):
            return (
                " ".join(
                    f"![{image.alt}]({processed_image_src(image.src)})"
                    for image in images
                )
                + "\n\n"
            )


def _front_matter_as_yaml(
    front_matter: dict[Any, Any],
    **context: Unpack[MarkdownRenderContext],
) -> str:
    if "image" in front_matter and "url" in front_matter["image"]:
        image_processor = _use_image_processor_with_fallback(**context)
        front_matter["image"]["url"] = image_processor(front_matter["image"]["url"])

    return (
        "---\n"
        + yaml.safe_dump(
            front_matter,
            default_flow_style=False,
            allow_unicode=True,
            default_style=None,
        )
        + "---\n\n"
    )


def _use_image_processor_with_fallback(**context: Unpack[MarkdownRenderContext]):
    if "image_context" not in context:
        default_context = with_default()
        assert "image_context" in default_context
        image_context = default_context["image_context"]
    else:
        image_context = context["image_context"]

    return use_image_processor(image_context)
