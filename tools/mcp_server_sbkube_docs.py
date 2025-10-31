#!/usr/bin/env python3
"""
SBKube Documentation MCP Server

Context7 스타일의 문서 조회를 제공하는 로컬 MCP 서버입니다.

Usage:
    python tools/mcp_server_sbkube_docs.py
"""

import asyncio
import json
from pathlib import Path
from typing import List, Optional

try:
    from mcp.server import Server
    from mcp.types import Resource, TextContent
except ImportError:
    print("Error: MCP SDK not installed. Install with: uv pip install mcp")
    exit(1)


# 프로젝트 루트 디렉토리
PROJECT_ROOT = Path(__file__).parent.parent
DOCS_ROOT = PROJECT_ROOT / "docs"


class SBKubeDocsServer:
    """SBKube 문서 서버"""

    def __init__(self):
        self.server = Server("sbkube-docs")
        self._register_handlers()

    def _register_handlers(self):
        """MCP 핸들러 등록"""

        @self.server.list_resources()
        async def list_resources() -> List[Resource]:
            """사용 가능한 문서 목록 반환"""
            resources = []

            # 모든 Markdown 파일 검색
            for md_file in DOCS_ROOT.rglob("*.md"):
                relative_path = md_file.relative_to(DOCS_ROOT)

                # 카테고리 추출 (첫 번째 디렉토리)
                category = relative_path.parts[0] if len(relative_path.parts) > 1 else "root"

                resources.append(
                    Resource(
                        uri=f"sbkube://docs/{relative_path}",
                        name=md_file.stem,
                        description=f"Category: {category}",
                        mimeType="text/markdown",
                    )
                )

            return resources

        @self.server.read_resource()
        async def read_resource(uri: str) -> str:
            """문서 내용 반환"""
            if not uri.startswith("sbkube://docs/"):
                raise ValueError(f"Invalid URI: {uri}")

            # URI에서 파일 경로 추출
            relative_path = uri.removeprefix("sbkube://docs/")
            file_path = DOCS_ROOT / relative_path

            if not file_path.exists():
                raise FileNotFoundError(f"Document not found: {relative_path}")

            content = file_path.read_text(encoding="utf-8")

            # 메타데이터 추가
            metadata = {
                "source": str(file_path.relative_to(PROJECT_ROOT)),
                "category": relative_path.parts[0] if len(relative_path.parts) > 1 else "root",
                "size": len(content),
            }

            return json.dumps({
                "content": content,
                "metadata": metadata,
            })

        @self.server.call_tool()
        async def search_docs(query: str, category: Optional[str] = None) -> str:
            """문서 검색 (Context7 스타일)

            Args:
                query: 검색 키워드
                category: 카테고리 필터 (예: "00-product", "02-features")
            """
            results = []

            for md_file in DOCS_ROOT.rglob("*.md"):
                relative_path = md_file.relative_to(DOCS_ROOT)

                # 카테고리 필터링
                if category and not str(relative_path).startswith(category):
                    continue

                # 파일 내용 검색
                content = md_file.read_text(encoding="utf-8")
                if query.lower() in content.lower():
                    # 관련 라인 추출 (컨텍스트 포함)
                    lines = content.split("\n")
                    matching_lines = []
                    for i, line in enumerate(lines):
                        if query.lower() in line.lower():
                            # 전후 2줄 포함
                            start = max(0, i - 2)
                            end = min(len(lines), i + 3)
                            context = "\n".join(lines[start:end])
                            matching_lines.append(f"Line {i+1}:\n{context}")

                    results.append({
                        "file": str(relative_path),
                        "uri": f"sbkube://docs/{relative_path}",
                        "matches": matching_lines[:3],  # 최대 3개 매칭
                    })

            return json.dumps({
                "query": query,
                "total_results": len(results),
                "results": results[:10],  # 상위 10개만 반환
            })

    async def run(self):
        """서버 실행"""
        from mcp.server.stdio import stdio_server

        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                self.server.create_initialization_options(),
            )


def main():
    """메인 함수"""
    server = SBKubeDocsServer()
    asyncio.run(server.run())


if __name__ == "__main__":
    main()
