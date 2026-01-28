# Wrap Up Changes

작업 완료 후 프로젝트 문서와 권한 설정을 현재 상태에 맞게 업데이트합니다.

## 문서 구조

이 프로젝트는 다음과 같은 문서 구조를 따릅니다:

- **README.md**: 사용자용 문서 (설치, 설정, 사용법)
- **CLAUDE.md**: AI용 컨텍스트 (아키텍처, 규약) - README.md를 @import로 참조
- **.claude/settings.local.json**: Claude Code 권한 설정 (자동 승인 규칙)

## 수행 작업

### 1. 문서 업데이트
1. 현재 프로젝트의 디렉토리 구조를 분석합니다 (`src/` 하위 파일들)
2. README.md와 CLAUDE.md 파일을 읽습니다
3. 변경된 내용에 따라 문서를 업데이트합니다

### 2. 권한 설정 동기화
현재 세션에서 사용자가 승인한 권한들을 `.claude/settings.local.json`에 기록하여, 이후 동일한 작업 시 반복적인 승인 요청을 방지합니다.

**수행 절차:**
1. `.claude/settings.local.json` 파일을 읽습니다
2. 현재 세션에서 승인된 도구/명령어 중 아직 등록되지 않은 것을 확인합니다
3. 누락된 권한을 `permissions.allow` 배열에 추가합니다

**권한 패턴 예시:**
```json
{
  "permissions": {
    "allow": [
      "Bash(*)",                              // 모든 Bash 명령어
      "Bash(git:*)",                          // git으로 시작하는 명령어
      "Bash(make:*)",                         // make로 시작하는 명령어
      "WebFetch(domain:github.com)",          // 특정 도메인
      "mcp__server-name__tool-name"           // MCP 도구
    ]
  }
}
```

**참고:** 보안상 민감한 명령어(rm -rf, sudo 등)는 개별 승인을 유지하는 것이 좋습니다.

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
