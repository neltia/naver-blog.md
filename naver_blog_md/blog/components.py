from bs4 import Tag

from naver_blog_md.markdown.models import (
    Block,
    CodeBlock,
    FileBlock,
    ImageBlock,
    HorizontalLineBlock,
    ImageGroupBlock,
    ParagraphBlock,
    SectionTitleBlock,
    QuotationBlock,
    TableBlock,
    MaterialBlock
)


def section_title_component(component: Tag) -> Block:
    return SectionTitleBlock(_text_from_tag(component))


def text_component(component: Tag) -> list[Block]:
    return [
        ParagraphBlock(text=_text_from_tag(tag))
        for tag in component.select(".se-text-paragraph")
    ]


def code_component(component: Tag) -> Block:
    """코드 블록 컴포넌트 처리"""
    code_view = component.select_one(".__se_code_view")

    if not code_view:
        return CodeBlock(code="", language="")

    # 언어 정보 추출 (class에서 language-xxx 형태로 되어 있음)
    language = ""
    if code_view.get("class"):
        for cls in code_view.get("class", []):
            if cls.startswith("language-"):
                language = cls.replace("language-", "")
                break

    # 코드 내용 추출 - 토큰별로 텍스트를 추출하여 재구성
    code_text = code_view.get_text()

    return CodeBlock(code=code_text, language=language)


def file_component(component: Tag) -> Block:
    """첨부파일 컴포넌트 처리"""
    # 파일명 추출
    filename_elem = component.select_one(".se-file-name")
    extension_elem = component.select_one(".se-file-extension")

    filename = ""
    if filename_elem:
        filename = _text_from_tag(filename_elem)

    extension = ""
    if extension_elem:
        extension = _text_from_tag(extension_elem)

    # 전체 파일명 (확장자 포함)
    full_filename = f"{filename}{extension}" if filename and extension else (filename or "unknown")

    # 다운로드 링크 추출
    download_link = component.select_one("a.se-file-save-button")
    file_url = ""
    if download_link and download_link.get("href"):
        file_url = str(download_link["href"])

    return FileBlock(
        filename=full_filename,
        file_url=file_url,
        extension=extension.lstrip('.') if extension else ""
    )


def horizontal_line_component(component: Tag) -> Block:
    """수평선 컴포넌트 처리"""
    return HorizontalLineBlock()


def material_component(component: Tag) -> Block:
    """Material 컴포넌트 처리 - 보통 광고나 외부 링크 등"""
    # Material 컴포넌트는 주로 광고나 외부 컨텐츠이므로
    # 텍스트를 추출하거나 무시할 수 있음
    content = _text_from_tag(component)
    return MaterialBlock(content=content)


def table_component(component: Tag) -> Block:
    """테이블 컴포넌트 처리"""
    table = component.select_one("table.se-table-content")

    if not table:
        return TableBlock(headers=[], rows=[])

    # 모든 행 가져오기
    all_rows = table.select("tr.se-tr")

    if not all_rows:
        return TableBlock(headers=[], rows=[])

    # 첫 번째 행을 헤더로 간주
    headers = []
    first_row = all_rows[0]
    header_cells = first_row.select("td.se-cell")

    for cell in header_cells:
        # 셀 내부의 텍스트 추출
        text_elem = cell.select_one(".se-module-text")
        if text_elem:
            headers.append(_text_from_tag(text_elem))
        else:
            headers.append(_text_from_tag(cell))

    # 나머지 행을 데이터로 처리
    rows = []
    for row in all_rows[1:]:
        cells = row.select("td.se-cell")
        row_data = []

        for cell in cells:
            text_elem = cell.select_one(".se-module-text")
            if text_elem:
                row_data.append(_text_from_tag(text_elem))
            else:
                row_data.append(_text_from_tag(cell))

        if row_data:  # 빈 행이 아닌 경우만 추가
            rows.append(row_data)

    return TableBlock(headers=headers, rows=rows)


def image_group_component(component: Tag) -> Block:
    images = component.select("img")
    caption = component.select_one(".se-caption")

    return ImageGroupBlock(
        images=[
            ImageBlock(
                src=str(img["src"]),
                alt=_text_from_tag(caption) if caption is not None else "",
            )
            for img in images
        ]
    )


def image_strip_component(component: Tag) -> Block:
    """이미지 스트립 컴포넌트 처리 - 나란히 배치된 여러 이미지"""
    # 각 이미지 모듈의 캡션 찾기 (있다면)
    image_modules = component.select(".se-module-image")

    image_blocks = []
    for img_module in image_modules:
        img = img_module.select_one("img")
        if not img:
            continue

        # 각 이미지의 캡션 찾기
        caption = img_module.select_one(".se-caption")
        alt_text = _text_from_tag(caption) if caption else ""

        image_blocks.append(
            ImageBlock(
                src=str(img["src"]),
                alt=alt_text,
            )
        )

    return ImageGroupBlock(images=image_blocks)


def quotation_component(component: Tag) -> Block:
    """인용구 컴포넌트 처리"""
    quote_elem = component.select_one(".se-quote")
    cite_elem = component.select_one(".se-cite")

    quote_text = _text_from_tag(quote_elem) if quote_elem else ""
    cite_text = _text_from_tag(cite_elem) if cite_elem else ""

    return QuotationBlock(text=quote_text, cite=cite_text)


def image_component(component: Tag) -> Block:
    img = component.select_one("img")
    video = component.select_one("video")

    match img, video:
        case Tag(), None:
            src = str(img["src"])
        case None, Tag():
            src = str(video["src"])
        case _:
            assert False, "Image and video are mutually exclusive"

    caption = component.select_one(".se-caption")

    return ImageBlock(
        src=src,
        alt=_text_from_tag(caption) if caption is not None else "",
    )


def _text_from_tag(tag: Tag):
    return tag.get_text(strip=True).strip()
