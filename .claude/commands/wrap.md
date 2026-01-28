# Wrap Up Changes

작업 완료 후 프로젝트 문서를 현재 코드베이스 상태에 맞게 업데이트합니다.

## 문서 구조

이 프로젝트는 다음과 같은 문서 구조를 따릅니다:

- **README.md**: 사용자용 문서 (설치, 설정, 사용법)
- **CLAUDE.md**: AI용 컨텍스트 (아키텍처, 규약) - README.md를 @import로 참조

## 수행 작업

1. 현재 프로젝트의 디렉토리 구조를 분석합니다 (`src/` 하위 파일들)
2. README.md와 CLAUDE.md 파일을 읽습니다
3. 변경된 내용에 따라 문서를 업데이트합니다

## 업데이트 규칙

### README.md (사용자용)
**수정 대상:**
- Prerequisites (외부 의존성 변경 시)
- Setup (설치 명령어 변경 시)
- Environment Variables (환경변수 변경 시)
- Usage (실행 방법 변경 시)

**수정하지 않음:**
- Description (프로젝트 목적이 변경되지 않는 한)
- Apply Cronicle (배포 설정은 별도 관리)

### CLAUDE.md (AI용)
**수정 대상:**
- Architecture (디렉토리 구조, Flow, 모듈 책임)
- External Dependencies (외부 시스템 의존성)

**수정하지 않음:**
- Project Overview (프로젝트 목적이 변경되지 않는 한)
- Design Principles
- Python Conventions
- AI Interaction Guidelines

## 규칙

- 기존 문서의 형식과 톤을 유지합니다
- README.md는 영어로 작성합니다
- CLAUDE.md는 영어로 작성합니다 (한국어 섹션 제외)
- **중복 금지**: 두 문서에 같은 내용이 있으면 안 됩니다
  - 사용자 정보(설치, 환경변수 등)는 README.md에만
  - AI 컨텍스트(아키텍처, 규약)는 CLAUDE.md에만
