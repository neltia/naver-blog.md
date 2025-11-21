from dataclasses import dataclass


@dataclass
class SectionTitleBlock:
    text: str


@dataclass
class ParagraphBlock:
    text: str


@dataclass
class ImageBlock:
    src: str
    alt: str


@dataclass
class ImageGroupBlock:
    images: list[ImageBlock]


@dataclass
class QuotationBlock:
    text: str
    cite: str = ""


@dataclass
class CodeBlock:
    code: str
    language: str = ""


@dataclass
class FileBlock:
    filename: str
    file_url: str
    extension: str = ""


@dataclass
class HorizontalLineBlock:
    """수평선 블록 - 데이터 없이 구분선만 표시"""
    pass


@dataclass
class TableBlock:
    """테이블 블록"""
    headers: list[str]
    rows: list[list[str]]


@dataclass
class MaterialBlock:
    """Material 컴포넌트 (광고, 외부 링크 등)"""
    content: str = ""


@dataclass
class FormulaBlock:
    """수식 블록 (LaTeX 등)"""
    formula: str
    display_mode: bool = True  # True: 블록 수식, False: 인라인 수식


Block = (
    SectionTitleBlock
    | ParagraphBlock
    | ImageBlock
    | ImageGroupBlock
    | QuotationBlock
    | CodeBlock
    | FileBlock
    | HorizontalLineBlock
    | TableBlock
    | MaterialBlock
    | FormulaBlock
)
